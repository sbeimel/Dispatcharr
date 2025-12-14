# Generated migration for Predictive Failover Settings

import json
from django.db import migrations, models
from django.utils.text import slugify


def create_predictive_failover_settings(apps, schema_editor):
    """Create default predictive failover settings entry."""
    CoreSettings = apps.get_model("core", "CoreSettings")
    
    # Default predictive failover settings - Master switch OFF by default
    default_settings = {
        # Main Settings - Master switch OFF by default
        "enabled": False,
        "warmup_threshold": 60,
        "failover_threshold": 85,
        "metrics_interval": 3,
        "cooldown_period": 30,
        # Learning Settings
        "pattern_learning_enabled": True,
        "pattern_confidence_threshold": 60,
        "time_pattern_enabled": True,
        "correlation_analysis_enabled": True,
        "auto_tune_enabled": False,
        "learning_rate": "normal",
        # Metric Weights
        "response_time_warning": 200,
        "response_time_critical": 400,
        "response_time_warning_weight": 15,
        "response_time_critical_weight": 20,
        "buffer_underrun_weight": 30,
        "bitrate_variance_threshold": 25,
        "bitrate_variance_weight": 15,
        "trend_detection_enabled": True,
        "connection_reset_weight": 20,
        "trend_weight": 10,
        "bitrate_drop_weight": 25,
        # Pattern Matching Weights
        "pattern_max_weight": 40,
        "pattern_confidence_factor": 0.4,
        "time_window_weight": 15,
        "correlation_weight": 20,
        # Optional Modules
        "quality_monitoring_enabled": False,
        "peak_time_awareness_enabled": False,
        "graceful_degradation_enabled": False,
        "provider_ranking_enabled": True,
        # Peak Time Settings
        "peak_time_start": "19:00",
        "peak_time_end": "23:00",
        "peak_days": [4, 5, 6],
        "peak_threshold_factor": 0.9,
        # MAC Portal Specific
        "mac_token_expiry_warning_weight": 40,
        "mac_token_expiry_critical_weight": 60,
        "mac_portal_slow_weight": 15,
        "mac_portal_very_slow_weight": 30,
        # QoS Settings
        "video_freeze_weight": 35,
        "black_frame_weight": 25,
        "low_bitrate_weight": 20,
        # Resource Management
        "max_memory_per_stream_kb": 500,
        "high_load_metrics_interval": 5,
        "very_high_load_metrics_interval": 10,
    }
    
    # Create the settings entry if it doesn't exist
    CoreSettings.objects.get_or_create(
        key=slugify("Predictive Failover Settings"),
        defaults={
            "name": "Predictive Failover Settings",
            "value": json.dumps(default_settings),
        }
    )


def reverse_predictive_failover_settings(apps, schema_editor):
    """Remove predictive failover settings entry."""
    CoreSettings = apps.get_model("core", "CoreSettings")
    CoreSettings.objects.filter(key=slugify("Predictive Failover Settings")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_alter_systemevent_event_type"),
    ]

    operations = [
        # First, alter the value field from CharField to TextField
        # This allows storing larger JSON configurations
        migrations.AlterField(
            model_name='coresettings',
            name='value',
            field=models.TextField(help_text='Setting value. Can store JSON for complex settings.'),
        ),
        # Then create the default predictive failover settings
        migrations.RunPython(
            create_predictive_failover_settings,
            reverse_predictive_failover_settings,
        ),
    ]
