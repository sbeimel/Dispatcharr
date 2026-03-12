#!/usr/bin/env python
"""
Reset Profile Connection Counters

This script resets all profile connection counters in Redis.
Use this when connections are stuck after failed stream checks or quality tests.

Usage:
    python reset_profile_connections.py

Or from Django shell:
    python manage.py shell < reset_profile_connections.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from core.utils import RedisClient
from apps.m3u.models import M3UAccountProfile

def reset_all_connections():
    """Reset all profile connection counters to 0"""
    
    redis_client = RedisClient.get_client()
    
    if not redis_client:
        print("ERROR: Could not connect to Redis")
        return False
    
    print("=" * 80)
    print("Profile Connection Counter Reset")
    print("=" * 80)
    print()
    
    # Get all profiles
    profiles = M3UAccountProfile.objects.all()
    
    if not profiles.exists():
        print("No profiles found in database.")
        return True
    
    print(f"Found {profiles.count()} profiles")
    print()
    
    reset_count = 0
    already_zero = 0
    
    for profile in profiles:
        profile_key = f"profile_connections:{profile.id}"
        current = redis_client.get(profile_key)
        
        if current:
            current_value = int(current)
            print(f"✓ Profile {profile.id:4d} ({profile.name:30s}): {current_value:3d} → 0")
            redis_client.delete(profile_key)
            reset_count += 1
        else:
            print(f"  Profile {profile.id:4d} ({profile.name:30s}): already at 0")
            already_zero += 1
    
    print()
    print("=" * 80)
    print(f"Reset complete!")
    print(f"  - {reset_count} profiles reset to 0")
    print(f"  - {already_zero} profiles already at 0")
    print("=" * 80)
    
    return True


def show_current_connections():
    """Show current connection counts for all profiles"""
    
    redis_client = RedisClient.get_client()
    
    if not redis_client:
        print("ERROR: Could not connect to Redis")
        return
    
    print("=" * 80)
    print("Current Profile Connection Counts")
    print("=" * 80)
    print()
    
    profiles = M3UAccountProfile.objects.all()
    
    if not profiles.exists():
        print("No profiles found in database.")
        return
    
    total_connections = 0
    profiles_with_connections = 0
    
    for profile in profiles:
        profile_key = f"profile_connections:{profile.id}"
        current = redis_client.get(profile_key)
        
        if current:
            current_value = int(current)
            max_streams = profile.max_streams if profile.max_streams > 0 else "∞"
            print(f"Profile {profile.id:4d} ({profile.name:30s}): {current_value:3d} / {max_streams}")
            total_connections += current_value
            profiles_with_connections += 1
        else:
            max_streams = profile.max_streams if profile.max_streams > 0 else "∞"
            print(f"Profile {profile.id:4d} ({profile.name:30s}):   0 / {max_streams}")
    
    print()
    print("=" * 80)
    print(f"Total: {total_connections} connections across {profiles_with_connections} profiles")
    print("=" * 80)


if __name__ == '__main__':
    try:
        # Show current state
        show_current_connections()
        print()
        
        # Ask for confirmation
        response = input("Do you want to reset all connection counters? (yes/no): ").strip().lower()
        
        if response == 'yes':
            print()
            success = reset_all_connections()
            
            if success:
                print()
                print("You can now try streaming again. All profiles should be available.")
            else:
                print()
                print("Reset failed. Check the error messages above.")
                sys.exit(1)
        else:
            print()
            print("Reset cancelled. No changes made.")
    
    except KeyboardInterrupt:
        print("\n\nReset cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during reset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
