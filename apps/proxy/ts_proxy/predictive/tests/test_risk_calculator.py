"""
Unit tests for the Risk Score Calculator.

Tests cover:
- RiskScore dataclass creation and serialization
- RiskContribution dataclass
- Score calculation for various metric combinations
- Score capping (0-100)
- Configurable weights

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from ..risk_calculator import (
    RiskReason,
    RiskContribution,
    RiskScore,
    RiskScoreCalculator,
    get_risk_calculator,
    reset_risk_calculator,
)
from ..config import PredictiveConfig


class TestRiskReason:
    """Tests for RiskReason enum."""
    
    def test_risk_reason_values(self):
        """Test that all expected risk reasons exist."""
        assert RiskReason.RESPONSE_TIME_WARNING.value == "response_time_warning"
        assert RiskReason.RESPONSE_TIME_CRITICAL.value == "response_time_critical"
        assert RiskReason.BUFFER_UNDERRUN.value == "buffer_underrun"
        assert RiskReason.BITRATE_VARIANCE.value == "bitrate_variance"
        assert RiskReason.CONNECTION_RESETS.value == "connection_resets"
        assert RiskReason.PATTERN_MATCH.value == "pattern_match"
        assert RiskReason.RESPONSE_TIME_TREND.value == "response_time_trend"
        assert RiskReason.BITRATE_DROP.value == "bitrate_drop"
    
    def test_risk_reason_from_string(self):
        """Test creating RiskReason from string value."""
        assert RiskReason("response_time_warning") == RiskReason.RESPONSE_TIME_WARNING
        assert RiskReason("buffer_underrun") == RiskReason.BUFFER_UNDERRUN


class TestRiskContribution:
    """Tests for RiskContribution dataclass."""
    
    def test_contribution_creation(self):
        """Test creating a RiskContribution instance."""
        contrib = RiskContribution(
            reason=RiskReason.RESPONSE_TIME_WARNING,
            points=15,
            description="Response time exceeds warning threshold",
            metric_value=250.0,
            threshold=200.0
        )
        
        assert contrib.reason == RiskReason.RESPONSE_TIME_WARNING
        assert contrib.points == 15
        assert contrib.description == "Response time exceeds warning threshold"
        assert contrib.metric_value == 250.0
        assert contrib.threshold == 200.0
    
    def test_contribution_to_dict(self):
        """Test converting RiskContribution to dictionary."""
        contrib = RiskContribution(
            reason=RiskReason.BUFFER_UNDERRUN,
            points=30,
            description="Buffer underrun detected",
            metric_value=2,
            threshold=0
        )
        
        d = contrib.to_dict()
        assert d['reason'] == "buffer_underrun"
        assert d['points'] == 30
        assert d['description'] == "Buffer underrun detected"
        assert d['metric_value'] == 2
        assert d['threshold'] == 0


class TestRiskScore:
    """Tests for RiskScore dataclass."""
    
    def test_risk_score_creation(self):
        """Test creating a RiskScore instance."""
        score = RiskScore(
            score=75,
            stream_id="stream-123",
            channel_id="channel-456"
        )
        
        assert score.score == 75
        assert score.stream_id == "stream-123"
        assert score.channel_id == "channel-456"
        assert score.raw_score == 75
    
    def test_risk_score_capping_high(self):
        """Test that score is capped at 100."""
        score = RiskScore(score=150, stream_id="stream-123")
        
        assert score.score == 100
        assert score.raw_score == 150
    
    def test_risk_score_capping_low(self):
        """Test that score is capped at 0."""
        score = RiskScore(score=-20, stream_id="stream-123")
        
        assert score.score == 0
        assert score.raw_score == -20
    
    def test_risk_score_with_reasons(self):
        """Test RiskScore with multiple reasons."""
        reasons = [
            RiskContribution(
                reason=RiskReason.RESPONSE_TIME_WARNING,
                points=15,
                description="Warning threshold exceeded"
            ),
            RiskContribution(
                reason=RiskReason.BUFFER_UNDERRUN,
                points=30,
                description="Buffer underrun"
            )
        ]
        
        score = RiskScore(
            score=45,
            reasons=reasons,
            stream_id="stream-123"
        )
        
        assert len(score.reasons) == 2
        assert score.reasons[0].points == 15
        assert score.reasons[1].points == 30
    
    def test_risk_score_to_dict(self):
        """Test converting RiskScore to dictionary."""
        reasons = [
            RiskContribution(
                reason=RiskReason.RESPONSE_TIME_WARNING,
                points=15,
                description="Warning"
            )
        ]
        
        score = RiskScore(
            score=75,
            reasons=reasons,
            stream_id="stream-123",
            channel_id="channel-456"
        )
        
        d = score.to_dict()
        assert d['score'] == 75
        assert d['stream_id'] == "stream-123"
        assert d['channel_id'] == "channel-456"
        assert len(d['reasons']) == 1
        assert d['reasons'][0]['reason'] == "response_time_warning"
    
    def test_risk_score_to_json(self):
        """Test converting RiskScore to JSON."""
        score = RiskScore(score=50, stream_id="stream-123")
        
        json_str = score.to_json()
        parsed = json.loads(json_str)
        
        assert parsed['score'] == 50
        assert parsed['stream_id'] == "stream-123"
    
    def test_risk_score_from_dict(self):
        """Test creating RiskScore from dictionary."""
        data = {
            'score': 65,
            'reasons': [
                {
                    'reason': 'buffer_underrun',
                    'points': 30,
                    'description': 'Buffer underrun',
                    'metric_value': 2,
                    'threshold': 0
                }
            ],
            'stream_id': 'stream-123',
            'channel_id': 'channel-456',
            'timestamp': 1234567890.0,
            'raw_score': 65
        }
        
        score = RiskScore.from_dict(data)
        
        assert score.score == 65
        assert score.stream_id == "stream-123"
        assert len(score.reasons) == 1
        assert score.reasons[0].reason == RiskReason.BUFFER_UNDERRUN
    
    def test_risk_score_from_json(self):
        """Test creating RiskScore from JSON string."""
        json_str = json.dumps({
            'score': 80,
            'reasons': [],
            'stream_id': 'stream-123',
            'channel_id': None,
            'timestamp': 1234567890.0,
            'raw_score': 80
        })
        
        score = RiskScore.from_json(json_str)
        
        assert score.score == 80
        assert score.stream_id == "stream-123"
    
    def test_is_warmup_threshold(self):
        """Test warmup threshold check."""
        score = RiskScore(score=65, stream_id="stream-123")
        
        assert score.is_warmup_threshold(60) is True
        assert score.is_warmup_threshold(70) is False
    
    def test_is_failover_threshold(self):
        """Test failover threshold check."""
        score = RiskScore(score=90, stream_id="stream-123")
        
        assert score.is_failover_threshold(85) is True
        assert score.is_failover_threshold(95) is False
    
    def test_get_primary_reason(self):
        """Test getting the highest contributing reason."""
        reasons = [
            RiskContribution(
                reason=RiskReason.RESPONSE_TIME_WARNING,
                points=15,
                description="Warning"
            ),
            RiskContribution(
                reason=RiskReason.BUFFER_UNDERRUN,
                points=30,
                description="Underrun"
            ),
            RiskContribution(
                reason=RiskReason.BITRATE_VARIANCE,
                points=10,
                description="Variance"
            )
        ]
        
        score = RiskScore(score=55, reasons=reasons, stream_id="stream-123")
        primary = score.get_primary_reason()
        
        assert primary.reason == RiskReason.BUFFER_UNDERRUN
        assert primary.points == 30
    
    def test_get_primary_reason_empty(self):
        """Test get_primary_reason with no reasons."""
        score = RiskScore(score=0, stream_id="stream-123")
        
        assert score.get_primary_reason() is None
    
    def test_get_reason_summary(self):
        """Test getting reason summary string."""
        reasons = [
            RiskContribution(
                reason=RiskReason.RESPONSE_TIME_WARNING,
                points=15,
                description="Warning"
            ),
            RiskContribution(
                reason=RiskReason.BUFFER_UNDERRUN,
                points=30,
                description="Underrun"
            )
        ]
        
        score = RiskScore(score=45, reasons=reasons, stream_id="stream-123")
        summary = score.get_reason_summary()
        
        assert "response_time_warning: +15" in summary
        assert "buffer_underrun: +30" in summary
    
    def test_get_reason_summary_empty(self):
        """Test get_reason_summary with no reasons."""
        score = RiskScore(score=0, stream_id="stream-123")
        
        assert score.get_reason_summary() == "No risk factors detected"


class TestRiskScoreCalculator:
    """Tests for RiskScoreCalculator class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.setex = MagicMock()
        redis.get = MagicMock(return_value=None)
        redis.keys = MagicMock(return_value=[])
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = True
        return config
    
    @pytest.fixture
    def disabled_config(self):
        """Create a disabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = False
        return config
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Create a mock metrics collector."""
        collector = MagicMock()
        collector.get_recent_metrics = MagicMock(return_value=[])
        return collector
    
    @pytest.fixture
    def calculator(self, mock_redis, enabled_config, mock_metrics_collector):
        """Create a RiskScoreCalculator with mocked dependencies."""
        return RiskScoreCalculator(
            config=enabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
    
    def test_calculate_risk_score_disabled(self, mock_redis, disabled_config, mock_metrics_collector):
        """Test that disabled calculator returns zero score."""
        calculator = RiskScoreCalculator(
            config=disabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
        
        score = calculator.calculate_risk_score("stream-123")
        
        assert score.score == 0
        assert len(score.reasons) == 0
    
    def test_calculate_risk_score_no_metrics(self, calculator):
        """Test calculation with no metrics returns zero score."""
        score = calculator.calculate_risk_score("stream-123", "channel-456")
        
        assert score.score == 0
        assert score.stream_id == "stream-123"
        assert score.channel_id == "channel-456"

    
    def test_response_time_warning_scoring(self, calculator, enabled_config):
        """Test response time warning adds correct points."""
        # Simulate metrics with high response time
        metrics = {
            'response_times': [250, 260, 270],  # Above warning (200ms)
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_response_time_score(metrics)
        
        assert len(contributions) >= 1
        warning_contrib = next(
            (c for c in contributions if c.reason == RiskReason.RESPONSE_TIME_WARNING),
            None
        )
        assert warning_contrib is not None
        assert warning_contrib.points == enabled_config.response_time_warning_weight
    
    def test_response_time_critical_scoring(self, calculator, enabled_config):
        """Test response time critical adds additional points."""
        # Simulate metrics with very high response time
        metrics = {
            'response_times': [450, 460, 470],  # Above critical (400ms)
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_response_time_score(metrics)
        
        # Should have both warning and critical
        assert len(contributions) == 2
        
        critical_contrib = next(
            (c for c in contributions if c.reason == RiskReason.RESPONSE_TIME_CRITICAL),
            None
        )
        assert critical_contrib is not None
        assert critical_contrib.points == enabled_config.response_time_critical_weight
    
    def test_response_time_below_threshold(self, calculator):
        """Test no points when response time is below threshold."""
        metrics = {
            'response_times': [100, 110, 120],  # Below warning (200ms)
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_response_time_score(metrics)
        
        assert len(contributions) == 0
    
    def test_response_time_empty_metrics(self, calculator):
        """Test no points when no response time metrics."""
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_response_time_score(metrics)
        
        assert len(contributions) == 0
    
    def test_buffer_underrun_scoring(self, calculator, enabled_config):
        """Test buffer underrun adds correct points."""
        metrics = {
            'response_times': [],
            'buffer_underruns': 2,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_buffer_underrun_score(metrics)
        
        assert len(contributions) == 1
        assert contributions[0].reason == RiskReason.BUFFER_UNDERRUN
        # 2 underruns * 30 points = 60, but capped at 50
        expected_points = min(2 * enabled_config.buffer_underrun_weight, 50)
        assert contributions[0].points == expected_points
    
    def test_buffer_underrun_capped_at_50(self, calculator, enabled_config):
        """Test buffer underrun points are capped at 50."""
        metrics = {
            'response_times': [],
            'buffer_underruns': 10,  # Many underruns
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_buffer_underrun_score(metrics)
        
        assert len(contributions) == 1
        assert contributions[0].points == 50  # Capped
    
    def test_buffer_underrun_zero(self, calculator):
        """Test no points when no buffer underruns."""
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_buffer_underrun_score(metrics)
        
        assert len(contributions) == 0
    
    def test_bitrate_variance_scoring(self, calculator, enabled_config):
        """Test bitrate variance adds correct points."""
        # High variance bitrates
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [1000, 500, 1500, 400, 1200],  # High variance
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_bitrate_variance_score(metrics)
        
        # Should detect high variance
        if contributions:
            assert contributions[0].reason == RiskReason.BITRATE_VARIANCE
            assert contributions[0].points == enabled_config.bitrate_variance_weight
    
    def test_bitrate_variance_stable(self, calculator):
        """Test no points when bitrate is stable."""
        # Stable bitrates
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [1000, 1010, 990, 1005, 995],  # Low variance
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_bitrate_variance_score(metrics)
        
        assert len(contributions) == 0
    
    def test_bitrate_variance_insufficient_data(self, calculator):
        """Test no points when insufficient bitrate data."""
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [1000],  # Only one sample
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_bitrate_variance_score(metrics)
        
        assert len(contributions) == 0
    
    def test_connection_reset_scoring(self, calculator, enabled_config):
        """Test connection resets add correct points."""
        # Simulate connection resets (1=connected, 0=disconnected)
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [1, 0, 1, 0, 1, 0, 1],  # 3 resets
            'bytes_received': []
        }
        
        contributions = calculator._calculate_connection_reset_score(metrics)
        
        assert len(contributions) == 1
        assert contributions[0].reason == RiskReason.CONNECTION_RESETS
        assert contributions[0].points == enabled_config.connection_reset_weight
    
    def test_connection_reset_below_threshold(self, calculator):
        """Test no points when resets below threshold."""
        # Only 2 resets (threshold is >2)
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [1, 0, 1, 0, 1],  # 2 resets
            'bytes_received': []
        }
        
        contributions = calculator._calculate_connection_reset_score(metrics)
        
        assert len(contributions) == 0
    
    def test_trend_detection_scoring(self, calculator, enabled_config):
        """Test rising trend detection adds points."""
        # 4 consecutive increases
        metrics = {
            'response_times': [100, 120, 140, 160, 180],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_trend_score(metrics)
        
        assert len(contributions) == 1
        assert contributions[0].reason == RiskReason.RESPONSE_TIME_TREND
        assert contributions[0].points == enabled_config.trend_weight
    
    def test_trend_detection_no_trend(self, calculator):
        """Test no points when no rising trend."""
        # Fluctuating values
        metrics = {
            'response_times': [100, 120, 110, 130, 115],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_trend_score(metrics)
        
        assert len(contributions) == 0
    
    def test_bitrate_drop_scoring(self, calculator, enabled_config):
        """Test sudden bitrate drop adds points."""
        # First half high, second half low (>50% drop)
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [1000, 1000, 1000, 300, 300, 300],  # 70% drop
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_bitrate_drop_score(metrics)
        
        assert len(contributions) == 1
        assert contributions[0].reason == RiskReason.BITRATE_DROP
        assert contributions[0].points == enabled_config.bitrate_drop_weight
    
    def test_bitrate_drop_small(self, calculator):
        """Test no points when bitrate drop is small."""
        # Small drop (<50%)
        metrics = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [1000, 1000, 1000, 700, 700, 700],  # 30% drop
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_bitrate_drop_score(metrics)
        
        assert len(contributions) == 0
    
    def test_pattern_match_scoring(self, calculator, enabled_config):
        """Test pattern match adds correct points."""
        contributions = calculator._calculate_pattern_score(80.0)  # 80% confidence
        
        assert len(contributions) == 1
        assert contributions[0].reason == RiskReason.PATTERN_MATCH
        # 80 * 0.4 = 32 points
        expected_points = int(80.0 * enabled_config.pattern_confidence_factor)
        assert contributions[0].points == expected_points
    
    def test_pattern_match_capped(self, calculator, enabled_config):
        """Test pattern match points are capped."""
        contributions = calculator._calculate_pattern_score(100.0)  # 100% confidence
        
        assert len(contributions) == 1
        # 100 * 0.4 = 40, capped at pattern_max_weight
        assert contributions[0].points <= enabled_config.pattern_max_weight
    
    def test_pattern_match_zero_confidence(self, calculator):
        """Test no points when pattern confidence is zero."""
        contributions = calculator._calculate_pattern_score(0.0)
        
        assert len(contributions) == 0
    
    def test_score_capping_at_100(self, calculator, mock_metrics_collector):
        """Test that total score is capped at 100."""
        # Mock metrics that would produce >100 points
        from ..metrics_collector import MetricType, Metric
        
        # Create mock metrics that return high values
        high_response_metrics = [
            MagicMock(value=500) for _ in range(10)  # Very high response times
        ]
        underrun_metrics = [MagicMock() for _ in range(5)]  # Many underruns
        
        def mock_get_metrics(stream_id, metric_type, seconds=60):
            if metric_type == MetricType.RESPONSE_TIME:
                return high_response_metrics
            elif metric_type == MetricType.BUFFER_UNDERRUN:
                return underrun_metrics
            return []
        
        mock_metrics_collector.get_recent_metrics = mock_get_metrics
        
        score = calculator.calculate_risk_score("stream-123", pattern_confidence=100)
        
        assert score.score <= 100
        assert score.raw_score >= score.score  # Raw score may be higher
    
    def test_score_minimum_zero(self, calculator):
        """Test that score never goes below zero."""
        score = RiskScore(score=-50, stream_id="stream-123")
        
        assert score.score == 0
        assert score.raw_score == -50
    
    def test_configurable_weights(self, mock_redis, mock_metrics_collector):
        """Test that weights are configurable."""
        # Create config with custom weights
        config = PredictiveConfig()
        config.enabled = True
        config.response_time_warning_weight = 25  # Custom weight
        config.response_time_warning = 200
        
        calculator = RiskScoreCalculator(
            config=config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
        
        metrics = {
            'response_times': [250, 260, 270],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': []
        }
        
        contributions = calculator._calculate_response_time_score(metrics)
        
        warning_contrib = next(
            (c for c in contributions if c.reason == RiskReason.RESPONSE_TIME_WARNING),
            None
        )
        assert warning_contrib is not None
        assert warning_contrib.points == 25  # Custom weight
    
    def test_store_risk_score(self, calculator, mock_redis):
        """Test that risk score is stored in Redis."""
        score = RiskScore(score=75, stream_id="stream-123")
        
        result = calculator._store_risk_score(score)
        
        assert result is True
        mock_redis.setex.assert_called_once()
    
    def test_get_risk_score(self, calculator, mock_redis):
        """Test retrieving risk score from Redis."""
        stored_data = json.dumps({
            'score': 65,
            'reasons': [],
            'stream_id': 'stream-123',
            'channel_id': None,
            'timestamp': 1234567890.0,
            'raw_score': 65
        })
        mock_redis.get = MagicMock(return_value=stored_data.encode('utf-8'))
        
        score = calculator.get_risk_score("stream-123")
        
        assert score is not None
        assert score.score == 65
        assert score.stream_id == "stream-123"
    
    def test_get_risk_score_not_found(self, calculator, mock_redis):
        """Test get_risk_score returns None when not found."""
        mock_redis.get = MagicMock(return_value=None)
        
        score = calculator.get_risk_score("stream-999")
        
        assert score is None


class TestRiskScoreCalculatorSingleton:
    """Tests for the singleton pattern."""
    
    def test_get_risk_calculator_returns_same_instance(self):
        """Test that get_risk_calculator returns the same instance."""
        reset_risk_calculator()
        
        calc1 = get_risk_calculator()
        calc2 = get_risk_calculator()
        
        assert calc1 is calc2
    
    def test_reset_risk_calculator(self):
        """Test that reset_risk_calculator creates a new instance."""
        calc1 = get_risk_calculator()
        reset_risk_calculator()
        calc2 = get_risk_calculator()
        
        assert calc1 is not calc2
