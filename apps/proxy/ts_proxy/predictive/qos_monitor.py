"""
Quality of Service (QoS) Monitor for the Predictive Failover System.

This module provides video quality monitoring:
- Video freeze detection
- Black frame detection
- Bitrate quality scoring
- Integration with risk score calculation

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class QoSMetricType(Enum):
    """Types of QoS metrics."""
    VIDEO_FREEZE = "video_freeze"
    BLACK_FRAME = "black_frame"
    LOW_BITRATE = "low_bitrate"
    AUDIO_SYNC = "audio_sync"
    FRAME_DROP = "frame_drop"


@dataclass
class QoSMetric:
    """
    A single QoS metric measurement.
    
    Attributes:
        metric_type: Type of QoS metric
        value: Metric value
        timestamp: When measured
        stream_id: Stream identifier
        duration_ms: Duration of the issue in milliseconds
        severity: Severity level (1-10)
    """
    metric_type: QoSMetricType
    value: float
    timestamp: float
    stream_id: str
    duration_ms: float = 0
    severity: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp,
            'stream_id': self.stream_id,
            'duration_ms': self.duration_ms,
            'severity': self.severity,
        }


@dataclass
class QoSScore:
    """
    Quality of Service score for a stream.
    
    Attributes:
        score: Overall QoS score (0-100, higher is better)
        video_freeze_count: Number of video freezes
        black_frame_count: Number of black frame events
        bitrate_quality: Bitrate quality percentage
        issues: List of detected issues
    """
    score: int = 100
    video_freeze_count: int = 0
    black_frame_count: int = 0
    bitrate_quality: float = 100.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'score': self.score,
            'video_freeze_count': self.video_freeze_count,
            'black_frame_count': self.black_frame_count,
            'bitrate_quality': self.bitrate_quality,
            'issues': self.issues,
        }


class QoSMonitor:
    """
    Monitors video quality for streams.
    
    Requirements:
    - 15.1: Detect video freezes >2 seconds
    - 15.2: Detect black frames (>10 consecutive)
    - 15.3: Calculate bitrate quality score
    - 15.4: Integrate with risk score
    """
    
    # Thresholds
    FREEZE_THRESHOLD_MS = 2000  # 2 seconds
    BLACK_FRAME_THRESHOLD = 10  # consecutive frames
    LOW_BITRATE_THRESHOLD = 0.5  # 50% of expected
    
    def __init__(self, config=None, redis_client=None):
        """
        Initialize the QoS monitor.
        
        Args:
            config: PredictiveConfig instance
            redis_client: Redis client for storage
        """
        self._config = config
        self._redis_client = redis_client
        self._stream_data: Dict[str, Dict[str, Any]] = {}
        self._qos_scores: Dict[str, QoSScore] = {}
    
    @property
    def config(self):
        """Lazy load config."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    @property
    def redis_client(self):
        """Lazy load Redis client."""
        if self._redis_client is None:
            try:
                from django_redis import get_redis_connection
                self._redis_client = get_redis_connection("default")
            except Exception as e:
                logger.error(f"Failed to get Redis connection: {e}")
        return self._redis_client
    
    def is_enabled(self) -> bool:
        """Check if QoS monitoring is enabled."""
        return self.config.quality_monitoring_enabled
    
    def start_monitoring(self, stream_id: str, expected_bitrate: float = None) -> bool:
        """
        Start QoS monitoring for a stream.
        
        Args:
            stream_id: Stream identifier
            expected_bitrate: Expected bitrate in bps
            
        Returns:
            True if started successfully
        """
        if not self.is_enabled():
            return False
        
        self._stream_data[stream_id] = {
            'started_at': time.time(),
            'expected_bitrate': expected_bitrate,
            'last_frame_time': time.time(),
            'consecutive_black_frames': 0,
            'freeze_events': [],
            'black_frame_events': [],
            'bitrate_samples': [],
        }
        
        self._qos_scores[stream_id] = QoSScore()
        
        logger.debug(f"Started QoS monitoring for stream {stream_id}")
        return True
    
    def stop_monitoring(self, stream_id: str) -> bool:
        """
        Stop QoS monitoring for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if stopped successfully
        """
        if stream_id in self._stream_data:
            del self._stream_data[stream_id]
        if stream_id in self._qos_scores:
            del self._qos_scores[stream_id]
        
        logger.debug(f"Stopped QoS monitoring for stream {stream_id}")
        return True

    def record_frame(self, stream_id: str, is_black: bool = False,
                     bitrate: float = None) -> bool:
        """
        Record a frame for QoS analysis.
        
        Args:
            stream_id: Stream identifier
            is_black: Whether the frame is black
            bitrate: Current bitrate in bps
            
        Returns:
            True if recorded successfully
        """
        if stream_id not in self._stream_data:
            return False
        
        now = time.time()
        data = self._stream_data[stream_id]
        
        # Check for video freeze (Requirement 15.1)
        time_since_last = (now - data['last_frame_time']) * 1000  # ms
        if time_since_last > self.FREEZE_THRESHOLD_MS:
            self._record_freeze(stream_id, time_since_last)
        
        data['last_frame_time'] = now
        
        # Check for black frames (Requirement 15.2)
        if is_black:
            data['consecutive_black_frames'] += 1
            if data['consecutive_black_frames'] >= self.BLACK_FRAME_THRESHOLD:
                self._record_black_frames(stream_id, data['consecutive_black_frames'])
        else:
            data['consecutive_black_frames'] = 0
        
        # Track bitrate (Requirement 15.3)
        if bitrate is not None:
            data['bitrate_samples'].append(bitrate)
            # Keep last 100 samples
            if len(data['bitrate_samples']) > 100:
                data['bitrate_samples'] = data['bitrate_samples'][-100:]
        
        # Recalculate QoS score
        self._recalculate_score(stream_id)
        
        return True
    
    def record_video_freeze(self, stream_id: str, duration_ms: float) -> bool:
        """
        Record a video freeze event.
        
        Requirement 15.1: Detect video freezes >2 seconds
        
        Args:
            stream_id: Stream identifier
            duration_ms: Freeze duration in milliseconds
            
        Returns:
            True if recorded successfully
        """
        if stream_id not in self._stream_data:
            return False
        
        if duration_ms >= self.FREEZE_THRESHOLD_MS:
            self._record_freeze(stream_id, duration_ms)
            return True
        
        return False
    
    def _record_freeze(self, stream_id: str, duration_ms: float):
        """Record a freeze event internally."""
        data = self._stream_data[stream_id]
        score = self._qos_scores[stream_id]
        
        event = {
            'type': 'video_freeze',
            'timestamp': time.time(),
            'duration_ms': duration_ms,
        }
        
        data['freeze_events'].append(event)
        score.video_freeze_count += 1
        score.issues.append(event)
        
        # Keep last 50 events
        if len(data['freeze_events']) > 50:
            data['freeze_events'] = data['freeze_events'][-50:]
        if len(score.issues) > 50:
            score.issues = score.issues[-50:]
        
        logger.warning(f"Video freeze detected for stream {stream_id}: {duration_ms:.0f}ms")
    
    def record_black_frames(self, stream_id: str, frame_count: int) -> bool:
        """
        Record black frame detection.
        
        Requirement 15.2: Detect black frames (>10 consecutive)
        
        Args:
            stream_id: Stream identifier
            frame_count: Number of consecutive black frames
            
        Returns:
            True if recorded successfully
        """
        if stream_id not in self._stream_data:
            return False
        
        if frame_count >= self.BLACK_FRAME_THRESHOLD:
            self._record_black_frames(stream_id, frame_count)
            return True
        
        return False
    
    def _record_black_frames(self, stream_id: str, frame_count: int):
        """Record black frame event internally."""
        data = self._stream_data[stream_id]
        score = self._qos_scores[stream_id]
        
        event = {
            'type': 'black_frames',
            'timestamp': time.time(),
            'frame_count': frame_count,
        }
        
        data['black_frame_events'].append(event)
        score.black_frame_count += 1
        score.issues.append(event)
        
        # Keep last 50 events
        if len(data['black_frame_events']) > 50:
            data['black_frame_events'] = data['black_frame_events'][-50:]
        
        logger.warning(f"Black frames detected for stream {stream_id}: {frame_count} frames")
    
    def _recalculate_score(self, stream_id: str):
        """Recalculate QoS score for a stream."""
        if stream_id not in self._qos_scores:
            return
        
        data = self._stream_data.get(stream_id, {})
        score = self._qos_scores[stream_id]
        
        # Start with 100
        qos_score = 100
        
        # Deduct for freezes (10 points each, max 40)
        freeze_penalty = min(score.video_freeze_count * 10, 40)
        qos_score -= freeze_penalty
        
        # Deduct for black frames (5 points each, max 25)
        black_penalty = min(score.black_frame_count * 5, 25)
        qos_score -= black_penalty
        
        # Calculate bitrate quality
        bitrate_samples = data.get('bitrate_samples', [])
        expected_bitrate = data.get('expected_bitrate')
        
        if bitrate_samples and expected_bitrate:
            avg_bitrate = sum(bitrate_samples) / len(bitrate_samples)
            bitrate_quality = min(100, (avg_bitrate / expected_bitrate) * 100)
            score.bitrate_quality = bitrate_quality
            
            # Deduct for low bitrate (max 35)
            if bitrate_quality < 50:
                bitrate_penalty = int((50 - bitrate_quality) * 0.7)
                qos_score -= bitrate_penalty
        
        score.score = max(0, min(100, qos_score))
    
    def get_qos_score(self, stream_id: str) -> Optional[QoSScore]:
        """
        Get QoS score for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            QoSScore or None
        """
        return self._qos_scores.get(stream_id)
    
    def get_risk_contribution(self, stream_id: str) -> List[Dict[str, Any]]:
        """
        Get risk score contributions from QoS metrics.
        
        Requirement 15.4: Integrate with risk score
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            List of risk contribution dicts
        """
        from .risk_calculator import RiskContribution, RiskReason
        
        contributions = []
        score = self._qos_scores.get(stream_id)
        
        if not score:
            return contributions
        
        # Video freeze contribution
        if score.video_freeze_count > 0:
            points = min(score.video_freeze_count * self.config.video_freeze_weight // 10, 
                        self.config.video_freeze_weight)
            contributions.append(RiskContribution(
                reason=RiskReason.BUFFER_UNDERRUN,  # Reuse existing reason
                points=points,
                description=f"{score.video_freeze_count} video freeze(s) detected",
                metric_value=score.video_freeze_count,
                threshold=0
            ))
        
        # Black frame contribution
        if score.black_frame_count > 0:
            points = min(score.black_frame_count * self.config.black_frame_weight // 5,
                        self.config.black_frame_weight)
            contributions.append(RiskContribution(
                reason=RiskReason.BITRATE_DROP,  # Reuse existing reason
                points=points,
                description=f"{score.black_frame_count} black frame event(s)",
                metric_value=score.black_frame_count,
                threshold=0
            ))
        
        # Low bitrate contribution
        if score.bitrate_quality < 50:
            points = self.config.low_bitrate_weight
            contributions.append(RiskContribution(
                reason=RiskReason.BITRATE_VARIANCE,  # Reuse existing reason
                points=points,
                description=f"Low bitrate quality ({score.bitrate_quality:.0f}%)",
                metric_value=score.bitrate_quality,
                threshold=50
            ))
        
        return contributions
    
    def get_all_scores(self) -> Dict[str, QoSScore]:
        """Get all QoS scores."""
        return self._qos_scores.copy()


# =============================================================================
# Singleton instance
# =============================================================================

_qos_monitor: Optional[QoSMonitor] = None


def get_qos_monitor() -> QoSMonitor:
    """Get the global QoSMonitor instance."""
    global _qos_monitor
    if _qos_monitor is None:
        _qos_monitor = QoSMonitor()
    return _qos_monitor


def reset_qos_monitor() -> None:
    """Reset the global instance (for testing)."""
    global _qos_monitor
    _qos_monitor = None
