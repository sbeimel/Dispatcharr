# Generated migration for stream performance settings

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0036_add_proxy_field_for_all_account_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='buffer_chunks',
            field=models.IntegerField(
                default=10,
                help_text='Buffer size in chunks (4-20, ~250KB per chunk)',
                validators=[
                    django.core.validators.MinValueValidator(4),
                    django.core.validators.MaxValueValidator(20)
                ]
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='health_check_timeout',
            field=models.IntegerField(
                default=10,
                help_text='Health check timeout in seconds (5-30)',
                validators=[
                    django.core.validators.MinValueValidator(5),
                    django.core.validators.MaxValueValidator(30)
                ]
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='health_check_timeout_switching',
            field=models.IntegerField(
                default=15,
                help_text='Health check timeout during stream switch in seconds (10-60)',
                validators=[
                    django.core.validators.MinValueValidator(10),
                    django.core.validators.MaxValueValidator(60)
                ]
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='smart_buffer_clear_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Enable smart buffer clearing on stream switch (only when codec/resolution changes)'
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='buffer_clear_on_codec_change',
            field=models.BooleanField(
                default=True,
                help_text='Clear buffer when codec changes (e.g., h264 → hevc)'
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='buffer_clear_on_resolution_change',
            field=models.BooleanField(
                default=True,
                help_text='Clear buffer when resolution changes (e.g., 720p → 1080p)'
            ),
        ),
    ]
