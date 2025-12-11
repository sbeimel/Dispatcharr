# Critical Fixes Applied - December 11, 2025

## Issues Fixed

### 1. **Stream URL Generation - localhost Issue (MAJOR FIX)**
**Problem**: MAC channels were generating URLs like `http://localhost/ch/599_` or `http://tvip.zeroonemac.xyz:8080/ch/599_` instead of the real stream URLs.

**Root Cause**: MAC/STB portals don't provide direct stream URLs in the channel list. The `cmd` field (e.g., `ffmpeg http://localhost/ch/599_`) is just a placeholder. You must call the `create_link` API for each channel to get the real stream URL.

**Fix Applied**:
- Modified `get_channels()` method to call `create_link()` API for each channel
- Added `resolve_urls` parameter (default True) to control URL resolution
- Now properly resolves each channel's `cmd` to a real stream URL via the portal's `create_link` API
- Falls back to URL extraction from `cmd` if resolution fails

**File**: `Dispatcharr-0.14.0/apps/m3u/mac_portal_client.py`

**Note**: This fix makes channel loading slower (one API call per channel) but provides working stream URLs.

### 2. **MAC Address Validation Regex**
**Problem**: The regex pattern for validating MAC addresses was incomplete (missing closing `$`), causing validation to fail.

**Root Cause**: Syntax error in the `is_valid_mac_format()` method - the regex pattern was truncated.

**Fix Applied**:
- Completed the regex pattern: `r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'`
- Now properly validates MAC address format

**File**: `Dispatcharr-0.14.0/apps/m3u/models.py`

### 3. **Channel URL Field Mapping**
**Problem**: MAC channels were using `cmd` field instead of `url` field when creating EXTINF data, resulting in raw commands instead of stream URLs.

**Root Cause**: The `_refresh_mac_account_with_groups()` function was mapping `channel.get('cmd')` to the `url` field in extinf_entry.

**Fix Applied**:
- Changed to use `channel.get('url')` which contains the properly extracted stream URL
- Added proper type conversion for channel ID to string

**File**: `Dispatcharr-0.14.0/apps/m3u/tasks.py`

### 4. **Logo URL Support**
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
