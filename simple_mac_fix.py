#!/usr/bin/env python3
"""
Simple MAC address fix that bypasses validation.
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
import re

def simple_mac_fix():
    """Simple MAC address fix that bypasses validation."""
    print("🔧 Starting simple MAC address fix...")
    
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
                # Parse MAC addresses manually
                raw_macs = re.split(r'[,\s\n\r]+', account.mac_address.strip())
                
                for i, mac in enumerate(raw_macs):
                    mac = mac.strip()
                    if mac and len(mac) >= 12:  # Basic length check
                        try:
                            # Create MAC object without calling full_clean()
                            mac_obj = M3UAccountMac(
                                account=account,
                                address=mac,
                                priority=i,
                                status=M3UAccountMac.Status.UNKNOWN
                            )
                            # Save without validation
                            super(M3UAccountMac, mac_obj).save()
                            print(f"     ✅ Created MAC object: {mac}")
                        except Exception as e:
                            print(f"     ❌ Failed to create MAC object for {mac}: {e}")
                            
            except Exception as e:
                print(f"   ❌ Error processing MACs: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ✅ Already has MAC objects:")
            for mac in account.macs.all():
                print(f"      - {mac.address} (priority: {mac.priority}, status: {mac.status})")

    print("\n🎯 Simple MAC fix complete!")

if __name__ == "__main__":
    simple_mac_fix()