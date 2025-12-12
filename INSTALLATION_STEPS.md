# Installation Steps for Cloudflare Fix

## Quick Setup

1. **Install cloudscraper dependency:**
   ```bash
   cd Dispatcharr-0.14.0
   python install_cloudscraper.py
   ```

2. **Verify the installation:**
   ```bash
   python test_cloudscraper.py
   ```

3. **Restart Dispatcharr** (stop and start the service)

## Manual Installation (Alternative)

If the automatic script doesn't work:

```bash
cd Dispatcharr-0.14.0
pip install cloudscraper==1.2.71
```

## What Was Fixed

### 1. Cloudflare Bypass
- **Problem**: MAC portals behind Cloudflare were returning empty responses
- **Solution**: Integrated cloudscraper (same as MacReplayXC) for automatic Cloudflare bypass
- **Result**: Portals like `ueawall.com` should now work correctly

### 2. Frontend Form Issue  
- **Problem**: Account type dropdown reset when editing existing accounts
- **Solution**: Fixed useEffect hook to properly handle account type state changes
- **Result**: Editing accounts now maintains the correct account type selection

### 3. Improved Reliability
- **Added**: No-proxy fallback when proxy requests fail
- **Added**: Simplified error handling matching MacReplayXC approach
- **Result**: Better success rate for MAC portal connections

## Testing

After installation, test with your MAC portal:
1. Go to M3U Accounts in Dispatcharr
2. Try refreshing a MAC account that was previously failing
3. Check logs for `"Created cloudscraper session for Cloudflare bypass"`
4. Verify channels are loaded successfully

## Troubleshooting

### If cloudscraper installation fails:
```bash
# Try with --user flag
pip install --user cloudscraper==1.2.71

# Or try upgrading pip first
python -m pip install --upgrade pip
pip install cloudscraper==1.2.71
```

### If MAC portals still don't work:
1. Check that cloudscraper is properly installed: `python test_cloudscraper.py`
2. Restart Dispatcharr completely
3. Check logs for cloudscraper session creation messages
4. Try without proxy if you're using one

## Files Modified

- `apps/m3u/mac_portal_client.py` - Main MAC portal client with Cloudflare bypass
- `frontend/src/components/forms/M3U.jsx` - Fixed account type dropdown
- `requirements.txt` - Added cloudscraper dependency
- Added installation and test scripts

## Rollback

If you need to rollback:
1. Remove cloudscraper: `pip uninstall cloudscraper`
2. Restore original files from backup
3. Restart Dispatcharr