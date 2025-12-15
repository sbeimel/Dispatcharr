# Generated migration for MAC Portal Improvements
# Requirements: 31, 45, 46, 47, 49, 55, 56, 57, 58, 59, 60, 61, 91

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0023_add_proxy_field'),
    ]

    operations = [
        # M3UAccountMac Model - Already created in migration 0022_m3uaccountmac
        # Skipping CreateModel to avoid "relation already exists" error
        
        # Add enable_vod_scanning field to M3UAccount (Requirement 91)
        migrations.AddField(
            model_name='m3uaccount',
            name='enable_vod_scanning',
            field=models.BooleanField(
                default=False,
                help_text='Scan and import VOD content (movies/series) for MAC/STB Portal accounts'
            ),
        ),
        
        # MACPortalGlobalSettings Model (Requirements 45, 46, 47)
        migrations.CreateModel(
            name='MACPortalGlobalSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('connection_timeout', models.IntegerField(default=30, validators=[django.core.validators.MinValueValidator(5), django.core.validators.MaxValueValidator(120)], help_text='Connection timeout in seconds (5-120)')),
                ('read_timeout', models.IntegerField(default=60, validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(300)], help_text='Read timeout in seconds (10-300)')),
                ('max_retries', models.IntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], help_text='Maximum retry attempts (1-10)')),
                ('retry_delay', models.IntegerField(default=2, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(30)], help_text='Base retry delay in seconds (1-30)')),
                ('exponential_backoff', models.BooleanField(default=True, help_text='Use exponential backoff for retries')),
                ('mac_cooldown_failure', models.IntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)], help_text='MAC cooldown after failure in minutes (1-60)')),
                ('mac_cooldown_block', models.IntegerField(default=30, validators=[django.core.validators.MinValueValidator(5), django.core.validators.MaxValueValidator(1440)], help_text='MAC cooldown after block in minutes (5-1440)')),
                ('portal_cooldown_error', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(120)], help_text='Portal cooldown after error in minutes (1-120)')),
                ('token_refresh_threshold', models.IntegerField(default=80, validators=[django.core.validators.MinValueValidator(50), django.core.validators.MaxValueValidator(95)], help_text='Token refresh threshold percentage (50-95)')),
                ('cloudscraper_enabled', models.BooleanField(default=True, help_text='Enable Cloudscraper integration')),
                ('vod_support_enabled', models.BooleanField(default=True, help_text='Enable VOD support')),
                ('series_support_enabled', models.BooleanField(default=True, help_text='Enable Series support')),
                ('epg_download_enabled', models.BooleanField(default=True, help_text='Enable EPG download')),
                ('short_epg_enabled', models.BooleanField(default=True, help_text='Enable Short EPG for live channels')),
                ('picon_download_enabled', models.BooleanField(default=True, help_text='Enable Picon/Logo download')),
                ('tmdb_integration_enabled', models.BooleanField(default=False, help_text='Enable TMDB integration for VOD metadata')),
                ('stream_validation_enabled', models.BooleanField(default=True, help_text='Enable stream link validation before playback')),
                ('multi_mac_rotation_enabled', models.BooleanField(default=True, help_text='Enable multi-MAC rotation')),
                ('token_auto_refresh_enabled', models.BooleanField(default=True, help_text='Enable automatic token refresh')),
                ('debug_logging_enabled', models.BooleanField(default=False, help_text='Enable debug logging for portal operations')),
                ('ob2_2025_engine_enabled', models.BooleanField(default=False, help_text='Use OB2_2025 checking logic instead of MacReplay')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'MAC Portal Global Settings',
                'verbose_name_plural': 'MAC Portal Global Settings',
            },
        ),

        # FailoverSettings Model (Requirements 55, 56, 57, 58, 59, 60)
        migrations.CreateModel(
            name='FailoverSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_failover_enabled', models.BooleanField(default=True, help_text='Enable MAC-level failover')),
                ('portal_failover_enabled', models.BooleanField(default=True, help_text='Enable Portal/Endpoint failover')),
                ('stream_failover_enabled', models.BooleanField(default=True, help_text='Enable Stream-level failover')),
                ('endpoint_failover_enabled', models.BooleanField(default=True, help_text='Enable Endpoint failover')),
                ('useragent_failover_enabled', models.BooleanField(default=False, help_text='Enable User-Agent failover')),
                ('mac_max_attempts', models.IntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], help_text='Maximum MAC failover attempts (1-10)')),
                ('mac_selection_strategy', models.CharField(choices=[('round_robin', 'Round Robin'), ('health_based', 'Health Based'), ('random', 'Random')], default='health_based', max_length=20, help_text='Strategy for selecting next MAC')),
                ('mac_cooldown_failure', models.IntegerField(default=5, help_text='MAC cooldown after failure in minutes')),
                ('mac_cooldown_block', models.IntegerField(default=30, help_text='MAC cooldown after block in minutes')),
                ('mac_auto_recovery_interval', models.IntegerField(default=15, help_text='Auto-recovery check interval in minutes')),
                ('endpoint_priority', models.JSONField(default=list, help_text='Ordered list of endpoints to try')),
                ('endpoint_timeout', models.IntegerField(default=10, help_text='Timeout per endpoint in seconds')),
                ('endpoint_cache_enabled', models.BooleanField(default=True, help_text='Cache successful endpoint')),
                ('stream_validation_enabled', models.BooleanField(default=True, help_text='Validate stream before playback')),
                ('stream_validation_timeout', models.IntegerField(default=5, help_text='Stream validation timeout in seconds')),
                ('stream_max_retries', models.IntegerField(default=3, help_text='Maximum stream retry attempts')),
                ('stream_retry_different_mac', models.BooleanField(default=True, help_text='Retry with different MAC on failure')),
                ('stream_retry_different_cmd', models.BooleanField(default=True, help_text='Retry with different cmd format on failure')),
                ('useragent_rotation_order', models.JSONField(default=list, help_text='Ordered list of User-Agents to try')),
                ('useragent_rotate_on_auth_failure', models.BooleanField(default=True, help_text='Rotate User-Agent on auth failure')),
                ('useragent_rotate_on_403', models.BooleanField(default=True, help_text='Rotate User-Agent on 403 Forbidden')),
                ('useragent_rotate_on_cloudflare', models.BooleanField(default=True, help_text='Rotate User-Agent on Cloudflare block')),
                ('useragent_remember_successful', models.BooleanField(default=True, help_text='Remember successful User-Agent per portal')),
                ('failover_priority', models.JSONField(default=list, help_text='Order of failover strategies to try')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Failover Settings',
                'verbose_name_plural': 'Failover Settings',
            },
        ),
        
        # VODResumePoint Model (Requirement 31)
        migrations.CreateModel(
            name='VODResumePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vod_id', models.CharField(max_length=50, help_text='VOD item ID from portal')),
                ('content_type', models.CharField(choices=[('vod', 'VOD'), ('series_episode', 'Series Episode')], default='vod', max_length=20, help_text='Type of content')),
                ('position_seconds', models.IntegerField(default=0, help_text='Playback position in seconds')),
                ('duration_seconds', models.IntegerField(blank=True, null=True, help_text='Total duration in seconds')),
                ('last_watched', models.DateTimeField(auto_now=True, help_text='When this content was last watched')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this resume point belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='vod_resume_points', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'VOD Resume Point',
                'verbose_name_plural': 'VOD Resume Points',
            },
        ),
        migrations.AddConstraint(
            model_name='vodresumepoint',
            constraint=models.UniqueConstraint(fields=['m3u_account', 'vod_id', 'content_type'], name='unique_vod_resume_point'),
        ),
        migrations.AddIndex(
            model_name='vodresumepoint',
            index=models.Index(fields=['m3u_account', 'last_watched'], name='m3u_vodresu_m3u_acc_idx'),
        ),

        # MACHealthRecord Model (Requirement 49)
        migrations.CreateModel(
            name='MACHealthRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, help_text='When this event occurred')),
                ('event_type', models.CharField(choices=[('success', 'Success'), ('failure', 'Failure'), ('cooldown', 'Cooldown'), ('block', 'Block'), ('recovery', 'Recovery'), ('expired', 'Expired')], max_length=20, help_text='Type of health event')),
                ('error_message', models.TextField(blank=True, help_text='Error message if applicable')),
                ('response_time_ms', models.IntegerField(blank=True, null=True, help_text='Response time in milliseconds')),
                ('http_status', models.IntegerField(blank=True, null=True, help_text='HTTP status code if applicable')),
                ('endpoint_used', models.CharField(blank=True, max_length=255, help_text='Endpoint that was used')),
                ('mac', models.ForeignKey(help_text='The MAC address this record belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='health_records', to='m3u.m3uaccountmac')),
            ],
            options={
                'verbose_name': 'MAC Health Record',
                'verbose_name_plural': 'MAC Health Records',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='machealthrecord',
            index=models.Index(fields=['mac', 'timestamp'], name='m3u_macheal_mac_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='machealthrecord',
            index=models.Index(fields=['mac', 'event_type'], name='m3u_macheal_mac_evt_idx'),
        ),
        
        # FailoverEvent Model (Requirement 61)
        migrations.CreateModel(
            name='FailoverEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, help_text='When this failover occurred')),
                ('failover_type', models.CharField(choices=[('mac', 'MAC Failover'), ('portal', 'Portal Failover'), ('stream', 'Stream Failover'), ('useragent', 'User-Agent Failover'), ('endpoint', 'Endpoint Failover')], max_length=20, help_text='Type of failover')),
                ('original_value', models.CharField(max_length=255, help_text='Original value before failover')),
                ('new_value', models.CharField(max_length=255, help_text='New value after failover')),
                ('reason', models.TextField(help_text='Reason for failover')),
                ('success', models.BooleanField(help_text='Whether the failover was successful')),
                ('duration_ms', models.IntegerField(blank=True, null=True, help_text='Duration of failover operation in milliseconds')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this event belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='failover_events', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Failover Event',
                'verbose_name_plural': 'Failover Events',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='failoverevent',
            index=models.Index(fields=['m3u_account', 'timestamp'], name='m3u_failove_acc_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='failoverevent',
            index=models.Index(fields=['failover_type', 'timestamp'], name='m3u_failove_type_ts_idx'),
        ),
        
        # VODWatchedStatus Model (Requirement 32)
        migrations.CreateModel(
            name='VODWatchedStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vod_id', models.CharField(max_length=50, help_text='VOD item ID from portal')),
                ('content_type', models.CharField(default='vod', max_length=20, help_text='Type of content (vod, series_episode)')),
                ('watched', models.BooleanField(default=False, help_text='Whether the content has been watched')),
                ('watch_time_minutes', models.IntegerField(default=0, help_text='Total watch time in minutes')),
                ('first_watched', models.DateTimeField(auto_now_add=True, help_text='When this content was first watched')),
                ('last_watched', models.DateTimeField(auto_now=True, help_text='When this content was last watched')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this status belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='vod_watched', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'VOD Watched Status',
                'verbose_name_plural': 'VOD Watched Statuses',
            },
        ),
        migrations.AddConstraint(
            model_name='vodwatchedstatus',
            constraint=models.UniqueConstraint(fields=['m3u_account', 'vod_id', 'content_type'], name='unique_vod_watched_status'),
        ),
        
        # MACCooldown Model (Requirement 46)
        migrations.CreateModel(
            name='MACCooldown',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('failure', 'Authentication Failure'), ('block', 'Blocked by Portal'), ('rate_limit', 'Rate Limited'), ('device_conflict', 'Device Conflict'), ('expired', 'Subscription Expired')], max_length=20, help_text='Reason for cooldown')),
                ('started_at', models.DateTimeField(auto_now_add=True, help_text='When cooldown started')),
                ('expires_at', models.DateTimeField(help_text='When cooldown expires')),
                ('is_active', models.BooleanField(default=True, help_text='Whether cooldown is still active')),
                ('mac', models.ForeignKey(help_text='The MAC address in cooldown', on_delete=django.db.models.deletion.CASCADE, related_name='cooldowns', to='m3u.m3uaccountmac')),
            ],
            options={
                'verbose_name': 'MAC Cooldown',
                'verbose_name_plural': 'MAC Cooldowns',
                'ordering': ['-started_at'],
            },
        ),
    ]
