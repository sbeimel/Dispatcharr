# Generated migration to clear cached portal_engine from account custom_properties
# This fixes the bug where changing global engine setting didn't take effect
# because accounts had a cached portal_engine value from previous refreshes.

from django.db import migrations


def clear_cached_portal_engine(apps, schema_editor):
    """
    Remove portal_engine from account custom_properties.
    
    This was incorrectly being saved during refresh, which caused the global
    engine setting to be ignored. The portal_engine should only be set
    explicitly by user selection or benchmark, not automatically cached.
    
    Note: fastest_engine is kept because it's set by benchmark and is intentional.
    """
    M3UAccount = apps.get_model('m3u', 'M3UAccount')
    
    updated_count = 0
    for account in M3UAccount.objects.filter(account_type='MAC'):
        custom_props = account.custom_properties or {}
        if 'portal_engine' in custom_props:
            del custom_props['portal_engine']
            account.custom_properties = custom_props
            account.save(update_fields=['custom_properties'])
            updated_count += 1
    
    if updated_count:
        print(f"\n  Cleared cached portal_engine from {updated_count} MAC accounts")
        print("  Global engine setting will now be used correctly")


def reverse_clear(apps, schema_editor):
    """Reverse is a no-op - we don't want to re-add the cached values."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0034_fix_vod_group_types'),
    ]

    operations = [
        migrations.RunPython(clear_cached_portal_engine, reverse_clear),
    ]
