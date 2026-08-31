# BUG #4: Stream Preview Failover Broken

**Severity:** 🔴 **CRITICAL** - Stream preview failover completely broken  
**Status:** ⚠️ **NEEDS FIX**  
**Date:** 2026-08-31  
**Version:** v0.30.0

---

## 🚨 Problem

**Stream Preview Failover does not work!**

**Log Evidence:**
```
2026-08-31 13:07:45,470 INFO live_proxy.url_utils Found 5 alternate profiles for stream preview 1187282: [582, 580, 581, 583, 584]
2026-08-31 13:07:45,470 WARNING live_proxy.manager No untried streams available for channel [...], tried: {1187282}
```

**What's happening:**
1. Stream preview finds 5 alternate **profiles** (582, 580, 581, 583, 584)
2. All profiles have **same stream_id** (1187282)
3. Manager filters based on `tried_stream_ids`
4. After first attempt, 1187282 is added to `tried_stream_ids`
5. **All** alternate profiles are filtered out because they all have stream_id 1187282
6. Failover fails: "No untried streams available"

---

## 🔍 Root Cause

### The Problem Code (v0.30.0)

**Location:** `apps/proxy/live_proxy/input/manager.py` Line 2134

```python
# Filter out streams we've already tried
untried_streams = [s for s in alternate_streams if s['stream_id'] not in self.tried_stream_ids]
```

**What's wrong:**
- Uses `self.tried_stream_ids` - a **Set of stream IDs**
- For stream preview, all alternates have **same stream_id**, different **profile_id**
- After first attempt, stream_id is marked as "tried"
- **All profiles** are then filtered out, even though they weren't tried

**Example:**
```python
alternate_streams = [
    {'stream_id': 1187282, 'profile_id': 582},  # Profile 1
    {'stream_id': 1187282, 'profile_id': 580},  # Profile 2
    {'stream_id': 1187282, 'profile_id': 581},  # Profile 3
]

# After trying profile 582:
tried_stream_ids = {1187282}

# Filter:
untried = [s for s in alternate_streams if s['stream_id'] not in tried_stream_ids]
# Result: [] (empty!) ← BUG!
```

---

## ✅ How v0.27.0 Solves This

### v0.27.0 Uses `tried_combinations`

**Location:** `Dispatcharr - 27.0/apps/proxy/live_proxy/input/manager.py`

**Initialization:**
```python
# Tracks (stream_id, profile_id) combinations
self.tried_combinations = set()
```

**When trying a stream:**
```python
# Add to tried combinations
self.tried_combinations.add((stream_id, profile_id))
```

**When filtering:**
```python
# Filter by (stream_id, profile_id) tuple, not just stream_id
untried_combinations = [
    s for s in alternate_streams 
    if (s['stream_id'], s['profile_id']) not in self.tried_combinations
]
```

**Why this works:**
- Tracks **combination** of (stream_id, profile_id)
- Stream 1187282 with profile 582 is **different** from stream 1187282 with profile 580
- Each profile gets a separate attempt

**Example:**
```python
alternate_streams = [
    {'stream_id': 1187282, 'profile_id': 582},
    {'stream_id': 1187282, 'profile_id': 580},
    {'stream_id': 1187282, 'profile_id': 581},
]

# After trying profile 582:
tried_combinations = {(1187282, 582)}

# Filter:
untried = [s for s in alternate_streams if (s['stream_id'], s['profile_id']) not in tried_combinations]
# Result: [
#   {'stream_id': 1187282, 'profile_id': 580},  ✅
#   {'stream_id': 1187282, 'profile_id': 581},  ✅
# ]
```

---

## 📊 Impact

### Before Fix (v0.30.0):
- ❌ Stream preview failover **completely broken**
- ❌ Only first profile tried, then gives up
- ❌ "No untried streams" after first attempt
- ❌ 5 alternate profiles found but not used

### After Fix (v0.27.0 logic):
- ✅ All profiles tried in order
- ✅ Failover works correctly
- ✅ Each (stream, profile) combination gets an attempt
- ✅ Default profile tried first, then others

---

## 🔧 Required Changes

### 1. Add `tried_combinations` Tracking

**File:** `apps/proxy/live_proxy/input/manager.py`

**Line 93** (after `self.tried_stream_ids = set()`):
```python
self.tried_combinations = set()  # Track (stream_id, profile_id) tuples
```

### 2. Update Failover Logic

**Line 2134** (change filter logic):
```python
# OLD:
untried_streams = [s for s in alternate_streams if s['stream_id'] not in self.tried_stream_ids]

# NEW:
untried_streams = [
    s for s in alternate_streams 
    if (s['stream_id'], s['profile_id']) not in self.tried_combinations
]
```

### 3. Add to tried_combinations When Attempting

**Line ~2160** (after selecting next stream):
```python
stream_id = next_stream['stream_id']
profile_id = next_stream['profile_id']

# Add to tried combinations
self.tried_combinations.add((stream_id, profile_id))
```

### 4. Keep tried_stream_ids for Backward Compatibility

**Don't remove** `tried_stream_ids` - it's still used for:
- Regular channel failover (different streams)
- Logging
- Other parts of the code

**Use both:**
- `tried_stream_ids` - for regular channel failover
- `tried_combinations` - for stream preview failover

---

## 🎯 Why This Was Missed

**During v0.26.0 → v0.30.0 port:**
1. ✅ Stream preview failover **feature** was ported
2. ✅ `get_alternate_streams()` returns profiles correctly
3. ❌ `tried_combinations` tracking was **NOT** ported
4. ❌ Only `tried_stream_ids` exists in v0.30.0
5. ❌ Works for **regular channels** (different stream_ids)
6. ❌ Fails for **stream preview** (same stream_id, different profile_id)

**Why it wasn't caught:**
- Regular channel failover still works (different stream_ids)
- Stream preview failover only fails at runtime
- Requires testing with multiple profiles
- Log shows "found 5 profiles" but then "no untried streams" - confusing

---

## 📝 Complete Fix (Summary)

**3 changes needed in `manager.py`:**

1. **Initialize** `tried_combinations` (line ~93)
2. **Filter** using `tried_combinations` (line ~2134)
3. **Add** to `tried_combinations` when trying (line ~2160)

**Estimated lines:** ~50 lines of code changes

**Complexity:** Medium (requires careful testing)

**Risk:** Low (additive change, doesn't break existing functionality)

---

## 🚀 Testing After Fix

```bash
# 1. Try stream preview
# 2. Let first profile fail (HTTP 456)
# 3. Check logs:

# Should see:
INFO live_proxy.url_utils Found 5 alternate profiles for stream preview 1187282
INFO live_proxy.manager Trying next stream ID 1187282 with profile ID 582
INFO live_proxy.manager Trying next stream ID 1187282 with profile ID 580  ← Works!
INFO live_proxy.manager Trying next stream ID 1187282 with profile ID 581  ← Works!
```

---

## 📊 Bug Summary

| Bug # | Issue | Status |
|-------|-------|--------|
| 1 | Missing `stream_cooldown_enabled()` | ✅ FIXED |
| 2 | Missing `stream_cooldown_seconds()` | ✅ FIXED |
| 3 | Missing `current_profile_id` parameter | ✅ FIXED |
| **4** | **Stream preview failover broken** | ⚠️ **NEEDS FIX** |

---

## 🔗 Related Files

- `apps/proxy/live_proxy/input/manager.py` - **NEEDS FIX**
- `apps/proxy/live_proxy/url_utils.py` - Works correctly (returns profiles)
- `Dispatcharr - 27.0/apps/proxy/live_proxy/input/manager.py` - Reference implementation

---

**Priority:** 🔴 **HIGH**  
**Affects:** All stream preview failover attempts  
**Fix Complexity:** Medium  
**Estimated Time:** 1-2 hours (code + testing)
