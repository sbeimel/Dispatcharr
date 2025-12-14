"""
Redis key patterns for the Predictive Failover System.

Centralizing key patterns makes it easier to maintain and ensures consistency
across all components of the predictive failover system.

Key Structure:
- predictive:metrics:{stream_id}:{metric_type} - Stream metrics (Sorted Set)
- predictive:risk_score:{stream_id} - Current risk score (String/JSON)
- predictive:warmup:{channel_id} - Warmup status (Hash)
- predictive:stats:daily:{date} - Daily statistics (Hash)
- predictive:patterns:{pattern_id} - Pattern data (Hash)
"""


class PredictiveRedisKeys:
    """Redis key patterns for the Predictive Failover System."""
    
    # Prefix for all predictive failover keys
    PREFIX = "predictive"
    
    # ==========================================================================
    # Metrics Keys (Sorted Sets with timestamp as score)
    # TTL: 1 hour
    # ==========================================================================
    
    @staticmethod
    def metrics(stream_id: str, metric_type: str) -> str:
        """
        Key for stream metrics stored as Sorted Set.
        
        Args:
            stream_id: Stream identifier
            metric_type: Type of metric (response_time, bytes_received, etc.)
            
        Returns:
            Redis key string
        """
        return f"predictive:metrics:{stream_id}:{metric_type}"
    
    @staticmethod
    def metrics_prefix(stream_id: str) -> str:
        """
        Prefix for all metrics of a stream (for pattern matching/cleanup).
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Redis key prefix
        """
        return f"predictive:metrics:{stream_id}:"
    
    @staticmethod
    def all_metrics_pattern() -> str:
        """
        Pattern to match all metrics keys (for cleanup).
        
        Returns:
            Redis key pattern
        """
        return "predictive:metrics:*"
    
    # ==========================================================================
    # Risk Score Keys (String with JSON)
    # TTL: 30 seconds
    # ==========================================================================
    
    @staticmethod
    def risk_score(stream_id: str) -> str:
        """
        Key for current risk score of a stream.
        
        Stores JSON with:
        - score: int (0-100)
        - reasons: list of contributing factors
        - timestamp: when calculated
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:risk_score:{stream_id}"
    
    @staticmethod
    def all_risk_scores_pattern() -> str:
        """
        Pattern to match all risk score keys.
        
        Returns:
            Redis key pattern
        """
        return "predictive:risk_score:*"
    
    # ==========================================================================
    # Warmup Keys (Hash)
    # TTL: 10 minutes
    # ==========================================================================
    
    @staticmethod
    def warmup(channel_id: str) -> str:
        """
        Key for warmup status of a channel.
        
        Stores Hash with:
        - backup_stream_id: ID of warmed up backup stream
        - backup_url: URL of backup stream
        - started_at: timestamp when warmup started
        - last_keepalive: timestamp of last keepalive
        - status: 'warming', 'ready', 'failed'
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:warmup:{channel_id}"
    
    @staticmethod
    def all_warmup_pattern() -> str:
        """
        Pattern to match all warmup keys.
        
        Returns:
            Redis key pattern
        """
        return "predictive:warmup:*"
    
    # ==========================================================================
    # Statistics Keys (Hash)
    # TTL: 30 days
    # ==========================================================================
    
    @staticmethod
    def stats_daily(date: str) -> str:
        """
        Key for daily statistics.
        
        Stores Hash with:
        - proactive_failovers: count
        - reactive_failovers: count
        - successful_predictions: count
        - false_positives: count
        - missed_predictions: count
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Redis key string
        """
        return f"predictive:stats:daily:{date}"
    
    @staticmethod
    def stats_hourly(date: str, hour: int) -> str:
        """
        Key for hourly statistics (for heatmap).
        
        Args:
            date: Date string in YYYY-MM-DD format
            hour: Hour (0-23)
            
        Returns:
            Redis key string
        """
        return f"predictive:stats:hourly:{date}:{hour:02d}"
    
    @staticmethod
    def stats_global() -> str:
        """
        Key for global/cumulative statistics.
        
        Returns:
            Redis key string
        """
        return "predictive:stats:global"
    
    # ==========================================================================
    # Pattern Keys (Hash)
    # No TTL (managed by Pattern Analyzer)
    # ==========================================================================
    
    @staticmethod
    def pattern_metrics(pattern_id: str) -> str:
        """
        Key for storing metrics snapshot of a failure pattern.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:pattern:{pattern_id}:metrics"
    
    @staticmethod
    def pattern_active(stream_id: str) -> str:
        """
        Key for tracking active pattern matches for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:pattern:active:{stream_id}"
    
    # ==========================================================================
    # Cooldown Keys (String)
    # TTL: configurable (default 30 seconds)
    # ==========================================================================
    
    @staticmethod
    def failover_cooldown(channel_id: str) -> str:
        """
        Key for failover cooldown marker.
        
        Prevents rapid successive failovers for the same channel.
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:cooldown:{channel_id}"
    
    # ==========================================================================
    # Event Keys (List)
    # TTL: 24 hours
    # ==========================================================================
    
    @staticmethod
    def recent_events(channel_id: str = None) -> str:
        """
        Key for recent failover events.
        
        Args:
            channel_id: Optional channel identifier for channel-specific events
            
        Returns:
            Redis key string
        """
        if channel_id:
            return f"predictive:events:{channel_id}"
        return "predictive:events:global"
    
    # ==========================================================================
    # Provider Health Keys (Hash)
    # TTL: 30 days
    # ==========================================================================
    
    @staticmethod
    def provider_health(provider_id: str) -> str:
        """
        Key for provider (portal/M3U account) health score.
        
        Stores Hash with:
        - health_score: int (0-100)
        - uptime_30d: float (percentage)
        - failure_count: int
        - avg_response_time: float (ms)
        - last_updated: timestamp
        
        Args:
            provider_id: Provider/M3U account identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:health:provider:{provider_id}"
    
    @staticmethod
    def mac_health(mac_id: str) -> str:
        """
        Key for MAC address health score.
        
        Args:
            mac_id: MAC address identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:health:mac:{mac_id}"
    
    # ==========================================================================
    # Time Window Pattern Keys (Set)
    # ==========================================================================
    
    @staticmethod
    def time_window_failures(provider_id: str, day_of_week: int, hour: int) -> str:
        """
        Key for tracking failures in specific time windows.
        
        Args:
            provider_id: Provider identifier
            day_of_week: Day of week (0=Monday, 6=Sunday)
            hour: Hour (0-23)
            
        Returns:
            Redis key string
        """
        return f"predictive:timewindow:{provider_id}:{day_of_week}:{hour:02d}"
    
    # ==========================================================================
    # Correlation Keys (Set)
    # ==========================================================================
    
    @staticmethod
    def correlated_failures(provider_id: str) -> str:
        """
        Key for tracking correlated failures across streams of same provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:correlation:{provider_id}"
    
    # ==========================================================================
    # Stream State Keys (Hash)
    # ==========================================================================
    
    @staticmethod
    def stream_state(stream_id: str) -> str:
        """
        Key for predictive failover state of a stream.
        
        Stores Hash with:
        - collecting: bool (is metrics collection active)
        - last_risk_score: int
        - warmup_triggered: bool
        - last_evaluation: timestamp
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Redis key string
        """
        return f"predictive:state:{stream_id}"
    
    @staticmethod
    def active_streams() -> str:
        """
        Key for set of streams with active predictive monitoring.
        
        Returns:
            Redis key string
        """
        return "predictive:active_streams"
    
    # ==========================================================================
    # TTL Constants
    # ==========================================================================
    
    # Metrics TTL: 1 hour
    METRICS_TTL = 3600
    
    # Risk score TTL: 30 seconds
    RISK_SCORE_TTL = 30
    
    # Warmup TTL: 10 minutes
    WARMUP_TTL = 600
    
    # Daily stats TTL: 30 days
    STATS_DAILY_TTL = 30 * 24 * 3600
    
    # Hourly stats TTL: 7 days
    STATS_HOURLY_TTL = 7 * 24 * 3600
    
    # Events TTL: 24 hours
    EVENTS_TTL = 24 * 3600
    
    # Provider health TTL: 30 days
    HEALTH_TTL = 30 * 24 * 3600
    
    # Stream state TTL: 1 hour (auto-cleanup for inactive streams)
    STATE_TTL = 3600
