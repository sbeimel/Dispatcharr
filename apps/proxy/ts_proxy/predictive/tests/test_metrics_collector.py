"""
Unit tests for the Stream Metrics Collector.

Tests cover:
- MetricType enum values
- Metric dataclass serialization
- StreamMetricsCollector start/stop collecting
- Recording and retrieving metrics

Requirements: 1.1, 1.2
"""

import json
import pytest
from unittest.mock import MagicMock

from ..metrics_collector import (
    MetricType,
    Metric,
    StreamMetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)
from ..config import PredictiveConfig


class TestMetricType:
    """Tests for MetricType enum."""
    
    def test_metric_type_values(self):
        """Test that all expected metric types exist."""
        assert MetricType.RESPONSE_TIME.value == "response_time"
        assert MetricType.BYTES_RECEIVED.value == "bytes_received"
        assert MetricType.CONNECTION_STATUS.value == "connection_status"
        assert MetricType.ERROR_COUNT.value == "error_count"
        assert MetricType.BUFFER_UNDERRUN.value == "buffer_underrun"
        assert MetricType.BITRATE.value == "bitrate"
        assert MetricType.MAC_TOKEN_TTL.value == "mac_token_ttl"
        assert MetricType.PORTAL_RESPONSE_TIME.value == "portal_response_time"
    
    def test_metric_type_from_string(self):
        """Test creating MetricType from string value."""
        assert MetricType("response_time") == MetricType.RESPONSE_TIME
        assert MetricType("bytes_received") == MetricType.BYTES_RECEIVED


class TestMetric:
    """Tests for Metric dataclass."""
    
    def test_metric_creation(self):
        """Test creating a Metric instance."""
        metric = Metric(
            metric_type=MetricType.RESPONSE_TIME,
            value=150.5,
            timestamp=1234567890.0,
            stream_id="stream-123",
            channel_id="channel-456"
        )
        
        assert metric.metric_type == MetricType.RESPONSE_TIME
        assert metric.value == 150.5
        assert metric.timestamp == 1234567890.0
        assert metric.stream_id == "stream-123"
        assert metric.channel_id == "channel-456"
    
    def test_metric_to_dict(self):
        """Test converting Metric to dictionary."""
        metric = Metric(
            metric_type=MetricType.RESPONSE_TIME,
            value=150.5,
            timestamp=1234567890.0,
            stream_id="stream-123"
        )
        
        d = metric.to_dict()
        assert d['metric_type'] == "response_time"
        assert d['value'] == 150.5
        assert d['timestamp'] == 1234567890.0
        assert d['stream_id'] == "stream-123"
    
    def test_metric_from_dict(self):
        """Test creating Metric from dictionary."""
        data = {
            'metric_type': 'response_time',
            'value': 150.5,
            'timestamp': 1234567890.0,
            'stream_id': 'stream-123',
            'channel_id': 'channel-456'
        }
        
        metric = Metric.from_dict(data)
        assert metric.metric_type == MetricType.RESPONSE_TIME
        assert metric.value == 150.5
        assert metric.stream_id == "stream-123"
    
    def test_metric_to_redis_value(self):
        """Test converting Metric to Redis storage format."""
        metric = Metric(
            metric_type=MetricType.RESPONSE_TIME,
            value=150.5,
            timestamp=1234567890.0,
            stream_id="stream-123",
            channel_id="channel-456"
        )
        
        redis_value = metric.to_redis_value()
        parsed = json.loads(redis_value)
        
        assert parsed['value'] == 150.5
        assert parsed['channel_id'] == "channel-456"
    
    def test_metric_from_redis(self):
        """Test creating Metric from Redis stored data."""
        redis_value = json.dumps({
            'value': 150.5,
            'channel_id': 'channel-456',
            'metadata': None
        })
        
        metric = Metric.from_redis(
            MetricType.RESPONSE_TIME,
            "stream-123",
            1234567890.0,
            redis_value
        )
        
        assert metric.metric_type == MetricType.RESPONSE_TIME
        assert metric.value == 150.5
        assert metric.stream_id == "stream-123"
        assert metric.timestamp == 1234567890.0


class TestStreamMetricsCollector:
    """Tests for StreamMetricsCollector class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.sadd = MagicMock()
        redis.srem = MagicMock()
        redis.hset = MagicMock()
        redis.expire = MagicMock()
        redis.zadd = MagicMock()
        redis.zrangebyscore = MagicMock(return_value=[])
        redis.keys = MagicMock(return_value=[])
        redis.zremrangebyscore = MagicMock(return_value=0)
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
    def collector(self, mock_redis, enabled_config):
        """Create a StreamMetricsCollector with mocked dependencies."""
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=enabled_config
        )
        return collector
    
    def test_is_enabled_when_enabled(self, collector):
        """Test is_enabled returns True when config is enabled."""
        assert collector.is_enabled() is True
    
    def test_is_enabled_when_disabled(self, mock_redis, disabled_config):
        """Test is_enabled returns False when config is disabled."""
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=disabled_config
        )
        assert collector.is_enabled() is False
    
    def test_start_collecting(self, collector, mock_redis):
        """Test starting metrics collection for a stream."""
        result = collector.start_collecting("stream-123", "channel-456")
        
        assert result is True
        assert "stream-123" in collector.get_active_stream_ids()
        mock_redis.sadd.assert_called()
        mock_redis.hset.assert_called()
    
    def test_start_collecting_disabled(self, mock_redis, disabled_config):
        """Test that start_collecting returns False when disabled."""
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=disabled_config
        )
        
        result = collector.start_collecting("stream-123", "channel-456")
        
        assert result is False
        assert "stream-123" not in collector.get_active_stream_ids()
    
    def test_start_collecting_already_collecting(self, collector):
        """Test that starting collection twice returns True without error."""
        collector.start_collecting("stream-123", "channel-456")
        result = collector.start_collecting("stream-123", "channel-456")
        
        assert result is True
    
    def test_stop_collecting(self, collector, mock_redis):
        """Test stopping metrics collection for a stream."""
        collector.start_collecting("stream-123", "channel-456")
        result = collector.stop_collecting("stream-123")
        
        assert result is True
        assert "stream-123" not in collector.get_active_stream_ids()
        mock_redis.srem.assert_called()
    
    def test_stop_collecting_not_collecting(self, collector):
        """Test that stopping collection for non-collected stream returns True."""
        result = collector.stop_collecting("stream-999")
        
        assert result is True
    
    def test_record_metric(self, collector, mock_redis):
        """Test recording a metric."""
        collector.start_collecting("stream-123", "channel-456")
        
        result = collector.record_metric(
            "stream-123",
            MetricType.RESPONSE_TIME,
            150.5
        )
        
        assert result is True
        mock_redis.zadd.assert_called()
        mock_redis.expire.assert_called()
    
    def test_record_metric_disabled(self, mock_redis, disabled_config):
        """Test that record_metric returns False when disabled."""
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=disabled_config
        )
        
        result = collector.record_metric(
            "stream-123",
            MetricType.RESPONSE_TIME,
            150.5
        )
        
        assert result is False
    
    def test_record_buffer_underrun(self, collector, mock_redis):
        """Test recording a buffer underrun event."""
        collector.start_collecting("stream-123", "channel-456")
        
        result = collector.record_buffer_underrun("stream-123", buffer_level=0)
        
        assert result is True
        mock_redis.zadd.assert_called()
    
    def test_record_connection_status(self, collector, mock_redis):
        """Test recording connection status."""
        collector.start_collecting("stream-123", "channel-456")
        
        result = collector.record_connection_status("stream-123", connected=True)
        
        assert result is True
        mock_redis.zadd.assert_called()
    
    def test_calculate_and_record_bitrate(self, collector, mock_redis):
        """Test calculating and recording bitrate."""
        collector.start_collecting("stream-123", "channel-456")
        
        result = collector.calculate_and_record_bitrate(
            "stream-123",
            bytes_received=1000000,  # 1MB
            interval_seconds=1.0
        )
        
        assert result is True
        # Should record both bytes_received and bitrate
        assert mock_redis.zadd.call_count >= 2
    
    def test_get_stream_stats(self, collector):
        """Test getting stream statistics."""
        collector.start_collecting("stream-123", "channel-456")
        
        # Record some metrics
        collector.record_metric("stream-123", MetricType.BYTES_RECEIVED, 1000)
        collector.record_metric("stream-123", MetricType.ERROR_COUNT, 1)
        
        stats = collector.get_stream_stats("stream-123")
        
        assert stats['stream_id'] == "stream-123"
        assert stats['channel_id'] == "channel-456"
        assert 'bytes_received' in stats
        assert 'error_count' in stats
    
    def test_get_stream_stats_not_collecting(self, collector):
        """Test getting stats for non-collected stream returns empty dict."""
        stats = collector.get_stream_stats("stream-999")
        
        assert stats == {}
    
    def test_get_active_stream_ids(self, collector):
        """Test getting list of active stream IDs."""
        collector.start_collecting("stream-1", "channel-1")
        collector.start_collecting("stream-2", "channel-2")
        
        active = collector.get_active_stream_ids()
        
        assert "stream-1" in active
        assert "stream-2" in active
        assert len(active) == 2
    
    def test_get_recent_metrics_empty(self, collector, mock_redis):
        """Test get_recent_metrics returns empty list when no metrics exist."""
        collector.start_collecting("stream-123", "channel-456")
        
        metrics = collector.get_recent_metrics("stream-123")
        
        assert metrics == []
        # Should have called zrangebyscore for each metric type
        assert mock_redis.zrangebyscore.called
    
    def test_get_recent_metrics_with_data(self, mock_redis, enabled_config):
        """Test get_recent_metrics returns metrics from Redis."""
        import time
        import json
        
        # Setup mock to return some metrics
        current_time = time.time()
        redis_value = json.dumps({
            'value': 150.5,
            'channel_id': 'channel-456',
            'metadata': None
        })
        mock_redis.zrangebyscore = MagicMock(return_value=[
            (redis_value.encode('utf-8'), current_time)
        ])
        
        collector = StreamMetricsCollector(
            redis_client=mock_redis,
            config=enabled_config
        )
        collector.start_collecting("stream-123", "channel-456")
        
        metrics = collector.get_recent_metrics(
            "stream-123", 
            metric_type=MetricType.RESPONSE_TIME,
            seconds=60
        )
        
        assert len(metrics) == 1
        assert metrics[0].metric_type == MetricType.RESPONSE_TIME
        assert metrics[0].value == 150.5
        assert metrics[0].stream_id == "stream-123"
    
    def test_get_recent_metrics_specific_type(self, collector, mock_redis):
        """Test get_recent_metrics with specific metric type."""
        collector.start_collecting("stream-123", "channel-456")
        
        metrics = collector.get_recent_metrics(
            "stream-123",
            metric_type=MetricType.RESPONSE_TIME,
            seconds=30
        )
        
        # Should only query for the specific metric type
        assert mock_redis.zrangebyscore.called
    
    def test_get_recent_metrics_no_redis(self, enabled_config):
        """Test get_recent_metrics returns empty list when Redis is unavailable."""
        collector = StreamMetricsCollector(
            redis_client=None,
            config=enabled_config
        )
        
        metrics = collector.get_recent_metrics("stream-123")
        
        assert metrics == []


class TestMetricsCollectorSingleton:
    """Tests for the singleton pattern."""
    
    def test_get_metrics_collector_returns_same_instance(self):
        """Test that get_metrics_collector returns the same instance."""
        reset_metrics_collector()
        
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_reset_metrics_collector(self):
        """Test that reset_metrics_collector creates a new instance."""
        collector1 = get_metrics_collector()
        reset_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is not collector2
