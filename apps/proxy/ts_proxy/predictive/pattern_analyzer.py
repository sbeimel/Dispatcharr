"""
Pattern Analyzer for the Predictive Failover System.

This module is responsible for:
- Recording failure events and their preceding metrics
- Identifying common patterns across multiple failures
- Matching current metrics against known patterns
- Managing pattern confidence scores

Requirements: 3.1, 3.2, 3.3, 3.4, 2.7
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# Task 6.1: FailurePattern Dataclass (runtime representation)
# =============================================================================

@dataclass
class FailurePatternData:
    """
    Runtime data class representing a failure pattern.
    
    This is used for pattern analysis before persisting to the database.
    The Django model FailurePattern is used for persistence.
    
    Attributes:
        pattern_type: Type of pattern (response_time, buffer_underrun, etc.)
        metrics_snapshot: Metrics captured before the failure
        confidence: Confidence score (0-100)
        stream_id: Stream where pattern was observed
        channel_id: Channel where pattern was observed
        m3u_account_id: M3U account ID if applicable
        timestamp: When the failure occurred
        day_of_week: Day of week (0=Monday, 6=Sunday)
        hour_of_day: Hour when failure occurred (0-23)
    """
    
    pattern_type: str
    metrics_snapshot: Dict[str, Any]
    confidence: int = 50
    stream_id: Optional[str] = None
    channel_id: Optional[str] = None
    m3u_account_id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    day_of_week: int = field(default_factory=lambda: datetime.now().weekday())
    hour_of_day: int = field(default_factory=lambda: datetime.now().hour)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailurePatternData':
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# Task 6.2-6.6: PatternAnalyzer Class
# =============================================================================

class PatternAnalyzer:
    """
    Analyzes stream failures to identify and learn patterns.
    
    The analyzer:
    - Records metrics before failures for pattern learning
    - Identifies common patterns after multiple failures
    - Matches current metrics against known patterns
    - Updates pattern confidence based on prediction accuracy
    
    Requirements:
    - 3.1: Store metrics from last 5 minutes before failure
    - 3.2: Identify patterns after 3+ failures
    - 3.3: Store patterns with confidence score
    - 3.4: Match current metrics against patterns
    - 2.7: Contribute pattern matches to risk score
    """
    
    # Pattern types
    PATTERN_RESPONSE_TIME = "response_time"
    PATTERN_BUFFER_UNDERRUN = "buffer_underrun"
    PATTERN_BITRATE_DROP = "bitrate_drop"
    PATTERN_CONNECTION_RESET = "connection_reset"
    PATTERN_TIME_WINDOW = "time_window"
    PATTERN_CORRELATION = "correlation"
    PATTERN_COMPOSITE = "composite"
    
    # Minimum failures needed to identify a pattern
    MIN_FAILURES_FOR_PATTERN = 3
    
    # Confidence thresholds
    DEFAULT_CONFIDENCE = 50
    MIN_CONFIDENCE_FOR_MATCH = 40
    CONFIDENCE_INCREASE_ON_SUCCESS = 5
    CONFIDENCE_DECREASE_ON_FALSE_POSITIVE = 10
    
    def __init__(self, config=None, metrics_collector=None, redis_client=None):
        """
        Initialize the pattern analyzer.
        
        Args:
            config: PredictiveConfig instance
            metrics_collector: StreamMetricsCollector instance
            redis_client: Redis client for temporary storage
        """
        self._config = config
        self._metrics_collector = metrics_collector
        self._redis_client = redis_client
        
        # Import here to avoid circular imports
        from .redis_keys import PredictiveRedisKeys
        self._redis_keys = PredictiveRedisKeys
    
    @property
    def config(self):
        """Lazy load config if not provided."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load predictive config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    @property
    def metrics_collector(self):
        """Lazy load metrics collector if not provided."""
        if self._metrics_collector is None:
            try:
                from .metrics_collector import get_metrics_collector
                self._metrics_collector = get_metrics_collector()
            except Exception as e:
                logger.error(f"Failed to get metrics collector: {e}")
        return self._metrics_collector
    
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
    
    # =========================================================================
    # Task 6.3: record_failure() Method
    # =========================================================================
    
    def record_failure(self, stream_id: str, channel_id: str = None,
                       m3u_account_id: int = None, failure_reason: str = None) -> bool:
        """
        Record a stream failure and capture metrics for pattern learning.
        
        Requirement 3.1: Store metrics from last 5 minutes before failure
        
        Args:
            stream_id: Stream identifier
            channel_id: Channel identifier
            m3u_account_id: M3U account ID if applicable
            failure_reason: Optional reason for the failure
            
        Returns:
            True if recorded successfully
        """
        if not self.config.enabled or not self.config.pattern_learning_enabled:
            return False
        
        try:
            # Get metrics from last 5 minutes
            metrics_snapshot = self._capture_metrics_snapshot(stream_id, seconds=300)
            
            if not metrics_snapshot:
                logger.debug(f"No metrics available for failure recording on stream {stream_id}")
                return False
            
            # Determine pattern type from metrics
            pattern_type = self._determine_pattern_type(metrics_snapshot)
            
            # Create failure pattern data
            pattern_data = FailurePatternData(
                pattern_type=pattern_type,
                metrics_snapshot=metrics_snapshot,
                stream_id=stream_id,
                channel_id=channel_id,
                m3u_account_id=m3u_account_id
            )
            
            # Store in Redis for later analysis
            self._store_failure_record(pattern_data)
            
            # Log the failure event
            self._log_failure_event(stream_id, channel_id, m3u_account_id, 
                                    pattern_type, failure_reason)
            
            # Trigger pattern analysis if we have enough failures
            self._maybe_analyze_patterns(stream_id, m3u_account_id)
            
            logger.info(f"Recorded failure for stream {stream_id}, pattern type: {pattern_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record failure for stream {stream_id}: {e}")
            return False
    
    def _capture_metrics_snapshot(self, stream_id: str, seconds: int = 300) -> Dict[str, Any]:
        """Capture a snapshot of recent metrics for pattern analysis."""
        if not self.metrics_collector:
            return {}
        
        from .metrics_collector import MetricType
        
        snapshot = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'avg_response_time': 0,
            'max_response_time': 0,
            'bitrate_variance': 0,
            'connection_resets': 0,
        }
        
        try:
            # Get response times
            response_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.RESPONSE_TIME, seconds
            )
            snapshot['response_times'] = [m.value for m in response_metrics]
            if snapshot['response_times']:
                snapshot['avg_response_time'] = sum(snapshot['response_times']) / len(snapshot['response_times'])
                snapshot['max_response_time'] = max(snapshot['response_times'])
            
            # Get buffer underruns
            underrun_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.BUFFER_UNDERRUN, seconds
            )
            snapshot['buffer_underruns'] = len(underrun_metrics)
            
            # Get bitrates
            bitrate_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.BITRATE, seconds
            )
            snapshot['bitrates'] = [m.value for m in bitrate_metrics]
            if len(snapshot['bitrates']) >= 2:
                avg_bitrate = sum(snapshot['bitrates']) / len(snapshot['bitrates'])
                if avg_bitrate > 0:
                    variance = sum((b - avg_bitrate) ** 2 for b in snapshot['bitrates']) / len(snapshot['bitrates'])
                    snapshot['bitrate_variance'] = (variance ** 0.5 / avg_bitrate) * 100
            
            # Get connection statuses and count resets
            status_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.CONNECTION_STATUS, seconds
            )
            snapshot['connection_statuses'] = [m.value for m in status_metrics]
            for i in range(1, len(snapshot['connection_statuses'])):
                if snapshot['connection_statuses'][i-1] == 1 and snapshot['connection_statuses'][i] <= 0:
                    snapshot['connection_resets'] += 1
            
        except Exception as e:
            logger.error(f"Error capturing metrics snapshot: {e}")
        
        return snapshot
    
    def _determine_pattern_type(self, metrics: Dict[str, Any]) -> str:
        """Determine the primary pattern type from metrics."""
        # Check for connection reset pattern
        if metrics.get('connection_resets', 0) > 2:
            return self.PATTERN_CONNECTION_RESET
        
        # Check for buffer underrun pattern
        if metrics.get('buffer_underruns', 0) > 0:
            return self.PATTERN_BUFFER_UNDERRUN
        
        # Check for bitrate drop pattern
        if metrics.get('bitrate_variance', 0) > 50:
            return self.PATTERN_BITRATE_DROP
        
        # Check for response time pattern
        if metrics.get('avg_response_time', 0) > self.config.response_time_critical:
            return self.PATTERN_RESPONSE_TIME
        
        # Default to composite
        return self.PATTERN_COMPOSITE
    
    def _store_failure_record(self, pattern_data: FailurePatternData) -> None:
        """Store failure record in Redis for later analysis."""
        if not self.redis_client:
            return
        
        try:
            # Key based on stream or account
            if pattern_data.m3u_account_id:
                key = f"predictive:failures:account:{pattern_data.m3u_account_id}"
            else:
                key = f"predictive:failures:stream:{pattern_data.stream_id}"
            
            # Store as list entry
            self.redis_client.lpush(key, json.dumps(pattern_data.to_dict()))
            
            # Keep only last 100 failures
            self.redis_client.ltrim(key, 0, 99)
            
            # Set TTL of 30 days
            self.redis_client.expire(key, 30 * 24 * 3600)
            
        except Exception as e:
            logger.error(f"Failed to store failure record: {e}")
    
    def _log_failure_event(self, stream_id: str, channel_id: str,
                           m3u_account_id: int, pattern_type: str,
                           failure_reason: str) -> None:
        """Log failure event to database."""
        try:
            from .models import PredictiveFailoverEvent
            
            PredictiveFailoverEvent.log_event(
                event_type=PredictiveFailoverEvent.EventType.PATTERN_LEARNED,
                channel_id=channel_id,
                stream_id=stream_id,
                reason=f"Failure recorded: {pattern_type}. {failure_reason or ''}",
                m3u_account_id=m3u_account_id
            )
        except Exception as e:
            logger.debug(f"Could not log failure event: {e}")
    
    def _maybe_analyze_patterns(self, stream_id: str, m3u_account_id: int = None) -> None:
        """Trigger pattern analysis if we have enough failures."""
        if not self.redis_client:
            return
        
        try:
            # Get failure count
            if m3u_account_id:
                key = f"predictive:failures:account:{m3u_account_id}"
            else:
                key = f"predictive:failures:stream:{stream_id}"
            
            failure_count = self.redis_client.llen(key)
            
            if failure_count >= self.MIN_FAILURES_FOR_PATTERN:
                self.analyze_patterns(stream_id, m3u_account_id)
                
        except Exception as e:
            logger.error(f"Error checking failure count: {e}")

    
    # =========================================================================
    # Task 6.4: analyze_patterns() Method
    # =========================================================================
    
    def analyze_patterns(self, stream_id: str = None, 
                         m3u_account_id: int = None) -> List[Dict[str, Any]]:
        """
        Analyze recorded failures to identify common patterns.
        
        Requirement 3.2: Identify patterns after 3+ failures
        Requirement 3.3: Store patterns with confidence score
        
        Args:
            stream_id: Optional stream to analyze
            m3u_account_id: Optional M3U account to analyze
            
        Returns:
            List of identified patterns
        """
        if not self.config.enabled or not self.config.pattern_learning_enabled:
            return []
        
        identified_patterns = []
        
        try:
            # Get failure records
            failures = self._get_failure_records(stream_id, m3u_account_id)
            
            if len(failures) < self.MIN_FAILURES_FOR_PATTERN:
                return []
            
            # Group failures by pattern type
            by_type = {}
            for failure in failures:
                ptype = failure.get('pattern_type', self.PATTERN_COMPOSITE)
                if ptype not in by_type:
                    by_type[ptype] = []
                by_type[ptype].append(failure)
            
            # Analyze each pattern type
            for pattern_type, type_failures in by_type.items():
                if len(type_failures) >= self.MIN_FAILURES_FOR_PATTERN:
                    pattern = self._create_pattern_from_failures(
                        pattern_type, type_failures, m3u_account_id
                    )
                    if pattern:
                        identified_patterns.append(pattern)
            
            # Analyze time-based patterns
            if self.config.time_pattern_enabled:
                time_patterns = self._analyze_time_patterns(failures, m3u_account_id)
                identified_patterns.extend(time_patterns)
            
            # Save identified patterns to database
            for pattern in identified_patterns:
                self._save_pattern_to_db(pattern, m3u_account_id)
            
            logger.info(f"Identified {len(identified_patterns)} patterns from {len(failures)} failures")
            return identified_patterns
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return []
    
    def _get_failure_records(self, stream_id: str = None, 
                             m3u_account_id: int = None) -> List[Dict[str, Any]]:
        """Get failure records from Redis."""
        if not self.redis_client:
            return []
        
        failures = []
        
        try:
            if m3u_account_id:
                key = f"predictive:failures:account:{m3u_account_id}"
            elif stream_id:
                key = f"predictive:failures:stream:{stream_id}"
            else:
                return []
            
            records = self.redis_client.lrange(key, 0, -1)
            
            for record in records:
                if isinstance(record, bytes):
                    record = record.decode('utf-8')
                failures.append(json.loads(record))
            
        except Exception as e:
            logger.error(f"Error getting failure records: {e}")
        
        return failures
    
    def _create_pattern_from_failures(self, pattern_type: str, 
                                       failures: List[Dict[str, Any]],
                                       m3u_account_id: int = None) -> Optional[Dict[str, Any]]:
        """Create a pattern from multiple failure records."""
        if len(failures) < self.MIN_FAILURES_FOR_PATTERN:
            return None
        
        # Calculate average metrics across failures
        avg_metrics = {
            'avg_response_time': 0,
            'max_response_time': 0,
            'buffer_underruns': 0,
            'bitrate_variance': 0,
            'connection_resets': 0,
        }
        
        for failure in failures:
            snapshot = failure.get('metrics_snapshot', {})
            avg_metrics['avg_response_time'] += snapshot.get('avg_response_time', 0)
            avg_metrics['max_response_time'] = max(
                avg_metrics['max_response_time'], 
                snapshot.get('max_response_time', 0)
            )
            avg_metrics['buffer_underruns'] += snapshot.get('buffer_underruns', 0)
            avg_metrics['bitrate_variance'] += snapshot.get('bitrate_variance', 0)
            avg_metrics['connection_resets'] += snapshot.get('connection_resets', 0)
        
        count = len(failures)
        avg_metrics['avg_response_time'] /= count
        avg_metrics['buffer_underruns'] /= count
        avg_metrics['bitrate_variance'] /= count
        avg_metrics['connection_resets'] /= count
        
        # Calculate initial confidence based on consistency
        confidence = min(50 + (count - self.MIN_FAILURES_FOR_PATTERN) * 5, 80)
        
        return {
            'name': f"{pattern_type.replace('_', ' ').title()} Pattern",
            'pattern_type': pattern_type,
            'pattern_data': {
                'avg_metrics': avg_metrics,
                'failure_count': count,
                'thresholds': self._calculate_thresholds(avg_metrics, pattern_type)
            },
            'confidence': confidence,
            'm3u_account_id': m3u_account_id,
        }
    
    def _calculate_thresholds(self, avg_metrics: Dict[str, float], 
                               pattern_type: str) -> Dict[str, float]:
        """Calculate matching thresholds from average metrics."""
        # Use 80% of average as threshold for matching
        return {
            'response_time_threshold': avg_metrics['avg_response_time'] * 0.8,
            'buffer_underrun_threshold': max(1, avg_metrics['buffer_underruns'] * 0.8),
            'bitrate_variance_threshold': avg_metrics['bitrate_variance'] * 0.8,
            'connection_reset_threshold': max(1, avg_metrics['connection_resets'] * 0.8),
        }
    
    def _analyze_time_patterns(self, failures: List[Dict[str, Any]],
                                m3u_account_id: int = None) -> List[Dict[str, Any]]:
        """Analyze failures for time-based patterns."""
        patterns = []
        
        # Group by hour of day
        by_hour = {}
        for failure in failures:
            hour = failure.get('hour_of_day', 0)
            if hour not in by_hour:
                by_hour[hour] = []
            by_hour[hour].append(failure)
        
        # Find hours with multiple failures
        for hour, hour_failures in by_hour.items():
            if len(hour_failures) >= self.MIN_FAILURES_FOR_PATTERN:
                patterns.append({
                    'name': f"Time Window Pattern ({hour:02d}:00-{(hour+1)%24:02d}:00)",
                    'pattern_type': self.PATTERN_TIME_WINDOW,
                    'pattern_data': {
                        'hour_start': hour,
                        'hour_end': (hour + 1) % 24,
                        'failure_count': len(hour_failures),
                    },
                    'confidence': min(50 + len(hour_failures) * 5, 75),
                    'm3u_account_id': m3u_account_id,
                })
        
        return patterns
    
    def _save_pattern_to_db(self, pattern: Dict[str, Any], 
                            m3u_account_id: int = None) -> None:
        """Save or update pattern in database."""
        try:
            from .models import FailurePattern
            from apps.m3u.models import M3UAccount
            
            m3u_account = None
            if m3u_account_id:
                try:
                    m3u_account = M3UAccount.objects.get(id=m3u_account_id)
                except M3UAccount.DoesNotExist:
                    pass
            
            # Check if similar pattern exists
            existing = FailurePattern.objects.filter(
                pattern_type=pattern['pattern_type'],
                m3u_account=m3u_account,
                status__in=[FailurePattern.Status.ACTIVE, FailurePattern.Status.CONFIRMED]
            ).first()
            
            if existing:
                # Update existing pattern
                existing.pattern_data = pattern['pattern_data']
                existing.confidence = max(existing.confidence, pattern['confidence'])
                existing.save()
                logger.debug(f"Updated existing pattern: {existing.name}")
            else:
                # Create new pattern
                FailurePattern.objects.create(
                    name=pattern['name'],
                    pattern_type=pattern['pattern_type'],
                    pattern_data=pattern['pattern_data'],
                    confidence=pattern['confidence'],
                    m3u_account=m3u_account,
                )
                logger.info(f"Created new pattern: {pattern['name']}")
                
        except Exception as e:
            logger.error(f"Failed to save pattern to database: {e}")
    
    # =========================================================================
    # Task 6.5: check_pattern_match() Method
    # =========================================================================
    
    def check_pattern_match(self, stream_id: str, 
                            m3u_account_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Check if current metrics match any known failure patterns.
        
        Requirement 3.4: Match current metrics against patterns with confidence threshold
        
        Args:
            stream_id: Stream to check
            m3u_account_id: Optional M3U account for account-specific patterns
            
        Returns:
            Dict with matched pattern info and confidence, or None
        """
        if not self.config.enabled:
            return None
        
        try:
            # Get current metrics
            current_metrics = self._capture_metrics_snapshot(stream_id, seconds=60)
            
            if not current_metrics:
                return None
            
            # Get active patterns
            patterns = self._get_active_patterns(m3u_account_id)
            
            best_match = None
            best_confidence = 0
            
            for pattern in patterns:
                match_confidence = self._calculate_match_confidence(
                    current_metrics, pattern
                )
                
                if match_confidence > best_confidence:
                    best_confidence = match_confidence
                    best_match = pattern
            
            # Check if best match exceeds threshold
            threshold = self.config.pattern_confidence_threshold
            if best_match and best_confidence >= threshold:
                # Record the hit
                self._record_pattern_hit(best_match)
                
                return {
                    'pattern_id': best_match.id if hasattr(best_match, 'id') else None,
                    'pattern_name': best_match.name if hasattr(best_match, 'name') else 'Unknown',
                    'pattern_type': best_match.pattern_type if hasattr(best_match, 'pattern_type') else 'unknown',
                    'confidence': best_confidence,
                    'pattern_confidence': best_match.confidence if hasattr(best_match, 'confidence') else 50,
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking pattern match: {e}")
            return None
    
    def _get_active_patterns(self, m3u_account_id: int = None):
        """Get active patterns from database."""
        try:
            from .models import FailurePattern
            from apps.m3u.models import M3UAccount
            
            m3u_account = None
            if m3u_account_id:
                try:
                    m3u_account = M3UAccount.objects.get(id=m3u_account_id)
                except M3UAccount.DoesNotExist:
                    pass
            
            return FailurePattern.get_active_patterns(m3u_account)
            
        except Exception as e:
            logger.error(f"Error getting active patterns: {e}")
            return []
    
    def _calculate_match_confidence(self, current_metrics: Dict[str, Any],
                                     pattern) -> float:
        """Calculate how well current metrics match a pattern."""
        try:
            pattern_data = pattern.pattern_data if hasattr(pattern, 'pattern_data') else {}
            thresholds = pattern_data.get('thresholds', {})
            avg_metrics = pattern_data.get('avg_metrics', {})
            
            if not thresholds and not avg_metrics:
                return 0
            
            # Calculate match score for each metric
            scores = []
            
            # Response time match
            if current_metrics.get('avg_response_time', 0) > 0:
                threshold = thresholds.get('response_time_threshold', 
                                          avg_metrics.get('avg_response_time', 0) * 0.8)
                if threshold > 0 and current_metrics['avg_response_time'] >= threshold:
                    scores.append(min(100, (current_metrics['avg_response_time'] / threshold) * 50))
            
            # Buffer underrun match
            if current_metrics.get('buffer_underruns', 0) > 0:
                threshold = thresholds.get('buffer_underrun_threshold', 1)
                if current_metrics['buffer_underruns'] >= threshold:
                    scores.append(min(100, current_metrics['buffer_underruns'] * 30))
            
            # Bitrate variance match
            if current_metrics.get('bitrate_variance', 0) > 0:
                threshold = thresholds.get('bitrate_variance_threshold',
                                          avg_metrics.get('bitrate_variance', 0) * 0.8)
                if threshold > 0 and current_metrics['bitrate_variance'] >= threshold:
                    scores.append(min(100, (current_metrics['bitrate_variance'] / threshold) * 50))
            
            # Connection reset match
            if current_metrics.get('connection_resets', 0) > 0:
                threshold = thresholds.get('connection_reset_threshold', 1)
                if current_metrics['connection_resets'] >= threshold:
                    scores.append(min(100, current_metrics['connection_resets'] * 25))
            
            # Time window match
            pattern_type = pattern.pattern_type if hasattr(pattern, 'pattern_type') else ''
            if pattern_type == self.PATTERN_TIME_WINDOW:
                hour_start = pattern_data.get('hour_start', 0)
                hour_end = pattern_data.get('hour_end', 0)
                current_hour = datetime.now().hour
                
                if hour_start <= current_hour < hour_end or \
                   (hour_end < hour_start and (current_hour >= hour_start or current_hour < hour_end)):
                    scores.append(80)  # Strong match for time window
            
            if not scores:
                return 0
            
            # Average score, weighted by pattern confidence
            avg_score = sum(scores) / len(scores)
            pattern_confidence = pattern.confidence if hasattr(pattern, 'confidence') else 50
            
            return (avg_score * pattern_confidence) / 100
            
        except Exception as e:
            logger.error(f"Error calculating match confidence: {e}")
            return 0
    
    def _record_pattern_hit(self, pattern) -> None:
        """Record that a pattern was matched."""
        try:
            if hasattr(pattern, 'record_hit'):
                # Don't mark as success yet - that happens after we verify
                pattern.hit_count += 1
                pattern.last_hit = datetime.now()
                pattern.save(update_fields=['hit_count', 'last_hit', 'updated_at'])
        except Exception as e:
            logger.debug(f"Could not record pattern hit: {e}")
    
    # =========================================================================
    # Task 6.6: Integration with Risk Score Calculator
    # =========================================================================
    
    def get_pattern_confidence_for_risk_score(self, stream_id: str,
                                               m3u_account_id: int = None) -> float:
        """
        Get pattern match confidence for risk score calculation.
        
        Requirement 2.7: Contribute pattern matches to risk score
        
        Args:
            stream_id: Stream to check
            m3u_account_id: Optional M3U account ID
            
        Returns:
            Pattern confidence (0-100) or 0 if no match
        """
        match = self.check_pattern_match(stream_id, m3u_account_id)
        
        if match:
            return match['confidence']
        
        return 0
    
    # =========================================================================
    # Pattern Feedback Methods
    # =========================================================================
    
    def record_prediction_success(self, pattern_id: int) -> None:
        """
        Record that a pattern-based prediction was successful.
        
        Requirement 3.6: Increase confidence on successful prediction
        """
        try:
            from .models import FailurePattern
            
            pattern = FailurePattern.objects.get(id=pattern_id)
            pattern.record_hit(success=True)
            
            logger.debug(f"Recorded successful prediction for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to record prediction success: {e}")
    
    def record_prediction_failure(self, pattern_id: int) -> None:
        """
        Record that a pattern-based prediction was a false positive.
        
        Requirement 3.7: Decrease confidence on false positive
        """
        try:
            from .models import FailurePattern
            
            pattern = FailurePattern.objects.get(id=pattern_id)
            pattern.record_hit(success=False)
            
            logger.debug(f"Recorded false positive for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to record prediction failure: {e}")
    
    def cleanup_low_confidence_patterns(self, threshold: int = 30) -> int:
        """
        Remove patterns with confidence below threshold.
        
        Requirement 3.5: Weekly cleanup of low confidence patterns
        
        Args:
            threshold: Minimum confidence to keep
            
        Returns:
            Number of patterns removed
        """
        try:
            from .models import FailurePattern
            
            deleted = FailurePattern.cleanup_low_confidence(threshold)
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} low confidence patterns")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup patterns: {e}")
            return 0


# =============================================================================
# Singleton instance for global access
# =============================================================================

_analyzer_instance: Optional[PatternAnalyzer] = None


def get_pattern_analyzer() -> PatternAnalyzer:
    """
    Get the global PatternAnalyzer instance.
    
    Returns:
        PatternAnalyzer singleton instance
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = PatternAnalyzer()
    return _analyzer_instance


def reset_pattern_analyzer() -> None:
    """Reset the global analyzer instance (mainly for testing)."""
    global _analyzer_instance
    _analyzer_instance = None
