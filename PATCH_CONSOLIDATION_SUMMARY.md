# Dispatcharr v0.27.0 - Patch Consolidation Summary

**Date:** June 18, 2026  
**Purpose:** Reference guide for all patches included in v0.27.0 COMPLETE release

---

## 📦 Patch Files Included

All functionality described in `DISPATCHARR_v0.27.0_COMPLETE_GUIDE.md` is available across these patch files:

### Primary Patches (Apply in Order)

**1. dispatcharr_v0.26.0_COMPLETE_FIX.patch**
- Docker build fix (psycopg/django-db-geventpool)
- Profile failover fix (3 bugs)
- Files: pyproject.toml, docker/DispatcharrBase, docker/Dockerfile, url_utils.py, manager.py, views.py

**2. dispatcharr_v0.26.0_ULTIMATE.patch**
- HTTP Proxy support (proxy + proxy_for_api fields)
- Extended timeouts (12 settings)
- XC Client proxy integration (10 calls)
- build_command() proxy fix
- UUID validation fix
- Files: All 18 backend files from Feature Summary

**3. dispatcharr_v0.26.0_cooldown_system.patch**
- Stream Cooldown System (backend + frontend)
- Last Resort recovery
- Redis key structure
- Files: config.py, config_helper.py, redis_keys.py, manager.py, frontend (3 files)

**4. dispatcharr_v0.27.0_bugfixes_final.patch**
- Global cooldown keys (removed channel_id)
- LAST RESORT safety (cursor-based scan)
- URL utils cooldown for channel playback
- Health monitor flags
- Files: redis_keys.py, url_utils.py, manager.py

---

## 🔄 Application Method

### Option A: Apply All Patches Sequentially (Recommended)

```bash
cd /path/to/dispatcharr

# 1. Docker build fixes + Profile failover
patch -p1 < dispatcharr_v0.26.0_COMPLETE_FIX.patch

# 2. HTTP Proxy + Extended features
patch -p1 < dispatcharr_v0.26.0_ULTIMATE.patch

# 3. Cooldown system
patch -p1 < dispatcharr_v0.26.0_cooldown_system.patch

# 4. Bug fixes
patch -p1 < dispatcharr_v0.27.0_bugfixes_final.patch

# Verify no conflicts
git status
```

### Option B: Manual Code Integration

If patches conflict or you have local modifications:

1. Review `DISPATCHARR_v0.27.0_COMPLETE_GUIDE.md` - Feature Deep Dive section
2. Apply changes manually file-by-file using the code examples
3. Reference individual patch files for exact line changes
4. Test after each feature group

---

## 📊 Feature-to-Patch Mapping

| Feature # | Feature Name | Primary Patch | Additional Patches |
|-----------|--------------|---------------|-------------------|
| 1 | Docker Build Fix | v0.26.0_COMPLETE_FIX | - |
| 2 | Profile Failover (3 bugs) | v0.26.0_COMPLETE_FIX | - |
| 3 | HTTP Proxy Support | v0.26.0_ULTIMATE | - |
| 4 | Extended Timeouts | v0.26.0_ULTIMATE | - |
| 5 | build_command() Proxy Fix | v0.26.0_ULTIMATE | - |
| 6 | UUID Validation Fix | v0.26.0_ULTIMATE | - |
| 7 | Adaptive Health Monitor | v0.26.0_ULTIMATE | - |
| 8 | HTTP Proxy Timeout Failover | v0.26.0_ULTIMATE | - |
| 9 | HTTP Reader Race Condition | v0.26.0_ULTIMATE | - |
| 10 | XC Client Proxy (10 calls) | v0.26.0_ULTIMATE | - |
| 11 | Stream Preview Failover | v0.26.0_ULTIMATE | - |
| 12 | Stream Cooldown System | v0.26.0_cooldown_system | v0.27.0_bugfixes_final |
| 13 | Buffer Timeout Failover | v0.27.0 BASE | (Already in v0.27.0) |
| 14 | Logo Timeout Fix | NOT IMPLEMENTED | Deferred to v0.27.1 |
| 15 | Basic Authentication | NOT IMPLEMENTED | Deferred to v0.27.1 |

---

## 🐛 Bug-to-Patch Mapping

| Bug # | Bug Name | Severity | Patch |
|-------|----------|----------|-------|
| #1 | Cooldown Missing in Channel Playback | CRITICAL | v0.27.0_bugfixes_final |
| #2 | Docker Build Failure | CRITICAL | v0.26.0_COMPLETE_FIX |
| #3 | Transcode Streams Broken | CRITICAL | v0.26.0_ULTIMATE |
| #4 | LAST RESORT Race Condition | HIGH | v0.27.0_bugfixes_final |
| #5 | Cooldown Key Mismatch | HIGH | v0.27.0_bugfixes_final |
| #6 | tried_combinations Never Reset | MEDIUM | v0.26.0_ULTIMATE |
| #7 | Missing Current Profile Check | MEDIUM | v0.26.0_ULTIMATE |
| #8 | Overly Broad Cleanup Pattern | LOW | v0.27.0_bugfixes_final |

---

## 📁 Files Modified by Patch

### dispatcharr_v0.26.0_COMPLETE_FIX.patch

**Docker & Dependencies (3 files):**
- pyproject.toml
- docker/DispatcharrBase
- docker/Dockerfile

**Profile Failover (3 files):**
- apps/proxy/live_proxy/url_utils.py
- apps/proxy/live_proxy/views.py
- apps/proxy/live_proxy/input/manager.py

---

### dispatcharr_v0.26.0_ULTIMATE.patch

**Core Models (3 files):**
- core/models.py
- core/utils.py
- core/xtream_codes.py

**M3U & Proxy (5 files):**
- apps/m3u/models.py
- apps/m3u/serializers.py
- apps/m3u/migrations/0022_m3uaccount_proxy_for_api.py
- apps/proxy/config.py
- apps/proxy/live_proxy/config_helper.py

**Proxy Live System (4 files):**
- apps/proxy/live_proxy/input/manager.py (extended)
- apps/proxy/live_proxy/input/http_streamer.py
- apps/proxy/live_proxy/url_utils.py (extended)
- apps/proxy/live_proxy/server.py

**Tasks (2 files):**
- apps/m3u/tasks.py (5 XC Client calls)
- apps/vod/tasks.py (5 XC Client calls)

**Channels (1 file):**
- apps/channels/api_views.py

**Output (1 file):**
- apps/output/views.py

---

### dispatcharr_v0.26.0_cooldown_system.patch

**Backend (4 files):**
- apps/proxy/config.py (extended)
- apps/proxy/live_proxy/config_helper.py (extended)
- apps/proxy/live_proxy/redis_keys.py
- apps/proxy/live_proxy/input/manager.py (extended)

**Frontend (3 files):**
- frontend/src/constants.js
- frontend/src/components/forms/settings/ProxySettingsForm.jsx
- frontend/src/utils/forms/settings/ProxySettingsFormUtils.js

---

### dispatcharr_v0.27.0_bugfixes_final.patch

**Critical Bug Fixes (3 files):**
- apps/proxy/live_proxy/redis_keys.py (global cooldown keys)
- apps/proxy/live_proxy/url_utils.py (channel playback cooldown)
- apps/proxy/live_proxy/input/manager.py (LAST RESORT safety)

---

## 🔍 Verification After Applying Patches

### Backend Verification

```bash
# 1. Check django-db-geventpool
docker exec dispatcharr python -c "import psycogreen.gevent; print('OK')"

# 2. Check profile tracking
docker-compose logs | grep "Loaded profile ID"

# 3. Check cooldown system
docker-compose logs | grep COOLDOWN

# 4. Check proxy support
docker exec dispatcharr python manage.py shell
>>> from apps.m3u.models import M3UAccount
>>> M3UAccount._meta.get_field('proxy')
>>> M3UAccount._meta.get_field('proxy_for_api')
```

### Frontend Verification

```bash
# Check static files rebuilt
docker exec dispatcharr ls /app/static/frontend/ | grep main

# Check UI in browser
# Navigate to Settings → Proxy Settings
# Verify "Stream Cooldown Enabled" checkbox exists
# Verify "Stream Cooldown Duration" number input exists
```

---

## ⚠️ Conflict Resolution

If patches conflict due to local modifications:

### Common Conflicts

**1. pyproject.toml**
- Conflict: You have additional dependencies
- Resolution: Manually add `django-db-geventpool>=4.0.8`

**2. manager.py __init__**
- Conflict: You have custom initialization
- Resolution: Add these lines to your __init__:
  ```python
  self.current_profile_id = None
  self.tried_combinations = set()
  ```

**3. url_utils.py get_alternate_streams()**
- Conflict: You modified stream selection logic
- Resolution: Ensure ALL profiles returned, no early break

**4. Frontend constants.js**
- Conflict: You have custom settings
- Resolution: Add cooldown settings to existing PROXY_SETTINGS_OPTIONS

---

## 📝 Post-Patch Checklist

After applying all patches:

- [ ] Docker build succeeds without errors
- [ ] Database migration 0022 applied
- [ ] Frontend rebuilt (npm run build)
- [ ] Services restart cleanly
- [ ] No errors in startup logs
- [ ] Profile failover works (test with multiple profiles)
- [ ] Cooldown UI visible in settings
- [ ] Cooldown logs appear when enabled
- [ ] HTTP proxy works when configured
- [ ] Buffer timeout triggers failover (not stop)

---

## 🆘 Rollback Procedure

If patches cause issues:

```bash
# 1. Restore from Git
git reset --hard HEAD  # Discard all changes
git checkout main      # Or your previous branch

# 2. Restore database
docker exec dispatcharr python manage.py flush --no-input
docker exec -i dispatcharr python manage.py loaddata < backup.json

# 3. Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 📚 Additional Resources

- **Complete Guide:** `DISPATCHARR_v0.27.0_COMPLETE_GUIDE.md` - Comprehensive documentation
- **Bug Analysis:** `BUG_ANALYSIS_v0.27.0.md` - Detailed bug descriptions
- **Fix Documentation:** `FIXES_COMPLETED_v0.27.0.md` - Technical fix details
- **Cooldown System:** `COOLDOWN_SYSTEM_v0.26.0.md` - Deep dive into cooldown logic
- **Ultimate Patch Guide:** `v0.27.0_ULTIMATE_PATCH_GUIDE.md` - Implementation details

---

## 🎯 Quick Start (TL;DR)

```bash
# Apply all patches
patch -p1 < dispatcharr_v0.26.0_COMPLETE_FIX.patch
patch -p1 < dispatcharr_v0.26.0_ULTIMATE.patch
patch -p1 < dispatcharr_v0.26.0_cooldown_system.patch
patch -p1 < dispatcharr_v0.27.0_bugfixes_final.patch

# Rebuild Docker
docker-compose build --no-cache

# Run migration
docker-compose up -d
docker exec dispatcharr python manage.py migrate m3u 0022

# Restart
docker-compose restart

# Verify
docker-compose logs | grep -E "COOLDOWN|profile|failover"
```

---

**Document Version:** 1.0  
**Last Updated:** June 18, 2026

*This document serves as a reference for applying all v0.27.0 patches. For detailed feature documentation, see DISPATCHARR_v0.27.0_COMPLETE_GUIDE.md*
