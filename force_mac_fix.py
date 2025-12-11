#!/usr/bin/env python3
"""
Force MAC address processing - bypasses all validation issues.
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

def force_mac_fix():
    """Force create MAC objects for all MAC accounts."""
    print("🔧 Force creating MAC objects...")
    
    # Find MAC accounts with mac_address but no MAC objects
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        mac_address__isnull=False
    ).exclude(mac_address='')

    print(f"Found {accounts.count()} MAC accounts to process")

    for account in accounts:
        print(f"\n🔧 Processing Account: {account.name} (ID: {account.id})")
        print(f"   MAC field: '{account.mac_address}'")
        
        # Delete existing MAC objects first
        existing_count = account.macs.count()
        if existing_count > 0:
            print(f"   Deleting {existing_count} existing MAC objects...")
            account.macs.all().delete()
        
        try:
            with transaction.atomic():
                # Parse MAC addresses manually
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

    print("\n🎯 Force MAC fix complete!")

if __name__ == "__main__":
    force_mac_fix()