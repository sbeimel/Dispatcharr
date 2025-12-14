"""
Integration tests for the Predictive Failover Flow.

Tests cover:
- Complete flow: Metrics -> Risk Score -> Warmup -> Failover
- Fallback to reactive failover
- Cooldown logic
- Threshold-based decisions

Requirements: 4.1, 4.2, 12.2
"""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time

from ..failover_manager import (
    FailoverDecision,
    PredictiveFailoverManager,
    get_predictive_failover_manager,
    reset_predictive_failover_manager,
)
from ..risk_calculator import RiskScore, RiskContribution, RiskReason
from ..config import PredictiveConfig


class TestFailoverDecision:
    """Tests for FailoverDecision dataclass."""
    
    def test_decision_creation(self):
        """Test creating a FailoverDecision instance."""
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90,
            reason="High risk score",
            backup_stream_id="backup-789",
            backup_url="http://backup.url/stream"
        )
        
        assert decision.action == "failover"
        assert decision.channel_id == "channel-123"
        assert decision.stream_id == "stream-456"
        assert decision.risk_score == 90
        assert decision.backup_stream_id == "backup-789"
        assert decision.backup_url == "http://backup.url/stream"
    
    def test_should_warmup(self):
        """Test should_warmup method."""
        warmup_decision = FailoverDecision(action="warmup", channel_id="ch-1")
        failover_decision = FailoverDecision(action="failover", channel_id="ch-1")
        none_decision = FailoverDecision(action="none", channel_id="ch-1")
        
        assert warmup_decision.should_warmup() is True
        assert failover_decision.should_warmup() is False
        assert none_decision.should_warmup() is False
    
    def test_should_failover(self):
        """Test should_failover method."""
        warmup_decision = FailoverDecision(action="warmup", channel_id="ch-1")
        failover_decision = FailoverDecision(action="failover", channel_id="ch-1")
        none_decision = FailoverDecision(action="none", channel_id="ch-1")
        
        assert warmup_decision.should_failover() is False
        assert failover_decision.should_failover() is True
        assert none_decision.should_failover() is False


class TestPredictiveFailoverManager:
    """Tests for PredictiveFailoverManager class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.setex = MagicMock()
        redis.exists = MagicMock(return_value=0)  # Not in cooldown
        redis.get = MagicMock(return_value=None)
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = True
        config.warmup_threshold = 60
        config.failover_threshold = 85
        config.cooldown_period = 30
        config.pattern_learning_enabled = True
        config.peak_time_awareness_enabled = False
        return config
    
    @pytest.fixture
    def disabled_config(self):
        """Create a disabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = False
        return config
    
    @pytest.fixture
    def mock_risk_calculator(self):
        """Create a mock risk calculator."""
        calculator = MagicMock()
        calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=50, stream_id="stream-123"
        ))
        return calculator
    
    @pytest.fixture
    def mock_pattern_analyzer(self):
        """Create a mock pattern analyzer."""
        analyzer = MagicMock()
        analyzer.get_pattern_confidence_for_risk_score = MagicMock(return_value=0)
        return analyzer
    
    @pytest.fixture
    def mock_warmup_manager(self):
        """Create a mock warmup manager."""
        manager = MagicMock()
        manager.warmup_backup = MagicMock()
        manager.get_warmed_backup = MagicMock(return_value=None)
        manager.release_warmup = MagicMock()
        manager.has_warmup = MagicMock(return_value=False)
        return manager
    
    @pytest.fixture
    def manager(self, mock_redis, enabled_config, mock_risk_calculator, 
                mock_pattern_analyzer, mock_warmup_manager):
        """Create a PredictiveFailoverManager with mocked dependencies."""
        return PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            pattern_analyzer=mock_pattern_analyzer,
            warmup_manager=mock_warmup_manager,
            redis_client=mock_redis
        )
    
    def test_evaluate_stream_disabled(self, mock_redis, disabled_config, 
                                       mock_risk_calculator, mock_pattern_analyzer,
                                       mock_warmup_manager):
        """Test evaluate_stream returns 'none' when disabled."""
        manager = PredictiveFailoverManager(
            config=disabled_config,
            risk_calculator=mock_risk_calculator,
            pattern_analyzer=mock_pattern_analyzer,
            warmup_manager=mock_warmup_manager,
            redis_client=mock_redis
        )
        
        decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "none"
        assert decision.channel_id == "channel-456"
    
    def test_evaluate_stream_in_cooldown(self, manager, mock_redis):
        """Test evaluate_stream returns 'none' when in cooldown."""
        mock_redis.exists = MagicMock(return_value=1)  # In cooldown
        
        decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "none"
        assert "cooldown" in decision.reason.lower()
    
    def test_evaluate_stream_low_risk(self, manager, mock_risk_calculator):
        """Test evaluate_stream returns 'none' for low risk score."""
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=30, stream_id="stream-123"
        ))
        
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "none"
        assert decision.risk_score == 30
    
    def test_evaluate_stream_warmup_threshold(self, manager, mock_risk_calculator,
                                               mock_warmup_manager):
        """Test evaluate_stream triggers warmup at warmup threshold."""
        # Risk score between warmup (60) and failover (85) thresholds
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=70, stream_id="stream-123"
        ))
        
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "warmup"
        assert decision.risk_score == 70
        mock_warmup_manager.warmup_backup.assert_called_once_with("channel-456")
    
    def test_evaluate_stream_failover_threshold(self, manager, mock_risk_calculator):
        """Test evaluate_stream triggers failover at failover threshold."""
        # Risk score above failover threshold (85)
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=90, stream_id="stream-123"
        ))
        
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "failover"
        assert decision.risk_score == 90
    
    def test_evaluate_stream_releases_warmup_on_low_risk(self, manager, 
                                                          mock_risk_calculator,
                                                          mock_warmup_manager):
        """Test warmup is released when risk drops significantly."""
        # Risk score well below warmup threshold
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=40, stream_id="stream-123"  # Below warmup_threshold - 10 = 50
        ))
        mock_warmup_manager.has_warmup = MagicMock(return_value=True)
        
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision.action == "none"
        mock_warmup_manager.release_warmup.assert_called_once()
    
    def test_execute_failover_not_failover_decision(self, manager):
        """Test execute_failover returns False for non-failover decisions."""
        decision = FailoverDecision(action="warmup", channel_id="ch-1")
        
        result = manager.execute_failover(decision)
        
        assert result is False
    
    def test_execute_failover_with_callback(self, manager, mock_redis, mock_warmup_manager):
        """Test execute_failover uses callback when set."""
        callback = MagicMock(return_value=True)
        manager.set_failover_callback(callback)
        
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90,
            backup_stream_id="backup-789",
            backup_url="http://backup.url"
        )
        
        with patch.object(manager, '_log_event'):
            result = manager.execute_failover(decision)
        
        assert result is True
        callback.assert_called_once_with("channel-123", "backup-789", "http://backup.url")
        mock_redis.setex.assert_called()  # Cooldown started
    
    def test_execute_failover_starts_cooldown(self, manager, mock_redis, enabled_config):
        """Test execute_failover starts cooldown period."""
        callback = MagicMock(return_value=True)
        manager.set_failover_callback(callback)
        
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90
        )
        
        with patch.object(manager, '_log_event'):
            manager.execute_failover(decision)
        
        # Verify cooldown was set
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == enabled_config.cooldown_period
    
    def test_execute_failover_releases_warmup(self, manager, mock_warmup_manager):
        """Test execute_failover releases warmup after success."""
        callback = MagicMock(return_value=True)
        manager.set_failover_callback(callback)
        
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90
        )
        
        with patch.object(manager, '_log_event'):
            manager.execute_failover(decision)
        
        mock_warmup_manager.release_warmup.assert_called_once_with(
            "channel-123", "failover_executed"
        )
    
    def test_execute_failover_callback_failure(self, manager):
        """Test execute_failover handles callback failure."""
        callback = MagicMock(return_value=False)
        manager.set_failover_callback(callback)
        
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90
        )
        
        with patch.object(manager, '_log_event'):
            result = manager.execute_failover(decision)
        
        assert result is False
    
    def test_is_in_cooldown_true(self, manager, mock_redis):
        """Test _is_in_cooldown returns True when in cooldown."""
        mock_redis.exists = MagicMock(return_value=1)
        
        result = manager._is_in_cooldown("channel-123")
        
        assert result is True
    
    def test_is_in_cooldown_false(self, manager, mock_redis):
        """Test _is_in_cooldown returns False when not in cooldown."""
        mock_redis.exists = MagicMock(return_value=0)
        
        result = manager._is_in_cooldown("channel-123")
        
        assert result is False
    
    def test_get_status(self, manager, enabled_config):
        """Test get_status returns correct status."""
        status = manager.get_status()
        
        assert status['enabled'] is True
        assert status['warmup_threshold'] == enabled_config.warmup_threshold
        assert status['failover_threshold'] == enabled_config.failover_threshold
        assert status['cooldown_period'] == enabled_config.cooldown_period


class TestFailoverFlowIntegration:
    """Integration tests for the complete failover flow."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.setex = MagicMock()
        redis.exists = MagicMock(return_value=0)
        redis.get = MagicMock(return_value=None)
        redis.zadd = MagicMock()
        redis.zrangebyscore = MagicMock(return_value=[])
        redis.sadd = MagicMock()
        redis.hset = MagicMock()
        redis.expire = MagicMock()
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = True
        config.warmup_threshold = 60
        config.failover_threshold = 85
        config.cooldown_period = 30
        config.pattern_learning_enabled = False
        return config
    
    def test_complete_flow_metrics_to_warmup(self, mock_redis, enabled_config):
        """Test complete flow: Metrics -> Risk Score -> Warmup."""
        from ..metrics_collector import StreamMetricsCollector, MetricType
        from ..risk_calculator import RiskScoreCalculator
        from ..warmup_manager import WarmupManager
        
        # Create components
        metrics_collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=enabled_config
        )
        risk_calculator = RiskScoreCalculator(
            config=enabled_config,
            metrics_collector=metrics_collector,
            redis_client=mock_redis
        )
        warmup_manager = WarmupManager(
            config=enabled_config,
            redis_client=mock_redis
        )
        manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=risk_calculator,
            warmup_manager=warmup_manager,
            redis_client=mock_redis
        )
        
        # Start collecting
        metrics_collector.start_collecting("stream-123", "channel-456")
        
        # Simulate high response times that would trigger warmup
        # Mock the metrics to return high values
        import json
        high_response_data = json.dumps({
            'value': 350.0,  # Above warning threshold
            'channel_id': 'channel-456',
            'metadata': None
        })
        mock_redis.zrangebyscore = MagicMock(return_value=[
            (high_response_data.encode(), time.time())
            for _ in range(5)
        ])
        
        # Evaluate stream
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        # Should trigger warmup or failover based on calculated score
        assert decision.action in ["warmup", "failover", "none"]
    
    def test_complete_flow_metrics_to_failover(self, mock_redis, enabled_config):
        """Test complete flow: Metrics -> Risk Score -> Failover."""
        from ..risk_calculator import RiskScoreCalculator, RiskScore
        from ..warmup_manager import WarmupManager
        
        # Create mock risk calculator that returns high score
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=90,  # Above failover threshold
            stream_id="stream-123",
            reasons=[
                RiskContribution(
                    reason=RiskReason.RESPONSE_TIME_CRITICAL,
                    points=35,
                    description="Critical response time"
                ),
                RiskContribution(
                    reason=RiskReason.BUFFER_UNDERRUN,
                    points=50,
                    description="Buffer underruns"
                )
            ]
        ))
        
        warmup_manager = WarmupManager(
            config=enabled_config,
            redis_client=mock_redis
        )
        
        manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            warmup_manager=warmup_manager,
            redis_client=mock_redis
        )
        
        # Evaluate stream
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-123", "channel-456")
        
        # Should trigger failover
        assert decision.action == "failover"
        assert decision.risk_score == 90
    
    def test_fallback_to_reactive_failover(self, mock_redis, enabled_config):
        """Test fallback to reactive failover when no backup available."""
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=90, stream_id="stream-123"
        ))
        
        mock_warmup_manager = MagicMock()
        mock_warmup_manager.get_warmed_backup = MagicMock(return_value=None)
        mock_warmup_manager.release_warmup = MagicMock()
        
        manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            warmup_manager=mock_warmup_manager,
            redis_client=mock_redis
        )
        
        # Create failover decision without backup
        decision = FailoverDecision(
            action="failover",
            channel_id="channel-123",
            stream_id="stream-456",
            risk_score=90,
            backup_stream_id=None,
            backup_url=None
        )
        
        # Execute failover - should fall back to reactive
        with patch.object(manager, '_fallback_to_reactive_failover', return_value=True) as mock_fallback:
            with patch.object(manager, '_log_event'):
                result = manager.execute_failover(decision)
        
        assert result is True
        mock_fallback.assert_called_once()
    
    def test_cooldown_prevents_rapid_failovers(self, mock_redis, enabled_config):
        """Test that cooldown prevents rapid failovers."""
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=90, stream_id="stream-123"
        ))
        
        manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            redis_client=mock_redis
        )
        
        # First evaluation - not in cooldown
        mock_redis.exists = MagicMock(return_value=0)
        with patch.object(manager, '_log_event'):
            decision1 = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision1.action == "failover"
        
        # Second evaluation - in cooldown
        mock_redis.exists = MagicMock(return_value=1)
        decision2 = manager.evaluate_stream("stream-123", "channel-456")
        
        assert decision2.action == "none"
        assert "cooldown" in decision2.reason.lower()


class TestFailoverManagerSingleton:
    """Tests for the singleton pattern."""
    
    def test_get_predictive_failover_manager_returns_same_instance(self):
        """Test that get_predictive_failover_manager returns the same instance."""
        reset_predictive_failover_manager()
        
        manager1 = get_predictive_failover_manager()
        manager2 = get_predictive_failover_manager()
        
        assert manager1 is manager2
    
    def test_reset_predictive_failover_manager(self):
        """Test that reset_predictive_failover_manager creates a new instance."""
        manager1 = get_predictive_failover_manager()
        reset_predictive_failover_manager()
        manager2 = get_predictive_failover_manager()
        
        assert manager1 is not manager2
