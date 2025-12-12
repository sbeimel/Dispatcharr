"""
Metrics collection and monitoring for failover system.
"""

import time
import logging
from typing import Dict, Any
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)


class FailoverMetrics:
    """Collects and tracks failover metrics for monitoring and analysis."""
    
    def __init__(self):
        self._lock = Lock()
        self._mac_failover_stats = defaultdict(lambda: {"success": 0, "failure": 0, "last_attempt": 0})
        self._profile_failover_stats = defaultdict(lambda: {"success": 0, "failure": 0, "last_attempt": 0})
        self._stream_failover_stats = defaultdict(lambda: {"success": 0, "failure": 0, "last_attempt": 0})
        
        # Recent failure tracking for predictive failover (last 100 events per channel)
        self._recent_failures = defaultdict(lambda: deque(maxlen=100))
        
        # Circuit breaker states
        self._circuit_breaker_states = defaultdict(lambda: {
            "failure_count": 0,
            "last_failure_time": 0,
            "state": "closed"  # closed, open, half_open
        })
    
    def record_mac_failover(self, channel_id: str, mac_id: int, success: bool = True):
        """Record MAC failover attempt."""
        with self._lock:
            stats = self._mac_failover_stats[f"{channel_id}:{mac_id}"]
            if success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
                self._recent_failures[channel_id].append({
                    "type": "mac_failover",
                    "timestamp": time.time(),
                    "mac_id": mac_id
                })
            stats["last_attempt"] = time.time()
            
        logger.info(f"MAC failover {'succeeded' if success else 'failed'} for channel {channel_id}, MAC {mac_id}")
    
    def record_profile_failover(self, channel_id: str, profile_id: int, success: bool = True):
        """Record profile failover attempt."""
        with self._lock:
            stats = self._profile_failover_stats[f"{channel_id}:{profile_id}"]
            if success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
                self._recent_failures[channel_id].append({
                    "type": "profile_failover",
                    "timestamp": time.time(),
                    "profile_id": profile_id
                })
            stats["last_attempt"] = time.time()
            
        logger.info(f"Profile failover {'succeeded' if success else 'failed'} for channel {channel_id}, profile {profile_id}")
    
    def record_stream_failover(self, channel_id: str, stream_id: int, success: bool = True):
        """Record stream failover attempt."""
        with self._lock:
            stats = self._stream_failover_stats[f"{channel_id}:{stream_id}"]
            if success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
                self._recent_failures[channel_id].append({
                    "type": "stream_failover",
                    "timestamp": time.time(),
                    "stream_id": stream_id
                })
            stats["last_attempt"] = time.time()
            
        logger.info(f"Stream failover {'succeeded' if success else 'failed'} for channel {channel_id}, stream {stream_id}")
    
    def get_failure_rate(self, channel_id: str, time_window: int = 300) -> float:
        """Get failure rate for a channel in the last time_window seconds."""
        with self._lock:
            recent_failures = self._recent_failures[channel_id]
            if not recent_failures:
                return 0.0
            
            current_time = time.time()
            recent_events = [
                event for event in recent_failures 
                if current_time - event["timestamp"] <= time_window
            ]
            
            if not recent_events:
                return 0.0
            
            # Calculate failure rate (failures / total events)
            # For simplicity, assume each failure represents one total event
            return len(recent_events) / max(len(recent_events), 1)
    
    def should_trigger_circuit_breaker(self, portal_url: str) -> bool:
        """Check if circuit breaker should be triggered for a portal."""
        from .failover_config import FailoverConfig
        
        if not FailoverConfig.is_circuit_breaker_enabled():
            return False
        
        with self._lock:
            state = self._circuit_breaker_states[portal_url]
            threshold = FailoverConfig.get_circuit_breaker_threshold()
            timeout = FailoverConfig.get_circuit_breaker_timeout()
            current_time = time.time()
            
            if state["state"] == "open":
                # Check if timeout has passed
                if current_time - state["last_failure_time"] > timeout:
                    state["state"] = "half_open"
                    state["failure_count"] = 0
                    logger.info(f"Circuit breaker for {portal_url} moved to half-open state")
                    return False
                return True
            
            return state["failure_count"] >= threshold
    
    def record_circuit_breaker_event(self, portal_url: str, success: bool):
        """Record circuit breaker event."""
        from .failover_config import FailoverConfig
        
        if not FailoverConfig.is_circuit_breaker_enabled():
            return
        
        with self._lock:
            state = self._circuit_breaker_states[portal_url]
            threshold = FailoverConfig.get_circuit_breaker_threshold()
            
            if success:
                if state["state"] == "half_open":
                    state["state"] = "closed"
                    state["failure_count"] = 0
                    logger.info(f"Circuit breaker for {portal_url} closed after successful request")
            else:
                state["failure_count"] += 1
                state["last_failure_time"] = time.time()
                
                if state["failure_count"] >= threshold and state["state"] != "open":
                    state["state"] = "open"
                    logger.warning(f"Circuit breaker for {portal_url} opened after {state['failure_count']} failures")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of failover system."""
        with self._lock:
            total_mac_success = sum(stats["success"] for stats in self._mac_failover_stats.values())
            total_mac_failure = sum(stats["failure"] for stats in self._mac_failover_stats.values())
            
            total_profile_success = sum(stats["success"] for stats in self._profile_failover_stats.values())
            total_profile_failure = sum(stats["failure"] for stats in self._profile_failover_stats.values())
            
            total_stream_success = sum(stats["success"] for stats in self._stream_failover_stats.values())
            total_stream_failure = sum(stats["failure"] for stats in self._stream_failover_stats.values())
            
            open_circuit_breakers = [
                url for url, state in self._circuit_breaker_states.items()
                if state["state"] == "open"
            ]
            
            return {
                "mac_failover": {
                    "total_success": total_mac_success,
                    "total_failure": total_mac_failure,
                    "success_rate": total_mac_success / max(total_mac_success + total_mac_failure, 1)
                },
                "profile_failover": {
                    "total_success": total_profile_success,
                    "total_failure": total_profile_failure,
                    "success_rate": total_profile_success / max(total_profile_success + total_profile_failure, 1)
                },
                "stream_failover": {
                    "total_success": total_stream_success,
                    "total_failure": total_stream_failure,
                    "success_rate": total_stream_success / max(total_stream_success + total_stream_failure, 1)
                },
                "circuit_breakers": {
                    "open_count": len(open_circuit_breakers),
                    "open_portals": open_circuit_breakers
                },
                "active_channels": len(self._recent_failures)
            }


# Global metrics instance
failover_metrics = FailoverMetrics()