# Orphaned Channel Cleanup Analysis

## Problem Description

Two channels are constantly being cleaned up as "orphaned" every 6-10 seconds:
- `9a15d5f4-6b42-4ac3-9363-07d60aafeed4`
- `a34b0a75-95f7-4c25-9dfa-1ad6257e3650`

Logs show:
```
Found orphaned metadata for channel X (state: unknown, owner: , clients: 0) - cleaning up
```

Each cleanup finds 17-47 Redis keys and deletes them, but the keys reappear shortly after.

## Code Analysis

### 1. Cleanup Frequency

**File**: `apps/proxy/ts_proxy/server.py` (lines 1218-1228)

The orphaned metadata check runs every **30 seconds**:

```python
# Periodically check for orphaned channels (every 30 seconds)
if hasattr(self, '_last_orphan_check'):
    if time.time() - self._last_orphan_check > 30:
        try:
            self._check_orphaned_metadata()
            self._last_orphan_check = time.time()
        except Exception as orphan_error:
            logger.error(f"Error checking orphaned metadata: {orphan_error}", exc_info=True)
else:
    self._last_orphan_check = time.time()
```

However, the cleanup thread itself runs every **1 second** (CLEANUP_CHECK_INTERVAL = 1).

### 2. Orphaned Metadata Detection Logic

**File**: `apps/proxy/ts_proxy/server.py` (lines 1273-1336)

The `_check_orphaned_metadata()` function:

1. Scans for all channel metadata keys: `ts_proxy:channel:*:metadata`
2. For each channel:
   - Gets metadata from Redis
   - Checks if owner is alive (via heartbeat key)
   - Checks client count from Redis set
   - If no owner AND no clients → cleanup

**Key Code**:
```python
# Get owner
owner = metadata.get(b'owner', b'').decode('utf-8') if b'owner' in metadata else ''

# Check if owner is still alive
owner_alive = False
if owner:
    owner_heartbeat_key = f"ts_proxy:worker:{owner}:heartbeat"
    owner_alive = self.redis_client.exists(owner_heartbeat_key)

# Check client count
client_set_key = RedisKeys.clients(channel_id)
client_count = self.redis_client.scard(client_set_key) or 0

# If no owner and no clients, clean it up
if not owner_alive and client_count == 0:
    # ... cleanup
```

### 3. Redis Key Cleanup

**File**: `apps/proxy/ts_proxy/server.py` (lines 1337-1377)

The `_clean_redis_keys()` function:

1. **FIRST** calls `channel.release_stream()` or `stream.release_stream()`
2. **THEN** scans and deletes all Redis keys matching:
   - `ts_proxy:channel:{channel_id}:*`
   - Event channel keys

**CRITICAL FINDING**: The `release_stream()` method **READS** from Redis but does NOT create new keys:

```python
# From apps/channels/models.py (Channel.release_stream)
stream_id = redis_client.get(f"channel_stream:{self.id}")  # READ only
if stream_id:
    redis_client.delete(f"channel_stream:{self.id}")  # DELETE
    
profile_id = redis_client.get(f"stream_profile:{stream_id}")  # READ only
if profile_id:
    redis_client.delete(f"stream_profile:{stream_id}")  # DELETE
    redis_client.decr(f"profile_connections:{profile_id}")  # DECREMENT
```

**No new keys are created during cleanup.**

### 4. Ghost Client Detection

**File**: `apps/proxy/ts_proxy/client_manager.py` (lines 100-145)

The heartbeat thread runs every **5 seconds** (CLIENT_HEARTBEAT_INTERVAL = 5) and:

1. Checks for stale clients (inactive > 30 seconds = 5s * 6.0 multiplier)
2. Removes ghost clients
3. Sends heartbeats for remaining clients

**Key Code**:
```python
ghost_timeout = self.heartbeat_interval * getattr(Config, 'GHOST_CLIENT_MULTIPLIER', 5.0)
# ghost_timeout = 5 * 6.0 = 30 seconds

if current_time - last_active_time > ghost_timeout:
    logger.debug(f"Client {client_id} inactive for {current_time - last_active_time:.1f}s, removing as ghost")
    clients_to_remove.add(client_id)
```

## Root Cause Analysis

### Hypothesis 1: Channels Don't Exist in Database ✅ MOST LIKELY

If the channels were deleted from the database but Redis keys remain:

1. `_clean_redis_keys()` tries to fetch the channel: `Channel.objects.get(uuid=channel_id)`
2. This **FAILS** (DoesNotExist exception)
3. Falls back to: `Stream.objects.get(stream_hash=channel_id)`
4. This also **FAILS** if stream doesn't exist
5. The exception is caught silently (`except: pass`)
6. **Redis keys are NOT deleted** because the function returns early
7. Keys remain in Redis → next cleanup cycle finds them again

**Evidence**:
- State shows as "unknown" (metadata exists but incomplete)
- Owner is empty string (no worker owns it)
- No client connections found in logs
- Keys keep reappearing after cleanup

### Hypothesis 2: Race Condition with Client Connections ❌ UNLIKELY

If clients are connecting and disconnecting rapidly:
- Would see client connection logs
- Would see varying client counts
- User confirmed: `grep "client_"` returns nothing

### Hypothesis 3: Cleanup Creates Keys ❌ RULED OUT

Analysis shows:
- `_check_orphaned_metadata()` only READS from Redis
- `_clean_redis_keys()` only DELETES keys
- `release_stream()` only READS and DELETES keys
- No code path creates new keys during cleanup

## Verification Steps

### Step 1: Check if Channels Exist in Database

Run these queries to verify:

```python
from apps.channels.models import Channel, Stream

# Check if channels exist
try:
    ch1 = Channel.objects.get(uuid='9a15d5f4-6b42-4ac3-9363-07d60aafeed4')
    print(f"Channel 1 exists: {ch1.name}")
except Channel.DoesNotExist:
    print("Channel 1 does NOT exist in database")

try:
    ch2 = Channel.objects.get(uuid='a34b0a75-95f7-4c25-9dfa-1ad6257e3650')
    print(f"Channel 2 exists: {ch2.name}")
except Channel.DoesNotExist:
    print("Channel 2 does NOT exist in database")

# Check if they exist as streams
try:
    st1 = Stream.objects.get(stream_hash='9a15d5f4-6b42-4ac3-9363-07d60aafeed4')
    print(f"Stream 1 exists: {st1.url}")
except Stream.DoesNotExist:
    print("Stream 1 does NOT exist in database")

try:
    st2 = Stream.objects.get(stream_hash='a34b0a75-95f7-4c25-9dfa-1ad6257e3650')
    print(f"Stream 2 exists: {st2.url}")
except Stream.DoesNotExist:
    print("Stream 2 does NOT exist in database")
```

### Step 2: Check Redis Keys

```bash
# Connect to Redis
docker exec -it <redis-container> redis-cli

# Check what keys exist for these channels
KEYS ts_proxy:channel:9a15d5f4-6b42-4ac3-9363-07d60aafeed4:*
KEYS ts_proxy:channel:a34b0a75-95f7-4c25-9dfa-1ad6257e3650:*

# Check metadata specifically
HGETALL ts_proxy:channel:9a15d5f4-6b42-4ac3-9363-07d60aafeed4:metadata
HGETALL ts_proxy:channel:a34b0a75-95f7-4c25-9dfa-1ad6257e3650:metadata
```

## Bug Identification

### BUG FOUND: Silent Exception Handling in _clean_redis_keys()

**File**: `apps/proxy/ts_proxy/server.py` (lines 1337-1347)

```python
def _clean_redis_keys(self, channel_id):
    """Clean up all Redis keys for a channel more efficiently"""
    # Release the channel, stream, and profile keys from the channel
    try:
        channel = Channel.objects.get(uuid=channel_id)
        channel.release_stream()
    except:  # ❌ BARE EXCEPT - catches ALL exceptions including DoesNotExist
        stream = Stream.objects.get(stream_hash=channel_id)
        stream.release_stream()
    # ... rest of cleanup
```

**Problem**:
1. If channel doesn't exist → `Channel.objects.get()` raises `DoesNotExist`
2. Bare `except:` catches it and tries stream lookup
3. If stream also doesn't exist → `Stream.objects.get()` raises `DoesNotExist`
4. This exception is **NOT caught** → function exits early
5. Redis keys are **NEVER deleted**
6. Next cleanup cycle finds the same orphaned keys again

**This is why the cleanup runs repeatedly but keys never disappear.**

## Solution

### Fix 1: Improve Exception Handling in _clean_redis_keys()

```python
def _clean_redis_keys(self, channel_id):
    """Clean up all Redis keys for a channel more efficiently"""
    # Release the channel, stream, and profile keys from the channel
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

    try:
        # ... rest of cleanup code
```

### Fix 2: Manual Cleanup (Immediate Solution)

If channels don't exist in database, manually delete all Redis keys:

```bash
# Connect to Redis
docker exec -it <redis-container> redis-cli

# Delete all keys for channel 1
EVAL "return redis.call('del', unpack(redis.call('keys', 'ts_proxy:channel:9a15d5f4-6b42-4ac3-9363-07d60aafeed4:*')))" 0

# Delete all keys for channel 2
EVAL "return redis.call('del', unpack(redis.call('keys', 'ts_proxy:channel:a34b0a75-95f7-4c25-9dfa-1ad6257e3650:*')))" 0
```

Or using Python:

```python
import redis
from django.conf import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)

# Delete all keys for both channels
for channel_id in ['9a15d5f4-6b42-4ac3-9363-07d60aafeed4', 'a34b0a75-95f7-4c25-9dfa-1ad6257e3650']:
    pattern = f"ts_proxy:channel:{channel_id}:*"
    cursor = 0
    total = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
        if keys:
            redis_client.delete(*keys)
            total += len(keys)
        if cursor == 0:
            break
    print(f"Deleted {total} keys for channel {channel_id}")
```

## Conclusion

**This is a BUG in the cleanup code**, not a feature working correctly.

The Ghost-Client Cleanup feature is working as designed (detecting orphaned metadata), but the `_clean_redis_keys()` function has a bug that prevents it from cleaning up Redis keys when the channel/stream doesn't exist in the database.

**Root Cause**: Bare `except:` clause catches `DoesNotExist` exception but the fallback code also raises `DoesNotExist`, causing the function to exit before Redis cleanup happens.

**Impact**: Orphaned Redis keys from deleted channels remain forever, causing repeated cleanup attempts every 30 seconds.

**Fix Required**: Improve exception handling to continue with Redis cleanup even when channel/stream doesn't exist in database.
