"""
Unit tests for the Pattern Analyzer.

Tests cover:
- FailurePatternData dataclass
- Pattern recording
- Pattern matching
- Pattern analysis

Requirements: 3.1, 3.4
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from ..pattern_analyzer import (
    FailurePatternData,
    PatternAnalyzer,
    get_pattern_analyzer,
    reset_pattern_analyzer,
)
from ..config import PredictiveConfig


class TestFailurePatternData:
    """Tests for FailurePatternData dataclass."""
    
    def test_pattern_data_creation(self):
        """Test creating a FailurePatternData instance."""
        metrics = {
            'avg_response_time': 250.0,
            'buffer_underruns': 2,
            'bitrate_variance': 15.0
        }
        
        pattern = FailurePatternData(
            pattern_type="response_time",
            metrics_snapshot=metrics,
            confidence=65,
            stream_id="stream-123",
            channel_id="channel-456",
            m3u_account_id=1
        )
        
        assert pattern.pattern_type == "response_time"
        assert pattern.metrics_snapshot == metrics
        assert pattern.confidence == 65
        assert pattern.stream_id == "stream-123"
        assert pattern.channel_id == "channel-456"
        assert pattern.m3u_account_id == 1
    
    def test_pattern_data_defaults(self):
        """Test FailurePatternData default values."""
        pattern = FailurePatternData(
            pattern_type="buffer_underrun",
            metrics_snapshot={}
        )
        
        assert pattern.confidence == 50
        assert pattern.stream_id is None
        assert pattern.channel_id is None
        assert pattern.m3u_account_id is None
        assert 0 <= pattern.day_of_week <= 6
        assert 0 <= pattern.hour_of_day <= 23
    
    def test_pattern_data_to_dict(self):
        """Test converting FailurePatternData to dictionary."""
        pattern = FailurePatternData(
            pattern_type="connection_reset",
            metrics_snapshot={'connection_resets': 3},
            confidence=70,
            stream_id="stream-123"
        )
        
        d = pattern.to_dict()
        
        assert d['pattern_type'] == "connection_reset"
        assert d['metrics_snapshot'] == {'connection_resets': 3}
        assert d['confidence'] == 70
        assert d['stream_id'] == "stream-123"
        assert 'timestamp' in d
        assert 'day_of_week' in d
        assert 'hour_of_day' in d
    
    def test_pattern_data_from_dict(self):
        """Test creating FailurePatternData from dictionary."""
        data = {
            'pattern_type': 'bitrate_drop',
            'metrics_snapshot': {'bitrate_variance': 60.0},
            'confidence': 55,
            'stream_id': 'stream-123',
            'channel_id': 'channel-456',
            'm3u_account_id': 2,
            'timestamp': 1234567890.0,
            'day_of_week': 3,
            'hour_of_day': 14
        }
        
        pattern = FailurePatternData.from_dict(data)
        
        assert pattern.pattern_type == "bitrate_drop"
        assert pattern.confidence == 55
        assert pattern.stream_id == "stream-123"
        assert pattern.day_of_week == 3
        assert pattern.hour_of_day == 14


class TestPatternAnalyzer:
    """Tests for PatternAnalyzer class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.lpush = MagicMock()
        redis.ltrim = MagicMock()
        redis.expire = MagicMock()
        redis.llen = MagicMock(return_value=0)
        redis.lrange = MagicMock(return_value=[])
        return redis
    
    @pytest.fixture
    def enabled_config(self):
        """Create an enabled PredictiveConfig."""
        config = PredictiveConfig()
        config.enabled = True
        config.pattern_learning_enabled = True
        config.time_pattern_enabled = True
        config.pattern_confidence_threshold = 60
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
    def analyzer(self, mock_redis, enabled_config, mock_metrics_collector):
        """Create a PatternAnalyzer with mocked dependencies."""
        return PatternAnalyzer(
            config=enabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
    
    def test_pattern_type_constants(self):
        """Test pattern type constants exist."""
        assert PatternAnalyzer.PATTERN_RESPONSE_TIME == "response_time"
        assert PatternAnalyzer.PATTERN_BUFFER_UNDERRUN == "buffer_underrun"
        assert PatternAnalyzer.PATTERN_BITRATE_DROP == "bitrate_drop"
        assert PatternAnalyzer.PATTERN_CONNECTION_RESET == "connection_reset"
        assert PatternAnalyzer.PATTERN_TIME_WINDOW == "time_window"
        assert PatternAnalyzer.PATTERN_CORRELATION == "correlation"
        assert PatternAnalyzer.PATTERN_COMPOSITE == "composite"
    
    def test_min_failures_for_pattern(self):
        """Test minimum failures constant."""
        assert PatternAnalyzer.MIN_FAILURES_FOR_PATTERN == 3
    
    def test_record_failure_disabled(self, mock_redis, disabled_config, mock_metrics_collector):
        """Test record_failure returns False when disabled."""
        analyzer = PatternAnalyzer(
            config=disabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
        
        result = analyzer.record_failure("stream-123")
        
        assert result is False
    
    def test_record_failure_no_metrics(self, analyzer, mock_metrics_collector):
        """Test record_failure returns False when no metrics available."""
        mock_metrics_collector.get_recent_metrics = MagicMock(return_value=[])
        
        result = analyzer.record_failure("stream-123", "channel-456")
        
        assert result is False
    
    def test_record_failure_with_metrics(self, analyzer, mock_redis, mock_metrics_collector):
        """Test record_failure stores failure when metrics available."""
        from ..metrics_collector import MetricType
        
        # Mock metrics
        mock_metric = MagicMock()
        mock_metric.value = 300.0
        
        def mock_get_metrics(stream_id, metric_type, seconds=60):
            if metric_type == MetricType.RESPONSE_TIME:
                return [mock_metric, mock_metric, mock_metric]
            return []
        
        mock_metrics_collector.get_recent_metrics = mock_get_metrics
        
        with patch.object(analyzer, '_log_failure_event'):
            result = analyzer.record_failure("stream-123", "channel-456")
        
        # Should store in Redis
        assert mock_redis.lpush.called
    
    def test_determine_pattern_type_connection_reset(self, analyzer):
        """Test pattern type detection for connection resets."""
        metrics = {
            'connection_resets': 3,
            'buffer_underruns': 0,
            'bitrate_variance': 10,
            'avg_response_time': 100
        }
        
        pattern_type = analyzer._determine_pattern_type(metrics)
        
        assert pattern_type == PatternAnalyzer.PATTERN_CONNECTION_RESET
    
    def test_determine_pattern_type_buffer_underrun(self, analyzer):
        """Test pattern type detection for buffer underruns."""
        metrics = {
            'connection_resets': 0,
            'buffer_underruns': 2,
            'bitrate_variance': 10,
            'avg_response_time': 100
        }
        
        pattern_type = analyzer._determine_pattern_type(metrics)
        
        assert pattern_type == PatternAnalyzer.PATTERN_BUFFER_UNDERRUN
    
    def test_determine_pattern_type_bitrate_drop(self, analyzer):
        """Test pattern type detection for bitrate drop."""
        metrics = {
            'connection_resets': 0,
            'buffer_underruns': 0,
            'bitrate_variance': 60,  # >50%
            'avg_response_time': 100
        }
        
        pattern_type = analyzer._determine_pattern_type(metrics)
        
        assert pattern_type == PatternAnalyzer.PATTERN_BITRATE_DROP
    
    def test_determine_pattern_type_response_time(self, analyzer, enabled_config):
        """Test pattern type detection for response time."""
        metrics = {
            'connection_resets': 0,
            'buffer_underruns': 0,
            'bitrate_variance': 10,
            'avg_response_time': 500  # Above critical threshold
        }
        
        pattern_type = analyzer._determine_pattern_type(metrics)
        
        assert pattern_type == PatternAnalyzer.PATTERN_RESPONSE_TIME
    
    def test_determine_pattern_type_composite(self, analyzer):
        """Test pattern type defaults to composite."""
        metrics = {
            'connection_resets': 0,
            'buffer_underruns': 0,
            'bitrate_variance': 10,
            'avg_response_time': 100
        }
        
        pattern_type = analyzer._determine_pattern_type(metrics)
        
        assert pattern_type == PatternAnalyzer.PATTERN_COMPOSITE
    
    def test_analyze_patterns_disabled(self, mock_redis, disabled_config, mock_metrics_collector):
        """Test analyze_patterns returns empty when disabled."""
        analyzer = PatternAnalyzer(
            config=disabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
        
        patterns = analyzer.analyze_patterns("stream-123")
        
        assert patterns == []
    
    def test_analyze_patterns_insufficient_failures(self, analyzer, mock_redis):
        """Test analyze_patterns returns empty with insufficient failures."""
        # Only 2 failures (need 3)
        mock_redis.lrange = MagicMock(return_value=[
            json.dumps({'pattern_type': 'response_time', 'metrics_snapshot': {}}).encode(),
            json.dumps({'pattern_type': 'response_time', 'metrics_snapshot': {}}).encode(),
        ])
        
        patterns = analyzer.analyze_patterns("stream-123")
        
        assert patterns == []
    
    def test_analyze_patterns_creates_pattern(self, analyzer, mock_redis):
        """Test analyze_patterns creates pattern from failures."""
        # 4 failures of same type
        failure_data = {
            'pattern_type': 'response_time',
            'metrics_snapshot': {
                'avg_response_time': 300,
                'max_response_time': 400,
                'buffer_underruns': 0,
                'bitrate_variance': 10,
                'connection_resets': 0
            },
            'hour_of_day': 20,
            'day_of_week': 5
        }
        
        mock_redis.lrange = MagicMock(return_value=[
            json.dumps(failure_data).encode() for _ in range(4)
        ])
        
        with patch.object(analyzer, '_save_pattern_to_db'):
            patterns = analyzer.analyze_patterns("stream-123")
        
        assert len(patterns) >= 1
        assert any(p['pattern_type'] == 'response_time' for p in patterns)
    
    def test_create_pattern_from_failures(self, analyzer):
        """Test creating pattern from failure records."""
        failures = [
            {
                'pattern_type': 'buffer_underrun',
                'metrics_snapshot': {
                    'avg_response_time': 200,
                    'max_response_time': 300,
                    'buffer_underruns': 2,
                    'bitrate_variance': 15,
                    'connection_resets': 0
                }
            },
            {
                'pattern_type': 'buffer_underrun',
                'metrics_snapshot': {
                    'avg_response_time': 220,
                    'max_response_time': 350,
                    'buffer_underruns': 3,
                    'bitrate_variance': 18,
                    'connection_resets': 0
                }
            },
            {
                'pattern_type': 'buffer_underrun',
                'metrics_snapshot': {
                    'avg_response_time': 180,
                    'max_response_time': 280,
                    'buffer_underruns': 2,
                    'bitrate_variance': 12,
                    'connection_resets': 0
                }
            }
        ]
        
        pattern = analyzer._create_pattern_from_failures(
            'buffer_underrun', failures, m3u_account_id=1
        )
        
        assert pattern is not None
        assert pattern['pattern_type'] == 'buffer_underrun'
        assert pattern['confidence'] >= 50
        assert 'pattern_data' in pattern
        assert 'avg_metrics' in pattern['pattern_data']
        assert 'thresholds' in pattern['pattern_data']
    
    def test_create_pattern_insufficient_failures(self, analyzer):
        """Test create_pattern returns None with insufficient failures."""
        failures = [
            {'pattern_type': 'response_time', 'metrics_snapshot': {}},
            {'pattern_type': 'response_time', 'metrics_snapshot': {}},
        ]
        
        pattern = analyzer._create_pattern_from_failures('response_time', failures)
        
        assert pattern is None
    
    def test_analyze_time_patterns(self, analyzer):
        """Test time-based pattern analysis."""
        # 4 failures at same hour
        failures = [
            {'hour_of_day': 20, 'pattern_type': 'response_time', 'metrics_snapshot': {}},
            {'hour_of_day': 20, 'pattern_type': 'response_time', 'metrics_snapshot': {}},
            {'hour_of_day': 20, 'pattern_type': 'response_time', 'metrics_snapshot': {}},
            {'hour_of_day': 20, 'pattern_type': 'response_time', 'metrics_snapshot': {}},
        ]
        
        patterns = analyzer._analyze_time_patterns(failures)
        
        assert len(patterns) >= 1
        assert any(p['pattern_type'] == PatternAnalyzer.PATTERN_TIME_WINDOW for p in patterns)
    
    def test_check_pattern_match_disabled(self, mock_redis, disabled_config, mock_metrics_collector):
        """Test check_pattern_match returns None when disabled."""
        analyzer = PatternAnalyzer(
            config=disabled_config,
            metrics_collector=mock_metrics_collector,
            redis_client=mock_redis
        )
        
        result = analyzer.check_pattern_match("stream-123")
        
        assert result is None
    
    def test_check_pattern_match_no_metrics(self, analyzer, mock_metrics_collector):
        """Test check_pattern_match returns None when no metrics."""
        mock_metrics_collector.get_recent_metrics = MagicMock(return_value=[])
        
        result = analyzer.check_pattern_match("stream-123")
        
        assert result is None
    
    def test_calculate_thresholds(self, analyzer):
        """Test threshold calculation from average metrics."""
        avg_metrics = {
            'avg_response_time': 300,
            'buffer_underruns': 2,
            'bitrate_variance': 20,
            'connection_resets': 3
        }
        
        thresholds = analyzer._calculate_thresholds(avg_metrics, 'response_time')
        
        assert 'response_time_threshold' in thresholds
        assert 'buffer_underrun_threshold' in thresholds
        assert 'bitrate_variance_threshold' in thresholds
        assert 'connection_reset_threshold' in thresholds
        
        # Thresholds should be 80% of average
        assert thresholds['response_time_threshold'] == 240  # 300 * 0.8
        assert thresholds['bitrate_variance_threshold'] == 16  # 20 * 0.8
    
    def test_get_failure_records_empty(self, analyzer, mock_redis):
        """Test get_failure_records returns empty list when no records."""
        mock_redis.lrange = MagicMock(return_value=[])
        
        records = analyzer._get_failure_records("stream-123")
        
        assert records == []
    
    def test_get_failure_records_with_data(self, analyzer, mock_redis):
        """Test get_failure_records returns parsed records."""
        failure_data = {
            'pattern_type': 'response_time',
            'metrics_snapshot': {'avg_response_time': 300}
        }
        
        mock_redis.lrange = MagicMock(return_value=[
            json.dumps(failure_data).encode()
        ])
        
        records = analyzer._get_failure_records("stream-123")
        
        assert len(records) == 1
        assert records[0]['pattern_type'] == 'response_time'


class TestPatternAnalyzerSingleton:
    """Tests for the singleton pattern."""
    
    def test_get_pattern_analyzer_returns_same_instance(self):
        """Test that get_pattern_analyzer returns the same instance."""
        reset_pattern_analyzer()
        
        analyzer1 = get_pattern_analyzer()
        analyzer2 = get_pattern_analyzer()
        
        assert analyzer1 is analyzer2
    
    def test_reset_pattern_analyzer(self):
        """Test that reset_pattern_analyzer creates a new instance."""
        analyzer1 = get_pattern_analyzer()
        reset_pattern_analyzer()
        analyzer2 = get_pattern_analyzer()
        
        assert analyzer1 is not analyzer2
