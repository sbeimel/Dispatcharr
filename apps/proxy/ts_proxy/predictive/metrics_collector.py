"""
Stream Metrics Collector for the Predictive Failover System.

This module is responsible for collecting stream metrics at configurable intervals
and storing them in Redis for analysis by the Risk Score Calculator.

Metrics collected:
- Response Time (ms)
- Bytes Received per interval
- Connection Status
- Error Count
- Buffer Underruns
- Bitrate (calculated from bytes/time)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# Task 4.1: MetricType Enum
# =============================================================================

class MetricType(Enum):
    """
    Enumeration of metric types collected for predictive failover analysis.
    
    Each metric type corresponds to a specific aspect of stream health
    that contributes to the risk score calculation.
    """
    
    # Time in milliseconds between request and first byte of response
    RESPONSE_TIME = "response_time"
    
    # Number of bytes received in the collection interval
    BYTES_RECEIVED = "bytes_received"
    
    # Connection status: 1=connected, 0=disconnected, -1=error
    CONNECTION_STATUS = "connection_status"
    
    # Count of errors in the collection interval
    ERROR_COUNT = "error_count"
    
    # Buffer underrun events (when buffer runs empty)
    BUFFER_UNDERRUN = "buffer_underrun"
    
    # Calculated bitrate in bits per second
    BITRATE = "bitrate"
    
    # MAC token time to expiry in seconds (for MAC portals)
    MAC_TOKEN_TTL = "mac_token_ttl"
    
    # Portal response time in milliseconds (for MAC portals)
    PORTAL_RESPONSE_TIME = "portal_response_time"


# =============================================================================
# Task 4.2: Metric Dataclass
# =============================================================================

@dataclass
class Metric:
    """
    Data class representing a single metric measurement.
    
    Attributes:
        metric_type: Type of the metric (from MetricType enum)
        value: Numeric value of the metric
        timestamp: Unix timestamp when the metric was recorded
        stream_id: Identifier of the stream this metric belongs to
        channel_id: Optional channel identifier
        metadata: Optional additional context about the metric
    """
    
    metric_type: MetricType
    value: float
    timestamp: float
    stream_id: str
    channel_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for JSON serialization."""
        return {
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp,
            'stream_id': self.stream_id,
            'channel_id': self.channel_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Metric':
        """Create Metric from dictionary."""
        return cls(
            metric_type=MetricType(data['metric_type']),
            value=data['value'],
            timestamp=data['timestamp'],
            stream_id=data['stream_id'],
            channel_id=data.get('channel_id'),
            metadata=data.get('metadata')
        )
    
    def to_redis_value(self) -> str:
        """Convert metric to string for Redis storage."""
        return json.dumps({
            'value': self.value,
            'channel_id': self.channel_id,
            'metadata': self.metadata
        })
    
    @classmethod
    def from_redis(cls, metric_type: MetricType, stream_id: str, 
                   timestamp: float, redis_value: str) -> 'Metric':
        """Create Metric from Redis stored data."""
        data = json.loads(redis_value)
        return cls(
            metric_type=metric_type,
            value=data['value'],
            timestamp=timestamp,
            stream_id=stream_id,
            channel_id=data.get('channel_id'),
            metadata=data.get('metadata')
        )


# =============================================================================
# Task 4.3 & 4.4: StreamMetricsCollector Class with Redis Storage
# =============================================================================

class StreamMetricsCollector:
    """
    Collects and stores stream metrics for predictive failover analysis.
    
    This class manages the collection of metrics from active streams,
    storing them in Redis sorted sets with timestamps as scores for
    efficient time-based queries.
    
    Requirements:
    - 1.1: Collect metrics every N seconds (configurable)
    - 1.2: Store metrics in Redis with 1 hour TTL
    - 1.3: Log warning when response time exceeds threshold
    - 1.4: Store buffer underrun events
    - 1.5: Stop collection and release resources when stream ends
    """
    
    def __init__(self, redis_client=None, config=None):
        """
        Initialize the metrics collector.
        
        Args:
            redis_client: Redis client instance for storage
            config: PredictiveConfig instance (loaded if not provided)
        """
        self._redis_client = redis_client
        self._config = config
        self._active_streams: Dict[str, Dict[str, Any]] = {}
        self._collection_tasks: Dict[str, Any] = {}
        
        # Import here to avoid circular imports
        from .redis_keys import PredictiveRedisKeys
        self._redis_keys = PredictiveRedisKeys
    
    @property
    def redis_client(self):
        """Lazy load Redis client if not provided."""
        if self._redis_client is None:
            try:
                from django_redis import get_redis_connection
                self._redis_client = get_redis_connection("default")
            except Exception as e:
                logger.error(f"Failed to get Redis connection: {e}")
        return self._redis_client
    
    @property
    def config(self):
        """Lazy load config if not provided."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load predictive config: {e}")
                # Return a minimal default config
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    def is_enabled(self) -> bool:
        """Check if predictive failover is enabled."""
        return self.config.enabled
    
    def start_collecting(self, stream_id: str, channel_id: str = None) -> bool:
        """
        Start collecting metrics for a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            channel_id: Optional channel identifier
            
        Returns:
            True if collection started successfully, False otherwise
            
        Requirement 1.1: Start metrics collection for active streams
        """
        if not self.is_enabled():
            logger.debug(f"Predictive failover disabled, not collecting metrics for stream {stream_id}")
            return False
        
        if stream_id in self._active_streams:
            logger.debug(f"Already collecting metrics for stream {stream_id}")
            return True
        
        try:
            # Initialize stream tracking
            self._active_streams[stream_id] = {
                'channel_id': channel_id,
                'started_at': time.time(),
                'last_collection': time.time(),
                'bytes_received': 0,
                'error_count': 0,
                'buffer_underruns': 0,
                'last_response_time': None,
                'response_times': [],  # For trend detection
            }
            
            # Add to active streams set in Redis
            if self.redis_client:
                self.redis_client.sadd(
                    self._redis_keys.active_streams(),
                    stream_id
                )
                
                # Initialize stream state
                state_key = self._redis_keys.stream_state(stream_id)
                self.redis_client.hset(state_key, mapping={
                    'collecting': '1',
                    'channel_id': channel_id or '',
                    'started_at': str(time.time())
                })
                self.redis_client.expire(state_key, self._redis_keys.STATE_TTL)
            
            logger.info(f"Started metrics collection for stream {stream_id} (channel: {channel_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start metrics collection for stream {stream_id}: {e}")
            return False
    
    def stop_collecting(self, stream_id: str) -> bool:
        """
        Stop collecting metrics for a stream and release resources.
        
        Args:
            stream_id: Unique identifier for the stream
            
        Returns:
            True if collection stopped successfully, False otherwise
            
        Requirement 1.5: Stop collection and release resources when stream ends
        """
        if stream_id not in self._active_streams:
            logger.debug(f"Stream {stream_id} not being collected")
            return True
        
        try:
            # Remove from active streams
            del self._active_streams[stream_id]
            
            # Update Redis
            if self.redis_client:
                # Remove from active streams set
                self.redis_client.srem(
                    self._redis_keys.active_streams(),
                    stream_id
                )
                
                # Update stream state
                state_key = self._redis_keys.stream_state(stream_id)
                self.redis_client.hset(state_key, 'collecting', '0')
                
                # Note: We don't delete metrics immediately - they have TTL
                # This allows post-mortem analysis of failed streams
            
            logger.info(f"Stopped metrics collection for stream {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop metrics collection for stream {stream_id}: {e}")
            return False
    
    def record_metric(self, stream_id: str, metric_type: MetricType, 
                      value: float, metadata: Dict[str, Any] = None) -> bool:
        """
        Record a single metric for a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            metric_type: Type of metric being recorded
            value: Numeric value of the metric
            metadata: Optional additional context
            
        Returns:
            True if metric recorded successfully, False otherwise
            
        Requirements:
        - 1.2: Store metrics in Redis with timestamp and 1 hour TTL
        - 1.3: Log warning when response time exceeds threshold
        - 1.4: Store buffer underrun events
        """
        if not self.is_enabled():
            return False
        
        timestamp = time.time()
        
        try:
            # Get channel_id from active streams if available
            channel_id = None
            if stream_id in self._active_streams:
                channel_id = self._active_streams[stream_id].get('channel_id')
            
            # Create metric object
            metric = Metric(
                metric_type=metric_type,
                value=value,
                timestamp=timestamp,
                stream_id=stream_id,
                channel_id=channel_id,
                metadata=metadata
            )
            
            # Requirement 1.3: Log warning for high response time
            if metric_type == MetricType.RESPONSE_TIME:
                self._check_response_time_warning(stream_id, value)
                # Track for trend detection
                if stream_id in self._active_streams:
                    self._active_streams[stream_id]['last_response_time'] = value
                    response_times = self._active_streams[stream_id]['response_times']
                    response_times.append(value)
                    # Keep only last 10 for trend detection
                    if len(response_times) > 10:
                        response_times.pop(0)
            
            # Requirement 1.4: Track buffer underruns
            if metric_type == MetricType.BUFFER_UNDERRUN:
                if stream_id in self._active_streams:
                    self._active_streams[stream_id]['buffer_underruns'] += 1
                logger.warning(f"Buffer underrun detected for stream {stream_id}")
            
            # Track bytes received for bitrate calculation
            if metric_type == MetricType.BYTES_RECEIVED:
                if stream_id in self._active_streams:
                    self._active_streams[stream_id]['bytes_received'] += value
            
            # Track errors
            if metric_type == MetricType.ERROR_COUNT:
                if stream_id in self._active_streams:
                    self._active_streams[stream_id]['error_count'] += int(value)
            
            # Store in Redis (Requirement 1.2)
            if self.redis_client:
                self._store_metric_in_redis(metric)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record metric for stream {stream_id}: {e}")
            return False
    
    def _store_metric_in_redis(self, metric: Metric) -> None:
        """
        Store a metric in Redis sorted set.
        
        Uses sorted set with timestamp as score for efficient time-based queries.
        
        Requirement 1.2: Store with 1 hour TTL
        """
        key = self._redis_keys.metrics(metric.stream_id, metric.metric_type.value)
        
        # Store in sorted set with timestamp as score
        self.redis_client.zadd(key, {metric.to_redis_value(): metric.timestamp})
        
        # Set TTL (1 hour)
        self.redis_client.expire(key, self._redis_keys.METRICS_TTL)
    
    def _check_response_time_warning(self, stream_id: str, response_time: float) -> None:
        """
        Check if response time exceeds warning threshold and log if so.
        
        Requirement 1.3: Log warning when response time exceeds 500ms
        """
        warning_threshold = self.config.response_time_warning
        critical_threshold = self.config.response_time_critical
        
        if response_time > critical_threshold:
            logger.warning(
                f"CRITICAL: Response time {response_time:.0f}ms exceeds critical threshold "
                f"({critical_threshold}ms) for stream {stream_id}"
            )
        elif response_time > warning_threshold:
            logger.warning(
                f"Response time {response_time:.0f}ms exceeds warning threshold "
                f"({warning_threshold}ms) for stream {stream_id}"
            )
    
    def get_recent_metrics(self, stream_id: str, metric_type: MetricType = None,
                           seconds: int = 60) -> List[Metric]:
        """
        Get recent metrics for a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            metric_type: Optional specific metric type to retrieve
            seconds: Number of seconds of history to retrieve (default 60)
            
        Returns:
            List of Metric objects
        """
        if not self.redis_client:
            return []
        
        metrics = []
        min_timestamp = time.time() - seconds
        
        try:
            if metric_type:
                # Get specific metric type
                metrics.extend(
                    self._get_metrics_from_redis(stream_id, metric_type, min_timestamp)
                )
            else:
                # Get all metric types
                for mt in MetricType:
                    metrics.extend(
                        self._get_metrics_from_redis(stream_id, mt, min_timestamp)
                    )
            
            # Sort by timestamp
            metrics.sort(key=lambda m: m.timestamp)
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get recent metrics for stream {stream_id}: {e}")
            return []
    
    def _get_metrics_from_redis(self, stream_id: str, metric_type: MetricType,
                                 min_timestamp: float) -> List[Metric]:
        """Retrieve metrics of a specific type from Redis."""
        key = self._redis_keys.metrics(stream_id, metric_type.value)
        
        # Get all entries with score >= min_timestamp
        results = self.redis_client.zrangebyscore(
            key, min_timestamp, '+inf', withscores=True
        )
        
        metrics = []
        for value, score in results:
            try:
                # Handle bytes from Redis
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                metric = Metric.from_redis(metric_type, stream_id, score, value)
                metrics.append(metric)
            except Exception as e:
                logger.debug(f"Failed to parse metric: {e}")
        
        return metrics
    
    def get_stream_stats(self, stream_id: str) -> Dict[str, Any]:
        """
        Get current statistics for a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            
        Returns:
            Dictionary with stream statistics
        """
        if stream_id not in self._active_streams:
            return {}
        
        stream_data = self._active_streams[stream_id]
        now = time.time()
        duration = now - stream_data['started_at']
        
        # Calculate average bitrate
        avg_bitrate = 0
        if duration > 0:
            avg_bitrate = (stream_data['bytes_received'] * 8) / duration
        
        return {
            'stream_id': stream_id,
            'channel_id': stream_data['channel_id'],
            'collecting_since': stream_data['started_at'],
            'duration_seconds': duration,
            'bytes_received': stream_data['bytes_received'],
            'average_bitrate_bps': avg_bitrate,
            'error_count': stream_data['error_count'],
            'buffer_underruns': stream_data['buffer_underruns'],
            'last_response_time': stream_data['last_response_time'],
        }
    
    def get_active_stream_ids(self) -> List[str]:
        """Get list of stream IDs currently being collected."""
        return list(self._active_streams.keys())
    
    def get_monitored_streams(self) -> List[Dict[str, Any]]:
        """
        Get list of all monitored streams with their info.
        
        Returns:
            List of dicts with stream_id, channel_id, channel_name, warmup_active
        """
        streams = []
        
        for stream_id, data in self._active_streams.items():
            streams.append({
                'stream_id': stream_id,
                'channel_id': data.get('channel_id'),
                'channel_name': data.get('channel_name', 'Unknown'),
                'warmup_active': False,  # Will be updated by caller
                'started_at': data.get('started_at'),
            })
        
        return streams
    
    def cleanup_old_metrics(self, stream_id: str = None) -> int:
        """
        Clean up old metrics from Redis.
        
        This is normally handled by TTL, but can be called manually
        for immediate cleanup.
        
        Args:
            stream_id: Optional specific stream to clean up
            
        Returns:
            Number of metrics removed
        """
        if not self.redis_client:
            return 0
        
        removed = 0
        min_timestamp = time.time() - self._redis_keys.METRICS_TTL
        
        try:
            if stream_id:
                stream_ids = [stream_id]
            else:
                # Get all streams with metrics
                pattern = self._redis_keys.all_metrics_pattern()
                keys = self.redis_client.keys(pattern)
                stream_ids = set()
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    parts = key.split(':')
                    if len(parts) >= 3:
                        stream_ids.add(parts[2])
                stream_ids = list(stream_ids)
            
            for sid in stream_ids:
                for mt in MetricType:
                    key = self._redis_keys.metrics(sid, mt.value)
                    # Remove entries older than TTL
                    count = self.redis_client.zremrangebyscore(key, '-inf', min_timestamp)
                    removed += count
            
            if removed > 0:
                logger.info(f"Cleaned up {removed} old metrics")
            
            return removed
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0
    
    def record_buffer_underrun(self, stream_id: str, 
                                buffer_level: float = 0,
                                expected_level: float = None) -> bool:
        """
        Record a buffer underrun event.
        
        Convenience method for recording buffer underrun events with
        additional context.
        
        Args:
            stream_id: Unique identifier for the stream
            buffer_level: Current buffer level when underrun occurred
            expected_level: Expected buffer level
            
        Returns:
            True if recorded successfully
            
        Requirement 1.4: Store buffer underrun events with timestamp and stream ID
        """
        metadata = {
            'buffer_level': buffer_level,
            'expected_level': expected_level
        }
        return self.record_metric(
            stream_id, 
            MetricType.BUFFER_UNDERRUN, 
            1,  # Count of 1 for each underrun
            metadata
        )
    
    def record_connection_status(self, stream_id: str, 
                                  connected: bool,
                                  error_message: str = None) -> bool:
        """
        Record connection status change.
        
        Args:
            stream_id: Unique identifier for the stream
            connected: True if connected, False if disconnected
            error_message: Optional error message if disconnected due to error
            
        Returns:
            True if recorded successfully
        """
        # Status values: 1=connected, 0=disconnected, -1=error
        if connected:
            status = 1
        elif error_message:
            status = -1
        else:
            status = 0
        
        metadata = {'error': error_message} if error_message else None
        return self.record_metric(
            stream_id,
            MetricType.CONNECTION_STATUS,
            status,
            metadata
        )
    
    def calculate_and_record_bitrate(self, stream_id: str, 
                                      bytes_received: int,
                                      interval_seconds: float) -> bool:
        """
        Calculate and record bitrate from bytes received.
        
        Args:
            stream_id: Unique identifier for the stream
            bytes_received: Number of bytes received in the interval
            interval_seconds: Duration of the interval in seconds
            
        Returns:
            True if recorded successfully
        """
        if interval_seconds <= 0:
            return False
        
        # Calculate bitrate in bits per second
        bitrate = (bytes_received * 8) / interval_seconds
        
        # Record both bytes received and calculated bitrate
        self.record_metric(stream_id, MetricType.BYTES_RECEIVED, bytes_received)
        return self.record_metric(stream_id, MetricType.BITRATE, bitrate)


# =============================================================================
# Singleton instance for global access
# =============================================================================

_collector_instance: Optional[StreamMetricsCollector] = None


def get_metrics_collector() -> StreamMetricsCollector:
    """
    Get the global StreamMetricsCollector instance.
    
    Returns:
        StreamMetricsCollector singleton instance
    """
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = StreamMetricsCollector()
    return _collector_instance


def reset_metrics_collector() -> None:
    """Reset the global collector instance (mainly for testing)."""
    global _collector_instance
    _collector_instance = None
