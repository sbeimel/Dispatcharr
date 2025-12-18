# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0XXX_previous_migration'),  # Replace with actual previous migration
    ]

    operations = [
        # Add indexes to M3UAccountMac for faster queries
        migrations.AddIndex(
            model_name='m3uaccountmac',
            index=models.Index(fields=['account', 'status'], name='m3u_mac_acc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='m3uaccountmac',
            index=models.Index(fields=['account', 'status', 'priority'], name='m3u_mac_acc_st_prio_idx'),
        ),
        migrations.AddIndex(
            model_name='m3uaccountmac',
            index=models.Index(fields=['account', 'last_checked'], name='m3u_mac_acc_checked_idx'),
        ),
    ]
