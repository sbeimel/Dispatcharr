#!/usr/bin/env python
"""
Script to manually clean up orphaned Redis keys for channels that no longer exist in the database.

This script is useful when channels have been deleted from the database but their Redis keys remain,
causing repeated cleanup attempts.

Usage:
    python cleanup_orphaned_redis_keys.py

Or from Django shell:
    python manage.py shell < cleanup_orphaned_redis_keys.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

import redis
from django.conf import settings
from apps.channels.models import Channel, Stream

def cleanup_orphaned_keys():
    """Clean up Redis keys for channels that don't exist in the database"""
    
    # Connect to Redis
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    
    print("=" * 80)
    print("Orphaned Redis Keys Cleanup Script")
    print("=" * 80)
    print()
    
    # Get all channel metadata keys
    pattern = "ts_proxy:channel:*:metadata"
    cursor = 0
    channel_ids = set()
    
    print(f"Scanning for channel metadata keys: {pattern}")
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
        for key in keys:
            # Extract channel ID from key
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            parts = key_str.split(':')
            if len(parts) >= 3:
                channel_id = parts[2]
                channel_ids.add(channel_id)
        
        if cursor == 0:
            break
    
    print(f"Found {len(channel_ids)} channels with Redis metadata")
    print()
    
    # Check each channel
    orphaned_channels = []
    
    for channel_id in channel_ids:
        # Check if channel exists in database
        channel_exists = Channel.objects.filter(uuid=channel_id).exists()
        stream_exists = Stream.objects.filter(stream_hash=channel_id).exists()
        
        if not channel_exists and not stream_exists:
            orphaned_channels.append(channel_id)
            print(f"❌ Orphaned: {channel_id} (not in database)")
        else:
            print(f"✅ Valid: {channel_id}")
    
    print()
    print("=" * 80)
    print(f"Found {len(orphaned_channels)} orphaned channels")
    print("=" * 80)
    print()
    
    if not orphaned_channels:
        print("No orphaned channels found. All Redis keys are valid.")
        return
    
    # Ask for confirmation
    print("The following channels will have ALL their Redis keys deleted:")
    for channel_id in orphaned_channels:
        print(f"  - {channel_id}")
    print()
    
    response = input("Do you want to proceed with cleanup? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Cleanup cancelled.")
        return
    
    print()
    print("Starting cleanup...")
    print()
    
    # Clean up each orphaned channel
    total_keys_deleted = 0
    
    for channel_id in orphaned_channels:
        print(f"Cleaning up channel: {channel_id}")
        
        # Delete all keys matching the channel pattern
        pattern = f"ts_proxy:channel:{channel_id}:*"
        cursor = 0
        channel_keys_deleted = 0
        
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
                channel_keys_deleted += len(keys)
            
            if cursor == 0:
                break
        
        print(f"  Deleted {channel_keys_deleted} keys")
        total_keys_deleted += channel_keys_deleted
    
    print()
    print("=" * 80)
    print(f"Cleanup complete! Deleted {total_keys_deleted} Redis keys total")
    print("=" * 80)


if __name__ == '__main__':
    try:
        cleanup_orphaned_keys()
    except KeyboardInterrupt:
        print("\n\nCleanup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
