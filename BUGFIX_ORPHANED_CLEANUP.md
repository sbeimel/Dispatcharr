# Bugfix: Orphaned Channel Cleanup

## Problem

Two channels were constantly being cleaned up as "orphaned" every 30 seconds:
- `9a15d5f4-6b42-4ac3-9363-07d60aafeed4`
- `a34b0a75-95f7-4c25-9dfa-1ad6257e3650`

Each cleanup found 17-47 Redis keys but they kept reappearing.

## Root Cause

**BUG in `apps/proxy/ts_proxy/server.py` - `_clean_redis_keys()` function**

The function used a bare `except:` clause that caught exceptions but didn't handle the case where both the channel AND stream don't exist in the database:

```python
# OLD CODE (BUGGY)
try:
    channel = Channel.objects.get(uuid=channel_id)
    channel.release_stream()
except:  # ❌ Catches DoesNotExist but fallback also fails
    stream = Stream.objects.get(stream_hash=channel_id)  # ❌ Also raises DoesNotExist
    stream.release_stream()
# Function exits here if stream doesn't exist - Redis keys never deleted!
```

**What happened**:
1. Channel was deleted from database but Redis keys remained
2. Cleanup detected orphaned metadata (correct behavior)
3. Tried to call `_clean_redis_keys()`
4. `Channel.objects.get()` raised `DoesNotExist`
5. Fallback `Stream.objects.get()` also raised `DoesNotExist`
6. Function exited early - **Redis keys were never deleted**
7. Next cleanup cycle found the same keys again → infinite loop

## Fix Applied

**File**: `apps/proxy/ts_proxy/server.py` (lines 1337-1352)

Improved exception handling to continue with Redis cleanup even when channel/stream doesn't exist:

```python
# NEW CODE (FIXED)
try:
    channel = Channel.objects.get(uuid=channel_id)
    channel.release_stream()
except Channel.DoesNotExist:
    try:
        stream = Stream.objects.get(stream_hash=channel_id)
        stream.release_stream()
    except Stream.DoesNotExist:
        # Channel/stream doesn't exist in DB - that's OK, just clean Redis
        logger.info(f"Channel/stream {channel_id} not found in database, cleaning Redis keys only")
except Exception as e:
    logger.error(f"Error releasing stream for channel {channel_id}: {e}")

# Continue with Redis cleanup regardless of DB state
if not self.redis_client:
    return 0
```

**Key improvements**:
1. Specific exception handling for `Channel.DoesNotExist`
2. Nested try-except for stream lookup
3. Logs when channel/stream not found (informational, not error)
4. **Always continues to Redis cleanup** regardless of database state
5. Separate exception handler for unexpected errors

## Manual Cleanup (If Needed)

If you still have orphaned Redis keys from before the fix, use the cleanup script:

```bash
# Run the cleanup script
python cleanup_orphaned_redis_keys.py
```

The script will:
1. Scan all channel metadata keys in Redis
2. Check if each channel exists in the database
3. Identify orphaned channels (not in DB)
4. Ask for confirmation
5. Delete all Redis keys for orphaned channels

**Or manually via Redis CLI**:

```bash
# Connect to Redis
docker exec -it <redis-container> redis-cli

# Delete all keys for a specific channel
EVAL "return redis.call('del', unpack(redis.call('keys', 'ts_proxy:channel:9a15d5f4-6b42-4ac3-9363-07d60aafeed4:*')))" 0
```

## Verification

After applying the fix and running cleanup:

1. **Check logs** - should see:
   ```
   Channel/stream {channel_id} not found in database, cleaning Redis keys only
   Cleaned up X Redis keys for channel {channel_id}
   ```

2. **No more repeated cleanup** - orphaned metadata warnings should stop

3. **Redis keys deleted** - verify with:
   ```bash
   redis-cli KEYS "ts_proxy:channel:9a15d5f4-6b42-4ac3-9363-07d60aafeed4:*"
   # Should return: (empty array)
   ```

## Impact

**Before fix**:
- Orphaned Redis keys remained forever
- Cleanup ran every 30 seconds but never succeeded
- Logs filled with repeated warnings
- Redis memory slowly leaked

**After fix**:
- Orphaned keys are properly deleted
- Cleanup succeeds on first attempt
- No repeated warnings
- Redis memory is freed

## Related Files

- `apps/proxy/ts_proxy/server.py` - Fixed `_clean_redis_keys()` function
- `cleanup_orphaned_redis_keys.py` - Manual cleanup script
- `ORPHANED_CHANNEL_CLEANUP_ANALYSIS.md` - Detailed analysis

## Conclusion

This was a **bug**, not a feature. The Ghost-Client Cleanup feature was correctly detecting orphaned metadata, but the cleanup function had a bug that prevented it from deleting Redis keys when channels were deleted from the database.

The fix ensures that Redis keys are always cleaned up, even when the channel/stream no longer exists in the database.
