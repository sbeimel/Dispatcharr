# Generated migration to fix VOD category group_type values
# This fixes groups that were created with group_type='live' instead of 'vod_movie' or 'vod_series'

from django.db import migrations


def fix_vod_group_types(apps, schema_editor):
    """
    Fix group_type for VOD category groups that were incorrectly set to 'live'.
    
    VOD groups are identified by their name prefix:
    - "VOD - Movies - *" -> group_type = 'vod_movie'
    - "VOD - Series - *" -> group_type = 'vod_series'
    """
    ChannelGroup = apps.get_model('dispatcharr_channels', 'ChannelGroup')
    
    # Fix VOD Movie categories
    movie_updated = ChannelGroup.objects.filter(
        name__startswith='VOD - Movies'
    ).exclude(
        group_type='vod_movie'
    ).update(group_type='vod_movie')
    
    # Fix VOD Series categories
    series_updated = ChannelGroup.objects.filter(
        name__startswith='VOD - Series'
    ).exclude(
        group_type='vod_series'
    ).update(group_type='vod_series')
    
    if movie_updated or series_updated:
        print(f"\n  Fixed VOD group_type: {movie_updated} movie categories, {series_updated} series categories")


def reverse_fix(apps, schema_editor):
    """Reverse is a no-op - we don't want to break the groups again."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0028_fix_invalid_account_types'),
    ]

    operations = [
        migrations.RunPython(fix_vod_group_types, reverse_fix),
    ]
