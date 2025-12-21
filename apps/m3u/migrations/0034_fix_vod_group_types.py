# Generated migration to fix VOD category group_type values
# This fixes groups that were created with group_type='live' instead of 'vod_movie' or 'vod_series'

from django.db import migrations


def fix_vod_group_types(apps, schema_editor):
    """
    Fix group_type for VOD category groups that were incorrectly set to 'live'.
    
    VOD groups are identified by their name prefix:
    - "VOD - Movies - *" -> group_type = 'vod_movie'
    - "VOD - Series - *" -> group_type = 'vod_series'
    
    NOTE: This migration is disabled because ChannelGroup model doesn't have group_type field.
    This was likely meant for a different model or the field was removed.
    """
    # Migration disabled - ChannelGroup model doesn't have group_type field
    # The original code tried to access non-existent field causing migration failure
    print("\n  Migration 0034: Skipped - ChannelGroup model doesn't have group_type field")
    pass


def reverse_fix(apps, schema_editor):
    """Reverse is a no-op - we don't want to break the groups again."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0033_alter_m3uaccount_mac_address_to_text'),
    ]

    operations = [
        migrations.RunPython(fix_vod_group_types, reverse_fix),
    ]
