from django.db import models

class Settings(models.Model):
    # General Settings
    server_name = models.CharField(max_length=255, default="Dispatcharr")
    time_zone = models.CharField(max_length=50, default="UTC")
    default_logo_url = models.URLField(blank=True, null=True)
    max_concurrent_streams = models.PositiveIntegerField(default=10)
    auto_backup_frequency = models.CharField(
        max_length=50,
        choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        default="weekly"
    )
    enable_debug_logs = models.BooleanField(default=False)

    # Schedules Direct Settings
    schedules_direct_username = models.CharField(max_length=255, blank=True, null=True)
    schedules_direct_password = models.CharField(max_length=255, blank=True, null=True)
    schedules_direct_update_frequency = models.CharField(
        max_length=50,
        choices=[("12h", "Every 12 Hours"), ("daily", "Daily")],
        default="daily"
    )
    schedules_direct_api_key = models.CharField(max_length=255, blank=True, null=True)

    # Stream and Channel Settings
    transcoding_bitrate = models.PositiveIntegerField(default=2000)  # in kbps
    transcoding_audio_codec = models.CharField(
        max_length=50,
        choices=[("aac", "AAC"), ("mp3", "MP3")],
        default="aac"
    )
    transcoding_resolution = models.CharField(
        max_length=50,
        choices=[("720p", "720p"), ("1080p", "1080p")],
        default="1080p"
    )
    failover_behavior = models.CharField(
        max_length=50,
        choices=[("sequential", "Sequential"), ("random", "Random")],
        default="sequential"
    )
    stream_health_check_frequency = models.PositiveIntegerField(default=5)  # in minutes

    # Notifications
    email_notifications = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True, null=True)
    cpu_alert_threshold = models.PositiveIntegerField(default=90)  # Percentage
    memory_alert_threshold = models.PositiveIntegerField(default=90)  # Percentage

    # API Settings
    hdhr_integration = models.BooleanField(default=True)
    custom_api_endpoints = models.JSONField(blank=True, null=True)

    # Backup and Restore
    backup_path = models.CharField(max_length=255, default="backups/")
    backup_frequency = models.CharField(
        max_length=50,
        choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        default="weekly"
    )

    # Advanced
    ffmpeg_path = models.CharField(max_length=255, default="/usr/bin/ffmpeg")
    custom_transcoding_flags = models.TextField(blank=True, null=True)
    celery_worker_concurrency = models.PositiveIntegerField(default=4)
