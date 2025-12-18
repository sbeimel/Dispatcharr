# Generated migration for engine cache field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0039_add_always_clear_buffer_setting'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='engine_cache',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Cached working engines per portal URL. Format: {portal_url: {engine: str, timestamp: int, success_count: int}}'
            ),
        ),
    ]
