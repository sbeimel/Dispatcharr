#!/usr/bin/env python3
"""
Fix MAC address processing issues.
This script manually processes MAC addresses for accounts that have them but no MAC objects.
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

def fix_mac_processing():
    """Fix MAC address processing for accounts that need it."""
    print("🔧 Starting MAC address processing fix...")
    
    # Find MAC accounts with mac_address but no MAC objects
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        mac_address__isnull=False
    ).exclude(mac_address='')

    print(f"Found {accounts.count()} MAC accounts to check")

    for account in accounts:
        print(f"\n🔧 Processing Account: {account.name} (ID: {account.id})")
        print(f"   MAC field: '{account.mac_address}'")
        print(f"   Existing MAC objects: {account.macs.count()}")
        
        try:
            with transaction.atomic():
                # Force process MAC addresses
                account._process_mac_addresses()
                
                # Check if MAC objects were created
                mac_count = account.macs.count()
                print(f"   ✅ MAC objects after processing: {mac_count}")
                
                if mac_count > 0:
                    for mac in account.macs.all():
                        print(f"      - {mac.address} (priority: {mac.priority}, status: {mac.status})")
                else:
                    print("   ❌ No MAC objects created - trying manual creation...")
                    
                    # Manual MAC processing as fallback
                    import re
                    raw_macs = re.split(r'[,\s\n\r]+', account.mac_address.strip())
                    
                    for i, mac in enumerate(raw_macs):
                        mac = mac.strip()
                        if mac:
                            # Normalize MAC address format
                            normalized_mac = M3UAccountMac.normalize_mac_address(mac)
                            print(f"      Processing: '{mac}' -> '{normalized_mac}'")
                            
                            if M3UAccountMac.is_valid_mac_format(normalized_mac):
                                try:
                                    mac_obj, created = M3UAccountMac.objects.get_or_create(
                                        account=account,
                                        address=normalized_mac,
                                        defaults={
                                            'priority': i,
                                            'status': M3UAccountMac.Status.UNKNOWN
                                        }
                                    )
                                    if created:
                                        print(f"        ✅ Created MAC object: {mac_obj}")
                                    else:
                                        print(f"        ℹ️  MAC object already exists: {mac_obj}")
                                except Exception as e:
                                    print(f"        ❌ Failed to create MAC object: {e}")
                            else:
                                print(f"        ❌ Invalid MAC format: '{normalized_mac}'")
                
        except Exception as e:
            print(f"   ❌ Error processing account {account.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n🎯 MAC processing fix complete!")

if __name__ == "__main__":
    fix_mac_processing()