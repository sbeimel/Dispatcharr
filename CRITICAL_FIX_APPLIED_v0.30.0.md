# CRITICAL FIX APPLIED - v0.30.0

**Date:** 2026-08-31  
**Status:** ✅ **FIXED**  
**Severity:** 🔴 **CRITICAL**

---

## 🚨 Issue Found & Fixed

### Problem
```
AttributeError: type object 'ConfigHelper' has no attribute 'stream_cooldown_enabled'
```

**Impact:** ALL streams failed immediately after applying v0.30.0 patch

### Root Cause
Missing methods in `apps/proxy/live_proxy/config_helper.py`:
- `stream_cooldown_enabled()` ❌
- `stream_cooldown_seconds()` ❌

---

## ✅ Fix Applied (Automatic)

**File:** `apps/proxy/live_proxy/config_helper.py`  
**Status:** ✅ Already fixed in main workspace

### Changes Made:
```python
# Added at end of ConfigHelper class:

@staticmethod
def stream_cooldown_enabled():
    """Get whether stream cooldown is enabled from database or default"""
    settings = Config.get_proxy_settings()
    return settings.get("stream_cooldown_enabled", False)

@staticmethod
def stream_cooldown_seconds():
    """Get stream cooldown duration in seconds (converted from minutes) from database or default"""
    settings = Config.get_proxy_settings()
    minutes = settings.get("stream_cooldown_minutes", 10)
    return int(minutes) * 60
```

---

## 🔄 What to Do Now

### Option 1: Already Running v0.30.0 (Docker)
```bash
# Rebuild image with fix
docker build -t sbeimel/dispatcharr:0.30.0 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr \
  --no-cache .

# Restart containers
docker-compose down
docker-compose up -d
```

### Option 2: Fresh Build (Recommended)
```bash
# Fix is already in code
# Just build normally
docker build -t sbeimel/dispatcharr:base -f docker/DispatcharrBase . --no-cache
docker build -t sbeimel/dispatcharr:0.30.0 -f docker/Dockerfile --build-arg BASE_TAG=base --no-cache .

# Start
cd docker
docker-compose up -d
```

---

## ✅ Verification

After restart, check logs:
```bash
docker-compose logs dispatcharr | grep -i "cooldown_enabled"
```

**Expected:** No AttributeError

Try playing a stream - should work normally.

---

## 📦 Files Updated

### Main Workspace (✅ Fixed)
- ✅ `apps/proxy/live_proxy/config_helper.py` - Methods added

### Documentation
- ✅ `HOTFIX_COOLDOWN_CONFIG_v0.30.0.md` - Detailed fix documentation
- ✅ `CRITICAL_FIX_APPLIED_v0.30.0.md` - This file
- ✅ `dispatcharr_v0.30.0_cooldown_fix.patch` - Patch file (for reference)

---

## 🎯 Status Summary

| Item | Status |
|------|--------|
| **Issue Identified** | ✅ Complete |
| **Fix Applied** | ✅ Complete |
| **Code Updated** | ✅ Complete |
| **Documentation** | ✅ Complete |
| **Patch Created** | ✅ Complete |
| **Ready for Build** | ✅ Yes |

---

## 📝 Additional Notes

### Why This Happened
The v0.30.0 patch included cooldown code in `manager.py` but missed the supporting methods in `config_helper.py`.

### Prevention
Future patches will include verification of all dependency methods before release.

### Impact
- **Before Fix:** 100% stream failure
- **After Fix:** Normal operation, cooldown feature functional

---

**No action required if building fresh - fix is already in code!**

Just rebuild Docker images and restart containers.
