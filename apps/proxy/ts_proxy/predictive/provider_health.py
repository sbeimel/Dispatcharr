"""
Provider Health Score System for the Predictive Failover System.

This module provides health scoring for providers and MAC addresses:
- Track uptime, failures, and response times
- Calculate health scores (0-100)
- Rank providers for failover prioritization
- Identify problematic MACs

Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8, 16.9
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class HealthScore:
    """
    Health score for a provider or MAC address.
    
    Attributes:
        score: Health score (0-100, higher is better)
        uptime_percent: Uptime percentage
        failure_count: Number of failures in period
        avg_response_time_ms: Average response time
        last_failure: Timestamp of last failure
        last_success: Timestamp of last success
        total_requests: Total requests in period
    """
    score: int = 100
    uptime_percent: float = 100.0
    failure_count: int = 0
    avg_response_time_ms: float = 0
    last_failure: Optional[float] = None
    last_success: Optional[float] = None
    total_requests: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'score': self.score,
            'uptime_percent': self.uptime_percent,
            'failure_count': self.failure_count,
            'avg_response_time_ms': self.avg_response_time_ms,
            'last_failure': self.last_failure,
            'last_success': self.last_success,
            'total_requests': self.total_requests,
        }


@dataclass
class ProviderHealthData:
    """
    Health data for a provider (M3U account).
    
    Attributes:
        account_id: The M3U account ID
        account_name: Display name
        health_score: Current health score
        mac_health_scores: Health scores per MAC address
        recent_events: Recent failure/success events
    """
    account_id: int
    account_name: str = ""
    health_score: HealthScore = field(default_factory=HealthScore)
    mac_health_scores: Dict[str, HealthScore] = field(default_factory=dict)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'health_score': self.health_score.to_dict(),
            'mac_health_scores': {
                mac: score.to_dict() 
                for mac, score in self.mac_health_scores.items()
            },
            'recent_events': self.recent_events[-20:],  # Last 20 events
        }


class ProviderHealthScorer:
    """
    Calculates and tracks health scores for providers and MACs.
    
    Requirements:
    - 16.1: Track uptime percentage
    - 16.2: Track failure count
    - 16.3: Track average response time
    - 16.8: Calculate composite health score
    - 16.9: Rank providers for failover
    """
    
    # Scoring weights
    UPTIME_WEIGHT = 0.4
    FAILURE_WEIGHT = 0.3
    RESPONSE_TIME_WEIGHT = 0.3
    
    # Thresholds
    RESPONSE_TIME_EXCELLENT = 500  # ms
    RESPONSE_TIME_GOOD = 1000
    RESPONSE_TIME_POOR = 3000
    
    def __init__(self, redis_client=None):
        """
        Initialize the health scorer.
        
        Args:
            redis_client: Redis client for storage
        """
        self._redis_client = redis_client
        self._provider_data: Dict[int, ProviderHealthData] = {}
        self._response_times: Dict[str, List[float]] = {}  # key -> recent times
        self._events: Dict[str, List[Dict]] = {}  # key -> recent events
    
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

    def record_success(self, account_id: int, mac_address: str = None,
                       response_time_ms: float = None) -> bool:
        """
        Record a successful request.
        
        Args:
            account_id: The M3U account ID
            mac_address: Optional MAC address
            response_time_ms: Optional response time
            
        Returns:
            True if recorded successfully
        """
        try:
            now = time.time()
            
            # Update provider data
            if account_id not in self._provider_data:
                self._provider_data[account_id] = ProviderHealthData(
                    account_id=account_id
                )
            
            provider = self._provider_data[account_id]
            provider.health_score.total_requests += 1
            provider.health_score.last_success = now
            
            # Track response time
            if response_time_ms is not None:
                key = f"provider:{account_id}"
                if key not in self._response_times:
                    self._response_times[key] = []
                self._response_times[key].append(response_time_ms)
                # Keep last 100
                if len(self._response_times[key]) > 100:
                    self._response_times[key] = self._response_times[key][-100:]
            
            # Update MAC-specific data
            if mac_address:
                if mac_address not in provider.mac_health_scores:
                    provider.mac_health_scores[mac_address] = HealthScore()
                
                mac_score = provider.mac_health_scores[mac_address]
                mac_score.total_requests += 1
                mac_score.last_success = now
                
                if response_time_ms is not None:
                    mac_key = f"mac:{account_id}:{mac_address}"
                    if mac_key not in self._response_times:
                        self._response_times[mac_key] = []
                    self._response_times[mac_key].append(response_time_ms)
                    if len(self._response_times[mac_key]) > 100:
                        self._response_times[mac_key] = self._response_times[mac_key][-100:]
            
            # Recalculate scores
            self._recalculate_scores(account_id, mac_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record success: {e}")
            return False
    
    def record_failure(self, account_id: int, mac_address: str = None,
                       error_type: str = None) -> bool:
        """
        Record a failed request.
        
        Args:
            account_id: The M3U account ID
            mac_address: Optional MAC address
            error_type: Optional error type description
            
        Returns:
            True if recorded successfully
        """
        try:
            now = time.time()
            
            # Update provider data
            if account_id not in self._provider_data:
                self._provider_data[account_id] = ProviderHealthData(
                    account_id=account_id
                )
            
            provider = self._provider_data[account_id]
            provider.health_score.total_requests += 1
            provider.health_score.failure_count += 1
            provider.health_score.last_failure = now
            
            # Add event
            event = {
                'type': 'failure',
                'timestamp': now,
                'mac_address': mac_address,
                'error_type': error_type,
            }
            provider.recent_events.append(event)
            if len(provider.recent_events) > 100:
                provider.recent_events = provider.recent_events[-100:]
            
            # Update MAC-specific data
            if mac_address:
                if mac_address not in provider.mac_health_scores:
                    provider.mac_health_scores[mac_address] = HealthScore()
                
                mac_score = provider.mac_health_scores[mac_address]
                mac_score.total_requests += 1
                mac_score.failure_count += 1
                mac_score.last_failure = now
            
            # Recalculate scores
            self._recalculate_scores(account_id, mac_address)
            
            logger.warning(
                f"Provider {account_id} failure recorded"
                f"{f' (MAC: {mac_address[:8]}...)' if mac_address else ''}"
                f"{f': {error_type}' if error_type else ''}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record failure: {e}")
            return False
    
    def _recalculate_scores(self, account_id: int, mac_address: str = None):
        """Recalculate health scores for provider and MAC."""
        provider = self._provider_data.get(account_id)
        if not provider:
            return
        
        # Calculate provider score
        provider.health_score.score = self._calculate_score(
            provider.health_score,
            f"provider:{account_id}"
        )
        
        # Calculate MAC score
        if mac_address and mac_address in provider.mac_health_scores:
            mac_score = provider.mac_health_scores[mac_address]
            mac_score.score = self._calculate_score(
                mac_score,
                f"mac:{account_id}:{mac_address}"
            )
    
    def _calculate_score(self, health: HealthScore, key: str) -> int:
        """
        Calculate composite health score.
        
        Requirement 16.8: Calculate composite health score
        """
        if health.total_requests == 0:
            return 100  # No data yet
        
        # Uptime score (0-100)
        success_count = health.total_requests - health.failure_count
        uptime_score = (success_count / health.total_requests) * 100
        health.uptime_percent = uptime_score
        
        # Failure penalty (more recent failures = worse)
        failure_score = 100
        if health.failure_count > 0:
            # Reduce score based on failure count
            failure_score = max(0, 100 - (health.failure_count * 10))
        
        # Response time score
        response_score = 100
        response_times = self._response_times.get(key, [])
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            health.avg_response_time_ms = avg_time
            
            if avg_time <= self.RESPONSE_TIME_EXCELLENT:
                response_score = 100
            elif avg_time <= self.RESPONSE_TIME_GOOD:
                response_score = 80
            elif avg_time <= self.RESPONSE_TIME_POOR:
                response_score = 50
            else:
                response_score = 20
        
        # Composite score
        score = int(
            uptime_score * self.UPTIME_WEIGHT +
            failure_score * self.FAILURE_WEIGHT +
            response_score * self.RESPONSE_TIME_WEIGHT
        )
        
        return max(0, min(100, score))
    
    def get_provider_health(self, account_id: int) -> Optional[ProviderHealthData]:
        """
        Get health data for a provider.
        
        Args:
            account_id: The M3U account ID
            
        Returns:
            ProviderHealthData or None
        """
        return self._provider_data.get(account_id)
    
    def get_mac_health(self, account_id: int, 
                       mac_address: str) -> Optional[HealthScore]:
        """
        Get health score for a specific MAC.
        
        Args:
            account_id: The M3U account ID
            mac_address: The MAC address
            
        Returns:
            HealthScore or None
        """
        provider = self._provider_data.get(account_id)
        if provider:
            return provider.mac_health_scores.get(mac_address)
        return None
    
    def get_ranked_providers(self) -> List[ProviderHealthData]:
        """
        Get providers ranked by health score.
        
        Requirement 16.9: Rank providers for failover
        
        Returns:
            List of ProviderHealthData sorted by score (highest first)
        """
        providers = list(self._provider_data.values())
        providers.sort(key=lambda p: p.health_score.score, reverse=True)
        return providers
    
    def get_ranked_macs(self, account_id: int) -> List[tuple]:
        """
        Get MACs ranked by health score for a provider.
        
        Args:
            account_id: The M3U account ID
            
        Returns:
            List of (mac_address, HealthScore) tuples sorted by score
        """
        provider = self._provider_data.get(account_id)
        if not provider:
            return []
        
        macs = list(provider.mac_health_scores.items())
        macs.sort(key=lambda x: x[1].score, reverse=True)
        return macs
    
    def get_problem_macs(self, account_id: int = None,
                         threshold: int = 50) -> List[Dict[str, Any]]:
        """
        Get MACs with health score below threshold.
        
        Requirement 16.6: Identify problematic MACs
        
        Args:
            account_id: Optional filter by account
            threshold: Health score threshold (default 50)
            
        Returns:
            List of problem MAC info dicts
        """
        problems = []
        
        providers = [self._provider_data.get(account_id)] if account_id else self._provider_data.values()
        
        for provider in providers:
            if not provider:
                continue
            
            for mac, score in provider.mac_health_scores.items():
                if score.score < threshold:
                    problems.append({
                        'account_id': provider.account_id,
                        'account_name': provider.account_name,
                        'mac_address': mac,
                        'health_score': score.score,
                        'failure_count': score.failure_count,
                        'uptime_percent': score.uptime_percent,
                        'last_failure': score.last_failure,
                    })
        
        # Sort by score (worst first)
        problems.sort(key=lambda x: x['health_score'])
        return problems
    
    def get_top_performers(self, account_id: int = None,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top performing MACs.
        
        Requirement 16.7: Identify top performers
        
        Args:
            account_id: Optional filter by account
            limit: Maximum number to return
            
        Returns:
            List of top performer info dicts
        """
        performers = []
        
        providers = [self._provider_data.get(account_id)] if account_id else self._provider_data.values()
        
        for provider in providers:
            if not provider:
                continue
            
            for mac, score in provider.mac_health_scores.items():
                if score.total_requests >= 10:  # Minimum requests
                    performers.append({
                        'account_id': provider.account_id,
                        'account_name': provider.account_name,
                        'mac_address': mac,
                        'health_score': score.score,
                        'uptime_percent': score.uptime_percent,
                        'avg_response_time_ms': score.avg_response_time_ms,
                        'total_requests': score.total_requests,
                    })
        
        # Sort by score (best first)
        performers.sort(key=lambda x: x['health_score'], reverse=True)
        return performers[:limit]
    
    def get_all_health_data(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all health data for all providers.
        
        Returns:
            Dict mapping account_id to health data dict
        """
        return {
            account_id: provider.to_dict()
            for account_id, provider in self._provider_data.items()
        }


# =============================================================================
# Singleton instance
# =============================================================================

_health_scorer: Optional[ProviderHealthScorer] = None


def get_provider_health_scorer() -> ProviderHealthScorer:
    """Get the global ProviderHealthScorer instance."""
    global _health_scorer
    if _health_scorer is None:
        _health_scorer = ProviderHealthScorer()
    return _health_scorer


def reset_provider_health_scorer() -> None:
    """Reset the global instance (for testing)."""
    global _health_scorer
    _health_scorer = None
