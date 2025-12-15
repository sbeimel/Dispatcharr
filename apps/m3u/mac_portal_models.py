"""
MAC Portal Models for enhanced portal management.

This module contains models for:
- Global settings (timeouts, retries, cooldowns, feature toggles)
- Failover configuration
- VOD resume points
- MAC health tracking
- Failover event logging
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class MACPortalGlobalSettings(models.Model):
    """
    Global settings for MAC Portal functionality.
    Singleton model - only one instance should exist.
    
    Requirements: 45.1, 46.1, 47.1
    """
    
    # Timeouts (Requirement 45.1)
    connection_timeout = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text="Connection timeout in seconds (5-120)"
    )
    read_timeout = models.IntegerField(
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(300)],
        help_text="Read timeout in seconds (10-300)"
    )
    
    # Retries (Requirement 45.1)
    max_retries = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum retry attempts (1-10)"
    )
    retry_delay = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Base retry delay in seconds (1-30)"
    )
    exponential_backoff = models.BooleanField(
        default=True,
        help_text="Use exponential backoff for retries"
    )
    
    # Cooldowns (Requirement 46.1)
    mac_cooldown_failure = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        help_text="MAC cooldown after failure in minutes (1-60)"
    )
    mac_cooldown_block = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(1440)],
        help_text="MAC cooldown after block in minutes (5-1440)"
    )
    portal_cooldown_error = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Portal cooldown after error in minutes (1-120)"
    )
    token_refresh_threshold = models.IntegerField(
        default=80,
        validators=[MinValueValidator(50), MaxValueValidator(95)],
        help_text="Token refresh threshold percentage (50-95)"
    )

    # Feature Toggles (Requirement 47.1)
    cloudscraper_enabled = models.BooleanField(
        default=True,
        help_text="Enable Cloudscraper integration"
    )
    vod_support_enabled = models.BooleanField(
        default=True,
        help_text="Enable VOD support"
    )
    series_support_enabled = models.BooleanField(
        default=True,
        help_text="Enable Series support"
    )
    epg_download_enabled = models.BooleanField(
        default=True,
        help_text="Enable EPG download"
    )
    short_epg_enabled = models.BooleanField(
        default=True,
        help_text="Enable Short EPG for live channels"
    )
    picon_download_enabled = models.BooleanField(
        default=True,
        help_text="Enable Picon/Logo download"
    )
    tmdb_integration_enabled = models.BooleanField(
        default=False,
        help_text="Enable TMDB integration for VOD metadata"
    )
    stream_validation_enabled = models.BooleanField(
        default=True,
        help_text="Enable stream link validation before playback"
    )
    multi_mac_rotation_enabled = models.BooleanField(
        default=True,
        help_text="Enable multi-MAC rotation"
    )
    token_auto_refresh_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic token refresh"
    )
    debug_logging_enabled = models.BooleanField(
        default=False,
        help_text="Enable debug logging for portal operations"
    )
    
    # OB2_2025 Engine Toggle (Requirement 76.1) - DEPRECATED, use portal_engine instead
    ob2_2025_engine_enabled = models.BooleanField(
        default=False,
        help_text="Use OB2_2025 checking logic instead of MacReplay (deprecated)"
    )
    
    # Unified Portal Engine Selection (Requirement 100.1)
    PORTAL_ENGINE_CHOICES = [
        ('auto', 'Auto-Detect (Recommended)'),
        ('unified', 'Unified (All Strategies)'),
        ('allinone', 'AllinOne Best-of-All (Empfohlen)'),
        ('macreplay', 'MacReplayXC (Standard)'),
        ('estalker', 'EStalker (Enigma2 Style)'),
        ('boxpirate', 'BoxPirate (Dreambox Style)'),
        ('ob2_2025', 'OB2_2025 (Extended Metrics)'),
    ]
    portal_engine = models.CharField(
        max_length=20,
        choices=PORTAL_ENGINE_CHOICES,
        default='auto',
        help_text="Portal authentication engine to use"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "MAC Portal Global Settings"
        verbose_name_plural = "MAC Portal Global Settings"
    
    def __str__(self):
        return "MAC Portal Global Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)


class FailoverSettings(models.Model):
    """
    Configurable failover strategies.
    Singleton model - only one instance should exist.
    
    Requirements: 55.1, 56.1, 57.1, 58.1, 59.1, 60.1
    """
    
    class MACSelectionStrategy(models.TextChoices):
        ROUND_ROBIN = "round_robin", "Round Robin"
        HEALTH_BASED = "health_based", "Health Based"
        RANDOM = "random", "Random"
    
    # Failover Toggles (Requirement 55.1)
    mac_failover_enabled = models.BooleanField(
        default=True,
        help_text="Enable MAC-level failover"
    )
    portal_failover_enabled = models.BooleanField(
        default=True,
        help_text="Enable Portal/Endpoint failover"
    )
    stream_failover_enabled = models.BooleanField(
        default=True,
        help_text="Enable Stream-level failover"
    )
    endpoint_failover_enabled = models.BooleanField(
        default=True,
        help_text="Enable Endpoint failover"
    )
    useragent_failover_enabled = models.BooleanField(
        default=False,
        help_text="Enable User-Agent failover"
    )
    
    # MAC Failover Config (Requirement 56.1)
    mac_max_attempts = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum MAC failover attempts (1-10)"
    )
    mac_selection_strategy = models.CharField(
        max_length=20,
        choices=MACSelectionStrategy.choices,
        default=MACSelectionStrategy.HEALTH_BASED,
        help_text="Strategy for selecting next MAC"
    )
    mac_cooldown_failure = models.IntegerField(
        default=5,
        help_text="MAC cooldown after failure in minutes"
    )
    mac_cooldown_block = models.IntegerField(
        default=30,
        help_text="MAC cooldown after block in minutes"
    )
    mac_auto_recovery_interval = models.IntegerField(
        default=15,
        help_text="Auto-recovery check interval in minutes"
    )

    # Portal/Endpoint Failover Config (Requirement 57.1)
    endpoint_priority = models.JSONField(
        default=list,
        help_text="Ordered list of endpoints to try"
    )
    endpoint_timeout = models.IntegerField(
        default=10,
        help_text="Timeout per endpoint in seconds"
    )
    endpoint_cache_enabled = models.BooleanField(
        default=True,
        help_text="Cache successful endpoint"
    )
    
    # Stream Failover Config (Requirement 58.1)
    stream_validation_enabled = models.BooleanField(
        default=True,
        help_text="Validate stream before playback"
    )
    stream_validation_timeout = models.IntegerField(
        default=5,
        help_text="Stream validation timeout in seconds"
    )
    stream_max_retries = models.IntegerField(
        default=3,
        help_text="Maximum stream retry attempts"
    )
    stream_retry_different_mac = models.BooleanField(
        default=True,
        help_text="Retry with different MAC on failure"
    )
    stream_retry_different_cmd = models.BooleanField(
        default=True,
        help_text="Retry with different cmd format on failure"
    )
    
    # User-Agent Failover Config (Requirement 59.1)
    useragent_rotation_order = models.JSONField(
        default=list,
        help_text="Ordered list of User-Agents to try"
    )
    useragent_rotate_on_auth_failure = models.BooleanField(
        default=True,
        help_text="Rotate User-Agent on auth failure"
    )
    useragent_rotate_on_403 = models.BooleanField(
        default=True,
        help_text="Rotate User-Agent on 403 Forbidden"
    )
    useragent_rotate_on_cloudflare = models.BooleanField(
        default=True,
        help_text="Rotate User-Agent on Cloudflare block"
    )
    useragent_remember_successful = models.BooleanField(
        default=True,
        help_text="Remember successful User-Agent per portal"
    )
    
    # Failover Priority Order (Requirement 60.1)
    failover_priority = models.JSONField(
        default=lambda: ['mac', 'useragent', 'endpoint', 'stream'],
        help_text="Order of failover strategies to try"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Failover Settings"
        verbose_name_plural = "Failover Settings"
    
    def __str__(self):
        return "Failover Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)


class VODResumePoint(models.Model):
    """
    Stores playback resume points for VOD content.
    
    Requirements: 31.1, 31.2
    """
    
    class ContentType(models.TextChoices):
        VOD = "vod", "VOD"
        SERIES_EPISODE = "series_episode", "Series Episode"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='vod_resume_points',
        help_text="The M3U account this resume point belongs to"
    )
    vod_id = models.CharField(
        max_length=50,
        help_text="VOD item ID from portal"
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.VOD,
        help_text="Type of content"
    )
    position_seconds = models.IntegerField(
        default=0,
        help_text="Playback position in seconds"
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total duration in seconds"
    )
    last_watched = models.DateTimeField(
        auto_now=True,
        help_text="When this content was last watched"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'vod_id', 'content_type']
        verbose_name = "VOD Resume Point"
        verbose_name_plural = "VOD Resume Points"
        indexes = [
            models.Index(fields=['m3u_account', 'last_watched']),
        ]
    
    def __str__(self):
        return f"{self.vod_id} @ {self.position_seconds}s"
    
    def is_near_end(self, threshold_minutes=15):
        """Check if resume point is within threshold of the end."""
        if not self.duration_seconds:
            return False
        threshold_seconds = threshold_minutes * 60
        remaining = self.duration_seconds - self.position_seconds
        return remaining <= threshold_seconds



class MACHealthRecord(models.Model):
    """
    Tracks MAC address health and history.
    
    Requirements: 49.1
    """
    
    class EventType(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        COOLDOWN = "cooldown", "Cooldown"
        BLOCK = "block", "Block"
        RECOVERY = "recovery", "Recovery"
        EXPIRED = "expired", "Expired"
    
    mac = models.ForeignKey(
        'M3UAccountMac',
        on_delete=models.CASCADE,
        related_name='health_records',
        help_text="The MAC address this record belongs to"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this event occurred"
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        help_text="Type of health event"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if applicable"
    )
    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Response time in milliseconds"
    )
    http_status = models.IntegerField(
        null=True,
        blank=True,
        help_text="HTTP status code if applicable"
    )
    endpoint_used = models.CharField(
        max_length=255,
        blank=True,
        help_text="Endpoint that was used"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "MAC Health Record"
        verbose_name_plural = "MAC Health Records"
        indexes = [
            models.Index(fields=['mac', 'timestamp']),
            models.Index(fields=['mac', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.mac.address} - {self.event_type} @ {self.timestamp}"
    
    @classmethod
    def record_success(cls, mac, response_time_ms=None, endpoint_used=""):
        """Record a successful MAC operation."""
        return cls.objects.create(
            mac=mac,
            event_type=cls.EventType.SUCCESS,
            response_time_ms=response_time_ms,
            endpoint_used=endpoint_used
        )
    
    @classmethod
    def record_failure(cls, mac, error_message="", http_status=None, endpoint_used=""):
        """Record a failed MAC operation."""
        return cls.objects.create(
            mac=mac,
            event_type=cls.EventType.FAILURE,
            error_message=error_message,
            http_status=http_status,
            endpoint_used=endpoint_used
        )
    
    @classmethod
    def get_health_score(cls, mac, hours=24):
        """Calculate health score for a MAC based on recent events."""
        from django.db.models import Count
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        events = cls.objects.filter(
            mac=mac,
            timestamp__gte=since
        ).values('event_type').annotate(count=Count('id'))
        
        success_count = 0
        failure_count = 0
        
        for event in events:
            if event['event_type'] == cls.EventType.SUCCESS:
                success_count = event['count']
            elif event['event_type'] in [cls.EventType.FAILURE, cls.EventType.BLOCK]:
                failure_count = event['count']
        
        total = success_count + failure_count
        if total == 0:
            return 50  # Default score for MACs with no history
        
        return int((success_count / total) * 100)


class FailoverEvent(models.Model):
    """
    Logs failover events for statistics and debugging.
    
    Requirements: 61.1
    """
    
    class FailoverType(models.TextChoices):
        MAC = "mac", "MAC Failover"
        PORTAL = "portal", "Portal Failover"
        STREAM = "stream", "Stream Failover"
        USERAGENT = "useragent", "User-Agent Failover"
        ENDPOINT = "endpoint", "Endpoint Failover"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='failover_events',
        help_text="The M3U account this event belongs to"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this failover occurred"
    )
    failover_type = models.CharField(
        max_length=20,
        choices=FailoverType.choices,
        help_text="Type of failover"
    )
    original_value = models.CharField(
        max_length=255,
        help_text="Original value before failover"
    )
    new_value = models.CharField(
        max_length=255,
        help_text="New value after failover"
    )
    reason = models.TextField(
        help_text="Reason for failover"
    )
    success = models.BooleanField(
        help_text="Whether the failover was successful"
    )
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of failover operation in milliseconds"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Failover Event"
        verbose_name_plural = "Failover Events"
        indexes = [
            models.Index(fields=['m3u_account', 'timestamp']),
            models.Index(fields=['failover_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.failover_type} - {self.original_value} → {self.new_value}"
    
    @classmethod
    def log_failover(cls, account, failover_type, original, new, reason, success, duration_ms=None):
        """Log a failover event."""
        return cls.objects.create(
            m3u_account=account,
            failover_type=failover_type,
            original_value=str(original),
            new_value=str(new),
            reason=reason,
            success=success,
            duration_ms=duration_ms
        )
    
    @classmethod
    def get_statistics(cls, account, days=7):
        """Get failover statistics for an account."""
        from django.db.models import Count, Avg
        since = timezone.now() - timezone.timedelta(days=days)
        
        events = cls.objects.filter(
            m3u_account=account,
            timestamp__gte=since
        )
        
        total = events.count()
        success_count = events.filter(success=True).count()
        
        by_type = events.values('failover_type').annotate(
            count=Count('id'),
            avg_duration=Avg('duration_ms')
        )
        
        common_reasons = events.values('reason').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return {
            'total': total,
            'success_rate': (success_count / total * 100) if total > 0 else 0,
            'by_type': list(by_type),
            'common_reasons': list(common_reasons),
        }


class VODWatchedStatus(models.Model):
    """
    Tracks watched status for VOD content.
    
    Requirements: 32.1, 32.2, 32.3, 32.4
    """
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='vod_watched',
        help_text="The M3U account this status belongs to"
    )
    vod_id = models.CharField(
        max_length=50,
        help_text="VOD item ID from portal"
    )
    content_type = models.CharField(
        max_length=20,
        default="vod",
        help_text="Type of content (vod, series_episode)"
    )
    watched = models.BooleanField(
        default=False,
        help_text="Whether the content has been watched"
    )
    watch_time_minutes = models.IntegerField(
        default=0,
        help_text="Total watch time in minutes"
    )
    first_watched = models.DateTimeField(
        auto_now_add=True,
        help_text="When this content was first watched"
    )
    last_watched = models.DateTimeField(
        auto_now=True,
        help_text="When this content was last watched"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'vod_id', 'content_type']
        verbose_name = "VOD Watched Status"
        verbose_name_plural = "VOD Watched Statuses"
    
    def __str__(self):
        status = "Watched" if self.watched else "Unwatched"
        return f"{self.vod_id} - {status}"
    
    def mark_as_watched(self):
        """Mark content as watched."""
        self.watched = True
        self.save(update_fields=['watched', 'last_watched'])
    
    def clear_watched(self):
        """Clear watched status."""
        self.watched = False
        self.watch_time_minutes = 0
        self.save(update_fields=['watched', 'watch_time_minutes', 'last_watched'])


class MACCooldown(models.Model):
    """
    Tracks cooldown periods for MAC addresses.
    
    Requirements: 46.1, 46.2, 46.3
    """
    
    class CooldownReason(models.TextChoices):
        FAILURE = "failure", "Authentication Failure"
        BLOCK = "block", "Blocked by Portal"
        RATE_LIMIT = "rate_limit", "Rate Limited"
        DEVICE_CONFLICT = "device_conflict", "Device Conflict"
        EXPIRED = "expired", "Subscription Expired"
    
    mac = models.ForeignKey(
        'M3UAccountMac',
        on_delete=models.CASCADE,
        related_name='cooldowns',
        help_text="The MAC address in cooldown"
    )
    reason = models.CharField(
        max_length=20,
        choices=CooldownReason.choices,
        help_text="Reason for cooldown"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When cooldown started"
    )
    expires_at = models.DateTimeField(
        help_text="When cooldown expires"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether cooldown is still active"
    )
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "MAC Cooldown"
        verbose_name_plural = "MAC Cooldowns"
    
    def __str__(self):
        return f"{self.mac.address} - {self.reason} until {self.expires_at}"
    
    @property
    def is_expired(self):
        """Check if cooldown has expired."""
        return timezone.now() >= self.expires_at
    
    @property
    def remaining_seconds(self):
        """Get remaining cooldown time in seconds."""
        if self.is_expired:
            return 0
        return int((self.expires_at - timezone.now()).total_seconds())
    
    @classmethod
    def apply_cooldown(cls, mac, reason, duration_minutes):
        """Apply a cooldown to a MAC address."""
        expires_at = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        
        # Deactivate any existing cooldowns for this MAC
        cls.objects.filter(mac=mac, is_active=True).update(is_active=False)
        
        return cls.objects.create(
            mac=mac,
            reason=reason,
            expires_at=expires_at
        )
    
    @classmethod
    def is_mac_in_cooldown(cls, mac):
        """Check if a MAC is currently in cooldown."""
        return cls.objects.filter(
            mac=mac,
            is_active=True,
            expires_at__gt=timezone.now()
        ).exists()
    
    @classmethod
    def get_active_cooldown(cls, mac):
        """Get the active cooldown for a MAC if any."""
        return cls.objects.filter(
            mac=mac,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()


# Extended Features Models (Phase 15)

class MACFavorite(models.Model):
    """
    Stores favorite channels and VOD items.
    
    Requirements: 15.1, 15.2, 15.3, 15.4
    """
    
    class ItemType(models.TextChoices):
        CHANNEL = "channel", "Channel"
        VOD = "vod", "VOD"
        SERIES = "series", "Series"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='favorites',
        help_text="The M3U account this favorite belongs to"
    )
    item_id = models.CharField(
        max_length=50,
        help_text="Item ID from portal"
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.CHANNEL,
        help_text="Type of favorite item"
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this item was added to favorites"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'item_id', 'item_type']
        verbose_name = "MAC Favorite"
        verbose_name_plural = "MAC Favorites"
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.item_type}: {self.item_id}"


class MACRecentlyWatched(models.Model):
    """
    Tracks recently watched items.
    
    Requirements: 16.1, 16.2, 16.3, 16.4
    """
    
    class ItemType(models.TextChoices):
        CHANNEL = "channel", "Channel"
        VOD = "vod", "VOD"
        SERIES_EPISODE = "series_episode", "Series Episode"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='recently_watched',
        help_text="The M3U account this entry belongs to"
    )
    item_id = models.CharField(
        max_length=50,
        help_text="Item ID from portal"
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.CHANNEL,
        help_text="Type of watched item"
    )
    watched_at = models.DateTimeField(
        auto_now=True,
        help_text="When this item was last watched"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'item_id', 'item_type']
        verbose_name = "Recently Watched"
        verbose_name_plural = "Recently Watched"
        ordering = ['-watched_at']
    
    def __str__(self):
        return f"{self.item_type}: {self.item_id} @ {self.watched_at}"


class MACHiddenCategory(models.Model):
    """
    Stores hidden categories.
    
    Requirements: 20.1, 20.2, 20.3, 20.4
    """
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='hidden_categories',
        help_text="The M3U account this hidden category belongs to"
    )
    category_id = models.CharField(
        max_length=50,
        help_text="Category ID from portal"
    )
    hidden_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this category was hidden"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'category_id']
        verbose_name = "Hidden Category"
        verbose_name_plural = "Hidden Categories"
    
    def __str__(self):
        return f"Hidden: {self.category_id}"


class MACPlaylistSettings(models.Model):
    """
    Playlist-specific settings.
    
    Requirements: 35.1, 35.2, 35.3, 35.4
    """
    
    class StreamType(models.TextChoices):
        IPTV = "iptv", "IPTV"
        DVB = "dvb", "DVB"
        GSTREAMER = "gstreamer", "GStreamer"
        EXTEPLAYER = "exteplayer", "ExtePlayer"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='playlist_settings',
        help_text="The M3U account these settings belong to"
    )
    stream_type = models.CharField(
        max_length=20,
        choices=StreamType.choices,
        default=StreamType.IPTV,
        help_text="Preferred stream type"
    )
    show_adult_content = models.BooleanField(
        default=False,
        help_text="Show adult content categories"
    )
    country_filter = models.CharField(
        max_length=10,
        blank=True,
        help_text="Country code filter for genres"
    )
    excluded_keywords = models.JSONField(
        default=list,
        help_text="Keywords to exclude from categories"
    )
    
    class Meta:
        verbose_name = "Playlist Settings"
        verbose_name_plural = "Playlist Settings"
    
    def __str__(self):
        return f"Settings for {self.m3u_account}"


class MACDebugLog(models.Model):
    """
    Stores debug logs for MAC Portal operations.
    
    Requirements: 53.1, 53.2, 53.3, 53.4
    """
    
    class LogLevel(models.TextChoices):
        DEBUG = "DEBUG", "Debug"
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='debug_logs',
        null=True,
        blank=True,
        help_text="The M3U account this log belongs to"
    )
    mac_address = models.CharField(
        max_length=20,
        blank=True,
        help_text="MAC address if applicable"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this log was created"
    )
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO,
        help_text="Log level"
    )
    message = models.TextField(
        help_text="Log message"
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Debug Log"
        verbose_name_plural = "Debug Logs"
        indexes = [
            models.Index(fields=['m3u_account', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.message[:50]}"
    
    @classmethod
    def log(cls, message, level='INFO', account=None, mac=None, context=None):
        """Create a debug log entry."""
        return cls.objects.create(
            m3u_account=account,
            mac_address=mac or '',
            level=level,
            message=message,
            context=context or {}
        )
    
    @classmethod
    def debug(cls, message, **kwargs):
        return cls.log(message, level='DEBUG', **kwargs)
    
    @classmethod
    def info(cls, message, **kwargs):
        return cls.log(message, level='INFO', **kwargs)
    
    @classmethod
    def warning(cls, message, **kwargs):
        return cls.log(message, level='WARNING', **kwargs)
    
    @classmethod
    def error(cls, message, **kwargs):
        return cls.log(message, level='ERROR', **kwargs)


class SeriesEpisodeTracking(models.Model):
    """
    Tracks watched episodes for series.
    
    Requirements: 39.1, 39.2, 39.3, 39.4
    """
    
    m3u_account = models.ForeignKey(
        'M3UAccount',
        on_delete=models.CASCADE,
        related_name='episode_tracking',
        help_text="The M3U account this tracking belongs to"
    )
    series_id = models.CharField(
        max_length=50,
        help_text="Series ID from portal"
    )
    season_number = models.IntegerField(
        help_text="Season number"
    )
    episode_id = models.CharField(
        max_length=50,
        help_text="Episode ID from portal"
    )
    episode_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Episode number"
    )
    watched = models.BooleanField(
        default=False,
        help_text="Whether episode has been watched"
    )
    watched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When episode was watched"
    )
    resume_position = models.IntegerField(
        default=0,
        help_text="Resume position in seconds"
    )
    
    class Meta:
        unique_together = ['m3u_account', 'series_id', 'season_number', 'episode_id']
        verbose_name = "Episode Tracking"
        verbose_name_plural = "Episode Tracking"
        ordering = ['series_id', 'season_number', 'episode_number']
    
    def __str__(self):
        return f"S{self.season_number}E{self.episode_number or self.episode_id}"
    
    def mark_watched(self):
        """Mark episode as watched."""
        self.watched = True
        self.watched_at = timezone.now()
        self.save(update_fields=['watched', 'watched_at'])
