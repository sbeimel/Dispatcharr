# Generated migration for Predictive Failover System
# Requirements: 3.3, 8.5, 9.2

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('m3u', '0025_extended_features'),
    ]

    operations = [
        # FailurePattern Model (Requirements 3.3, 8.5)
        migrations.CreateModel(
            name='FailurePattern',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, help_text='Human-readable name for this pattern')),
                ('pattern_type', models.CharField(
                    max_length=30,
                    choices=[
                        ('response_time', 'Response Time Degradation'),
                        ('buffer_underrun', 'Buffer Underrun Pattern'),
                        ('bitrate_drop', 'Bitrate Drop Pattern'),
                        ('connection_reset', 'Connection Reset Pattern'),
                        ('time_window', 'Time Window Pattern'),
                        ('correlation', 'Portal Correlation Pattern'),
                        ('composite', 'Composite Pattern'),
                    ],
                    default='composite',
                    help_text='Type of failure pattern'
                )),
                ('pattern_data', models.JSONField(default=dict, help_text='JSON data describing the pattern characteristics')),
                ('confidence', models.IntegerField(
                    default=50,
                    validators=[
                        django.core.validators.MinValueValidator(0),
                        django.core.validators.MaxValueValidator(100)
                    ],
                    help_text='Confidence score (0-100%) for this pattern'
                )),
                ('hit_count', models.PositiveIntegerField(default=0, help_text='Number of times this pattern was matched')),
                ('success_count', models.PositiveIntegerField(default=0, help_text='Number of successful predictions using this pattern')),
                ('false_positive_count', models.PositiveIntegerField(default=0, help_text='Number of false positive predictions')),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('active', 'Active'),
                        ('disabled', 'Disabled'),
                        ('false_positive', 'False Positive'),
                        ('confirmed', 'Confirmed'),
                    ],
                    default='active',
                    help_text='Current status of this pattern'
                )),
                ('last_hit', models.DateTimeField(blank=True, null=True, help_text='When this pattern was last matched')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this pattern was first identified')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this pattern was last updated')),
                ('m3u_account', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='failure_patterns',
                    to='m3u.m3uaccount',
                    help_text='M3U account this pattern is associated with (if portal-specific)'
                )),
            ],
            options={
                'verbose_name': 'Failure Pattern',
                'verbose_name_plural': 'Failure Patterns',
                'ordering': ['-confidence', '-hit_count'],
            },
        ),
        migrations.AddIndex(
            model_name='failurepattern',
            index=models.Index(fields=['pattern_type', 'status'], name='proxy_failpat_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='failurepattern',
            index=models.Index(fields=['m3u_account', 'status'], name='proxy_failpat_acc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='failurepattern',
            index=models.Index(fields=['confidence'], name='proxy_failpat_confidence_idx'),
        ),

        # PredictiveFailoverEvent Model (Requirements 3.3, 8.5)
        migrations.CreateModel(
            name='PredictiveFailoverEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(
                    max_length=30,
                    choices=[
                        ('warmup_started', 'Warmup Started'),
                        ('warmup_completed', 'Warmup Completed'),
                        ('warmup_failed', 'Warmup Failed'),
                        ('warmup_released', 'Warmup Released'),
                        ('proactive_failover', 'Proactive Failover'),
                        ('failover_success', 'Failover Success'),
                        ('failover_failed', 'Failover Failed'),
                        ('pattern_matched', 'Pattern Matched'),
                        ('pattern_learned', 'Pattern Learned'),
                        ('false_positive', 'False Positive Detected'),
                        ('missed_prediction', 'Missed Prediction'),
                        ('threshold_crossed', 'Threshold Crossed'),
                        ('cooldown_started', 'Cooldown Started'),
                        ('cooldown_ended', 'Cooldown Ended'),
                    ],
                    help_text='Type of predictive failover event'
                )),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, help_text='When this event occurred')),
                ('channel_id', models.UUIDField(blank=True, null=True, db_index=True, help_text='Channel UUID if applicable')),
                ('channel_name', models.CharField(blank=True, max_length=255, help_text='Channel name for display')),
                ('stream_id', models.CharField(blank=True, max_length=100, help_text='Stream identifier')),
                ('risk_score', models.IntegerField(
                    blank=True,
                    null=True,
                    validators=[
                        django.core.validators.MinValueValidator(0),
                        django.core.validators.MaxValueValidator(100)
                    ],
                    help_text='Risk score at time of event (0-100)'
                )),
                ('reason', models.TextField(blank=True, help_text='Human-readable reason for this event')),
                ('metrics_snapshot', models.JSONField(blank=True, default=dict, help_text='Snapshot of metrics at time of event')),
                ('success', models.BooleanField(blank=True, null=True, help_text='Whether the action was successful (if applicable)')),
                ('pattern', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='events',
                    to='proxy.failurepattern',
                    help_text='Pattern that triggered this event (if applicable)'
                )),
                ('m3u_account', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='predictive_events',
                    to='m3u.m3uaccount',
                    help_text='M3U account associated with this event'
                )),
            ],
            options={
                'verbose_name': 'Predictive Failover Event',
                'verbose_name_plural': 'Predictive Failover Events',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='predictivefailoverevent',
            index=models.Index(fields=['event_type', '-timestamp'], name='proxy_predfail_type_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='predictivefailoverevent',
            index=models.Index(fields=['channel_id', '-timestamp'], name='proxy_predfail_chan_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='predictivefailoverevent',
            index=models.Index(fields=['m3u_account', '-timestamp'], name='proxy_predfail_acc_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='predictivefailoverevent',
            index=models.Index(fields=['-timestamp'], name='proxy_predfail_ts_idx'),
        ),

        # StreamPredictiveSettings Model (Requirement 9.2)
        migrations.CreateModel(
            name='StreamPredictiveSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_id', models.UUIDField(
                    blank=True,
                    null=True,
                    unique=True,
                    help_text='Channel UUID for stream-specific settings'
                )),
                ('sensitivity', models.CharField(
                    max_length=20,
                    choices=[
                        ('low', 'Low'),
                        ('normal', 'Normal'),
                        ('high', 'High'),
                        ('disabled', 'Disabled'),
                    ],
                    default='normal',
                    help_text='Sensitivity level for predictive failover'
                )),
                ('custom_warmup_threshold', models.IntegerField(
                    blank=True,
                    null=True,
                    validators=[
                        django.core.validators.MinValueValidator(40),
                        django.core.validators.MaxValueValidator(85)
                    ],
                    help_text='Custom warmup threshold (40-85), overrides global setting'
                )),
                ('custom_failover_threshold', models.IntegerField(
                    blank=True,
                    null=True,
                    validators=[
                        django.core.validators.MinValueValidator(55),
                        django.core.validators.MaxValueValidator(95)
                    ],
                    help_text='Custom failover threshold (55-95), overrides global setting'
                )),
                ('false_positive_count', models.PositiveIntegerField(default=0, help_text='Number of false positives for this stream/portal')),
                ('total_predictions', models.PositiveIntegerField(default=0, help_text='Total number of predictions made')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When these settings were created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When these settings were last updated')),
                ('m3u_account', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='predictive_settings',
                    to='m3u.m3uaccount',
                    help_text='M3U account for portal-wide settings'
                )),
            ],
            options={
                'verbose_name': 'Stream Predictive Settings',
                'verbose_name_plural': 'Stream Predictive Settings',
            },
        ),
        migrations.AddIndex(
            model_name='streampredictivesettings',
            index=models.Index(fields=['channel_id'], name='proxy_streampred_chan_idx'),
        ),
        migrations.AddIndex(
            model_name='streampredictivesettings',
            index=models.Index(fields=['m3u_account'], name='proxy_streampred_acc_idx'),
        ),
        migrations.AddConstraint(
            model_name='streampredictivesettings',
            constraint=models.CheckConstraint(
                condition=models.Q(channel_id__isnull=False) | models.Q(m3u_account__isnull=False),
                name='predictive_settings_has_target'
            ),
        ),
    ]
