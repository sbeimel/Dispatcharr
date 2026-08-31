# Frontend UI Implementation Guide - HTTP Proxy Settings

**Date:** 2026-06-18  
**Component:** M3U Account Form  
**Status:** Implementation Guide

---

## Required Changes

### File: `frontend/src/components/forms/M3U.jsx` (or similar M3U form component)

Add the following two fields to the M3U Account form:

```jsx
import { TextInput, Switch } from '@mantine/core';

// Inside the form component, add these fields:

<TextInput
  label="HTTP Proxy URL"
  placeholder="http://proxy.example.com:8080"
  description="Optional HTTP proxy for streaming (supports http://, https://, socks5://)"
  {...form.getInputProps('proxy')}
/>

<Switch
  label="Use Proxy for API Calls"
  description="When enabled, proxy will be used for M3U download and XC API calls. When disabled, proxy is only used for streaming."
  disabled={!form.values.proxy || !form.values.proxy.trim()}
  {...form.getInputProps('proxy_for_api', { type: 'checkbox' })}
/>
```

---

## Form Schema Update

Make sure the form schema includes these fields:

```javascript
const formSchema = {
  // ... existing fields ...
  proxy: '',
  proxy_for_api: false,
};
```

---

## Serializer Verification

The backend serializer already includes these fields (completed in Step 1.3):

**File:** `apps/m3u/serializers.py`

```python
class M3UAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = M3UAccount
        fields = [
            # ... existing fields ...
            'proxy',
            'proxy_for_api',
        ]
```

---

## Field Behavior

1. **Proxy Field:**
   - Optional text input
   - Accepts URLs like: `http://proxy:8080`, `https://proxy:443`, `socks5://proxy:1080`
   - Can include credentials: `http://user:pass@proxy:8080`
   - Validation happens on backend (see Bug #3 fix in core/utils.py)

2. **Proxy for API Field:**
   - Boolean checkbox
   - Disabled when proxy field is empty
   - When **enabled**: Proxy used for M3U download + XC API calls + Streaming
   - When **disabled**: Proxy ONLY used for streaming (NOT for API calls)

---

## User Flow Example

### Scenario 1: Proxy for Streaming Only (Default)
```
User enters proxy: http://192.168.1.100:8080
User leaves "Use Proxy for API" unchecked
Result:
  - M3U download: Direct (NO proxy)
  - XC API calls: Direct (NO proxy)
  - Stream playback: Through proxy ✓
```

### Scenario 2: Proxy for Everything
```
User enters proxy: http://192.168.1.100:8080
User checks "Use Proxy for API"
Result:
  - M3U download: Through proxy ✓
  - XC API calls: Through proxy ✓
  - Stream playback: Through proxy ✓
```

### Scenario 3: No Proxy
```
User leaves proxy field empty
Result:
  - "Use Proxy for API" checkbox disabled
  - All connections direct (NO proxy)
```

---

## Error Handling

The backend validates proxy URLs and shows helpful errors:

1. **Invalid URL format:**
   ```
   "Proxy URL must use http://, https://, socks5://, or socks5h:// protocol"
   ```

2. **Missing hostname:**
   ```
   "Proxy URL must include hostname and optional port"
   ```

3. **Proxy connection errors:**
   ```
   "Proxy connection error: Check proxy configuration: http://proxy:8080"
   ```

4. **Proxy timeout:**
   ```
   "Connection timeout: Proxy may be slow or unreachable"
   ```

5. **Proxy auth required:**
   ```
   "Proxy authentication required (407)"
   ```

---

## Security Note

Proxy URLs with credentials (e.g., `http://user:pass@proxy:8080`) are automatically sanitized in logs:
- Logs show: `http://***:***@proxy:8080`
- Database stores full URL (needed for actual connections)
- See `core/utils.py::sanitize_proxy_url()` for implementation

---

## Testing Checklist

### Frontend
- [ ] Proxy field accepts valid URLs
- [ ] Proxy field shows validation errors for invalid URLs
- [ ] "Use Proxy for API" checkbox is disabled when proxy is empty
- [ ] "Use Proxy for API" checkbox is enabled when proxy is filled
- [ ] Form submits successfully with proxy configured
- [ ] Form submits successfully without proxy (empty field)

### Backend Integration
- [ ] Proxy saved to database
- [ ] proxy_for_api saved to database
- [ ] M3U download uses proxy when proxy_for_api=True
- [ ] M3U download bypasses proxy when proxy_for_api=False
- [ ] XC API calls use proxy when proxy_for_api=True
- [ ] Stream playback uses proxy (always when configured)
- [ ] FFmpeg transcode uses proxy (always when configured)

### Error Scenarios
- [ ] Invalid proxy URL shows validation error
- [ ] Unreachable proxy shows clear error message
- [ ] Proxy timeout shows clear error message
- [ ] Proxy auth failure (407) shows clear error message

---

## Implementation Priority

This is the **last step** of Phase 1. All backend code is complete:
- ✅ Database migrations
- ✅ Model fields & validation
- ✅ Proxy integration in streaming
- ✅ Proxy integration in XC Client
- ✅ Proxy integration in M3U download
- ⏳ Frontend UI (this guide)

The system is **fully functional** even without the frontend UI. The proxy fields can be set via:
- Django Admin interface
- API calls directly
- Database updates

---

## Next Steps

1. **Locate the M3U form component** in the frontend codebase
2. **Add the two fields** as shown above
3. **Test the form** submission
4. **Verify** the fields appear in the UI
5. **Test** with a real proxy to verify functionality

---

**Implementation Guide Complete**  
**Backend Status:** ✅ 100% Complete  
**Frontend Status:** ⏳ Pending Implementation (this guide provides all needed info)
