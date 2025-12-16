# Migration to change mac_address from CharField to TextField
# This allows storing many MAC addresses without length limit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0032_fix_health_scores_for_bad_macs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='m3uaccount',
            name='mac_address',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='MAC address(es) for STB/MAC portal accounts. Multiple MACs can be separated by spaces or commas.',
            ),
        ),
    ]
