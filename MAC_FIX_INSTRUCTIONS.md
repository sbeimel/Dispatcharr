# MAC Address Fix Instructions

## Issue
The "No valid MAC addresses" error occurs because MAC addresses stored in the `mac_address` field are not being converted to `M3UAccountMac` objects that the system expects.

## Root Cause
The MAC addresses "00:1A:79:19:1F:00 00:1A:79:19:1F:A7 00:1A:79:19:1F:A9" are valid but the processing function is failing to create the database objects.

## What Was Fixed

### 1. Syntax Error in models.py
- Fixed regex pattern in `is_valid_mac_format()` method
- Removed duplicate `$'` characters from the pattern

### 2. Enhanced MAC Processing
- The `M3UAccount.save()` method now automatically processes MAC addresses
- The `_process_mac_addresses()` method parses the `mac_address` field and creates `M3UAccountMac` objects
- The MAC refresh function checks for missing MAC objects and processes them automatically

## How to Apply the Fix

### Option 1: Using Docker (Recommended)
```bash
# Navigate to the docker directory
cd Dispatcharr-0.14.0/docker

# Try the debug script first to see what's happening
docker-compose exec web python /app/debug_mac_fix.py

# If that works, run the main fix
docker-compose exec web python /app/fix_mac_addresses_standalone.py

# If validation is causing issues, try the simple fix
docker-compose exec web python /app/simple_mac_fix.py
```

### Option 2: Using Django Shell (if you have Django installed locally)
```bash
cd Dispatcharr-0.14.0

# Debug first
python debug_mac_fix.py

# Then run the fix
python manage.py shell -c "exec(open('quick_mac_fix.py').read())"
```

### Option 3: Manual Database Fix
If the above methods don't work, you can manually trigger the MAC processing by:
1. Edit the MAC account in the admin interface
2. Save the account (this will trigger the `_process_mac_addresses()` method)
3. The MAC addresses will be automatically parsed and converted to MAC objects

### Option 4: Direct SQL Fix (Last Resort)
If all else fails, you can manually insert the MAC objects:
```sql
INSERT INTO m3u_m3uaccountmac (account_id, address, priority, status, last_checked, expires_at, expires_text, last_error)
VALUES 
(4, '00:1A:79:19:1F:00', 0, 'unknown', NULL, NULL, NULL, NULL),
(4, '00:1A:79:19:1F:A7', 1, 'unknown', NULL, NULL, NULL, NULL),
(4, '00:1A:79:19:1F:A9', 2, 'unknown', NULL, NULL, NULL, NULL);
```

## Verification

After running the fix, you should see:
1. MAC objects created in the database for each MAC address
2. The "No valid MAC addresses" error should be resolved
3. MAC failover should work properly

## Files Modified

1. **Dispatcharr-0.14.0/apps/m3u/models.py**
   - Fixed regex syntax error in `is_valid_mac_format()`
   - Fixed duplicate import issue
   - Enhanced `save()` method to auto-process MAC addresses

2. **Fix Scripts Created**
   - `debug_mac_fix.py` - Debug script with detailed logging
   - `simple_mac_fix.py` - Simple fix that bypasses validation
   - `quick_mac_fix.py` - Django shell script
   - `fix_mac_addresses_standalone.py` - Standalone script for Docker

## Troubleshooting

If you're still getting the error after running the fix:

1. **Check if MAC objects were created:**
   ```bash
   docker-compose exec web python manage.py shell -c "
   from apps.m3u.models import M3UAccount, M3UAccountMac
   account = M3UAccount.objects.get(id=4)
   print(f'MAC objects: {account.macs.count()}')
   for mac in account.macs.all():
       print(f'  - {mac.address} (status: {mac.status})')
   "
   ```

2. **Check the logs for more details:**
   ```bash
   docker-compose logs web | grep -i mac
   ```

3. **Try refreshing the account manually:**
   - Go to the admin interface
   - Find the MAC account
   - Click "Refresh" to trigger the MAC processing again

The system should now properly handle multiple MAC addresses and provide automatic failover when one MAC expires or fails.