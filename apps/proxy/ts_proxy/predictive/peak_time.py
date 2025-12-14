"""
Peak Time Awareness for the Predictive Failover System.

This module provides peak time detection and threshold adjustment:
- Peak time configuration (time windows, days)
- Dynamic threshold adjustment during peak times
- Automatic learning of peak times from usage patterns

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class PeakTimeManager:
    """
    Manages peak time detection and threshold adjustment.
    
    Requirements:
    - 17.1: Configure peak time windows
    - 17.2: Adjust thresholds during peak times
    - 17.3: Learn peak times from usage patterns
    - 17.4: Apply threshold reduction factor
    """
    
    def __init__(self, config=None, redis_client=None):
        """
        Initialize the peak time manager.
        
        Args:
            config: PredictiveConfig instance
            redis_client: Redis client for storage
        """
        self._config = config
        self._redis_client = redis_client
        self._usage_history: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._learned_peak_times: List[Tuple[int, int, int]] = []  # (day, start_hour, end_hour)
    
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
        """Check if peak time awareness is enabled."""
        return self.config.peak_time_awareness_enabled
    
    def is_peak_time(self, dt: datetime = None) -> bool:
        """
        Check if the given time is during peak hours.
        
        Requirement 17.1: Check configured peak time windows
        
        Args:
            dt: Datetime to check (default: now)
            
        Returns:
            True if during peak time
        """
        if not self.is_enabled():
            return False
        
        if dt is None:
            dt = datetime.now()
        
        # Check day of week (0=Monday, 6=Sunday)
        if dt.weekday() not in self.config.peak_days:
            return False
        
        # Parse configured times
        try:
            start_hour, start_min = self._parse_time(self.config.peak_time_start)
            end_hour, end_min = self._parse_time(self.config.peak_time_end)
            
            current_minutes = dt.hour * 60 + dt.minute
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            # Handle overnight windows (e.g., 22:00 - 02:00)
            if end_minutes < start_minutes:
                return current_minutes >= start_minutes or current_minutes <= end_minutes
            else:
                return start_minutes <= current_minutes <= end_minutes
                
        except Exception as e:
            logger.error(f"Error checking peak time: {e}")
            return False
    
    def _parse_time(self, time_str: str) -> Tuple[int, int]:
        """Parse time string in HH:MM format."""
        parts = time_str.split(':')
        return int(parts[0]), int(parts[1])
    
    def get_adjusted_thresholds(self) -> Dict[str, int]:
        """
        Get thresholds adjusted for peak time.
        
        Requirement 17.2: Adjust thresholds during peak times
        
        Returns:
            Dict with adjusted warmup_threshold and failover_threshold
        """
        warmup = self.config.warmup_threshold
        failover = self.config.failover_threshold
        
        if self.is_peak_time():
            factor = self.config.peak_threshold_factor
            warmup = int(warmup * factor)
            failover = int(failover * factor)
            
            logger.debug(f"Peak time active: thresholds adjusted to {warmup}/{failover}")
        
        return {
            'warmup_threshold': warmup,
            'failover_threshold': failover,
            'is_peak_time': self.is_peak_time(),
        }
    
    def record_usage(self, stream_count: int = 1):
        """
        Record current usage for peak time learning.
        
        Requirement 17.3: Learn peak times from usage
        
        Args:
            stream_count: Number of active streams
        """
        now = datetime.now()
        day = now.weekday()
        hour = now.hour
        
        self._usage_history[day][hour] += stream_count
        
        # Periodically analyze and update learned peak times
        if sum(sum(h.values()) for h in self._usage_history.values()) % 100 == 0:
            self._analyze_usage_patterns()
    
    def _analyze_usage_patterns(self):
        """
        Analyze usage patterns to learn peak times.
        
        Requirement 17.3: Automatic learning of peak times
        """
        if not self._usage_history:
            return
        
        learned = []
        
        for day, hours in self._usage_history.items():
            if not hours:
                continue
            
            # Find hours with above-average usage
            avg_usage = sum(hours.values()) / max(len(hours), 1)
            peak_hours = [h for h, count in hours.items() if count > avg_usage * 1.5]
            
            if peak_hours:
                # Group consecutive hours
                peak_hours.sort()
                start = peak_hours[0]
                end = peak_hours[0]
                
                for h in peak_hours[1:]:
                    if h == end + 1:
                        end = h
                    else:
                        learned.append((day, start, end + 1))
                        start = h
                        end = h
                
                learned.append((day, start, end + 1))
        
        self._learned_peak_times = learned
        logger.info(f"Learned peak times: {learned}")
    
    def get_learned_peak_times(self) -> List[Dict[str, Any]]:
        """
        Get learned peak time windows.
        
        Returns:
            List of peak time window dicts
        """
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return [
            {
                'day': days[day],
                'day_num': day,
                'start_hour': start,
                'end_hour': end,
            }
            for day, start, end in self._learned_peak_times
        ]
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dict with usage statistics
        """
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        stats = {}
        for day, hours in self._usage_history.items():
            day_name = days[day]
            stats[day_name] = {
                'total': sum(hours.values()),
                'by_hour': dict(hours),
                'peak_hour': max(hours.items(), key=lambda x: x[1])[0] if hours else None,
            }
        
        return stats


# =============================================================================
# Singleton instance
# =============================================================================

_peak_time_manager: Optional[PeakTimeManager] = None


def get_peak_time_manager() -> PeakTimeManager:
    """Get the global PeakTimeManager instance."""
    global _peak_time_manager
    if _peak_time_manager is None:
        _peak_time_manager = PeakTimeManager()
    return _peak_time_manager


def reset_peak_time_manager() -> None:
    """Reset the global instance (for testing)."""
    global _peak_time_manager
    _peak_time_manager = None
