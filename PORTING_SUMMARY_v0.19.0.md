# Dispatcharr Enhancements v0.19.0 - Porting Summary

## Overview
This document summarizes the porting of ALL features from Dispatcharr v0.18.1 Enhanced to v0.19.0.

## Features Being Ported

### 1. Profile Failover System ✅
**Status**: Partially present in v0.19.0, needs enhancement
**Changes Required**:
- Enhance `get_alternate_streams()` to return ALL profiles for each stream
- Track `tried_combinations` (stream_id, profile_id) instead of just `tried_stream_ids`
- Add `get_stream_info_for_profile()` function to url_utils.py
- Update `_try_next_stream()` to iterate through all stream/profile combinations

### 2. Universal HTTP Proxy Support ✅
**Status**: NOT present in v0.19.0, needs to be added
**Changes Required**:
- Add `proxy` field to M3UAccount model (migration required)
- Update `build_command()` in StreamProfile to accept proxy parameter
- Add proxy support to FFmpeg profiles (via -http_proxy parameter)
- Add proxy support to Proxy profiles (via HTTPStreamReader)
- Update frontend M3U form to include proxy field
- Update serializers to include proxy field

### 3. Basic Authentication ✅
**Status**: NOT present in v0.19.0, needs to be added
**Changes Required**:
- Add `get_basic_auth_user()` function to apps/output/views.py
- Add `require_basic_auth()` function to apps/output/views.py
- Update `m3u_endpoint()` to check Basic Auth if no user provided
- Update `epg_endpoint()` to check Basic Auth if no user provided

### 4. Extended Timeout Configuration ✅
**Status**: Partially present, needs enhancement
**Changes Required**:
- Update BaseConfig.get_proxy_settings() to include all new settings
- Add getter methods for: max_retries, url_switch_timeout, max_stream_switches, connection_timeout
- Update ConfigHelper to use database values instead of hardcoded defaults
- Update frontend ProxySettingsForm to include all new fields
- Update frontend constants.js with new setting descriptions
- Set max_stream_switches default to 200 (user requested)

### 5. Ghost-Client Auto-Cleanup ✅
**Status**: Already present in v0.19.0
**No changes required** - v0.19.0 already has ghost client cleanup

## Key Differences Between v0.18.1 and v0.19.0

### Settings Architecture
- **v0.18.1**: Individual CharField for each setting
- **v0.19.0**: Grouped JSON settings (proxy_settings, stream_settings, etc.)
- **Impact**: Need to adapt all setting getters to use CoreSettings.get_proxy_settings()

### OpenAPI Migration
- **v0.18.1**: Uses drf-yasg
- **v0.19.0**: Uses drf-spectacular
- **Impact**: No changes needed for our enhancements

### New Fields in v0.19.0
- stream_id and stream_chno fields in Stream model
- **Impact**: No conflicts with our enhancements

## Files to Modify

### Backend Files
1. `apps/proxy/config.py` - Add new getter methods
2. `apps/m3u/models.py` - Add proxy field
3. `core/models.py` - Update build_command() to accept proxy
4. `apps/m3u/serializers.py` - Add proxy field
5. `apps/proxy/ts_proxy/stream_manager.py` - Add proxy support, enhance failover
6. `apps/proxy/ts_proxy/url_utils.py` - Add get_stream_info_for_profile(), enhance get_alternate_streams()
7. `apps/proxy/ts_proxy/http_streamer.py` - Add proxy parameter
8. `apps/proxy/ts_proxy/config_helper.py` - Update to use database values
9. `apps/output/views.py` - Add Basic Authentication
10. `dispatcharr/settings.py` - Add logo timeout settings

### Frontend Files
1. `frontend/src/components/forms/M3U.jsx` - Add proxy field
2. `frontend/src/components/forms/settings/ProxySettingsForm.jsx` - Add new settings
3. `frontend/src/constants.js` - Add new setting descriptions
4. `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js` - Add defaults

### Migration Files
1. `apps/m3u/migrations/0XXX_add_proxy_field.py` - Add proxy field to M3UAccount

## Implementation Priority

1. **High Priority** (Core functionality):
   - Profile Failover System
   - HTTP Proxy Support
   - Extended Configuration

2. **Medium Priority** (Security):
   - Basic Authentication

3. **Low Priority** (Already done):
   - Ghost-Client Cleanup (already in v0.19.0)

## Testing Checklist

- [ ] Profile Failover: Verify tried_combinations tracking
- [ ] HTTP Proxy: Test with FFmpeg profiles
- [ ] HTTP Proxy: Test with Proxy profiles
- [ ] Basic Auth: Test M3U endpoint without user parameter
- [ ] Basic Auth: Test EPG endpoint without user parameter
- [ ] Configuration: Verify all settings are saved to database
- [ ] Configuration: Verify all settings are loaded from database
- [ ] Max Stream Switches: Verify limit is 200

## Notes

- All features are designed to be backward compatible
- No breaking changes to existing functionality
- All new settings have sensible defaults
- Frontend changes are minimal and focused
