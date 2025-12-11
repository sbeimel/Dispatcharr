#!/usr/bin/env python3
"""
Standalone MAC address fix script that can be run in Docker container.
This script processes MAC addresses without requiring Django shell.
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

def fix_mac_addresses():
    """Fix MAC addresses for all MAC accounts."""
    print("🔧 Starting MAC address fix...")
    
    # Find MAC accounts with mac_address but no MAC objects
    accounts = M3UAccount.objects.filter(
        account_type='MAC',
        mac_address__isnull=False
    ).exclude(mac_address='')

    print(f"Found {accounts.count()} MAC accounts")

    for account in accounts:
        print(f"\n🔧 Account: {account.name}")
        print(f"   MAC field: {account.mac_address}")
        print(f"   Existing MACs: {account.macs.count()}")
        
        if account.macs.count() == 0:
            print("   Processing...")
            try:
                account._process_mac_addresses()
                print(f"   ✅ Created {account.macs.count()} MAC objects")
                
                for mac in account.macs.all():
                    print(f"      - {mac.address} (priority: {mac.priority})")
            except Exception as e:
                print(f"   ❌ Error processing MACs: {e}")
        else:
            print("   ✅ Already processed")

    print("\n🎯 MAC processing complete!")

if __name__ == "__main__":
    fix_mac_addresses()