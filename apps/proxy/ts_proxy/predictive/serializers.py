"""
Serializers for the Predictive Failover System.

This module provides REST framework serializers for validating and
serializing predictive failover configuration data.
"""

from rest_framework import serializers


class PredictiveConfigSerializer(serializers.Serializer):
    """
    Serializer for Predictive Failover configuration.
    
    Validates all configuration parameters with appropriate ranges
    and provides clear error messages for invalid values.
    """
    
    # ==========================================================================
    # Main Settings (Haupt-Einstellungen)
    # ==========================================================================
    
    enabled = serializers.BooleanField(
        default=False,
        help_text="Master switch for predictive failover. System is OFF by default."
    )
    
    warmup_threshold = serializers.IntegerField(
        min_value=40,
        max_value=85,
        default=60,
        help_text="Risk score threshold to start warming up backup stream (40-85)"
    )
    
    failover_threshold = serializers.IntegerField(
        min_value=55,
        max_value=95,
        default=85,
        help_text="Risk score threshold to trigger proactive failover (55-95)"
    )
    
    metrics_interval = serializers.IntegerField(
        min_value=1,
        max_value=10,
        default=3,
        help_text="Interval in seconds for collecting metrics (1-10)"
    )
    
    cooldown_period = serializers.IntegerField(
        min_value=5,
        max_value=300,
        default=30,
        help_text="Cooldown period in seconds after a failover"
    )
    
    # ==========================================================================
    # Learning Settings (Lern-Einstellungen)
    # ==========================================================================
    
    pattern_learning_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable pattern learning from failures"
    )
    
    pattern_confidence_threshold = serializers.IntegerField(
        min_value=40,
        max_value=90,
        default=60,
        help_text="Minimum confidence threshold for trusting patterns (40-90%)"
    )
    
    time_pattern_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable time-window based pattern detection"
    )
    
    correlation_analysis_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable correlation analysis for portal-wide problems"
    )
    
    auto_tune_enabled = serializers.BooleanField(
        default=False,
        help_text="Enable automatic threshold optimization"
    )
    
    learning_rate = serializers.ChoiceField(
        choices=['slow', 'normal', 'fast'],
        default='normal',
        help_text="Learning rate: 'slow', 'normal', or 'fast'"
    )
    
    # ==========================================================================
    # Metric Weights (Metriken-Gewichtungen)
    # ==========================================================================
    
    response_time_warning = serializers.IntegerField(
        min_value=50,
        max_value=500,
        default=200,
        help_text="Response time warning threshold in ms (50-500)"
    )
    
    response_time_critical = serializers.IntegerField(
        min_value=150,
        max_value=1000,
        default=400,
        help_text="Response time critical threshold in ms (150-1000)"
    )
    
    response_time_warning_weight = serializers.IntegerField(
        min_value=5,
        max_value=30,
        default=15,
        help_text="Points added for response time warning (5-30)"
    )
    
    response_time_critical_weight = serializers.IntegerField(
        min_value=10,
        max_value=40,
        default=20,
        help_text="Additional points for critical response time (10-40)"
    )
    
    buffer_underrun_weight = serializers.IntegerField(
        min_value=15,
        max_value=50,
        default=30,
        help_text="Points added per buffer underrun (15-50)"
    )
    
    bitrate_variance_threshold = serializers.IntegerField(
        min_value=10,
        max_value=50,
        default=25,
        help_text="Bitrate variance threshold in % (10-50)"
    )
    
    bitrate_variance_weight = serializers.IntegerField(
        min_value=5,
        max_value=30,
        default=15,
        help_text="Points for high bitrate variance (5-30)"
    )
    
    trend_detection_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable trend detection (3+ consecutive increases)"
    )
    
    connection_reset_weight = serializers.IntegerField(
        min_value=5,
        max_value=40,
        default=20,
        help_text="Points for connection resets (>2 in 5 minutes)"
    )
    
    trend_weight = serializers.IntegerField(
        min_value=5,
        max_value=25,
        default=10,
        help_text="Points for rising response time trend"
    )
    
    bitrate_drop_weight = serializers.IntegerField(
        min_value=10,
        max_value=40,
        default=25,
        help_text="Points for sudden bitrate drop (>50%)"
    )
    
    # ==========================================================================
    # Pattern Matching Weights
    # ==========================================================================
    
    pattern_max_weight = serializers.IntegerField(
        min_value=20,
        max_value=60,
        default=40,
        help_text="Maximum points from pattern matching"
    )
    
    pattern_confidence_factor = serializers.FloatField(
        min_value=0.1,
        max_value=1.0,
        default=0.4,
        help_text="Factor for pattern confidence to points conversion"
    )
    
    time_window_weight = serializers.IntegerField(
        min_value=5,
        max_value=30,
        default=15,
        help_text="Points when current time is in known failure window"
    )
    
    correlation_weight = serializers.IntegerField(
        min_value=10,
        max_value=40,
        default=20,
        help_text="Points for portal-wide problems"
    )
    
    # ==========================================================================
    # Optional Modules (Optionale Module)
    # ==========================================================================
    
    quality_monitoring_enabled = serializers.BooleanField(
        default=False,
        help_text="Enable Quality of Service monitoring"
    )
    
    peak_time_awareness_enabled = serializers.BooleanField(
        default=False,
        help_text="Enable peak time awareness"
    )
    
    graceful_degradation_enabled = serializers.BooleanField(
        default=False,
        help_text="Enable graceful degradation"
    )
    
    provider_ranking_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable provider ranking for failover prioritization"
    )
    
    # ==========================================================================
    # Peak Time Settings
    # ==========================================================================
    
    peak_time_start = serializers.RegexField(
        regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
        default="19:00",
        help_text="Peak time window start (HH:MM format)"
    )
    
    peak_time_end = serializers.RegexField(
        regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
        default="23:00",
        help_text="Peak time window end (HH:MM format)"
    )
    
    peak_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        default=[4, 5, 6],
        help_text="Peak days (0=Monday, 6=Sunday)"
    )
    
    peak_threshold_factor = serializers.FloatField(
        min_value=0.5,
        max_value=1.0,
        default=0.9,
        help_text="Threshold reduction factor during peak times"
    )
    
    # ==========================================================================
    # MAC Portal Specific Settings
    # ==========================================================================
    
    mac_token_expiry_warning_weight = serializers.IntegerField(
        min_value=20,
        max_value=60,
        default=40,
        help_text="Points for token expiring in <5 minutes"
    )
    
    mac_token_expiry_critical_weight = serializers.IntegerField(
        min_value=40,
        max_value=80,
        default=60,
        help_text="Points for token expiring in <2 minutes"
    )
    
    mac_portal_slow_weight = serializers.IntegerField(
        min_value=5,
        max_value=30,
        default=15,
        help_text="Points for slow portal response (>2s)"
    )
    
    mac_portal_very_slow_weight = serializers.IntegerField(
        min_value=15,
        max_value=50,
        default=30,
        help_text="Points for very slow portal response (>5s)"
    )
    
    # ==========================================================================
    # QoS Settings
    # ==========================================================================
    
    video_freeze_weight = serializers.IntegerField(
        min_value=20,
        max_value=50,
        default=35,
        help_text="Points for video freeze >2 seconds"
    )
    
    black_frame_weight = serializers.IntegerField(
        min_value=10,
        max_value=40,
        default=25,
        help_text="Points for black frames detected"
    )
    
    low_bitrate_weight = serializers.IntegerField(
        min_value=10,
        max_value=35,
        default=20,
        help_text="Points for bitrate below 50% of expected"
    )
    
    # ==========================================================================
    # Resource Management
    # ==========================================================================
    
    max_memory_per_stream_kb = serializers.IntegerField(
        min_value=100,
        max_value=2000,
        default=500,
        help_text="Maximum memory per stream in KB"
    )
    
    high_load_metrics_interval = serializers.IntegerField(
        min_value=3,
        max_value=15,
        default=5,
        help_text="Metrics interval when >50 streams active"
    )
    
    very_high_load_metrics_interval = serializers.IntegerField(
        min_value=5,
        max_value=30,
        default=10,
        help_text="Metrics interval when >100 streams active"
    )
    
    def validate(self, data):
        """
        Cross-field validation for configuration consistency.
        """
        errors = {}
        
        # Warmup threshold must be less than failover threshold
        warmup = data.get('warmup_threshold', 60)
        failover = data.get('failover_threshold', 85)
        if warmup >= failover:
            errors['warmup_threshold'] = (
                "Warmup threshold must be less than failover threshold"
            )
        
        # Response time warning must be less than critical
        rt_warning = data.get('response_time_warning', 200)
        rt_critical = data.get('response_time_critical', 400)
        if rt_warning >= rt_critical:
            errors['response_time_warning'] = (
                "Response time warning must be less than critical threshold"
            )
        
        # High load interval must be less than very high load interval
        high_load = data.get('high_load_metrics_interval', 5)
        very_high_load = data.get('very_high_load_metrics_interval', 10)
        if high_load >= very_high_load:
            errors['high_load_metrics_interval'] = (
                "High load interval must be less than very high load interval"
            )
        
        # MAC token warning weight must be less than critical
        mac_warning = data.get('mac_token_expiry_warning_weight', 40)
        mac_critical = data.get('mac_token_expiry_critical_weight', 60)
        if mac_warning >= mac_critical:
            errors['mac_token_expiry_warning_weight'] = (
                "MAC token warning weight must be less than critical weight"
            )
        
        # MAC portal slow weight must be less than very slow
        portal_slow = data.get('mac_portal_slow_weight', 15)
        portal_very_slow = data.get('mac_portal_very_slow_weight', 30)
        if portal_slow >= portal_very_slow:
            errors['mac_portal_slow_weight'] = (
                "Portal slow weight must be less than very slow weight"
            )
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data
