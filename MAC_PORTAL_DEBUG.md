# MAC Portal Debugging Guide

## Current Status - MAJOR DISCOVERY! 🔍

**PROBLEM IDENTIFIED**: The portal `dlta4k.com` is returning **EMPTY RESPONSES** with status 200!

### Latest Log Analysis (2025-12-22 11:04)

✅ **Working:**
- Handshake succeeds and gets token
- Cloudscraper active ("Created cloudscraper session for Cloudflare bypass")
- Status 200 responses
- Correct Content-Type: `text/javascript;charset=UTF-8`
- Cloudflare headers present

❌ **Problem:**
- `Response content (first 1000 chars):` shows **NOTHING**
- Empty response body causes JSON parsing to fail
- Alternative endpoints return 403/404 errors

### Root Cause Analysis

The portal is likely:
1. **Session State Dependent**: Requires cookies/session from handshake to be maintained
2. **CSRF Protected**: Needs specific tokens or headers after handshake
3. **Timing Sensitive**: May require delays between requests
4. **Cookie Dependent**: Handshake may set cookies that must be used in subsequent requests

### Recent Fixes Applied

1. **Session Persistence**: Now uses the SAME session for handshake and subsequent requests
2. **Cookie Management**: Stores and reuses cookies from handshake response
3. **Request Timing**: Added 0.1s delay after handshake
4. **Enhanced Debugging**: Added cookie logging to see what's being sent
5. **Fixed Alternative Endpoints**: Removed double-path issue in alternatives

### Next Test Results Will Show

The enhanced implementation will now log:
- Cookies being sent with each request
- Session cookies stored from handshake
- Whether the portal sets any cookies during handshake
- If the timing delay helps

## Implementation Status

✅ **Already Implemented from MacReplayXC-main:**
- Cloudscraper for Cloudflare bypass (working - logs show "Created cloudscraper session")
- Multiple proxy types (HTTP, SOCKS, Shadowsocks)
- Enhanced cookies with device IDs
- Alternative endpoint fallbacks
- MAG250/254/420 model headers
- Session management

✅ **New Fixes Applied:**
- Session persistence between handshake and API calls
- Cookie storage and reuse from handshake
- Request timing delays
- Enhanced debugging with cookie logging
- Fixed alternative endpoint URLs

## Expected Behavior After Fixes

If the issue was session/cookie related, you should now see:
1. Cookies being stored from handshake
2. Same cookies being sent with subsequent requests
3. Non-empty responses from the portal
4. Successful JSON parsing

If the portal still returns empty responses, it may require:
- Specific User-Agent strings
- Additional headers or authentication
- Different request timing
- Portal-specific session handling

## Manual Testing Command

Test the exact same flow manually:
```bash
# 1. Handshake (save cookies)
curl -c cookies.txt -H "User-Agent: Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3" \
     -H "X-User-Agent: Model: MAG250; Link: WiFi; MAC: 00:1A:79:A3:B8:A4" \
     -H "Authorization: Bearer undefined" \
     --cookie "mac=00:1A:79:A3:B8:A4;stb_lang=en;timezone=Europe/Berlin" \
     "http://dlta4k.com/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"

# 2. Get expiry (use saved cookies + token from step 1)
curl -b cookies.txt -H "User-Agent: Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3" \
     -H "X-User-Agent: Model: MAG250; Link: WiFi; MAC: 00:1A:79:A3:B8:A4" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     --cookie "mac=00:1A:79:A3:B8:A4;stb_lang=en;timezone=Europe/Berlin" \
     "http://dlta4k.com/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
```
