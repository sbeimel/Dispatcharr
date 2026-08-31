#!/usr/bin/env python3
"""
Debug script to check what's actually in Redis for cooldown keys
"""

import redis
import sys

def main():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    print("=" * 80)
    print("REDIS COOLDOWN DEBUG")
    print("=" * 80)
    
    # 1. Check all keys matching cooldown pattern
    patterns = [
        "live:cooldown:*",  # v0.27.0 format
        "live:channel:*:cooldown",  # v0.30.0 format
        "*cooldown*",  # Any cooldown key
    ]
    
    for pattern in patterns:
        print(f"\n🔍 Pattern: {pattern}")
        keys = list(r.scan_iter(match=pattern, count=1000))
        if keys:
            print(f"   Found {len(keys)} keys:")
            for key in sorted(keys):
                ttl = r.ttl(key)
                value = r.get(key)
                mins = int(ttl // 60) if ttl > 0 else 0
                secs = int(ttl % 60) if ttl > 0 else 0
                print(f"   - {key}")
                print(f"     TTL: {mins}m {secs}s (expires in {ttl}s)")
                print(f"     Value: {value}")
        else:
            print(f"   No keys found")
    
    # 2. Check specific stream IDs from logs
    stream_ids = [1187282, 1341574]  # From your logs
    
    print(f"\n" + "=" * 80)
    print("CHECKING SPECIFIC STREAMS")
    print("=" * 80)
    
    for stream_id in stream_ids:
        print(f"\n🔍 Stream ID: {stream_id}")
        
        # v0.27.0 format
        pattern_v27 = f"live:cooldown:stream:{stream_id}:profile:*"
        keys_v27 = list(r.scan_iter(match=pattern_v27, count=100))
        if keys_v27:
            print(f"   v0.27.0 format: Found {len(keys_v27)} keys")
            for key in keys_v27:
                print(f"   - {key}")
        
        # v0.30.0 format (need channel_id)
        pattern_v30 = f"live:channel:*:stream:{stream_id}:profile:*:cooldown"
        keys_v30 = list(r.scan_iter(match=pattern_v30, count=100))
        if keys_v30:
            print(f"   v0.30.0 format: Found {len(keys_v30)} keys")
            for key in keys_v30:
                ttl = r.ttl(key)
                print(f"   - {key} (TTL: {ttl}s)")
        
        if not keys_v27 and not keys_v30:
            print(f"   ❌ No cooldown keys found for stream {stream_id}")
    
    # 3. Count total keys
    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_keys = list(r.scan_iter(match="*", count=10000))
    print(f"Total Redis keys: {len(all_keys)}")
    
    cooldown_keys = [k for k in all_keys if 'cooldown' in k.lower()]
    print(f"Keys with 'cooldown': {len(cooldown_keys)}")
    
    if cooldown_keys:
        print("\nAll cooldown keys:")
        for key in sorted(cooldown_keys):
            ttl = r.ttl(key)
            print(f"  - {key} (TTL: {ttl}s)")

if __name__ == "__main__":
    try:
        main()
    except redis.ConnectionError:
        print("❌ ERROR: Could not connect to Redis at localhost:6379")
        print("   Is Redis running?")
        print("   Try: docker compose exec redis redis-cli")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
