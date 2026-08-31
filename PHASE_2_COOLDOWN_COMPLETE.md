# Phase 2: Cooldown System Merge - COMPLETE ✅

## Implementation Date
June 18, 2026

## Overview
Successfully merged the Redis-based Stream Cooldown System from v0.26.0 into Dispatcharr v0.30.0. This system prevents rapid retries of failed stream/profile combinations, working complementarily with v0.30.0's existing FAILOVER_ROTATION_COOLDOWN.

## Features Implemented

### 1. Configuration Layer (`apps/proxy/config.py`)
**Added:**
- `STREAM_COOLDOWN_ENABLED = False` (default: disabled, no breaking changes)
- `STREAM_COOLDOWN_MINUTES = 10` (default: 10 minutes)
- `stream_cooldown_enabled()` method - reads from CoreSettings with fallback
- `stream_cooldown_seconds()` method - converts minutes to seconds
- Default values in `get_proxy_settings()` fallback dict

### 2. Redis Key Management (`apps/proxy/live_proxy/redis_keys.py`)
**Added:**
```python
@staticmethod
def stream_cooldown(channel_id, stream_id, profile_id):
    """Key for stream/profile combination cooldown tracking."""
    return f"live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown"
```

### 3. Stream Manager Integration (`apps/proxy/live_proxy/input/manager.py`)
**Added:**

#### A. Cooldown Setting Method
```python
def _set_stream_cooldown(self, stream_id=None, profile_id=None):
    """Set a cooldown for the given stream/profile combination."""
```
- Reads `stream_cooldown_enabled` from config
- Retrieves profile_id from Redis metadata if not provided
- Sets Redis key with TTL from `stream_cooldown_seconds()`
- Logs cooldown activation

#### B. Cooldown Filtering in Failover Selection
Modified `_try_next_stream_with_cooldown()`:
- Filters `untried_streams` to exclude streams on cooldown
- Checks `redis_client.exists(cooldown_key)` for each candidate
- Logs remaining TTL for streams on cooldown
- Falls back to rotation cooldown if all untried streams are on cooldown

#### C. Cooldown Activation on Failure
Modified failure handling in `run()`:
- Calls `self._set_stream_cooldown()` when `failures >= self.max_retries`
- Activates cooldown in both connection failure paths:
  - Normal connection failures (line ~625)
  - Exception-based failures (line ~660)

### 4. Database Schema (`core/models.py`)
**Modified:**
- `CoreSettings.get_proxy_settings()` defaults now include:
  - `"stream_cooldown_enabled": False`
  - `"stream_cooldown_minutes": 10`

## How It Works

### Cooldown Lifecycle
1. **Stream Fails:** After `MAX_RETRIES` attempts, `_set_stream_cooldown()` is called
2. **Cooldown Activated:** Redis key set with TTL: `live:channel:{cid}:stream:{sid}:profile:{pid}:cooldown`
3. **Failover Selection:** When selecting next stream, cooldowns are checked via `redis_client.exists()`
4. **Cooldown Expires:** After TTL expires, stream+profile combo becomes available again

### Complementary with Rotation Cooldown
- **v0.30.0 Rotation Cooldown:** 60s wait after exhausting ALL streams (prevents fast wrap-around)
- **Our Stream Cooldown:** Per stream/profile combo cooldown (prevents retrying known-bad combinations)
- **Combined Effect:** More intelligent failover that avoids both rapid cycling AND bad stream choices

## Configuration Example

### Via Django Admin (CoreSettings)
```json
{
  "stream_cooldown_enabled": true,
  "stream_cooldown_minutes": 10
}
```

### Via Code (config.py)
```python
ConfigHelper.stream_cooldown_enabled()  # Returns: bool
ConfigHelper.stream_cooldown_seconds()  # Returns: int (minutes * 60)
```

## Testing Recommendations

### 1. Manual Testing
```bash
# Enable cooldown
curl -X POST http://localhost:8000/api/settings/proxy/ \
  -H "Content-Type: application/json" \
  -d '{"stream_cooldown_enabled": true, "stream_cooldown_minutes": 2}'

# Trigger stream failure (disconnect provider)
# Watch logs for: "Set 120s cooldown for stream X with profile Y on channel Z"

# Check Redis
redis-cli KEYS "live:channel:*:cooldown"
redis-cli TTL "live:channel:123:stream:456:profile:789:cooldown"
```

### 2. Verify Cooldown Filtering
**Expected Log Output:**
```
Found 5 potential alternate streams for channel 123
Stream 456 with profile 789 is on cooldown for channel 123 (87s remaining)
Found 4 untried streams for channel 123: [457, 458, 459, 460]
```

### 3. Verify Cooldown Activation
**Expected Log Output:**
```
Maximum retry attempts (3) reached for URL: http://... for channel: 123
Set 600s cooldown for stream 456 with profile 789 on channel 123
```

## Files Modified
1. `Dispatcharr-0.30.0/apps/proxy/config.py` (+16 lines)
2. `Dispatcharr-0.30.0/apps/proxy/live_proxy/redis_keys.py` (+6 lines)
3. `Dispatcharr-0.30.0/apps/proxy/live_proxy/input/manager.py` (+81 lines)
4. `Dispatcharr-0.30.0/core/models.py` (+2 lines)

**Total:** 4 files, ~105 lines added

## Backwards Compatibility
- ✅ Default `stream_cooldown_enabled = False` (no impact on existing systems)
- ✅ No database migrations required (JSON field in CoreSettings)
- ✅ Gracefully handles missing Redis client
- ✅ Gracefully handles missing profile_id metadata

## Known Limitations
1. **No Frontend UI Yet:** Settings must be configured via Django Admin or API
2. **No Cooldown Clear API:** Once set, cooldowns must expire naturally (or delete Redis key manually)
3. **Profile ID Dependency:** If profile_id is missing from Redis metadata, cooldown is silently skipped

## Next Steps (Phase 3)
1. **Frontend UI Implementation** (if required)
   - Add cooldown settings to Proxy Settings page
   - Add cooldown status display in Channel Stream Management
2. **Extended Features:**
   - Extended Timeouts (config.py)
   - UUID Validation Fix (core/utils.py)
   - Adaptive Health Monitor (manager.py)
   - Stream Preview Failover (url_utils.py)

## Related Documents
- `COOLDOWN_SYSTEM_v0.26.0.md` - Original cooldown system design
- `dispatcharr_v0.26.0_ULTIMATE_WITH_COOLDOWN.patch` - Source patch
- `PHASE_1_COMPLETE_REPORT.md` - HTTP Proxy implementation report
- `V0.30.0_IMPLEMENTATION_PLAN.md` - Overall porting plan

---
**Status:** ✅ COMPLETE
**Phase:** 2 of 3
**Next:** Phase 3 - Extended Features
