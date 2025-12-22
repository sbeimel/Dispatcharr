# MAC Portal Debugging Guide

## Current Status

The Dispatcharr MAC portal client has been enhanced with improvements from MacReplayXC-main, including:

1. **Cloudscraper Integration** ✅
   - Cloudflare bypass support via cloudscraper library
   - Automatic session management with periodic refresh
   - Installed in Docker container via requirements.txt

2. **Enhanced Error Handling** ✅
   - Alternative endpoint fallbacks for all API calls
   - Proper JSON parsing error handling
   - Detailed logging of response content and headers

3. **Multiple Device Model Support** ✅
   - MAG250, MAG254, MAG420 header fallbacks
   - Enhanced cookies with device IDs
   - Automatic retry with different models on 403 errors

4. **Proxy Support** ✅
   - HTTP, HTTPS, SOCKS4/5 proxy support
   - Shadowsocks proxy support (via parse_proxy_url)
   - Proxy configuration per account

## Known Issue: dlta4k.com Portal

### Problem
The portal `http://dlta4k.com/portal.php` returns HTML instead of JSON for expiry and channel requests, despite:
- Handshake succeeding
- Cloudscraper being active
- Proxy being used
- Alternative endpoints being tried

### Logs Show
```
2025-12-22 10:31:27,064 ERROR apps.m3u.mac_portal_client Error getting expiry for MAC 00:1A:79:A3:B8:A4: Expecting value: line 1 column 1 (char 0)
2025-12-22 10:31:27,265 ERROR apps.m3u.mac_portal_client Error getting channels for MAC 00:1A:79:A3:B8:A4: Expecting value: line 1 column 1 (char 0)
```

### Recent Improvements
1. **Enhanced Logging**: Now logs full response content, headers, and detects HTML responses
2. **Better Alternative Endpoint Handling**: Properly catches JSON errors in alternative endpoints
3. **Cloudflare Detection**: Detects if Cloudflare or access denied messages are in response

### Next Steps for Debugging

When you run the refresh again, the logs will now show:
- Full response content (first 1000 chars)
- Response headers
- Whether the response is HTML
- Whether Cloudflare protection is detected
- Whether alternative endpoints are being tried
- What each alternative endpoint returns

### Possible Causes

1. **Portal Requires Additional Authentication**
   - Some portals require specific cookies or headers after handshake
   - May need to store and reuse session cookies from handshake

2. **Portal Uses Different Endpoint Structure**
   - May not follow standard Stalker portal API
   - Could require custom endpoint detection

3. **Cloudflare Challenge**
   - Despite cloudscraper, some Cloudflare configurations require browser-like behavior
   - May need additional headers or cookie handling

4. **Portal Blocks Automated Access**
   - Some portals detect and block non-browser clients
   - May require more sophisticated browser emulation

### Testing with MacReplayXC

To compare behavior:
1. Run MacReplayXC with same MAC and portal
2. Enable debug logging in MacReplayXC
3. Compare request/response headers and cookies
4. Check if MacReplayXC uses any special handling for this portal

### Manual Testing

You can test the portal manually:
```bash
# Test handshake
curl -H "User-Agent: Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3" \
     -H "X-User-Agent: Model: MAG250; Link: WiFi; MAC: 00:1A:79:A3:B8:A4" \
     -H "Authorization: Bearer undefined" \
     --cookie "mac=00:1A:79:A3:B8:A4;stb_lang=en;timezone=Europe/Berlin" \
     "http://dlta4k.com/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"

# Test expiry (replace TOKEN with actual token from handshake)
curl -H "User-Agent: Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3" \
     -H "X-User-Agent: Model: MAG250; Link: WiFi; MAC: 00:1A:79:A3:B8:A4" \
     -H "Authorization: Bearer TOKEN" \
     --cookie "mac=00:1A:79:A3:B8:A4;stb_lang=en;timezone=Europe/Berlin" \
     "http://dlta4k.com/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
```

## Comparison with MacReplayXC-main

### Already Implemented ✅
- Cloudscraper for Cloudflare bypass
- Multiple proxy type support (HTTP, SOCKS, Shadowsocks)
- Enhanced cookies with device IDs
- Alternative endpoint fallbacks
- GET and POST method support
- MAG model header fallbacks
- Session management with periodic refresh

### Not Needed ❌
- Smart MAC Selection System (Dispatcharr has its own MAC management)
- VOD/Series support (not requested by user)
- M3U parsing (Dispatcharr has its own M3U handling)

### Differences
- MacReplayXC uses global session, Dispatcharr uses per-MAC session cache
- MacReplayXC has separate utils.py for proxy parsing, Dispatcharr has it inline
- Dispatcharr has more sophisticated Django integration and database models
