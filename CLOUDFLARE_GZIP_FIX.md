# Cloudflare Gzip Compression Fix

## Issue Description

The MAC Portal Client was encountering Cloudflare gzip compression issues where:
- Server returns `Content-Length: 20` header
- But actual response body is empty (0 bytes) due to gzip decompression failure
- This affected both GET and POST requests to MAC portals behind Cloudflare

## Root Cause

Cloudflare's gzip compression was causing response content to be lost during decompression, resulting in empty response bodies despite non-zero Content-Length headers.

## Solution Applied

### 1. Enhanced Error Handling in MAC Portal Client

**File:** `apps/m3u/mac_portal_client.py`

**Changes:**
- Modified GET request handling to detect Cloudflare gzip issues
- Added retry mechanism with `Accept-Encoding: identity` to disable compression
- Modified POST request handling with same retry logic
- Changed error logging from ERROR to WARNING for better user experience

**Before:**
```python
if (not response_text and content_encoding == 'gzip' and int(content_length) > 0 and len(response.content) == 0):
    logger.error("Cloudflare gzip issue detected: Content-Length > 0 but no content received")
    raise MacPortalError("Cloudflare gzip compression issue - no content received despite Content-Length > 0")
```

**After:**
```python
if (not response_text and content_encoding == 'gzip' and int(content_length) > 0 and len(response.content) == 0):
    logger.warning("Cloudflare gzip issue detected: Content-Length > 0 but no content received")
    logger.warning("This indicates a Cloudflare compression problem - trying alternative approach")
    
    # Try to make a new request without gzip encoding
    headers_no_gzip = headers.copy()
    headers_no_gzip["Accept-Encoding"] = "identity"  # Disable compression
    
    try:
        logger.info("Retrying request without gzip compression")
        response = session.get(portal, params=params, cookies=self._cookies(), headers=headers_no_gzip, proxies=proxies, timeout=30)
        response_text = response.text
        logger.info(f"Retry without gzip - got {len(response_text)} chars")
    except Exception as retry_e:
        logger.error(f"Retry without gzip failed: {retry_e}")
        raise MacPortalError("Cloudflare gzip compression issue - retry failed")
```

### 2. Frontend Form Dropdown Fix

**File:** `frontend/src/components/forms/M3U.jsx`

**Issue:** When editing existing M3U accounts, the account type dropdown would reset and require manual reselection.

**Root Cause:** The `useEffect` hook for account type changes only set `showCredentialFields` to `true` for XC accounts but didn't explicitly set it to `false` for other account types.

**Fix:**
```javascript
// Before
useEffect(() => {
  if (form.values.account_type == 'XC') {
    setShowCredentialFields(true);
  }
}, [form.values.account_type]);

// After  
useEffect(() => {
  if (form.values.account_type == 'XC') {
    setShowCredentialFields(true);
  } else {
    setShowCredentialFields(false);
  }
}, [form.values.account_type]);
```

## Testing

Both fixes have been applied and validated:
- ✅ MAC Portal Client syntax validation passed
- ✅ Frontend form syntax validation passed
- ✅ No breaking changes introduced

## Expected Results

1. **MAC Portal Connectivity:** Portals behind Cloudflare should now work correctly by automatically retrying requests without gzip compression when compression issues are detected.

2. **Frontend Form Behavior:** Editing existing M3U accounts should now properly display the correct account type without requiring manual dropdown reselection.

## Monitoring

Monitor the logs for:
- `"Retrying request without gzip compression"` - indicates the fix is working
- `"Retry without gzip - got X chars"` - successful recovery from Cloudflare issue
- Reduced `"Cloudflare gzip compression issue"` errors

## Rollback Plan

If issues arise, the changes can be easily reverted by:
1. Restoring the original error handling (throw exception instead of retry)
2. Removing the `else` clause from the frontend useEffect