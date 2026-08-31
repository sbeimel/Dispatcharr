# Feature Analysis: Bugs and Logic Errors

**Analysis Date:** 2026-06-18  
**Project:** Dispatcharr v0.26.0-v0.27.1 Implementation  
**Status:** 🔴 CRITICAL BUGS FOUND

## Executive Summary

Comprehensive analysis of all implemented features revealed **5 critical bugs** and **multiple logic inconsistencies** across the HTTP Proxy, Cooldown, and Failover systems.

**Critical Findings:**
- ✅ HTTP Proxy **partially implemented** but has 5 critical bugs
- ⚠️ Cooldown System has **logic inconsistencies** 
- ✅ Failover Rotation **correctly implemented**
- ⚠️ Missing **error handling** in multiple paths

---

## 🔴 CRITICAL BUG #1: Transcode Streams Never Use Proxy

**Severity:** HIGH  
**Impact:** FFmpeg transcoding bypasses proxy configuration completely

### Problem
`StreamProfile.build_command()` accepts a `proxy` parameter (line 127 in `core/models.py`):

```python
def build_command(self, stream_url, user_agent, proxy=None):
```

But `_establish_transcode_connection()` NEVER passes the proxy parameter (line 707 in `apps/proxy/live_proxy/input/manager.py`):

```python
self.transcode_cmd = stream_profile.build_command(self.url, self.user_agent)
# Missing third parameter - proxy is always None!
```

### Evidence
- HTTP streaming correctly retrieves proxy (lines 1194-1205 in manager.py)
- Transcode path has NO proxy retrieval code
- build_command() defaults proxy to None when not provided

### Fix Required
```python
# Add proxy retrieval in _establish_transcode_connection()
proxy = None
try:
    if hasattr(self, 'current_stream_id') and self.current_stream_id:
        from apps.channels.models import Stream
        stream = Stream.objects.get(id=self.current_stream_id)
        if hasattr(stream, 'm3u_account') and stream.m3u_account:
            proxy = stream.m3u_account.get_proxy_for_streaming()
except Exception as e:
    logger.debug(f"Could not get proxy for transcode: {e}")

# Pass proxy to build_command
self.transcode_cmd = stream_profile.build_command(self.url, self.user_agent, proxy)
```

---

## 🔴 CRITICAL BUG #2: M3U Download Ignores Proxy

**Severity:** HIGH  
**Impact:** M3U playlist downloads bypass proxy even when `proxy_for_api=True`

### Problem
In `fetch_m3u_lines()` (line 72 in `apps/m3u/tasks.py`):

```python
response = requests.get(
    account.server_url, headers=headers, stream=True,
    timeout=(30, 60),
)
# NO proxy parameter!
```

### Evidence
- All XC API calls correctly use `proxy=account.get_proxy_for_api()` (10 locations)
- M3U download is an API call but doesn't use proxy
- Inconsistent with user expectations when enabling `proxy_for_api`

### Fix Required
```python
# Build proxies dict if proxy_for_api is enabled
proxies = None
proxy_url = account.get_proxy_for_api()
if proxy_url:
    proxies = {'http': proxy_url, 'https': proxy_url}
    logger.info(f"Using proxy for M3U download: {proxy_url}")

response = requests.get(
    account.server_url, 
    headers=headers, 
    stream=True,
    timeout=(30, 60),
    proxies=proxies,  # Add proxies parameter
)
```

---

## 🔴 CRITICAL BUG #3: No Proxy URL Validation

**Severity:** MEDIUM  
**Impact:** Invalid proxy URLs cause cryptic errors, hard to debug

### Problem
`M3UAccount.proxy` field (line 106 in `apps/m3u/models.py`):

```python
proxy = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    help_text="HTTP proxy URL for streaming (e.g., http://proxy.example.com:8080)",
)
```

- **No validators** on the field
- `clean()` method (line 134) only validates `max_streams`
- Accepts ANY string: "not-a-url", "file:///etc/passwd", "javascript:alert(1)"

### Evidence
```python
def clean(self):
    if self.max_streams < 0:
        raise ValidationError("Max streams cannot be negative.")
    # NO proxy validation!
```

### Fix Required
```python
from django.core.exceptions import ValidationError
from urllib.parse import urlparse

def clean(self):
    if self.max_streams < 0:
        raise ValidationError("Max streams cannot be negative.")
    
    # Validate proxy URL format
    if self.proxy and self.proxy.strip():
        proxy_url = self.proxy.strip()
        try:
            parsed = urlparse(proxy_url)
            if parsed.scheme not in ('http', 'https', 'socks5'):
                raise ValidationError(
                    f"Proxy URL must use http://, https://, or socks5:// protocol, got: {parsed.scheme}"
                )
            if not parsed.netloc:
                raise ValidationError(
                    "Proxy URL must include host and port (e.g., http://proxy.example.com:8080)"
                )
        except Exception as e:
            raise ValidationError(f"Invalid proxy URL format: {e}")
```

---

## 🔴 CRITICAL BUG #4: Proxy Credentials Logged in Plaintext

**Severity:** HIGH (Security)  
**Impact:** Passwords exposed in logs

### Problem
Multiple locations log proxy URLs without sanitization:

**apps/m3u/models.py (line 123):**
```python
logger.info(f"M3UAccount {self.id} ({self.name}): Using proxy for API calls: {self.proxy}")
# If proxy = "http://user:password@proxy:8080", password is logged!
```

**core/xtream_codes.py (line 37):**
```python
logger.info(f"Using proxy: {proxy}")
# Same issue
```

**apps/proxy/live_proxy/input/http_streamer.py (line 62):**
```python
logger.info(f"HTTP reader using proxy: {self.proxy}")
# Same issue
```

### Fix Required
```python
def _sanitize_proxy_url(proxy_url):
    """Remove credentials from proxy URL for logging"""
    if not proxy_url:
        return proxy_url
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(proxy_url)
        # Replace username:password with ***
        if parsed.username or parsed.password:
            netloc = f"{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            sanitized = parsed._replace(netloc=netloc)
            return urlunparse(sanitized)
    except:
        return "[invalid proxy URL]"
    return proxy_url

# Usage:
logger.info(f"Using proxy: {_sanitize_proxy_url(self.proxy)}")
```

---

## 🔴 CRITICAL BUG #5: No Proxy-Specific Error Messages

**Severity:** MEDIUM  
**Impact:** Users cannot diagnose proxy misconfigurations

### Problem
All proxy-related requests catch generic `RequestException`:

**core/xtream_codes.py (lines 76-80):**
```python
try:
    response = self.session.get(url, timeout=60)
    response.raise_for_status()
    return response.json()
except requests.RequestException as e:
    logger.error(f"Error making request to {url}: {e}")
    return {}
```

**Can't distinguish between:**
- Proxy connection failure (proxy:8080 unreachable)
- Proxy authentication failure (wrong credentials)
- Source server unreachable (through proxy)
- Timeout (proxy or source)

### Fix Required
```python
try:
    response = self.session.get(url, timeout=60)
    response.raise_for_status()
    return response.json()
except requests.exceptions.ProxyError as e:
    logger.error(f"Proxy connection error for {url}: {e}")
    if self.proxy:
        logger.error(f"Check proxy configuration: {_sanitize_proxy_url(self.proxy)}")
    return {}
except requests.exceptions.ConnectTimeout as e:
    logger.error(f"Connection timeout for {url}: {e}")
    if self.proxy:
        logger.error(f"Proxy may be slow or unreachable: {_sanitize_proxy_url(self.proxy)}")
    return {}
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 407:
        logger.error(f"Proxy authentication required (407) for {url}")
    else:
        logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
    return {}
except requests.RequestException as e:
    logger.error(f"Error making request to {url}: {e}")
    return {}
```

---

## ⚠️ LOGIC ISSUE #6: Cooldown System Inconsistencies

**Severity:** LOW  
**Impact:** Confusing behavior when cooldown expires during failover

### Problem
Stream cooldown logic in `_select_next_failover()` (manager.py):

```python
# Check if stream is in cooldown
if stream_cooldown_enabled and redis_client:
    cooldown_key = redis_keys.stream_cooldown(stream_profile_combo)
    if redis_client.exists(cooldown_key):
        ttl = redis_client.ttl(cooldown_key)
        logger.info(f"Skipping stream {stream.id} - in cooldown for {ttl}s more")
        continue
```

**Issue:** If cooldown expires BETWEEN the `exists()` check and attempting connection, the stream will be tried again immediately (expected) but may fail again and re-enter cooldown (creates rapid retry loop).

**Not a bug** but could benefit from atomic check-and-extend operation.

### Suggested Improvement
```python
# Use Redis pipeline for atomic check-and-extend
if stream_cooldown_enabled and redis_client:
    cooldown_key = redis_keys.stream_cooldown(stream_profile_combo)
    pipe = redis_client.pipeline()
    pipe.exists(cooldown_key)
    pipe.ttl(cooldown_key)
    exists, ttl = pipe.execute()
    
    if exists:
        logger.info(f"Skipping stream {stream.id} - in cooldown for {ttl}s more")
        continue
```

---

## ⚠️ LOGIC ISSUE #7: HTTPStreamReader Race Condition

**Severity:** LOW  
**Impact:** Harmless AttributeError during shutdown

### Problem
In `http_streamer.py` `_read_stream()` method:

```python
except AttributeError as e:
    # Attribute error - could be race condition during shutdown (response becomes None)
    if self.running:
        logger.error(f"HTTP reader AttributeError (unexpected): {e}")
        self.error_occurred = True
    else:
        # Expected during shutdown - response might be None
        logger.debug(f"HTTP reader AttributeError during shutdown (expected): {e}")
```

**Issue:** `self.response` can become None during shutdown while thread is still iterating chunks. This is caught but indicates potential race condition.

**Not critical** - properly handled with try/except and self.running check.

### Suggested Improvement
```python
# Check self.running more frequently during iteration
for chunk in self.response.iter_content(chunk_size=self.chunk_size):
    if not self.running or not self.response:  # Add self.response check
        break
    # ...
```

---

## ✅ CORRECTLY IMPLEMENTED FEATURES

### 1. Failover Rotation Wrapping
**Status:** ✅ Fully functional  
**Location:** `apps/proxy/live_proxy/input/manager.py` lines 2057-2103

- Tracks rotation passes with `_failover_rotation_passes`
- Implements 60s cooldown after exhaustion
- Resets state on manual stream change
- Correctly wraps around failover list

### 2. XC Client Proxy Integration
**Status:** ✅ Correctly implemented for API calls  
**Locations:** 10 instantiations across vod/tasks.py, m3u/tasks.py

- All XC API calls use `proxy=account.get_proxy_for_api()`
- Session-level proxy configuration
- Consistent implementation

### 3. HTTP Streaming Proxy
**Status:** ✅ Correctly implemented  
**Location:** `apps/proxy/live_proxy/input/http_streamer.py`

- Proxy passed to requests.Session
- Error tracking with `error_occurred` flag
- Thread-safe shutdown handling

### 4. FFmpeg Auto-Proxy Injection
**Status:** ✅ Correctly implemented  
**Location:** `core/models.py` StreamProfile.build_command()

- Automatically inserts `-http_proxy` for FFmpeg
- Handles both `{proxy}` placeholder and auto-injection
- Falls back gracefully if no `-i` flag

---

## SUMMARY STATISTICS

| Category | Count | Status |
|----------|-------|--------|
| **Critical Bugs** | 5 | 🔴 MUST FIX |
| **Logic Issues** | 2 | ⚠️ SHOULD FIX |
| **Correctly Implemented** | 4 | ✅ VERIFIED |
| **Missing Validations** | 3 | ⚠️ SHOULD ADD |
| **Security Issues** | 1 | 🔴 MUST FIX |

---

## PRIORITY RECOMMENDATIONS

### Immediate (Before v0.30.0 Port)
1. **Fix Bug #1**: Add proxy parameter to transcode path
2. **Fix Bug #2**: Add proxy to M3U download
3. **Fix Bug #4**: Sanitize proxy URLs in logs (security)

### High Priority (During v0.30.0 Port)
4. **Fix Bug #3**: Add proxy URL validation
5. **Fix Bug #5**: Add proxy-specific error handling

### Nice to Have (Post-Port)
6. **Improve Logic #6**: Atomic cooldown check-and-extend
7. **Improve Logic #7**: More frequent self.running checks

---

## TESTING RECOMMENDATIONS

### Test Cases Needed
1. ✅ **Transcode with proxy** - verify FFmpeg uses -http_proxy
2. ✅ **M3U download with proxy_for_api=True** - verify proxy used
3. ✅ **Invalid proxy URL** - should show validation error
4. ✅ **Proxy with credentials** - verify not logged in plaintext
5. ✅ **Proxy connection failure** - verify clear error message
6. ✅ **Proxy timeout** - verify timeout detection
7. ✅ **HTTP streaming with proxy** - verify works (already working)
8. ✅ **XC API calls with proxy** - verify works (already working)

### Edge Cases to Test
- Proxy URL with authentication: `http://user:pass@proxy:8080`
- SOCKS5 proxy: `socks5://proxy:1080`
- Proxy with non-standard port: `http://proxy:3128`
- Invalid proxy URL: `not-a-url`, `file:///etc/passwd`
- Unreachable proxy: `http://10.255.255.1:9999`
- Proxy that times out after connection
- Proxy that returns 407 Proxy Authentication Required

---

## NEXT STEPS

1. **Review this analysis** with team
2. **Decide priority** - fix bugs now or during v0.30.0 port?
3. **Create patches** for each critical bug
4. **Test patches** with comprehensive test suite
5. **Port to v0.30.0** with all fixes included
6. **Document** proxy configuration in user guide

---

**Analysis completed:** 2026-06-18  
**Analyzed by:** Kiro AI Multi-Agent System  
**Files analyzed:** 12 core files across HTTP proxy implementation  
**Total issues found:** 7 (5 critical bugs + 2 logic issues)
