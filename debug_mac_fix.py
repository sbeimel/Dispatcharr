#!/usr/bin/env python3
"""
Debug MAC address processing with detailed logging.
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

def debug_mac_processing():
    """Debug MAC address processing with detailed logging."""
    print("🔧 Starting MAC address debug...")
    
    # Find MAC accounts with mac_address but no MAC objects
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        mac_address__isnull=False
    ).exclude(mac_address='')

    print(f"Found {accounts.count()} MAC accounts")

    for account in accounts:
        print(f"\n🔧 Account: {account.name} (ID: {account.id})")
        print(f"   MAC field: '{account.mac_address}'")
        print(f"   Existing MACs: {account.macs.count()}")
        
        if account.macs.count() == 0:
            print("   Processing MAC addresses...")
            
            try:
                # Test the MAC validation first
                import re
                mac_addresses = []
                
                # Split by various separators and clean up
                raw_macs = re.split(r'[,\s\n\r]+', account.mac_address.strip())
                print(f"   Raw MACs after split: {raw_macs}")
                
                for mac in raw_macs:
                    mac = mac.strip()
                    if mac:
                        print(f"     Processing MAC: '{mac}'")
                        # Normalize MAC address format
                        normalized_mac = M3UAccountMac.normalize_mac_address(mac)
                        print(f"       Normalized: '{normalized_mac}'")
                        if M3UAccountMac.is_valid_mac_format(normalized_mac):
                            print(f"       ✅ Valid")
                            mac_addresses.append(normalized_mac)
                        else:
                            print(f"       ❌ Invalid")
                
                print(f"   Valid MAC addresses: {mac_addresses}")
                
                if mac_addresses:
                    # Try to create MAC objects manually
                    for i, mac_address in enumerate(mac_addresses):
                        try:
                            mac_obj = M3UAccountMac.objects.create(
                                account=account,
                                address=mac_address,
                                priority=i,
                                status=M3UAccountMac.Status.UNKNOWN
                            )
                            print(f"     ✅ Created MAC object: {mac_obj}")
                        except Exception as e:
                            print(f"     ❌ Failed to create MAC object for {mac_address}: {e}")
                else:
                    print("   ❌ No valid MAC addresses found")
                    
            except Exception as e:
                print(f"   ❌ Error processing MACs: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ✅ Already has MAC objects:")
            for mac in account.macs.all():
                print(f"      - {mac.address} (priority: {mac.priority}, status: {mac.status})")

    print("\n🎯 MAC debug complete!")

if __name__ == "__main__":
    debug_mac_processing()