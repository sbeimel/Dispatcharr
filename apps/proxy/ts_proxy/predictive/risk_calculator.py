"""
Risk Score Calculator for the Predictive Failover System.

This module calculates risk scores (0-100) for active streams based on
collected metrics. The risk score indicates the probability of an
imminent stream failure.

Risk Score Components:
- Response Time Analysis (warning/critical thresholds)
- Buffer Underrun Counting
- Bitrate Variance Analysis
- Connection Reset Counting
- Pattern Matching (from Pattern Analyzer)
- Trend Detection

All weights and thresholds are configurable via Web-UI.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Task 5.1: RiskScore Dataclass
# =============================================================================

class RiskReason(Enum):
    """Enumeration of reasons that contribute to risk score."""
    
    RESPONSE_TIME_WARNING = "response_time_warning"
    RESPONSE_TIME_CRITICAL = "response_time_critical"
    BUFFER_UNDERRUN = "buffer_underrun"
    BITRATE_VARIANCE = "bitrate_variance"
    CONNECTION_RESETS = "connection_resets"
    PATTERN_MATCH = "pattern_match"
    RESPONSE_TIME_TREND = "response_time_trend"
    BITRATE_DROP = "bitrate_drop"
    TIME_WINDOW_MATCH = "time_window_match"
    CORRELATION_MATCH = "correlation_match"
    MAC_TOKEN_EXPIRY = "mac_token_expiry"
    MAC_PORTAL_SLOW = "mac_portal_slow"


@dataclass
class RiskContribution:
    """
    Represents a single contribution to the risk score.
    
    Attributes:
        reason: The type of risk factor
        points: Points added to the risk score
        description: Human-readable description
        metric_value: The actual metric value that triggered this
        threshold: The threshold that was exceeded (if applicable)
    """
    reason: RiskReason
    points: int
    description: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'reason': self.reason.value,
            'points': self.points,
            'description': self.description,
            'metric_value': self.metric_value,
            'threshold': self.threshold
        }


@dataclass
class RiskScore:
    """
    Data class representing a calculated risk score for a stream.
    
    The risk score is a value between 0 and 100 indicating the
    probability of an imminent stream failure.
    
    Attributes:
        score: The calculated risk score (0-100, capped)
        reasons: List of RiskContribution objects explaining the score
        stream_id: Identifier of the stream
        channel_id: Optional channel identifier
        timestamp: When the score was calculated
        raw_score: The uncapped score (for debugging)
    
    Requirement 2.1: Score must be between 0 and 100
    """
    
    score: int
    reasons: List[RiskContribution] = field(default_factory=list)
    stream_id: str = ""
    channel_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    raw_score: int = 0
    
    def __post_init__(self):
        """Ensure score is capped between 0 and 100."""
        self.raw_score = self.score
        self.score = max(0, min(100, self.score))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'score': self.score,
            'reasons': [r.to_dict() for r in self.reasons],
            'stream_id': self.stream_id,
            'channel_id': self.channel_id,
            'timestamp': self.timestamp,
            'raw_score': self.raw_score
        }
    
    def to_json(self) -> str:
        """Convert to JSON string for Redis storage."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskScore':
        """Create RiskScore from dictionary."""
        reasons = []
        for r in data.get('reasons', []):
            reasons.append(RiskContribution(
                reason=RiskReason(r['reason']),
                points=r['points'],
                description=r['description'],
                metric_value=r.get('metric_value'),
                threshold=r.get('threshold')
            ))
        
        return cls(
            score=data['score'],
            reasons=reasons,
            stream_id=data.get('stream_id', ''),
            channel_id=data.get('channel_id'),
            timestamp=data.get('timestamp', time.time()),
            raw_score=data.get('raw_score', data['score'])
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RiskScore':
        """Create RiskScore from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def is_warmup_threshold(self, threshold: int) -> bool:
        """Check if score has reached warmup threshold."""
        return self.score >= threshold
    
    def is_failover_threshold(self, threshold: int) -> bool:
        """Check if score has reached failover threshold."""
        return self.score >= threshold
    
    def get_primary_reason(self) -> Optional[RiskContribution]:
        """Get the highest contributing reason."""
        if not self.reasons:
            return None
        return max(self.reasons, key=lambda r: r.points)
    
    def get_reason_summary(self) -> str:
        """Get a summary of all reasons."""
        if not self.reasons:
            return "No risk factors detected"
        
        summaries = [f"{r.reason.value}: +{r.points}" for r in self.reasons]
        return ", ".join(summaries)



# =============================================================================
# Task 5.2-5.7: RiskScoreCalculator Class
# =============================================================================

class RiskScoreCalculator:
    """
    Calculates risk scores for streams based on collected metrics.
    
    The calculator analyzes various metrics and applies configurable
    weights to produce a risk score between 0 and 100.
    
    Requirements:
    - 2.1: Calculate score between 0 and 100
    - 2.2: Response time warning scoring
    - 2.3: Response time critical scoring
    - 2.4: Buffer underrun scoring
    - 2.5: Bitrate variance scoring
    - 2.6: Connection reset scoring
    - 2.7: Pattern matching scoring
    - 2.8: Trend detection scoring
    - 2.9: Sudden bitrate drop scoring
    """
    
    def __init__(self, config=None, metrics_collector=None, redis_client=None):
        """
        Initialize the risk score calculator.
        
        Args:
            config: PredictiveConfig instance (loaded if not provided)
            metrics_collector: StreamMetricsCollector instance
            redis_client: Redis client for storing scores
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
    
    def calculate_risk_score(self, stream_id: str, channel_id: str = None,
                              pattern_confidence: float = None,
                              mac_address: str = None,
                              account_id: int = None) -> RiskScore:
        """
        Calculate the risk score for a stream.
        
        This is the main entry point for risk score calculation.
        It collects recent metrics and applies all scoring rules.
        
        Args:
            stream_id: Unique identifier for the stream
            channel_id: Optional channel identifier
            pattern_confidence: Optional pattern match confidence (0-100)
            mac_address: Optional MAC address for MAC-specific metrics
            account_id: Optional M3U account ID for MAC-specific metrics
            
        Returns:
            RiskScore object with calculated score and reasons
            
        Requirement 2.1: Score must be between 0 and 100
        """
        if not self.config.enabled:
            return RiskScore(score=0, stream_id=stream_id, channel_id=channel_id)
        
        contributions: List[RiskContribution] = []
        
        try:
            # Get recent metrics (last 60 seconds for most, 5 minutes for resets)
            metrics_60s = self._get_metrics_summary(stream_id, seconds=60)
            metrics_5m = self._get_metrics_summary(stream_id, seconds=300)
            
            # Task 5.3: Response Time Scoring
            contributions.extend(
                self._calculate_response_time_score(metrics_60s)
            )
            
            # Task 5.4: Buffer Underrun Scoring
            contributions.extend(
                self._calculate_buffer_underrun_score(metrics_60s)
            )
            
            # Task 5.5: Bitrate Variance Scoring
            contributions.extend(
                self._calculate_bitrate_variance_score(metrics_60s)
            )
            
            # Task 5.6: Connection Reset Scoring
            contributions.extend(
                self._calculate_connection_reset_score(metrics_5m)
            )
            
            # Trend Detection (Requirement 2.8)
            if self.config.trend_detection_enabled:
                contributions.extend(
                    self._calculate_trend_score(metrics_60s)
                )
            
            # Sudden Bitrate Drop (Requirement 2.9)
            contributions.extend(
                self._calculate_bitrate_drop_score(metrics_60s)
            )
            
            # Pattern Matching (Requirement 2.7)
            if pattern_confidence is not None and pattern_confidence > 0:
                contributions.extend(
                    self._calculate_pattern_score(pattern_confidence)
                )
            
            # MAC-specific metrics (Requirement 14.3)
            if mac_address and account_id:
                contributions.extend(
                    self._calculate_mac_risk_score(mac_address, account_id)
                )
            
            # Calculate total score
            total_score = sum(c.points for c in contributions)
            
            # Task 5.7: Cap score to 0-100
            risk_score = RiskScore(
                score=total_score,
                reasons=contributions,
                stream_id=stream_id,
                channel_id=channel_id
            )
            
            # Store in Redis
            self._store_risk_score(risk_score)
            
            return risk_score
            
        except Exception as e:
            logger.error(f"Error calculating risk score for stream {stream_id}: {e}")
            return RiskScore(score=0, stream_id=stream_id, channel_id=channel_id)
    
    def _calculate_mac_risk_score(self, mac_address: str, 
                                   account_id: int) -> List[RiskContribution]:
        """
        Calculate MAC-specific risk score contributions.
        
        Requirement 14.3: MAC-specific risk score factors
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        
        try:
            from .mac_metrics import get_mac_metrics_collector, get_mac_risk_calculator
            
            collector = get_mac_metrics_collector()
            calculator = get_mac_risk_calculator()
            
            mac_metrics = collector.get_mac_metrics(mac_address, account_id)
            if mac_metrics:
                contributions.extend(
                    calculator.calculate_mac_risk_contributions(mac_metrics)
                )
        except Exception as e:
            logger.debug(f"Error calculating MAC risk score: {e}")
        
        return contributions
    
    def _get_metrics_summary(self, stream_id: str, seconds: int = 60) -> Dict[str, Any]:
        """
        Get a summary of metrics for the specified time window.
        
        Args:
            stream_id: Stream identifier
            seconds: Time window in seconds
            
        Returns:
            Dictionary with metric summaries
        """
        from .metrics_collector import MetricType
        
        summary = {
            'response_times': [],
            'buffer_underruns': 0,
            'bitrates': [],
            'connection_statuses': [],
            'bytes_received': [],
        }
        
        if not self.metrics_collector:
            return summary
        
        try:
            # Get response times
            response_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.RESPONSE_TIME, seconds
            )
            summary['response_times'] = [m.value for m in response_metrics]
            
            # Get buffer underruns
            underrun_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.BUFFER_UNDERRUN, seconds
            )
            summary['buffer_underruns'] = len(underrun_metrics)
            
            # Get bitrates
            bitrate_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.BITRATE, seconds
            )
            summary['bitrates'] = [m.value for m in bitrate_metrics]
            
            # Get connection statuses
            status_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.CONNECTION_STATUS, seconds
            )
            summary['connection_statuses'] = [m.value for m in status_metrics]
            
            # Get bytes received
            bytes_metrics = self.metrics_collector.get_recent_metrics(
                stream_id, MetricType.BYTES_RECEIVED, seconds
            )
            summary['bytes_received'] = [m.value for m in bytes_metrics]
            
        except Exception as e:
            logger.error(f"Error getting metrics summary for stream {stream_id}: {e}")
        
        return summary
    
    # =========================================================================
    # Task 5.3: Response Time Scoring
    # =========================================================================
    
    def _calculate_response_time_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from response time.
        
        Requirements:
        - 2.2: Add points when avg response time exceeds warning threshold
        - 2.3: Add additional points when exceeds critical threshold
        
        Args:
            metrics: Metrics summary dictionary
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        response_times = metrics.get('response_times', [])
        
        if not response_times:
            return contributions
        
        avg_response_time = sum(response_times) / len(response_times)
        
        # Check warning threshold (Requirement 2.2)
        if avg_response_time > self.config.response_time_warning:
            contributions.append(RiskContribution(
                reason=RiskReason.RESPONSE_TIME_WARNING,
                points=self.config.response_time_warning_weight,
                description=f"Average response time ({avg_response_time:.0f}ms) exceeds warning threshold",
                metric_value=avg_response_time,
                threshold=self.config.response_time_warning
            ))
        
        # Check critical threshold (Requirement 2.3)
        if avg_response_time > self.config.response_time_critical:
            contributions.append(RiskContribution(
                reason=RiskReason.RESPONSE_TIME_CRITICAL,
                points=self.config.response_time_critical_weight,
                description=f"Average response time ({avg_response_time:.0f}ms) exceeds critical threshold",
                metric_value=avg_response_time,
                threshold=self.config.response_time_critical
            ))
        
        return contributions
    
    # =========================================================================
    # Task 5.4: Buffer Underrun Scoring
    # =========================================================================
    
    def _calculate_buffer_underrun_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from buffer underruns.
        
        Requirement 2.4: Add points per underrun (max 50 total)
        
        Args:
            metrics: Metrics summary dictionary
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        underrun_count = metrics.get('buffer_underruns', 0)
        
        if underrun_count > 0:
            # Calculate points (capped at 50)
            points = min(underrun_count * self.config.buffer_underrun_weight, 50)
            
            contributions.append(RiskContribution(
                reason=RiskReason.BUFFER_UNDERRUN,
                points=points,
                description=f"{underrun_count} buffer underrun(s) in last 60 seconds",
                metric_value=underrun_count,
                threshold=0
            ))
        
        return contributions
    
    # =========================================================================
    # Task 5.5: Bitrate Variance Scoring
    # =========================================================================
    
    def _calculate_bitrate_variance_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from bitrate variance.
        
        Requirement 2.5: Add points when bitrate variance exceeds threshold
        
        Args:
            metrics: Metrics summary dictionary
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        bitrates = metrics.get('bitrates', [])
        
        if len(bitrates) < 2:
            return contributions
        
        # Calculate variance as percentage of mean
        avg_bitrate = sum(bitrates) / len(bitrates)
        if avg_bitrate <= 0:
            return contributions
        
        # Calculate standard deviation
        variance = sum((b - avg_bitrate) ** 2 for b in bitrates) / len(bitrates)
        std_dev = variance ** 0.5
        
        # Variance as percentage of mean
        variance_percent = (std_dev / avg_bitrate) * 100
        
        if variance_percent > self.config.bitrate_variance_threshold:
            contributions.append(RiskContribution(
                reason=RiskReason.BITRATE_VARIANCE,
                points=self.config.bitrate_variance_weight,
                description=f"Bitrate variance ({variance_percent:.1f}%) exceeds threshold",
                metric_value=variance_percent,
                threshold=self.config.bitrate_variance_threshold
            ))
        
        return contributions
    
    # =========================================================================
    # Task 5.6: Connection Reset Scoring
    # =========================================================================
    
    def _calculate_connection_reset_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from connection resets.
        
        Requirement 2.6: Add 20 points when >2 connection resets in 5 minutes
        
        Args:
            metrics: Metrics summary dictionary (5 minute window)
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        statuses = metrics.get('connection_statuses', [])
        
        if len(statuses) < 2:
            return contributions
        
        # Count transitions from connected (1) to disconnected (0 or -1)
        reset_count = 0
        for i in range(1, len(statuses)):
            if statuses[i-1] == 1 and statuses[i] <= 0:
                reset_count += 1
        
        if reset_count > 2:
            contributions.append(RiskContribution(
                reason=RiskReason.CONNECTION_RESETS,
                points=self.config.connection_reset_weight,
                description=f"{reset_count} connection resets in last 5 minutes",
                metric_value=reset_count,
                threshold=2
            ))
        
        return contributions
    
    # =========================================================================
    # Trend Detection (Requirement 2.8)
    # =========================================================================
    
    def _calculate_trend_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from response time trend.
        
        Requirement 2.8: Add 10 points when response time shows rising trend
        (3+ consecutive increases)
        
        Args:
            metrics: Metrics summary dictionary
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        response_times = metrics.get('response_times', [])
        
        if len(response_times) < 4:
            return contributions
        
        # Check for 3+ consecutive increases
        consecutive_increases = 0
        max_consecutive = 0
        
        for i in range(1, len(response_times)):
            if response_times[i] > response_times[i-1]:
                consecutive_increases += 1
                max_consecutive = max(max_consecutive, consecutive_increases)
            else:
                consecutive_increases = 0
        
        if max_consecutive >= 3:
            contributions.append(RiskContribution(
                reason=RiskReason.RESPONSE_TIME_TREND,
                points=self.config.trend_weight,
                description=f"Response time showing rising trend ({max_consecutive} consecutive increases)",
                metric_value=max_consecutive,
                threshold=3
            ))
        
        return contributions
    
    # =========================================================================
    # Bitrate Drop Detection (Requirement 2.9)
    # =========================================================================
    
    def _calculate_bitrate_drop_score(self, metrics: Dict[str, Any]) -> List[RiskContribution]:
        """
        Calculate risk score contribution from sudden bitrate drop.
        
        Requirement 2.9: Add 25 points when bitrate drops by >50%
        
        Args:
            metrics: Metrics summary dictionary
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        bitrates = metrics.get('bitrates', [])
        
        if len(bitrates) < 2:
            return contributions
        
        # Check for sudden drop (compare recent to earlier)
        # Use first half average vs second half average
        mid = len(bitrates) // 2
        if mid < 1:
            return contributions
        
        first_half_avg = sum(bitrates[:mid]) / mid
        second_half_avg = sum(bitrates[mid:]) / (len(bitrates) - mid)
        
        if first_half_avg <= 0:
            return contributions
        
        drop_percent = ((first_half_avg - second_half_avg) / first_half_avg) * 100
        
        if drop_percent > 50:
            contributions.append(RiskContribution(
                reason=RiskReason.BITRATE_DROP,
                points=self.config.bitrate_drop_weight,
                description=f"Bitrate dropped by {drop_percent:.1f}%",
                metric_value=drop_percent,
                threshold=50
            ))
        
        return contributions
    
    # =========================================================================
    # Pattern Matching (Requirement 2.7)
    # =========================================================================
    
    def _calculate_pattern_score(self, pattern_confidence: float) -> List[RiskContribution]:
        """
        Calculate risk score contribution from pattern matching.
        
        Requirement 2.7: Add points based on pattern confidence
        (confidence% * 0.4, max 40)
        
        Args:
            pattern_confidence: Pattern match confidence (0-100)
            
        Returns:
            List of RiskContribution objects
        """
        contributions = []
        
        if pattern_confidence <= 0:
            return contributions
        
        # Calculate points: confidence * factor, capped at max
        points = int(pattern_confidence * self.config.pattern_confidence_factor)
        points = min(points, self.config.pattern_max_weight)
        
        if points > 0:
            contributions.append(RiskContribution(
                reason=RiskReason.PATTERN_MATCH,
                points=points,
                description=f"Known failure pattern matched with {pattern_confidence:.0f}% confidence",
                metric_value=pattern_confidence,
                threshold=self.config.pattern_confidence_threshold
            ))
        
        return contributions
    
    # =========================================================================
    # Redis Storage
    # =========================================================================
    
    def _store_risk_score(self, risk_score: RiskScore) -> bool:
        """
        Store risk score in Redis.
        
        Args:
            risk_score: RiskScore object to store
            
        Returns:
            True if stored successfully
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._redis_keys.risk_score(risk_score.stream_id)
            self.redis_client.setex(
                key,
                self._redis_keys.RISK_SCORE_TTL,
                risk_score.to_json()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store risk score: {e}")
            return False
    
    def get_risk_score(self, stream_id: str) -> Optional[RiskScore]:
        """
        Get the current risk score for a stream from Redis.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            RiskScore object or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._redis_keys.risk_score(stream_id)
            data = self.redis_client.get(key)
            
            if data:
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                return RiskScore.from_json(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get risk score for stream {stream_id}: {e}")
            return None
    
    def get_all_risk_scores(self) -> Dict[str, RiskScore]:
        """
        Get all current risk scores.
        
        Returns:
            Dictionary mapping stream_id to RiskScore
        """
        if not self.redis_client:
            return {}
        
        scores = {}
        
        try:
            pattern = self._redis_keys.all_risk_scores_pattern()
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                # Extract stream_id from key
                parts = key.split(':')
                if len(parts) >= 3:
                    stream_id = parts[2]
                    score = self.get_risk_score(stream_id)
                    if score:
                        scores[stream_id] = score
            
            return scores
            
        except Exception as e:
            logger.error(f"Failed to get all risk scores: {e}")
            return {}


# =============================================================================
# Singleton instance for global access
# =============================================================================

_calculator_instance: Optional[RiskScoreCalculator] = None


def get_risk_calculator() -> RiskScoreCalculator:
    """
    Get the global RiskScoreCalculator instance.
    
    Returns:
        RiskScoreCalculator singleton instance
    """
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = RiskScoreCalculator()
    return _calculator_instance


def reset_risk_calculator() -> None:
    """Reset the global calculator instance (mainly for testing)."""
    global _calculator_instance
    _calculator_instance = None
