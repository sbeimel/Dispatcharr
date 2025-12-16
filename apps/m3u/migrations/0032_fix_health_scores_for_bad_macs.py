# Generated migration for fixing health scores

from django.db import migrations
from django.utils import timezone


def fix_health_scores_for_bad_macs(apps, schema_editor):
    """
    Create failure health records for MACs with bad status to ensure
    they get appropriate health scores instead of the default 50%.
    """
    M3UAccountMac = apps.get_model('m3u', 'M3UAccountMac')
    MACHealthRecord = apps.get_model('m3u', 'MACHealthRecord')
    
    # Find MACs with bad status but no health records
    bad_macs = M3UAccountMac.objects.filter(
        status__in=['error', 'expired', 'blocked', 'unknown']
    )
    
    created_count = 0
    for mac in bad_macs:
        # Check if MAC already has health records
        existing_records = MACHealthRecord.objects.filter(mac=mac).exists()
        if not existing_records:
            # Create a failure record to ensure low health score
            MACHealthRecord.objects.create(
                mac=mac,
                timestamp=timezone.now(),
                event_type='failure',
                error_message=f'MAC status: {mac.status}',
                http_status=None,
                endpoint_used='',
            )
            created_count += 1
    
    print(f"Created {created_count} health records for MACs with bad status")


def reverse_fix_health_scores(apps, schema_editor):
    """
    Reverse migration - remove the health records we created.
    """
    MACHealthRecord = apps.get_model('m3u', 'MACHealthRecord')
    
    # Remove health records created by this migration
    deleted_count = MACHealthRecord.objects.filter(
        error_message__startswith='MAC status:'
    ).delete()[0]
    
    print(f"Removed {deleted_count} health records created by migration")


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0031_add_macattack_engine'),
    ]

    operations = [
        migrations.RunPython(
            fix_health_scores_for_bad_macs,
            reverse_fix_health_scores,
        ),
    ]