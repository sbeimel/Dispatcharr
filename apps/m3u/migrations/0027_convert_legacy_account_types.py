# Migration to convert legacy account_type values to STD format
# This handles databases that may have 'Standard', 'M3U', or other legacy values

from django.db import migrations


def convert_legacy_account_types(apps, schema_editor):
    """
    Convert any legacy account_type values to the correct format.
    
    Converts:
    - 'Standard' -> 'STD'
    - 'M3U' -> 'STD'
    - '' (empty) -> 'STD'
    - NULL -> 'STD'
    
    Leaves 'STD', 'XC', 'MAC' unchanged.
    """
    M3UAccount = apps.get_model('m3u', 'M3UAccount')
    
    # Convert 'Standard' to 'STD'
    updated = M3UAccount.objects.filter(account_type='Standard').update(account_type='STD')
    if updated:
        print(f"  Converted {updated} accounts from 'Standard' to 'STD'")
    
    # Convert 'M3U' to 'STD' (legacy value)
    updated = M3UAccount.objects.filter(account_type='M3U').update(account_type='STD')
    if updated:
        print(f"  Converted {updated} accounts from 'M3U' to 'STD'")
    
    # Convert empty string to 'STD'
    updated = M3UAccount.objects.filter(account_type='').update(account_type='STD')
    if updated:
        print(f"  Converted {updated} accounts from empty to 'STD'")
    
    # Convert NULL to 'STD'
    updated = M3UAccount.objects.filter(account_type__isnull=True).update(account_type='STD')
    if updated:
        print(f"  Converted {updated} accounts from NULL to 'STD'")


def reverse_migration(apps, schema_editor):
    """
    Reverse is a no-op since we don't know what the original values were.
    The data migration is one-way only.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0026_unified_portal_engine'),
    ]

    operations = [
        migrations.RunPython(
            convert_legacy_account_types,
            reverse_migration,
            elidable=True,  # Can be squashed away in future migrations
        ),
    ]
