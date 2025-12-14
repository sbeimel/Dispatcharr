"""
Analytics for the Predictive Failover System.

This module provides analytics and reporting:
- Health score trends
- Failure heatmaps
- Portal comparisons
- MAC statistics
- Export functions

Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6
"""

import logging
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class PredictiveAnalytics:
    """
    Analytics engine for predictive failover data.
    
    Requirements:
    - 19.1: Health score trends (30 days)
    - 19.2: Failure heatmap by time of day
    - 19.3: Portal comparison view
    - 19.4: MAC statistics per portal
    - 19.5: Problem MACs list
    - 19.6: Export functions (CSV, JSON)
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize the analytics engine.
        
        Args:
            redis_client: Redis client for data access
        """
        self._redis_client = redis_client
        self._health_history: Dict[int, List[Dict]] = defaultdict(list)
        self._failure_events: List[Dict] = []
    
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
    
    def record_health_score(self, account_id: int, score: int, 
                            mac_address: str = None):
        """
        Record a health score data point.
        
        Args:
            account_id: Provider account ID
            score: Health score (0-100)
            mac_address: Optional MAC address
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'mac_address': mac_address,
        }
        
        self._health_history[account_id].append(entry)
        
        # Keep last 30 days (assuming ~1 entry per minute = ~43200 entries)
        if len(self._health_history[account_id]) > 50000:
            self._health_history[account_id] = self._health_history[account_id][-50000:]
    
    def record_failure(self, account_id: int, mac_address: str = None,
                       error_type: str = None, channel_name: str = None):
        """
        Record a failure event.
        
        Args:
            account_id: Provider account ID
            mac_address: Optional MAC address
            error_type: Type of error
            channel_name: Channel name
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'account_id': account_id,
            'mac_address': mac_address,
            'error_type': error_type,
            'channel_name': channel_name,
            'hour': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
        }
        
        self._failure_events.append(event)
        
        # Keep last 10000 events
        if len(self._failure_events) > 10000:
            self._failure_events = self._failure_events[-10000:]
    
    def get_health_trend(self, account_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get health score trend for a provider.
        
        Requirement 19.1: Health score trends (30 days)
        
        Args:
            account_id: Provider account ID
            days: Number of days to include
            
        Returns:
            List of daily average scores
        """
        cutoff = datetime.now() - timedelta(days=days)
        history = self._health_history.get(account_id, [])
        
        # Group by day
        daily_scores: Dict[str, List[int]] = defaultdict(list)
        
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                if ts >= cutoff:
                    day_key = ts.strftime('%Y-%m-%d')
                    daily_scores[day_key].append(entry['score'])
            except (ValueError, KeyError):
                continue
        
        # Calculate daily averages
        trend = []
        for day in sorted(daily_scores.keys()):
            scores = daily_scores[day]
            trend.append({
                'date': day,
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'min_score': min(scores) if scores else 0,
                'max_score': max(scores) if scores else 0,
                'sample_count': len(scores),
            })
        
        return trend
    
    def get_failure_heatmap(self, account_id: int = None, 
                            days: int = 7) -> Dict[str, Any]:
        """
        Get failure heatmap by hour and day of week.
        
        Requirement 19.2: Failure heatmap by time of day
        
        Args:
            account_id: Optional filter by provider
            days: Number of days to include
            
        Returns:
            Heatmap data structure
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        # Initialize heatmap (7 days x 24 hours)
        heatmap = [[0 for _ in range(24)] for _ in range(7)]
        
        for event in self._failure_events:
            try:
                ts = datetime.fromisoformat(event['timestamp'])
                if ts < cutoff:
                    continue
                
                if account_id and event.get('account_id') != account_id:
                    continue
                
                day = event.get('day_of_week', ts.weekday())
                hour = event.get('hour', ts.hour)
                heatmap[day][hour] += 1
                
            except (ValueError, KeyError):
                continue
        
        days_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                      'Friday', 'Saturday', 'Sunday']
        
        return {
            'heatmap': heatmap,
            'days': days_names,
            'hours': list(range(24)),
            'max_value': max(max(row) for row in heatmap) if heatmap else 0,
        }
    
    def get_portal_comparison(self) -> List[Dict[str, Any]]:
        """
        Get comparison data for all portals.
        
        Requirement 19.3: Portal comparison view
        
        Returns:
            List of portal comparison data
        """
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        providers = scorer.get_ranked_providers()
        
        comparison = []
        for provider in providers:
            # Get trend data
            trend = self.get_health_trend(provider.account_id, days=7)
            
            # Calculate trend direction
            if len(trend) >= 2:
                recent_avg = sum(t['avg_score'] for t in trend[-3:]) / min(3, len(trend))
                older_avg = sum(t['avg_score'] for t in trend[:3]) / min(3, len(trend))
                trend_direction = 'up' if recent_avg > older_avg else 'down' if recent_avg < older_avg else 'stable'
            else:
                trend_direction = 'stable'
            
            comparison.append({
                'account_id': provider.account_id,
                'account_name': provider.account_name,
                'health_score': provider.health_score.score,
                'uptime_percent': provider.health_score.uptime_percent,
                'failure_count': provider.health_score.failure_count,
                'avg_response_time_ms': provider.health_score.avg_response_time_ms,
                'mac_count': len(provider.mac_health_scores),
                'trend_direction': trend_direction,
            })
        
        return comparison
    
    def get_mac_statistics(self, account_id: int) -> Dict[str, Any]:
        """
        Get MAC statistics for a portal.
        
        Requirement 19.4: MAC statistics per portal
        
        Args:
            account_id: Provider account ID
            
        Returns:
            MAC statistics dict
        """
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        provider = scorer.get_provider_health(account_id)
        
        if not provider:
            return {'error': 'Provider not found'}
        
        mac_stats = []
        for mac, score in provider.mac_health_scores.items():
            mac_stats.append({
                'mac_address': mac,
                'health_score': score.score,
                'uptime_percent': score.uptime_percent,
                'failure_count': score.failure_count,
                'avg_response_time_ms': score.avg_response_time_ms,
                'total_requests': score.total_requests,
                'status': 'healthy' if score.score >= 80 else 'warning' if score.score >= 50 else 'critical',
            })
        
        # Sort by score
        mac_stats.sort(key=lambda x: x['health_score'], reverse=True)
        
        return {
            'account_id': account_id,
            'account_name': provider.account_name,
            'total_macs': len(mac_stats),
            'healthy_macs': len([m for m in mac_stats if m['status'] == 'healthy']),
            'warning_macs': len([m for m in mac_stats if m['status'] == 'warning']),
            'critical_macs': len([m for m in mac_stats if m['status'] == 'critical']),
            'macs': mac_stats,
        }
    
    def get_problem_macs_report(self, threshold: int = 50) -> List[Dict[str, Any]]:
        """
        Get detailed report of problem MACs.
        
        Requirement 19.5: Problem MACs list
        
        Args:
            threshold: Health score threshold
            
        Returns:
            List of problem MAC reports
        """
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        problems = scorer.get_problem_macs(threshold=threshold)
        
        # Enrich with failure history
        for problem in problems:
            mac = problem['mac_address']
            recent_failures = [
                e for e in self._failure_events[-100:]
                if e.get('mac_address') == mac
            ]
            
            problem['recent_failures'] = len(recent_failures)
            problem['last_failure'] = recent_failures[-1]['timestamp'] if recent_failures else None
            problem['recommendation'] = self._get_mac_recommendation(problem)
        
        return problems
    
    def _get_mac_recommendation(self, problem: Dict) -> str:
        """Generate recommendation for a problem MAC."""
        score = problem.get('health_score', 0)
        failures = problem.get('failure_count', 0)
        
        if score < 20:
            return "Critical: Replace immediately"
        elif score < 40:
            return "High priority: Schedule replacement"
        elif failures > 10:
            return "Monitor closely: High failure rate"
        else:
            return "Watch: Performance degraded"
    
    def export_to_json(self, data: Any) -> str:
        """
        Export data to JSON format.
        
        Requirement 19.6: Export functions
        
        Args:
            data: Data to export
            
        Returns:
            JSON string
        """
        return json.dumps(data, indent=2, default=str)
    
    def export_to_csv(self, data: List[Dict], filename: str = None) -> str:
        """
        Export data to CSV format.
        
        Requirement 19.6: Export functions
        
        Args:
            data: List of dicts to export
            filename: Optional filename
            
        Returns:
            CSV string
        """
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get summary data for analytics dashboard.
        
        Returns:
            Dashboard summary dict
        """
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        
        # Get overall stats
        providers = scorer.get_ranked_providers()
        total_providers = len(providers)
        
        if providers:
            avg_health = sum(p.health_score.score for p in providers) / total_providers
            total_failures = sum(p.health_score.failure_count for p in providers)
        else:
            avg_health = 100
            total_failures = 0
        
        # Get problem counts
        problems = scorer.get_problem_macs(threshold=50)
        
        # Get recent failure count
        cutoff = datetime.now() - timedelta(hours=24)
        recent_failures = len([
            e for e in self._failure_events
            if datetime.fromisoformat(e['timestamp']) >= cutoff
        ])
        
        return {
            'total_providers': total_providers,
            'average_health_score': round(avg_health, 1),
            'total_failures_all_time': total_failures,
            'failures_last_24h': recent_failures,
            'problem_macs_count': len(problems),
            'top_provider': providers[0].to_dict() if providers else None,
            'worst_provider': providers[-1].to_dict() if providers else None,
        }


# =============================================================================
# Singleton instance
# =============================================================================

_analytics: Optional[PredictiveAnalytics] = None


def get_predictive_analytics() -> PredictiveAnalytics:
    """Get the global PredictiveAnalytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = PredictiveAnalytics()
    return _analytics


def reset_predictive_analytics() -> None:
    """Reset the global instance (for testing)."""
    global _analytics
    _analytics = None
