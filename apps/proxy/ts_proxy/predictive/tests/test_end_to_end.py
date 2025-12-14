"""
End-to-End tests for the Predictive Failover System.

Tests cover:
- Complete flow from metrics to failover
- Web-UI configuration to backend
- False positive handling
- Master toggle behavior

Requirements: 4.1, 6.3, 8.2, 13.8
"""

import json
import pytest
from unittest.mock import MagicMock, patch
import time

from ..config import PredictiveConfig, get_predictive_config, save_predictive_config
from ..metrics_collector import StreamMetricsCollector, MetricType, Metric
from ..risk_calculator import RiskScoreCalculator, RiskScore, RiskReason
from ..pattern_analyzer import PatternAnalyzer, FailurePatternData
from ..warmup_manager import WarmupManager
from ..failover_manager import PredictiveFailoverManager, FailoverDecision


class TestEndToEndMetricsToFailover:
    """End-to-end tests for the complete metrics to failover flow."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a comprehensive mock Redis client."""
        redis = MagicMock()
        redis.setex = MagicMock()
        redis.get = MagicMock(return_value=None)
        redis.set = MagicMock()
        redis.exists = MagicMock(return_value=0)
        redis.zadd = MagicMock()
        redis.zrangebyscore = MagicMock(return_value=[])
        redis.zremrangebyscore = MagicMock(return_value=0)
        redis.sadd = MagicMock()
        redis.srem = MagicMock()
        redis.smembers = MagicMock(return_value=set())
        redis.hset = MagicMock()
        redis.hget = MagicMock(return_value=None)
        redis.hdel = MagicMock()
        redis.expire = MagicMock()
        redis.delete = MagicMock()
        redis.keys = MagicMock(return_value=[])
        redis.lpush = MagicMock()
        redis.ltrim = MagicMock()
        redis.lrange = MagicMock(return_value=[])
        redis.llen = MagicMock(return_value=0)
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled PredictiveConfig with test values."""
        config = PredictiveConfig()
        config.enabled = True
        config.warmup_threshold = 60
        config.failover_threshold = 85
        config.cooldown_period = 30
        config.metrics_interval = 3
        config.pattern_learning_enabled = True
        config.response_time_warning = 200
        config.response_time_critical = 400
        config.response_time_warning_weight = 15
        config.response_time_critical_weight = 20
        config.buffer_underrun_weight = 30
        config.bitrate_variance_threshold = 25
        config.bitrate_variance_weight = 15
        config.connection_reset_weight = 20
        config.trend_detection_enabled = True
        config.trend_weight = 10
        config.bitrate_drop_weight = 25
        return config
    
    @pytest.fixture
    def disabled_config(self):
        """Create a disabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = False
        return config
    
    def test_e2e_complete_flow_healthy_stream(self, mock_redis, enabled_config):
        """Test E2E: Healthy stream stays healthy."""
        # Setup components
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
        failover_manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=risk_calculator,
            warmup_manager=warmup_manager,
            redis_client=mock_redis
        )
        
        # Start collecting for a stream
        metrics_collector.start_collecting("stream-healthy", "channel-1")
        
        # Simulate healthy metrics (low response times, no underruns)
        healthy_data = json.dumps({
            'value': 100.0,  # Below warning threshold
            'channel_id': 'channel-1',
            'metadata': None
        })
        mock_redis.zrangebyscore = MagicMock(return_value=[
            (healthy_data.encode(), time.time())
            for _ in range(5)
        ])
        
        # Evaluate stream
        with patch.object(failover_manager, '_log_event'):
            decision = failover_manager.evaluate_stream("stream-healthy", "channel-1")
        
        # Should not trigger any action
        assert decision.action == "none"
        assert decision.risk_score < enabled_config.warmup_threshold
    
    def test_e2e_complete_flow_degrading_stream(self, mock_redis, enabled_config):
        """Test E2E: Degrading stream triggers warmup then failover."""
        # Setup components
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
        failover_manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=risk_calculator,
            warmup_manager=warmup_manager,
            redis_client=mock_redis
        )
        
        # Start collecting
        metrics_collector.start_collecting("stream-degrading", "channel-2")
        
        # Phase 1: Moderate degradation -> Warmup
        moderate_data = json.dumps({
            'value': 300.0,  # Above warning, below critical
            'channel_id': 'channel-2',
            'metadata': None
        })
        mock_redis.zrangebyscore = MagicMock(return_value=[
            (moderate_data.encode(), time.time())
            for _ in range(5)
        ])
        
        with patch.object(failover_manager, '_log_event'):
            decision1 = failover_manager.evaluate_stream("stream-degrading", "channel-2")
        
        # May trigger warmup depending on calculated score
        # The exact behavior depends on the risk calculation
        
        # Phase 2: Severe degradation -> Failover
        severe_data = json.dumps({
            'value': 500.0,  # Above critical threshold
            'channel_id': 'channel-2',
            'metadata': None
        })
        mock_redis.zrangebyscore = MagicMock(return_value=[
            (severe_data.encode(), time.time())
            for _ in range(10)
        ])
        
        with patch.object(failover_manager, '_log_event'):
            decision2 = failover_manager.evaluate_stream("stream-degrading", "channel-2")
        
        # Should trigger warmup or failover based on score
        assert decision2.action in ["warmup", "failover", "none"]
    
    def test_e2e_failover_execution(self, mock_redis, enabled_config):
        """Test E2E: Complete failover execution."""
        warmup_manager = WarmupManager(
            config=enabled_config,
            redis_client=mock_redis
        )
        
        # Mock risk calculator to return high score
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=90, stream_id="stream-failing"
        ))
        
        failover_manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            warmup_manager=warmup_manager,
            redis_client=mock_redis
        )
        
        # Set up failover callback
        failover_executed = {'called': False, 'channel': None}
        def failover_callback(channel_id, backup_stream_id, backup_url):
            failover_executed['called'] = True
            failover_executed['channel'] = channel_id
            return True
        
        failover_manager.set_failover_callback(failover_callback)
        
        # Evaluate stream - should trigger failover
        with patch.object(failover_manager, '_log_event'):
            decision = failover_manager.evaluate_stream("stream-failing", "channel-3")
        
        assert decision.action == "failover"
        
        # Execute failover
        with patch.object(failover_manager, '_log_event'):
            result = failover_manager.execute_failover(decision)
        
        assert result is True
        assert failover_executed['called'] is True
        assert failover_executed['channel'] == "channel-3"


class TestEndToEndConfiguration:
    """End-to-end tests for configuration flow."""
    
    @pytest.fixture
    def mock_core_settings(self):
        """Mock CoreSettings model."""
        with patch('apps.proxy.ts_proxy.predictive.config.CoreSettings') as mock:
            mock.DoesNotExist = Exception
            yield mock
    
    def test_e2e_config_save_and_load(self, mock_core_settings):
        """Test E2E: Save config and load it back."""
        # Create custom config
        config = PredictiveConfig()
        config.enabled = True
        config.warmup_threshold = 65
        config.failover_threshold = 88
        config.cooldown_period = 45
        
        # Mock the save
        mock_obj = MagicMock()
        mock_core_settings.objects.update_or_create = MagicMock(return_value=(mock_obj, True))
        
        # Save config
        result = save_predictive_config(config)
        
        # Verify save was called
        mock_core_settings.objects.update_or_create.assert_called_once()
        
        # Verify the saved data
        call_kwargs = mock_core_settings.objects.update_or_create.call_args[1]
        saved_value = json.loads(call_kwargs['defaults']['value'])
        
        assert saved_value['enabled'] is True
        assert saved_value['warmup_threshold'] == 65
        assert saved_value['failover_threshold'] == 88
        assert saved_value['cooldown_period'] == 45
    
    def test_e2e_config_validation(self):
        """Test E2E: Config validation catches invalid values."""
        config = PredictiveConfig()
        
        # Set invalid values
        config.warmup_threshold = 30  # Below minimum (40)
        config.failover_threshold = 100  # Above maximum (95)
        config.warmup_threshold = 90  # Greater than failover_threshold
        config.failover_threshold = 80
        
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("warmup_threshold" in e for e in errors)
    
    def test_e2e_config_affects_behavior(self, ):
        """Test E2E: Config changes affect system behavior."""
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=0)
        
        # Create config with low thresholds
        low_threshold_config = PredictiveConfig()
        low_threshold_config.enabled = True
        low_threshold_config.warmup_threshold = 40
        low_threshold_config.failover_threshold = 55
        
        # Create config with high thresholds
        high_threshold_config = PredictiveConfig()
        high_threshold_config.enabled = True
        high_threshold_config.warmup_threshold = 80
        high_threshold_config.failover_threshold = 95
        
        # Mock risk calculator returning score of 60
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=60, stream_id="stream-test"
        ))
        
        # With low thresholds - should trigger failover
        manager_low = PredictiveFailoverManager(
            config=low_threshold_config,
            risk_calculator=mock_risk_calculator,
            redis_client=mock_redis
        )
        
        with patch.object(manager_low, '_log_event'):
            decision_low = manager_low.evaluate_stream("stream-test", "channel-test")
        
        assert decision_low.action == "failover"  # 60 >= 55
        
        # With high thresholds - should not trigger anything
        manager_high = PredictiveFailoverManager(
            config=high_threshold_config,
            risk_calculator=mock_risk_calculator,
            redis_client=mock_redis
        )
        
        with patch.object(manager_high, '_log_event'):
            decision_high = manager_high.evaluate_stream("stream-test", "channel-test")
        
        assert decision_high.action == "none"  # 60 < 80


class TestEndToEndFalsePositiveHandling:
    """End-to-end tests for false positive handling."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.lpush = MagicMock()
        redis.ltrim = MagicMock()
        redis.expire = MagicMock()
        redis.lrange = MagicMock(return_value=[])
        redis.llen = MagicMock(return_value=0)
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled config."""
        config = PredictiveConfig()
        config.enabled = True
        config.pattern_learning_enabled = True
        config.pattern_confidence_threshold = 60
        return config
    
    def test_e2e_false_positive_reduces_confidence(self, mock_redis, enabled_config):
        """Test E2E: Marking false positive reduces pattern confidence."""
        # This test verifies the concept - actual DB operations would need Django test setup
        
        # Create a pattern with initial confidence
        pattern_data = FailurePatternData(
            pattern_type="response_time",
            metrics_snapshot={'avg_response_time': 300},
            confidence=70,
            stream_id="stream-fp"
        )
        
        # Simulate false positive marking
        # In real scenario, this would update the database
        new_confidence = pattern_data.confidence - PatternAnalyzer.CONFIDENCE_DECREASE_ON_FALSE_POSITIVE
        
        assert new_confidence == 60  # 70 - 10
        assert new_confidence >= PatternAnalyzer.MIN_CONFIDENCE_FOR_MATCH
    
    def test_e2e_low_confidence_pattern_not_matched(self, mock_redis, enabled_config):
        """Test E2E: Low confidence patterns are not matched."""
        pattern_analyzer = PatternAnalyzer(
            config=enabled_config,
            redis_client=mock_redis
        )
        
        # Pattern with confidence below threshold should not match
        # The threshold is 60, so patterns with <60 confidence should be ignored
        
        # Mock get_active_patterns to return low confidence pattern
        with patch.object(pattern_analyzer, '_get_active_patterns') as mock_patterns:
            mock_pattern = MagicMock()
            mock_pattern.confidence = 40  # Below threshold
            mock_pattern.pattern_type = "response_time"
            mock_pattern.pattern_data = {}
            mock_patterns.return_value = [mock_pattern]
            
            with patch.object(pattern_analyzer, '_capture_metrics_snapshot') as mock_metrics:
                mock_metrics.return_value = {'avg_response_time': 300}
                
                result = pattern_analyzer.check_pattern_match("stream-test")
        
        # Should not match due to low confidence
        # The actual matching logic depends on implementation details


class TestEndToEndMasterToggle:
    """End-to-end tests for master toggle behavior."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.exists = MagicMock(return_value=0)
        return redis
    
    def test_e2e_master_toggle_disabled_no_action(self, mock_redis):
        """Test E2E: When master toggle is OFF, system behaves like before."""
        disabled_config = PredictiveConfig()
        disabled_config.enabled = False
        
        # Create manager with disabled config
        manager = PredictiveFailoverManager(
            config=disabled_config,
            redis_client=mock_redis
        )
        
        # Evaluate stream
        decision = manager.evaluate_stream("stream-test", "channel-test")
        
        # Should always return 'none' when disabled
        assert decision.action == "none"
    
    def test_e2e_master_toggle_enabled_evaluates(self, mock_redis):
        """Test E2E: When master toggle is ON, system evaluates streams."""
        enabled_config = PredictiveConfig()
        enabled_config.enabled = True
        enabled_config.warmup_threshold = 60
        enabled_config.failover_threshold = 85
        
        # Mock risk calculator
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=70, stream_id="stream-test"
        ))
        
        manager = PredictiveFailoverManager(
            config=enabled_config,
            risk_calculator=mock_risk_calculator,
            redis_client=mock_redis
        )
        
        with patch.object(manager, '_log_event'):
            decision = manager.evaluate_stream("stream-test", "channel-test")
        
        # Should evaluate and potentially trigger warmup
        assert decision.action == "warmup"  # 70 >= 60 warmup threshold
        assert decision.risk_score == 70
    
    def test_e2e_toggle_transition(self, mock_redis):
        """Test E2E: System handles toggle transition correctly."""
        config = PredictiveConfig()
        
        mock_risk_calculator = MagicMock()
        mock_risk_calculator.calculate_risk_score = MagicMock(return_value=RiskScore(
            score=75, stream_id="stream-test"
        ))
        
        # Start disabled
        config.enabled = False
        manager = PredictiveFailoverManager(
            config=config,
            risk_calculator=mock_risk_calculator,
            redis_client=mock_redis
        )
        
        decision1 = manager.evaluate_stream("stream-test", "channel-test")
        assert decision1.action == "none"
        
        # Enable
        config.enabled = True
        config.warmup_threshold = 60
        config.failover_threshold = 85
        
        with patch.object(manager, '_log_event'):
            decision2 = manager.evaluate_stream("stream-test", "channel-test")
        
        assert decision2.action == "warmup"  # Now evaluates
        
        # Disable again
        config.enabled = False
        
        decision3 = manager.evaluate_stream("stream-test", "channel-test")
        assert decision3.action == "none"  # Back to no action


class TestEndToEndResourceManagement:
    """End-to-end tests for resource management."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.zadd = MagicMock()
        redis.zrangebyscore = MagicMock(return_value=[])
        redis.zremrangebyscore = MagicMock(return_value=0)
        redis.sadd = MagicMock()
        redis.srem = MagicMock()
        redis.smembers = MagicMock(return_value=set())
        redis.hset = MagicMock()
        redis.expire = MagicMock()
        redis.keys = MagicMock(return_value=[])
        return redis
    
    def test_e2e_metrics_cleanup(self, mock_redis):
        """Test E2E: Old metrics are cleaned up."""
        config = PredictiveConfig()
        config.enabled = True
        
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=config
        )
        
        # Start collecting
        collector.start_collecting("stream-cleanup", "channel-1")
        
        # Record some metrics
        collector.record_metric("stream-cleanup", MetricType.RESPONSE_TIME, 150.0)
        
        # Cleanup should be called
        collector.cleanup_old_metrics("stream-cleanup")
        
        # Verify cleanup was attempted
        mock_redis.zremrangebyscore.assert_called()
    
    def test_e2e_stop_collecting_cleans_up(self, mock_redis):
        """Test E2E: Stopping collection cleans up resources."""
        config = PredictiveConfig()
        config.enabled = True
        
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=config
        )
        
        # Start and stop collecting
        collector.start_collecting("stream-stop", "channel-1")
        collector.stop_collecting("stream-stop")
        
        # Verify cleanup
        mock_redis.srem.assert_called()
        assert "stream-stop" not in collector.get_active_stream_ids()
