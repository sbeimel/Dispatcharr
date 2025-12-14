"""
Configuration management for the Predictive Failover System.

This module defines the PredictiveConfig dataclass with all configurable parameters
and provides functions to load/save configuration from/to CoreSettings.

All parameters are configurable via Web-UI without code changes.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Literal

logger = logging.getLogger(__name__)

# CoreSettings key for predictive failover configuration
PREDICTIVE_FAILOVER_SETTINGS_KEY = "predictive-failover-settings"


@dataclass
class PredictiveConfig:
    """
    Configuration dataclass for the Predictive Failover System.
    
    All parameters have sensible defaults and can be configured via Web-UI.
    The system is disabled by default (enabled=False) to ensure existing
    behavior is preserved until explicitly activated.
    """
    
    # ==========================================================================
    # Main Settings (Haupt-Einstellungen)
    # ==========================================================================
    
    # Master switch - system is OFF by default
    enabled: bool = False
    
    # Risk score threshold to start warming up backup stream (40-85)
    warmup_threshold: int = 60
    
    # Risk score threshold to trigger proactive failover (55-95)
    failover_threshold: int = 85
    
    # Interval in seconds for collecting metrics (1-10)
    metrics_interval: int = 3
    
    # Cooldown period in seconds after a failover (prevents rapid failovers)
    cooldown_period: int = 30
    
    # ==========================================================================
    # Learning Settings (Lern-Einstellungen)
    # ==========================================================================
    
    # Enable pattern learning from failures
    pattern_learning_enabled: bool = True
    
    # Minimum confidence threshold for trusting patterns (40-90%)
    pattern_confidence_threshold: int = 60
    
    # Enable time-window based pattern detection
    time_pattern_enabled: bool = True
    
    # Enable correlation analysis for portal-wide problems
    correlation_analysis_enabled: bool = True
    
    # Enable automatic threshold optimization
    auto_tune_enabled: bool = False
    
    # Learning rate: 'slow', 'normal', 'fast'
    learning_rate: Literal['slow', 'normal', 'fast'] = 'normal'
    
    # ==========================================================================
    # Metric Weights (Metriken-Gewichtungen)
    # ==========================================================================
    
    # Response time thresholds in milliseconds
    response_time_warning: int = 200  # Warning threshold (50-500ms)
    response_time_critical: int = 400  # Critical threshold (150-1000ms)
    
    # Points added to risk score for response time issues
    response_time_warning_weight: int = 15  # Points for warning (5-30)
    response_time_critical_weight: int = 20  # Additional points for critical (10-40)
    
    # Points added per buffer underrun (max 50 total)
    buffer_underrun_weight: int = 30  # Points per underrun (15-50)
    
    # Bitrate variance threshold and weight
    bitrate_variance_threshold: int = 25  # Variance threshold in % (10-50)
    bitrate_variance_weight: int = 15  # Points for high variance (5-30)
    
    # Enable trend detection (3+ consecutive increases)
    trend_detection_enabled: bool = True
    
    # Points for connection resets (>2 in 5 minutes)
    connection_reset_weight: int = 20
    
    # Points for rising response time trend
    trend_weight: int = 10
    
    # Points for sudden bitrate drop (>50%)
    bitrate_drop_weight: int = 25
    
    # ==========================================================================
    # Pattern Matching Weights
    # ==========================================================================
    
    # Maximum points from pattern matching (confidence% * factor, max this value)
    pattern_max_weight: int = 40
    
    # Factor for pattern confidence to points conversion
    pattern_confidence_factor: float = 0.4
    
    # Points added when current time is in known failure window
    time_window_weight: int = 15
    
    # Points added for portal-wide problems
    correlation_weight: int = 20
    
    # ==========================================================================
    # Optional Modules (Optionale Module)
    # ==========================================================================
    
    # Enable Quality of Service monitoring (video freeze, black frames)
    quality_monitoring_enabled: bool = False
    
    # Enable peak time awareness (lower thresholds during peak hours)
    peak_time_awareness_enabled: bool = False
    
    # Enable graceful degradation (switch to lower quality before failover)
    graceful_degradation_enabled: bool = False
    
    # Enable provider ranking for failover prioritization
    provider_ranking_enabled: bool = True
    
    # ==========================================================================
    # Peak Time Settings (when peak_time_awareness_enabled)
    # ==========================================================================
    
    # Peak time window start (24h format, e.g., "19:00")
    peak_time_start: str = "19:00"
    
    # Peak time window end (24h format, e.g., "23:00")
    peak_time_end: str = "23:00"
    
    # Peak days (0=Monday, 6=Sunday)
    peak_days: list = field(default_factory=lambda: [4, 5, 6])  # Fri, Sat, Sun
    
    # Threshold reduction factor during peak times (e.g., 0.9 = 10% lower)
    peak_threshold_factor: float = 0.9
    
    # ==========================================================================
    # MAC Portal Specific Settings
    # ==========================================================================
    
    # Points for token expiring in <5 minutes
    mac_token_expiry_warning_weight: int = 40
    
    # Points for token expiring in <2 minutes
    mac_token_expiry_critical_weight: int = 60
    
    # Points for slow portal response (>2s)
    mac_portal_slow_weight: int = 15
    
    # Points for very slow portal response (>5s)
    mac_portal_very_slow_weight: int = 30
    
    # ==========================================================================
    # QoS Settings (when quality_monitoring_enabled)
    # ==========================================================================
    
    # Points for video freeze >2 seconds
    video_freeze_weight: int = 35
    
    # Points for black frames detected (>10 frames)
    black_frame_weight: int = 25
    
    # Points for bitrate below 50% of expected
    low_bitrate_weight: int = 20
    
    # ==========================================================================
    # Resource Management
    # ==========================================================================
    
    # Maximum memory per stream in KB
    max_memory_per_stream_kb: int = 500
    
    # Metrics interval when >50 streams active
    high_load_metrics_interval: int = 5
    
    # Metrics interval when >100 streams active
    very_high_load_metrics_interval: int = 10
    
    # ==========================================================================
    # Validation Methods
    # ==========================================================================
    
    def validate(self) -> list:
        """
        Validate configuration values and return list of errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Threshold validations
        if not 40 <= self.warmup_threshold <= 85:
            errors.append("warmup_threshold must be between 40 and 85")
        
        if not 55 <= self.failover_threshold <= 95:
            errors.append("failover_threshold must be between 55 and 95")
        
        if self.warmup_threshold >= self.failover_threshold:
            errors.append("warmup_threshold must be less than failover_threshold")
        
        if not 1 <= self.metrics_interval <= 10:
            errors.append("metrics_interval must be between 1 and 10 seconds")
        
        # Response time validations
        if not 50 <= self.response_time_warning <= 500:
            errors.append("response_time_warning must be between 50 and 500ms")
        
        if not 150 <= self.response_time_critical <= 1000:
            errors.append("response_time_critical must be between 150 and 1000ms")
        
        if self.response_time_warning >= self.response_time_critical:
            errors.append("response_time_warning must be less than response_time_critical")
        
        # Weight validations
        if not 5 <= self.response_time_warning_weight <= 30:
            errors.append("response_time_warning_weight must be between 5 and 30")
        
        if not 10 <= self.response_time_critical_weight <= 40:
            errors.append("response_time_critical_weight must be between 10 and 40")
        
        if not 15 <= self.buffer_underrun_weight <= 50:
            errors.append("buffer_underrun_weight must be between 15 and 50")
        
        if not 10 <= self.bitrate_variance_threshold <= 50:
            errors.append("bitrate_variance_threshold must be between 10 and 50%")
        
        if not 5 <= self.bitrate_variance_weight <= 30:
            errors.append("bitrate_variance_weight must be between 5 and 30")
        
        # Pattern confidence validation
        if not 40 <= self.pattern_confidence_threshold <= 90:
            errors.append("pattern_confidence_threshold must be between 40 and 90%")
        
        # Learning rate validation
        if self.learning_rate not in ('slow', 'normal', 'fast'):
            errors.append("learning_rate must be 'slow', 'normal', or 'fast'")
        
        # Peak time validation
        if self.peak_time_awareness_enabled:
            try:
                self._parse_time(self.peak_time_start)
                self._parse_time(self.peak_time_end)
            except ValueError as e:
                errors.append(f"Invalid peak time format: {e}")
            
            if not all(0 <= d <= 6 for d in self.peak_days):
                errors.append("peak_days must contain values 0-6 (Monday-Sunday)")
        
        return errors
    
    def _parse_time(self, time_str: str) -> tuple:
        """Parse time string in HH:MM format."""
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {time_str}")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time values: {time_str}")
        return hour, minute
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PredictiveConfig':
        """Create config from dictionary."""
        # Filter out unknown keys to handle version differences
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
    
    @classmethod
    def get_defaults(cls) -> 'PredictiveConfig':
        """Get a config instance with all default values."""
        return cls()


def get_predictive_config() -> PredictiveConfig:
    """
    Load predictive failover configuration from CoreSettings.
    
    Returns:
        PredictiveConfig instance with current settings
    """
    try:
        from core.models import CoreSettings
        
        try:
            settings_obj = CoreSettings.objects.get(key=PREDICTIVE_FAILOVER_SETTINGS_KEY)
            config_data = json.loads(settings_obj.value)
            return PredictiveConfig.from_dict(config_data)
        except CoreSettings.DoesNotExist:
            # Return defaults if not configured
            logger.debug("Predictive failover settings not found, using defaults")
            return PredictiveConfig.get_defaults()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in predictive failover settings: {e}")
            return PredictiveConfig.get_defaults()
            
    except Exception as e:
        logger.error(f"Error loading predictive failover config: {e}")
        return PredictiveConfig.get_defaults()


def save_predictive_config(config: PredictiveConfig) -> bool:
    """
    Save predictive failover configuration to CoreSettings.
    
    Args:
        config: PredictiveConfig instance to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from core.models import CoreSettings
        
        # Validate before saving
        errors = config.validate()
        if errors:
            logger.error(f"Config validation failed: {errors}")
            return False
        
        config_json = json.dumps(config.to_dict())
        
        obj, created = CoreSettings.objects.update_or_create(
            key=PREDICTIVE_FAILOVER_SETTINGS_KEY,
            defaults={
                'name': 'Predictive Failover Settings',
                'value': config_json
            }
        )
        
        logger.info(f"Predictive failover config {'created' if created else 'updated'}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving predictive failover config: {e}")
        return False


def reset_predictive_config() -> PredictiveConfig:
    """
    Reset predictive failover configuration to defaults.
    
    Returns:
        Default PredictiveConfig instance
    """
    default_config = PredictiveConfig.get_defaults()
    save_predictive_config(default_config)
    return default_config
