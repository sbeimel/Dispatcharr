#!/usr/bin/env python
"""
Quick fix script to process MAC addresses for existing accounts.
Run this in Django shell: python manage.py shell < fix_mac_addresses.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from apps.m3u.models import M3UAccount, M3UAccountMac

def fix_mac_addresses():
    """Process MAC addresses for all MAC accounts that need it."""
    
    # Find MAC accounts that have mac_address but no M3UAccountMac objects
    mac_accounts = M3UAccount.objects.filter(
        account_type=M3UAccount.Types.MAC,
        mac_address__isnull=False
    ).exclude(mac_address='')
    
    print(f"Found {mac_accounts.count()} MAC accounts to check")
    
    processed = 0
    for account in mac_accounts:
        existing_macs = account.macs.count()
        
        print(f"\nAccount: {account.name} (ID: {account.id})")
        print(f"  MAC addresses field: {account.mac_address}")
        print(f"  Existing MAC objects: {existing_macs}")
        
        if existing_macs == 0:
            print("  Processing MAC addresses...")
            try:
                account._process_mac_addresses()
                new_mac_count = account.macs.count()
                print(f"  ✅ Created {new_mac_count} MAC objects:")
                
                for mac in account.macs.all():
                    print(f"    - {mac.address} (priority: {mac.priority}, status: {mac.status})")
                
                processed += 1
            except Exception as e:
                print(f"  ❌ Error processing: {e}")
        else:
            print("  ✅ Already has MAC objects, skipping")
    
    print(f"\n🎯 Summary: Processed {processed} accounts")
    return processed

if __name__ == "__main__":
    fix_mac_addresses()