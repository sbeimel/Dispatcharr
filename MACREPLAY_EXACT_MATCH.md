# MacReplayXC Exact Match Implementation

## Changes Made to Match MacReplayXC Behavior

Based on the successful MacReplayXC logs showing:
- `Got 9092 channels for MAC 00:1A:79:00:02:ED`
- `Got 2937 channels for MAC 00:1A:79:67:74:53`

### Key Changes Applied

#### 1. Session Management
**Changed**: Use regular requests session for channel fetching (not cloudscraper)
**Reason**: MacReplayXC uses `_get_session()` without `use_cloudscraper=True` for `getAllChannels`

```python
# Before
session = _get_session(use_cloudscraper=True)

# After (matching MacReplayXC)
session = _get_session()
```

#### 2. Response Handling
**Changed**: Direct JSON parsing without status code checks
**Reason**: MacReplayXC uses `response.json()["js"]["data"]` directly

```python
# Before
if response.status_code == 200:
    data = response.json()
    channels = data["js"]["data"]
else:
    raise Exception(f"HTTP {response.status_code}")

# After (matching MacReplayXC)
channels = response.json()["js"]["data"]
```

#### 3. Cloudscraper Usage
**Kept**: Cloudscraper only for portal discovery (xpcom.common.js parsing)
**Reason**: MacReplayXC uses cloudscraper in `getUrl()` but not in `getAllChannels()`

#### 4. Headers and Parameters
**Verified**: Exact match with MacReplayXC implementation
- Same User-Agent string
- Same Authorization header format
- Same request parameters
- Same cookies

#### 5. Fallback Logic
**Enhanced**: Added no-proxy fallback like MacReplayXC
**Reason**: MacReplayXC tries without proxy when proxy requests fail

### Expected Results

With these changes, Dispatcharr should now:
1. Successfully connect to `ueawall.com` portal
2. Get thousands of channels like MacReplayXC does
3. Handle the same edge cases MacReplayXC handles

### Testing

The next test should show:
- `"Got X channels for MAC ..."` messages
- Successful channel import
- No more empty response errors

### Files Modified

- `apps/m3u/mac_portal_client.py` - Made exact match with MacReplayXC `getAllChannels()`
- `requirements.txt` - Added cloudscraper (for portal discovery only)

### Verification

To verify the fix works:
1. Check logs for successful channel retrieval
2. Verify MAC accounts can refresh without errors
3. Confirm channel counts match MacReplayXC output