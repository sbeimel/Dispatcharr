"""
Django Models for the Predictive Failover System.

This module contains models for:
- FailurePattern: Stores learned failure patterns with confidence scores
- PredictiveFailoverEvent: Logs all predictive failover events
- StreamPredictiveSettings: Per-stream sensitivity and threshold settings

Requirements: 3.3, 8.5, 9.2
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class FailurePattern(models.Model):
    """
    Stores learned failure patterns for predictive analysis.
    
    Patterns are identified by analyzing metrics before stream failures.
    Each pattern has a confidence score that increases with successful
    predictions and decreases with false positives.
    
    Requirements: 3.3, 8.5
    """
    
    class PatternType(models.TextChoices):
        """Types of failure patterns that can be detected."""
        RESPONSE_TIME = "response_time", "Response Time Degradation"
        BUFFER_UNDERRUN = "buffer_underrun", "Buffer Underrun Pattern"
        BITRATE_DROP = "bitrate_drop", "Bitrate Drop Pattern"
        CONNECTION_RESET = "connection_reset", "Connection Reset Pattern"
        TIME_WINDOW = "time_window", "Time Window Pattern"
        CORRELATION = "correlation", "Portal Correlation Pattern"
        COMPOSITE = "composite", "Composite Pattern"
    
    class Status(models.TextChoices):
        """Status of the failure pattern."""
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        FALSE_POSITIVE = "false_positive", "False Positive"
        CONFIRMED = "confirmed", "Confirmed"
    
    # Pattern identification
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for this pattern"
    )
    pattern_type = models.CharField(
        max_length=30,
        choices=PatternType.choices,
        default=PatternType.COMPOSITE,
        help_text="Type of failure pattern"
    )
    
    # Pattern data stored as JSON
    pattern_data = models.JSONField(
        default=dict,
        help_text="JSON data describing the pattern characteristics"
    )
    
    # Confidence and statistics
    confidence = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Confidence score (0-100%) for this pattern"
    )
    hit_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this pattern was matched"
    )
    success_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of successful predictions using this pattern"
    )
    false_positive_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of false positive predictions"
    )
    
    # Status and timestamps
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current status of this pattern"
    )
    last_hit = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this pattern was last matched"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this pattern was first identified"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this pattern was last updated"
    )

    # Optional relationships to M3U accounts and streams
    m3u_account = models.ForeignKey(
        'm3u.M3UAccount',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='failure_patterns',
        help_text="M3U account this pattern is associated with (if portal-specific)"
    )
    
    class Meta:
        ordering = ['-confidence', '-hit_count']
        verbose_name = "Failure Pattern"
        verbose_name_plural = "Failure Patterns"
        indexes = [
            models.Index(fields=['pattern_type', 'status']),
            models.Index(fields=['m3u_account', 'status']),
            models.Index(fields=['confidence']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_pattern_type_display()}) - {self.confidence}%"
    
    def record_hit(self, success: bool = True):
        """
        Record a pattern match and update statistics.
        
        Args:
            success: Whether the prediction was correct
        """
        self.hit_count += 1
        self.last_hit = timezone.now()
        
        if success:
            self.success_count += 1
            # Increase confidence by 5% on success (max 100)
            self.confidence = min(100, self.confidence + 5)
        else:
            self.false_positive_count += 1
            # Decrease confidence by 10% on false positive (min 0)
            self.confidence = max(0, self.confidence - 10)
        
        self.save(update_fields=[
            'hit_count', 'last_hit', 'success_count', 
            'false_positive_count', 'confidence', 'updated_at'
        ])
    
    def mark_as_false_positive(self):
        """Mark this pattern as a false positive and disable it."""
        self.status = self.Status.FALSE_POSITIVE
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_confirmed(self):
        """Mark this pattern as confirmed (protected from auto-cleanup)."""
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status', 'updated_at'])
    
    def disable(self):
        """Disable this pattern without marking as false positive."""
        self.status = self.Status.DISABLED
        self.save(update_fields=['status', 'updated_at'])
    
    def enable(self):
        """Re-enable a disabled pattern."""
        if self.status == self.Status.DISABLED:
            self.status = self.Status.ACTIVE
            self.save(update_fields=['status', 'updated_at'])
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of this pattern."""
        if self.hit_count == 0:
            return 0.0
        return (self.success_count / self.hit_count) * 100
    
    @classmethod
    def get_active_patterns(cls, m3u_account=None):
        """
        Get all active patterns, optionally filtered by M3U account.
        
        Args:
            m3u_account: Optional M3UAccount to filter by
            
        Returns:
            QuerySet of active FailurePattern objects
        """
        qs = cls.objects.filter(
            status__in=[cls.Status.ACTIVE, cls.Status.CONFIRMED]
        )
        if m3u_account:
            # Include both account-specific and global patterns
            qs = qs.filter(
                models.Q(m3u_account=m3u_account) | 
                models.Q(m3u_account__isnull=True)
            )
        return qs
    
    @classmethod
    def cleanup_low_confidence(cls, threshold: int = 30):
        """
        Remove patterns with confidence below threshold.
        Confirmed patterns are protected from cleanup.
        
        Args:
            threshold: Minimum confidence to keep (default 30%)
            
        Returns:
            Number of patterns deleted
        """
        deleted, _ = cls.objects.filter(
            confidence__lt=threshold
        ).exclude(
            status=cls.Status.CONFIRMED
        ).delete()
        return deleted



class PredictiveFailoverEvent(models.Model):
    """
    Logs all predictive failover events for statistics and debugging.
    
    Each event records the decision made by the predictive system,
    including the risk score, reason, and outcome.
    
    Requirements: 3.3, 8.5
    """
    
    class EventType(models.TextChoices):
        """Types of predictive failover events."""
        WARMUP_STARTED = "warmup_started", "Warmup Started"
        WARMUP_COMPLETED = "warmup_completed", "Warmup Completed"
        WARMUP_FAILED = "warmup_failed", "Warmup Failed"
        WARMUP_RELEASED = "warmup_released", "Warmup Released"
        PROACTIVE_FAILOVER = "proactive_failover", "Proactive Failover"
        FAILOVER_SUCCESS = "failover_success", "Failover Success"
        FAILOVER_FAILED = "failover_failed", "Failover Failed"
        PATTERN_MATCHED = "pattern_matched", "Pattern Matched"
        PATTERN_LEARNED = "pattern_learned", "Pattern Learned"
        FALSE_POSITIVE = "false_positive", "False Positive Detected"
        MISSED_PREDICTION = "missed_prediction", "Missed Prediction"
        THRESHOLD_CROSSED = "threshold_crossed", "Threshold Crossed"
        COOLDOWN_STARTED = "cooldown_started", "Cooldown Started"
        COOLDOWN_ENDED = "cooldown_ended", "Cooldown Ended"
    
    # Event identification
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        help_text="Type of predictive failover event"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this event occurred"
    )
    
    # Stream/Channel identification
    channel_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Channel UUID if applicable"
    )
    channel_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Channel name for display"
    )
    stream_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stream identifier"
    )
    
    # Risk score and decision data
    risk_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Risk score at time of event (0-100)"
    )
    reason = models.TextField(
        blank=True,
        help_text="Human-readable reason for this event"
    )
    
    # Metrics snapshot at time of event
    metrics_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of metrics at time of event"
    )
    
    # Outcome tracking
    success = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the action was successful (if applicable)"
    )
    
    # Related pattern (if event was triggered by pattern match)
    pattern = models.ForeignKey(
        FailurePattern,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        help_text="Pattern that triggered this event (if applicable)"
    )
    
    # M3U Account reference
    m3u_account = models.ForeignKey(
        'm3u.M3UAccount',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='predictive_events',
        help_text="M3U account associated with this event"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Predictive Failover Event"
        verbose_name_plural = "Predictive Failover Events"
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['channel_id', '-timestamp']),
            models.Index(fields=['m3u_account', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.channel_name or 'N/A'} @ {self.timestamp}"
    
    @classmethod
    def log_event(
        cls,
        event_type: str,
        channel_id=None,
        channel_name: str = "",
        stream_id: str = "",
        risk_score: int = None,
        reason: str = "",
        metrics_snapshot: dict = None,
        success: bool = None,
        pattern=None,
        m3u_account=None
    ):
        """
        Create a new predictive failover event log entry.
        
        Args:
            event_type: Type of event (from EventType choices)
            channel_id: UUID of the channel
            channel_name: Display name of the channel
            stream_id: Stream identifier
            risk_score: Risk score at time of event
            reason: Human-readable reason
            metrics_snapshot: Dict of metrics at time of event
            success: Whether action was successful
            pattern: Related FailurePattern if applicable
            m3u_account: Related M3UAccount if applicable
            
        Returns:
            Created PredictiveFailoverEvent instance
        """
        return cls.objects.create(
            event_type=event_type,
            channel_id=channel_id,
            channel_name=channel_name,
            stream_id=stream_id,
            risk_score=risk_score,
            reason=reason,
            metrics_snapshot=metrics_snapshot or {},
            success=success,
            pattern=pattern,
            m3u_account=m3u_account
        )
    
    @classmethod
    def get_statistics(cls, days: int = 7, m3u_account=None):
        """
        Get statistics for predictive failover events.
        
        Args:
            days: Number of days to look back
            m3u_account: Optional M3UAccount to filter by
            
        Returns:
            Dict with statistics
        """
        from django.db.models import Count, Avg
        
        since = timezone.now() - timezone.timedelta(days=days)
        qs = cls.objects.filter(timestamp__gte=since)
        
        if m3u_account:
            qs = qs.filter(m3u_account=m3u_account)
        
        # Count by event type
        by_type = qs.values('event_type').annotate(
            count=Count('id')
        )
        
        # Calculate success rate for failovers
        failover_events = qs.filter(
            event_type__in=[
                cls.EventType.PROACTIVE_FAILOVER,
                cls.EventType.FAILOVER_SUCCESS,
                cls.EventType.FAILOVER_FAILED
            ]
        )
        total_failovers = failover_events.count()
        successful_failovers = failover_events.filter(success=True).count()
        
        # Average risk score at failover
        avg_risk_score = qs.filter(
            event_type=cls.EventType.PROACTIVE_FAILOVER,
            risk_score__isnull=False
        ).aggregate(avg=Avg('risk_score'))['avg']
        
        # Count false positives and missed predictions
        false_positives = qs.filter(
            event_type=cls.EventType.FALSE_POSITIVE
        ).count()
        missed_predictions = qs.filter(
            event_type=cls.EventType.MISSED_PREDICTION
        ).count()
        
        return {
            'total_events': qs.count(),
            'by_type': {item['event_type']: item['count'] for item in by_type},
            'total_failovers': total_failovers,
            'successful_failovers': successful_failovers,
            'success_rate': (successful_failovers / total_failovers * 100) if total_failovers > 0 else 0,
            'avg_risk_score_at_failover': avg_risk_score,
            'false_positives': false_positives,
            'missed_predictions': missed_predictions,
        }
    
    @classmethod
    def get_recent_events(cls, limit: int = 100, m3u_account=None, channel_id=None):
        """
        Get recent predictive failover events.
        
        Args:
            limit: Maximum number of events to return
            m3u_account: Optional M3UAccount to filter by
            channel_id: Optional channel UUID to filter by
            
        Returns:
            QuerySet of recent events
        """
        qs = cls.objects.all()
        
        if m3u_account:
            qs = qs.filter(m3u_account=m3u_account)
        if channel_id:
            qs = qs.filter(channel_id=channel_id)
        
        return qs[:limit]



class StreamPredictiveSettings(models.Model):
    """
    Per-stream or per-portal predictive failover settings.
    
    Allows customization of sensitivity and thresholds for individual
    streams or entire M3U accounts/portals.
    
    Requirements: 9.2
    """
    
    class Sensitivity(models.TextChoices):
        """Sensitivity levels for predictive failover."""
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        DISABLED = "disabled", "Disabled"
    
    # Can be associated with either a stream (channel) or an M3U account
    channel_id = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="Channel UUID for stream-specific settings"
    )
    m3u_account = models.ForeignKey(
        'm3u.M3UAccount',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='predictive_settings',
        help_text="M3U account for portal-wide settings"
    )
    
    # Sensitivity setting
    sensitivity = models.CharField(
        max_length=20,
        choices=Sensitivity.choices,
        default=Sensitivity.NORMAL,
        help_text="Sensitivity level for predictive failover"
    )
    
    # Custom thresholds (override global settings when set)
    custom_warmup_threshold = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(40), MaxValueValidator(85)],
        help_text="Custom warmup threshold (40-85), overrides global setting"
    )
    custom_failover_threshold = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(55), MaxValueValidator(95)],
        help_text="Custom failover threshold (55-95), overrides global setting"
    )
    
    # Statistics for this stream/portal
    false_positive_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of false positives for this stream/portal"
    )
    total_predictions = models.PositiveIntegerField(
        default=0,
        help_text="Total number of predictions made"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When these settings were created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When these settings were last updated"
    )
    
    class Meta:
        verbose_name = "Stream Predictive Settings"
        verbose_name_plural = "Stream Predictive Settings"
        indexes = [
            models.Index(fields=['channel_id']),
            models.Index(fields=['m3u_account']),
        ]
        constraints = [
            # Ensure at least one of channel_id or m3u_account is set
            models.CheckConstraint(
                condition=models.Q(channel_id__isnull=False) | models.Q(m3u_account__isnull=False),
                name='predictive_settings_has_target'
            )
        ]
    
    def __str__(self):
        if self.channel_id:
            return f"Stream {self.channel_id} - {self.get_sensitivity_display()}"
        elif self.m3u_account:
            return f"Portal {self.m3u_account.name} - {self.get_sensitivity_display()}"
        return f"Settings - {self.get_sensitivity_display()}"
    
    def get_effective_warmup_threshold(self, global_threshold: int = 60) -> int:
        """
        Get the effective warmup threshold based on sensitivity.
        
        Args:
            global_threshold: Global warmup threshold from config
            
        Returns:
            Effective warmup threshold
        """
        if self.custom_warmup_threshold is not None:
            return self.custom_warmup_threshold
        
        # Adjust based on sensitivity
        adjustments = {
            self.Sensitivity.LOW: 10,      # Higher threshold = less sensitive
            self.Sensitivity.NORMAL: 0,    # Use global
            self.Sensitivity.HIGH: -10,    # Lower threshold = more sensitive
            self.Sensitivity.DISABLED: 999 # Effectively disabled
        }
        
        adjusted = global_threshold + adjustments.get(self.sensitivity, 0)
        return max(40, min(85, adjusted))
    
    def get_effective_failover_threshold(self, global_threshold: int = 85) -> int:
        """
        Get the effective failover threshold based on sensitivity.
        
        Args:
            global_threshold: Global failover threshold from config
            
        Returns:
            Effective failover threshold
        """
        if self.custom_failover_threshold is not None:
            return self.custom_failover_threshold
        
        # Adjust based on sensitivity
        adjustments = {
            self.Sensitivity.LOW: 5,       # Higher threshold = less sensitive
            self.Sensitivity.NORMAL: 0,    # Use global
            self.Sensitivity.HIGH: -5,     # Lower threshold = more sensitive
            self.Sensitivity.DISABLED: 999 # Effectively disabled
        }
        
        adjusted = global_threshold + adjustments.get(self.sensitivity, 0)
        return max(55, min(95, adjusted))
    
    def is_predictive_enabled(self) -> bool:
        """Check if predictive failover is enabled for this stream/portal."""
        return self.sensitivity != self.Sensitivity.DISABLED
    
    def record_prediction(self, was_false_positive: bool = False):
        """
        Record a prediction for statistics.
        
        Args:
            was_false_positive: Whether this was a false positive
        """
        self.total_predictions += 1
        if was_false_positive:
            self.false_positive_count += 1
        self.save(update_fields=['total_predictions', 'false_positive_count', 'updated_at'])
    
    @property
    def false_positive_rate(self) -> float:
        """Calculate the false positive rate."""
        if self.total_predictions == 0:
            return 0.0
        return (self.false_positive_count / self.total_predictions) * 100
    
    @property
    def should_suggest_lower_sensitivity(self) -> bool:
        """
        Check if we should suggest lowering sensitivity due to high false positive rate.
        
        Returns True if false positive rate > 30% and at least 5 predictions made.
        """
        return (
            self.total_predictions >= 5 and 
            self.false_positive_rate > 30 and
            self.sensitivity != self.Sensitivity.LOW
        )
    
    @classmethod
    def get_for_channel(cls, channel_id):
        """
        Get or create settings for a specific channel.
        
        Args:
            channel_id: UUID of the channel
            
        Returns:
            StreamPredictiveSettings instance
        """
        settings, _ = cls.objects.get_or_create(
            channel_id=channel_id,
            defaults={'sensitivity': cls.Sensitivity.NORMAL}
        )
        return settings
    
    @classmethod
    def get_for_account(cls, m3u_account):
        """
        Get or create settings for an M3U account.
        
        Args:
            m3u_account: M3UAccount instance
            
        Returns:
            StreamPredictiveSettings instance
        """
        settings, _ = cls.objects.get_or_create(
            m3u_account=m3u_account,
            channel_id__isnull=True,
            defaults={'sensitivity': cls.Sensitivity.NORMAL}
        )
        return settings
