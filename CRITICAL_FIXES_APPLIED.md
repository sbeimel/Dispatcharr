# Critical Fixes Applied - December 11, 2025

## Issues Fixed

### 0. **MAC Failover Fix (LATEST FIX)**
**Problem**: MAC failover wasn't working - when one MAC failed, it didn't switch to another MAC.

**Root Cause**: The failover implementation was too simple compared to the original patch. Missing:
1. Proper candidate MAC selection (excluding EXPIRED/ERROR MACs)
2. MAC busy tracking via Redis
3. Multi-proxy support per MAC
4. Proper MAC status management (VALID/ERROR/EXPIRED)
5. Integration with the original patch's `_resolve_mac_stream_with_failover` logic

**Fix Applied**:
- Implemented proper MAC failover logic based on the original patch
- Added `_get_candidate_macs_for_streaming()` to filter valid MACs
- Added multi-proxy support per MAC address
- Proper MAC status management (VALID/ERROR/EXPIRED)
- MAC busy tracking via Redis to prevent conflicts
- Automatic profile creation for MAC accounts
- Proper error handling and cooldown management

**Files Modified**:
- `Dispatcharr-0.14.0/apps/m3u/mac_portal_client.py` - Added `resolve_mac_url_with_failover_mac()` method
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/failover_utils.py` - Complete rewrite of MAC failover logic based on original patch

### 1. **MAC Object Creation Fix**
**Problem**: MAC objects weren't being created when all existing MACs had ERROR status.

**Root Cause**: The code checked `if account.mac_address and not account.macs.exists()` but if MAC objects existed with ERROR status, `macs.exists()` returned True, so `_process_mac_addresses()` was never called. Then the filter for VALID/UNKNOWN returned nothing.

**Fix Applied**:
- Changed logic to also process MAC addresses if all existing MACs have ERROR status
- Added reset of ERROR status MACs to UNKNOWN so they can be retried
- Added detailed logging to `_process_mac_addresses()` method
- Fixed both `_refresh_mac_account_with_groups()` and `_refresh_mac_account_direct()` functions

**Files Modified**:
- `Dispatcharr-0.14.0/apps/m3u/models.py` - Added detailed logging to `_process_mac_addresses()`
- `Dispatcharr-0.14.0/apps/m3u/tasks.py` - Fixed MAC processing logic in both refresh functions

### 2. **Stream URL Generation - On-Demand Resolution (MAJOR FIX)**
**Problem**: MAC channels were generating URLs like `http://localhost/ch/599_` instead of the real stream URLs.

**Root Cause**: MAC/STB portals don't provide direct stream URLs in the channel list. The `cmd` field is just a placeholder. You must call the `create_link` API to get the real stream URL.

**Fix Applied**:
- Channels are now stored with special `mac://` URLs that encode portal info, MAC address, cmd, and proxy
- URLs are resolved on-demand when the stream is actually played (not during import)
- `transform_url()` in `url_utils.py` detects `mac://` URLs and resolves them via `create_link` API
- This makes import fast while still providing working stream URLs at playback time

**Files Modified**:
- `Dispatcharr-0.14.0/apps/m3u/mac_portal_client.py` - Added `resolve_mac_url()` static method
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/url_utils.py` - Added MAC URL detection in `transform_url()`

### 3. **Failover UUID Issue (MAJOR FIX)**
**Problem**: Failover was failing with error `"e6a977516830147ace4c798f5461b5b75ad6bdabf7a35bc1110c758147de9d2e" is not a valid UUID`

**Root Cause**: The system sometimes uses stream_hash instead of UUID for channel identification. The failover code only handled UUIDs.

**Fix Applied**:
- Added `get_channel_by_id()` helper function in `utils.py` that handles both UUID and stream_hash
- Updated `failover_utils.py` to use the new helper function
- Updated `url_utils.py` and `stream_manager.py` to use the new helper function
- Now failover works correctly regardless of whether channel_id is a UUID or stream_hash

**Files Modified**:
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/utils.py` - Added `get_channel_by_id()` helper
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/failover_utils.py` - Fixed channel lookup
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/url_utils.py` - Fixed channel lookup
- `Dispatcharr-0.14.0/apps/proxy/ts_proxy/stream_manager.py` - Fixed channel lookup

### 4. **MAC Address Validation Regex**
**Problem**: The regex pattern for validating MAC addresses was incomplete (missing closing `$`), causing validation to fail.

**Root Cause**: Syntax error in the `is_valid_mac_format()` method - the regex pattern was truncated.

**Fix Applied**:
- Completed the regex pattern: `r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'`
- Now properly validates MAC address format

**File**: `Dispatcharr-0.14.0/apps/m3u/models.py`

### 5. **Channel URL Field Mapping**
**Problem**: MAC channels were using `cmd` field instead of `url` field when creating EXTINF data, resulting in raw commands instead of stream URLs.

**Root Cause**: The `_refresh_mac_account_with_groups()` function was mapping `channel.get('cmd')` to the `url` field in extinf_entry.

**Fix Applied**:
- Changed to use `channel.get('url')` which contains the properly extracted stream URL
- Added proper type conversion for channel ID to string

**File**: `Dispatcharr-0.14.0/apps/m3u/tasks.py`

### 6. **Logo URL Support**
**Problem**: Channel logos were not being extracted from MAC portal data.

**Fix Applied**:
- Added logo extraction in `get_channels()` method
- Checks both `logo` and `logo_url` fields from portal data
- Includes logo in normalized channel data

**File**: `Dispatcharr-0.14.0/apps/m3u/mac_portal_client.py`

## Testing Instructions

1. **Restart Docker Container**:
   ```bash
   docker-compose restart web
   ```

2. **Test MAC Account**:
   - Go to M3U Accounts
   - Create or edit a MAC account
   - Enter MAC addresses (space or comma separated)
   - Enter proxy if needed
   - Save the account

3. **Verify MAC Processing**:
   - Click "Refresh" button on the account
   - Check that MAC objects are created (visible in Actions > MAC Status)
   - Verify all MACs are checked (not just the first one)

4. **Verify Groups and Channels**:
   - After refresh, groups should appear
   - Activate desired groups
   - Verify channels are imported with correct stream URLs
   - URLs should use the portal domain, not localhost

5. **Test Streaming**:
   - Try playing a channel
   - Verify the stream URL is correct (not localhost)
   - Check that failover works if multiple MACs are configured

## Expected Behavior

- ✅ MAC addresses are properly validated and normalized
- ✅ MAC objects are created automatically when account is saved
- ✅ All MAC addresses are checked for status (not just first one)
- ✅ Stream URLs use the actual portal URL (e.g., `http://tvip.zeroonemac.xyz:8080/ch/599_`)
- ✅ Groups are extracted and can be activated
- ✅ Channels are imported with correct URLs
- ✅ Proxy settings are saved and used
- ✅ Channel logos are extracted when available

## Files Modified

1. `Dispatcharr-0.14.0/apps/m3u/mac_portal_client.py`
   - Fixed `_extract_stream_url()` method to use correct base URL
   - Added logo extraction in `get_channels()` method

2. `Dispatcharr-0.14.0/apps/m3u/models.py`
   - Fixed regex pattern in `is_valid_mac_format()` method

3. `Dispatcharr-0.14.0/apps/m3u/tasks.py`
   - Fixed channel URL mapping in `_refresh_mac_account_with_groups()` function

## No Fix Scripts Created

As requested, all fixes were applied directly to the source files. No separate fix scripts were created.
