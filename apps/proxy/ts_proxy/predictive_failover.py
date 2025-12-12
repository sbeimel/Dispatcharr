"""
Predictive failover system using historical data and machine learning.
"""

import time
import logging
from typing import Dict
from collections import defaultdict, deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FailoverPrediction:
    """Represents a failover prediction."""
    should_failover: bool
    confidence: float
    recommended_action: str
    reason: str


class PredictiveFailover:
    """Analyzes historical data to predict and prevent failures."""
    
    def __init__(self):
        # Historical failure data (last 1000 events per channel)
        self._failure_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance metrics (last 100 measurements per channel)
        self._performance_history = defaultdict(lambda: deque(maxlen=100))
        
        # Pattern detection
        self._failure_patterns = defaultdict(list)
        
        # Time-based failure tracking
        self._time_based_failures = defaultdict(lambda: defaultdict(int))
    
    def record_failure_event(self, channel_id: str, failure_type: str, context: Dict):
        """Record a failure event for analysis."""
        event = {
            "timestamp": time.time(),
            "type": failure_type,
            "context": context,
            "hour_of_day": time.localtime().tm_hour,
            "day_of_week": time.localtime().tm_wday
        }
        
        self._failure_history[channel_id].append(event)
        
        # Track time-based patterns
        time_key = f"{event['hour_of_day']}:{event['day_of_week']}"
        self._time_based_failures[channel_id][time_key] += 1
        
        logger.debug(f"Recorded failure event for channel {channel_id}: {failure_type}")
    
    def record_performance_metric(self, channel_id: str, metric_type: str, value: float):
        """Record performance metrics for trend analysis."""
        metric = {
            "timestamp": time.time(),
            "type": metric_type,
            "value": value
        }
        
        self._performance_history[channel_id].append(metric)
    
    def should_preemptive_failover(self, channel_id: str) -> FailoverPrediction:
        """Determine if preemptive failover should be triggered."""
        from .failover_config import FailoverConfig
        
        if not FailoverConfig.is_predictive_failover_enabled():
            return FailoverPrediction(
                should_failover=False,
                confidence=0.0,
                recommended_action="none",
                reason="Predictive failover disabled"
            )
        
        # Analyze failure rate
        failure_rate = self._calculate_recent_failure_rate(channel_id)
        threshold = FailoverConfig.get_failure_rate_threshold()
        
        if failure_rate > threshold:
            return FailoverPrediction(
                should_failover=True,
                confidence=min(failure_rate / threshold, 1.0),
                recommended_action="immediate_failover",
                reason=f"High failure rate: {failure_rate:.2%} > {threshold:.2%}"
            )
        
        # Analyze time-based patterns
        time_pattern_risk = self._analyze_time_patterns(channel_id)
        if time_pattern_risk > 0.7:
            return FailoverPrediction(
                should_failover=True,
                confidence=time_pattern_risk,
                recommended_action="scheduled_failover",
                reason=f"Time-based failure pattern detected (risk: {time_pattern_risk:.2%})"
            )
        
        # Analyze performance trends
        performance_trend = self._analyze_performance_trends(channel_id)
        if performance_trend < -0.5:  # Significant degradation
            return FailoverPrediction(
                should_failover=True,
                confidence=abs(performance_trend),
                recommended_action="gradual_failover",
                reason=f"Performance degradation detected (trend: {performance_trend:.2f})"
            )
        
        return FailoverPrediction(
            should_failover=False,
            confidence=0.0,
            recommended_action="monitor",
            reason="No failure indicators detected"
        )
    
    def _calculate_recent_failure_rate(self, channel_id: str, time_window: int = 300) -> float:
        """Calculate failure rate in the last time_window seconds."""
        history = self._failure_history[channel_id]
        if not history:
            return 0.0
        
        current_time = time.time()
        recent_failures = [
            event for event in history
            if current_time - event["timestamp"] <= time_window
        ]
        
        if not recent_failures:
            return 0.0
        
        # Calculate failures per minute
        return len(recent_failures) / (time_window / 60)
    
    def _analyze_time_patterns(self, channel_id: str) -> float:
        """Analyze time-based failure patterns."""
        current_time = time.localtime()
        current_key = f"{current_time.tm_hour}:{current_time.tm_wday}"
        
        time_failures = self._time_based_failures[channel_id]
        if not time_failures:
            return 0.0
        
        current_failures = time_failures.get(current_key, 0)
        max_failures = max(time_failures.values()) if time_failures else 1
        
        # Risk is proportional to failures at this time vs max failures
        return current_failures / max_failures if max_failures > 0 else 0.0
    
    def _analyze_performance_trends(self, channel_id: str) -> float:
        """Analyze performance trends (negative = degrading, positive = improving)."""
        performance = self._performance_history[channel_id]
        if len(performance) < 10:  # Need at least 10 data points
            return 0.0
        
        # Simple linear trend analysis
        recent_metrics = list(performance)[-10:]  # Last 10 measurements
        
        if not recent_metrics:
            return 0.0
        
        # Calculate trend using simple linear regression
        n = len(recent_metrics)
        sum_x = sum(range(n))
        sum_y = sum(metric["value"] for metric in recent_metrics)
        sum_xy = sum(i * metric["value"] for i, metric in enumerate(recent_metrics))
        sum_x2 = sum(i * i for i in range(n))
        
        # Slope of trend line
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize slope to [-1, 1] range
        avg_value = sum_y / n if n > 0 else 1
        normalized_slope = slope / avg_value if avg_value != 0 else 0
        
        return max(-1.0, min(1.0, normalized_slope))
    
    def get_channel_insights(self, channel_id: str) -> Dict:
        """Get detailed insights for a channel."""
        failure_rate = self._calculate_recent_failure_rate(channel_id)
        time_risk = self._analyze_time_patterns(channel_id)
        performance_trend = self._analyze_performance_trends(channel_id)
        
        return {
            "channel_id": channel_id,
            "failure_rate_per_minute": failure_rate,
            "time_pattern_risk": time_risk,
            "performance_trend": performance_trend,
            "total_failures": len(self._failure_history[channel_id]),
            "performance_samples": len(self._performance_history[channel_id]),
            "prediction": self.should_preemptive_failover(channel_id).__dict__
        }
    
    def get_global_insights(self) -> Dict:
        """Get global insights across all channels."""
        total_channels = len(self._failure_history)
        total_failures = sum(len(history) for history in self._failure_history.values())
        
        high_risk_channels = []
        for channel_id in self._failure_history.keys():
            prediction = self.should_preemptive_failover(channel_id)
            if prediction.should_failover and prediction.confidence > 0.7:
                high_risk_channels.append({
                    "channel_id": channel_id,
                    "confidence": prediction.confidence,
                    "reason": prediction.reason
                })
        
        return {
            "total_channels_monitored": total_channels,
            "total_failures_recorded": total_failures,
            "high_risk_channels": high_risk_channels,
            "high_risk_count": len(high_risk_channels)
        }


# Global predictive failover instance
predictive_failover = PredictiveFailover()