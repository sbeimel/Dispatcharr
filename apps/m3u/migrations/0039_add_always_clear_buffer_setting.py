# Generated migration for always_clear_buffer_on_switch setting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0038_add_failover_timeout_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='legacy_buffer_mode',
            field=models.BooleanField(
                default=False,
                help_text='Use legacy buffer clearing (0.12.0-04 style): always clear buffer on stream switch'
            ),
        ),
    ]
