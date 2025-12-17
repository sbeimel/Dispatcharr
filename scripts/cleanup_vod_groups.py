"""
Cleanup script for VOD category groups.

Removes old groups with wrong naming pattern:
- "VOD - Movies - ..." 
- "VOD - Series - ..."
- "Category XXXX" (fallback names)

Run with: python manage.py shell < scripts/cleanup_vod_groups.py
"""

from apps.channels.models import ChannelGroup, ChannelGroupM3UAccount

# Find and delete old VOD groups with prefix pattern
old_patterns = [
    'VOD - Movies - ',
    'VOD - Series - ',
]

deleted_count = 0

for pattern in old_patterns:
    old_groups = ChannelGroup.objects.filter(name__startswith=pattern)
    count = old_groups.count()
    if count > 0:
        print(f"Found {count} groups starting with '{pattern}'")
        # Delete relations first
        for group in old_groups:
            ChannelGroupM3UAccount.objects.filter(channel_group=group).delete()
        # Delete groups
        old_groups.delete()
        deleted_count += count
        print(f"Deleted {count} groups")

# Also delete "Category XXXX" fallback names
category_groups = ChannelGroup.objects.filter(name__startswith='Category ')
count = category_groups.count()
if count > 0:
    print(f"Found {count} groups starting with 'Category '")
    for group in category_groups:
        ChannelGroupM3UAccount.objects.filter(channel_group=group).delete()
    category_groups.delete()
    deleted_count += count
    print(f"Deleted {count} groups")

print(f"\nTotal deleted: {deleted_count} groups")
print("Now run VOD refresh to recreate groups with correct names.")
