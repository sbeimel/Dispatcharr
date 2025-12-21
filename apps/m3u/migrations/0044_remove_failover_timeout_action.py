# Generated migration to remove failover_timeout_action field
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0043_add_buffering_settings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='macportalglobalsettings',
            name='failover_timeout_action',
        ),
    ]
