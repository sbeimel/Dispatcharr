#!/usr/bin/env python3
"""
Test MAC refresh functionality to ensure all MACs are being checked.
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

# Now import Django models and tasks
from apps.m3u.models import M3UAccount, M3UAccountMac
from apps.m3u.tasks import _refresh_mac_account_direct, _refresh_mac_account_with_groups

def test_mac_refresh():
    """Test MAC refresh functionality."""
    print("🧪 Testing MAC refresh functionality...")
    
    # Find MAC accounts
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        is_active=True
    )

    print(f"Found {accounts.count()} active MAC accounts")

    for account in accounts:
        print(f"\n🧪 Testing Account: {account.name} (ID: {account.id})")
        print(f"   Server URL: {account.server_url}")
        print(f"   MAC field: '{account.mac_address}'")
        
        # Check MAC objects
        macs = account.macs.all()
        print(f"   MAC objects: {macs.count()}")
        
        for mac in macs:
            print(f"      - {mac.address} (priority: {mac.priority}, status: {mac.status})")
        
        if macs.count() == 0:
            print("   ❌ No MAC objects found - running fix first...")
            account._process_mac_addresses()
            macs = account.macs.all()
            print(f"   MAC objects after fix: {macs.count()}")
        
        if macs.count() > 0:
            print("   🧪 Testing direct MAC refresh...")
            try:
                result = _refresh_mac_account_direct(account.id)
                print(f"   Result: {result}")
                
                # Check MAC statuses after refresh
                print("   MAC statuses after refresh:")
                for mac in account.macs.all():
                    print(f"      - {mac.address}: {mac.status} (last_checked: {mac.last_checked})")
                
            except Exception as e:
                print(f"   ❌ Error during MAC refresh: {e}")
                import traceback
                traceback.print_exc()
            
            print("   🧪 Testing MAC refresh with groups...")
            try:
                result = _refresh_mac_account_with_groups(account.id)
                print(f"   Result: {result}")
                
                if result and not result.get('error'):
                    groups = result.get('groups', {})
                    channels = result.get('channels', 0)
                    print(f"   Groups found: {len(groups)}")
                    print(f"   Channels found: {channels}")
                    
                    if groups:
                        print("   Group names:")
                        for group_name in list(groups.keys())[:10]:  # Show first 10
                            print(f"      - {group_name}")
                        if len(groups) > 10:
                            print(f"      ... and {len(groups) - 10} more")
                
            except Exception as e:
                print(f"   ❌ Error during MAC refresh with groups: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ⚠️  Skipping refresh test - no MAC objects available")

    print("\n🎯 MAC refresh test complete!")

if __name__ == "__main__":
    test_mac_refresh()