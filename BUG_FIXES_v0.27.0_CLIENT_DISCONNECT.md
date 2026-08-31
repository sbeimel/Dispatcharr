# Bug Fixes v0.27.0 - Client Disconnect Issue

## Date: 2026-06-18

## Problem Description

Users reported immediate client disconnects with "Broken pipe" errors after buffer initialization completed successfully. Logs showed:

```
14:07:25 WARNING Method Not Allowed: /proxy/ts/stream/...
14:07:25 INFO Worker ID: 2 HEAD 405
uwsgi_response_write_body_do(): Broken pipe
OSError: write error
Client disconnected after 0.12s
```

### Root Causes Identified

1. **HTTP 302 Redirect Not Followed**
   - IPTV provider returns HTTP 302 redirect
   - HTTP streamer wasn't explicitly following redirects
   - Example: `http://iptv.watchhd.to:5050/...` → `http://89.36.95.53:80/auth/...`

2. **HEAD Request Returns 405 Method Not Allowed**
   - Media players (Jellyfin, Plex, etc.) send HEAD request before streaming
   - Django views only accepted GET requests
   - Client receives 405 error and disconnects

---

## Fixes Applied

### Fix 1: HTTP Redirect Support

**File:** `apps/proxy/live_proxy/input/http_streamer.py`

**Changes:**
- Added `allow_redirects=True` to `session.get()` call (line 87)
- Added redirect chain logging to track redirect URLs
- Added final URL logging to show actual streaming URL after redirects

**Code:**
```python
self.response = self.session.get(
    self.url,
    headers=headers,
    stream=True,
    timeout=(5, 30),  # 5s connect, 30s read
    proxies=proxies,
    allow_redirects=True,  # Follow HTTP redirects (302, 301, etc.)
)

# Log if URL was redirected
if self.response.history:
    redirect_chain = ' -> '.join([resp.url for resp in self.response.history])
    logger.info(f"HTTP reader followed redirects: {redirect_chain} -> {self.response.url}")
```

**Expected Result:** Stream will now follow 302 redirects correctly

---

### Fix 2: HEAD Request Support (Live Proxy)

**File:** `apps/proxy/live_proxy/views.py`

**Changes:**
1. Modified `stream_ts` function (line 97)
   - Changed `@api_view(["GET"])` to `@api_view(["GET", "HEAD"])`
   - Added HEAD request handler that returns 200 OK without initializing stream

2. Modified `stream_xc` function (line 663)
   - Changed `@api_view(["GET"])` to `@api_view(["GET", "HEAD"])`

**Code:**
```python
@api_view(["GET", "HEAD"])
@permission_classes([AllowAny])
def stream_ts(request, channel_id, user=None, force_output_format=None):
    if not network_access_allowed(request, "STREAMS"):
        return JsonResponse({"error": "Forbidden"}, status=403)
    
    # Handle HEAD requests - just return success without initializing stream
    if request.method == "HEAD":
        response = HttpResponse(status=200)
        response["Cache-Control"] = "no-cache"
        response["Content-Type"] = "video/mp2t"
        return response
    
    # ... rest of GET request handling ...
```

**Expected Result:** Media players will receive 200 OK on HEAD requests and proceed with GET request

---

### Fix 3: HEAD Request Support (VOD Proxy)

**File:** `apps/proxy/vod_proxy/views.py`

**Changes:**
1. Modified `stream_xc_movie` function (line 1141)
   - Changed `@api_view(["GET"])` to `@api_view(["GET", "HEAD"])`
   - Added HEAD request handler

2. Modified `stream_xc_episode` function (line 1178)
   - Changed `@api_view(["GET"])` to `@api_view(["GET", "HEAD"])`
   - Added HEAD request handler

**Code:**
```python
@api_view(["GET", "HEAD"])
@permission_classes([AllowAny])
def stream_xc_movie(request, username, password, stream_id, extension):
    if not network_access_allowed(request, "STREAMS"):
        return JsonResponse({"error": "Forbidden"}, status=403)
    
    # Handle HEAD requests
    if request.method == "HEAD":
        response = HttpResponse(status=200)
        response["Cache-Control"] = "no-cache"
        response["Content-Type"] = "video/mp4" if extension.lower() == ".mp4" else "video/mp2t"
        return response
    
    # ... rest of GET request handling ...
```

**Expected Result:** VOD streams will also respond correctly to HEAD requests

---

## Testing Instructions

### 1. Test HTTP 302 Redirect

```bash
# Test with curl - should follow redirect
curl -v "http://iptv.watchhd.to:5050/live/watchgrisu/uBMGG0XQ1hFw/136095.ts"

# Expected: See redirect chain in logs
# HTTP reader followed redirects: http://iptv.watchhd.to:5050/... -> http://89.36.95.53:80/auth/...
```

### 2. Test HEAD Request Support

```bash
# Test HEAD request to Dispatcharr
curl -I "http://localhost:8000/proxy/ts/stream/{channel_uuid}"

# Expected: HTTP 200 OK
# Content-Type: video/mp2t
# Cache-Control: no-cache
```

### 3. Test Full Streaming Flow

1. Start Dispatcharr
2. Play a channel in Jellyfin/Plex
3. Check logs for:
   - No "405 Method Not Allowed" errors
   - Stream connects and stays connected
   - Buffer fills and clients receive data
   - No "Broken pipe" errors

### 4. Monitor Logs

Look for these log messages:
```
✅ HTTP reader followed redirects: ... -> ...
✅ HTTP reader connected successfully to ..., streaming data...
✅ Client registered with channel ...
✅ [client_id] Stream started successfully
```

Look for absence of these errors:
```
❌ WARNING Method Not Allowed: /proxy/ts/stream/...
❌ uwsgi_response_write_body_do(): Broken pipe
❌ Client disconnected after 0.12s
```

---

## Additional Recommendations

### 1. Increase Buffer Timeout

Current timeout of 5 seconds is too aggressive for slow connections.

**Recommendation:** Increase to 25-30 seconds

**How to apply:**
1. Open Dispatcharr WebUI
2. Go to Settings → Proxy Settings
3. Change "Channel Initialization Grace Period" to 30 seconds
4. Save settings

### 2. Monitor Channel States

Use the WebUI to monitor channel states:
- `INITIALIZING` → `BUFFERING` → `WAITING_FOR_CLIENTS` → `ACTIVE` (✅ Good)
- Rapid transitions or stuck in `ERROR` (❌ Bad)

### 3. Check Stream Validation

If streams still fail, check stream validation in logs:
```
✅ Redirecting to validated URL: ... (HTTP 200 OK, Content-Type: video/mp2ts)
❌ All available redirect URLs failed validation
```

---

## Files Modified

1. `apps/proxy/live_proxy/input/http_streamer.py` - Added redirect support
2. `apps/proxy/live_proxy/views.py` - Added HEAD request support for live streams
3. `apps/proxy/vod_proxy/views.py` - Added HEAD request support for VOD streams

---

## Related Issues

- Buffer Timeout Failover (v0.26.0) - Fixed by increasing grace period
- HTTP 302 Redirect Issue (v0.27.0) - Fixed by `allow_redirects=True`
- HEAD Request 405 Error (v0.27.0) - Fixed by accepting HEAD requests

---

## Version

Applied to: **v0.27.0**

Status: ✅ **FIXED**

Last Updated: 2026-06-18
