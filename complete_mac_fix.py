#!/usr/bin/env python3
"""
Complete MAC fix - addresses all remaining issues.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

# Now import Django models
from apps.m3u.models import M3UAccount, M3UAccountMac
from django.db import transaction

def complete_mac_fix():
    """Complete fix for all MAC issues."""
    print("🔧 Starting complete MAC fix...")
    
    # Step 1: Fix MAC object creation
    print("\n📋 Step 1: Creating MAC objects...")
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        mac_address__isnull=False
    ).exclude(mac_address='')

    print(f"Found {accounts.count()} MAC accounts")

    for account in accounts:
        print(f"\n🔧 Processing Account: {account.name} (ID: {account.id})")
        print(f"   MAC field: '{account.mac_address}'")
        
        # Delete existing MAC objects first to start fresh
        existing_count = account.macs.count()
        if existing_count > 0:
            print(f"   Deleting {existing_count} existing MAC objects...")
            account.macs.all().delete()
        
        try:
            with transaction.atomic():
                # Parse MAC addresses manually with robust parsing
                import re
                raw_macs = re.split(r'[,\s\n\r]+', account.mac_address.strip())
                
                created_count = 0
                for i, mac in enumerate(raw_macs):
                    mac = mac.strip()
                    if mac and len(mac) >= 12:  # Basic length check
                        # Normalize to standard format
                        clean_mac = re.sub(r'[:-]', '', mac.upper())
                        if len(clean_mac) == 12:
                            formatted_mac = ':'.join(clean_mac[j:j+2] for j in range(0, 12, 2))
                            
                            try:
                                mac_obj = M3UAccountMac.objects.create(
                                    account=account,
                                    address=formatted_mac,
                                    priority=i,
                                    status=M3UAccountMac.Status.UNKNOWN
                                )
                                print(f"      ✅ Created: {mac_obj}")
                                created_count += 1
                            except Exception as e:
                                print(f"      ❌ Failed to create {formatted_mac}: {e}")
                        else:
                            print(f"      ⚠️  Invalid length for '{mac}': {len(clean_mac)}")
                    else:
                        print(f"      ⚠️  Skipping invalid MAC: '{mac}'")
                
                print(f"   ✅ Created {created_count} MAC objects")
                
        except Exception as e:
            print(f"   ❌ Error processing account {account.name}: {e}")
            import traceback
            traceback.print_exc()

    # Step 2: Verify account types
    print("\n📋 Step 2: Verifying account types...")
    for account in M3UAccount.objects.filter(account_type='MAC'):
        print(f"   Account {account.name}: type='{account.account_type}', MACs={account.macs.count()}")

    # Step 3: Test MAC refresh
    print("\n📋 Step 3: Testing MAC refresh...")
    try:
        from apps.m3u.tasks import _refresh_mac_account_with_groups
        
        for account in accounts[:1]:  # Test first account only
            print(f"   Testing MAC refresh for account {account.name}...")
            result = _refresh_mac_account_with_groups(account.id)
            
            if result and not result.get('error'):
                print(f"   ✅ Success: {result.get('channels', 0)} channels, {len(result.get('groups', {}))} groups")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   ❌ Error testing MAC refresh: {e}")

    print("\n🎯 Complete MAC fix finished!")
    print("\n📋 Next steps:")
    print("   1. Restart the web service: docker-compose restart web")
    print("   2. Try refreshing a MAC account from the UI")
    print("   3. Check that groups are created and can be activated")
    print("   4. Verify that channels appear in activated groups")

if __name__ == "__main__":
    complete_mac_fix()