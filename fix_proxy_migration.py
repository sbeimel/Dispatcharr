#!/usr/bin/env python
"""
Script to manually fix proxy field migration issues.
Run this if the migration fails.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from django.db import connection
from apps.m3u.models import M3UAccount

def check_proxy_fields():
    """Check which proxy fields exist in the database."""
    with connection.cursor() as cursor:
        # Check if proxy field exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'm3u_m3uaccount' 
            AND column_name IN ('proxy', 'proxy_std_xc')
            ORDER BY column_name;
        """)
        
        existing_fields = [row[0] for row in cursor.fetchall()]
        
        print("Existing proxy fields in m3u_m3uaccount table:")
        for field in existing_fields:
            print(f"  ✅ {field}")
        
        missing_fields = []
        if 'proxy' not in existing_fields:
            missing_fields.append('proxy')
        if 'proxy_std_xc' not in existing_fields:
            missing_fields.append('proxy_std_xc')
            
        if missing_fields:
            print("\nMissing proxy fields:")
            for field in missing_fields:
                print(f"  ❌ {field}")
        else:
            print("\n✅ All proxy fields exist!")
            
        return existing_fields, missing_fields

def add_missing_proxy_fields():
    """Manually add missing proxy fields."""
    existing_fields, missing_fields = check_proxy_fields()
    
    if not missing_fields:
        print("No missing fields to add.")
        return
    
    with connection.cursor() as cursor:
        if 'proxy' in missing_fields:
            print("Adding 'proxy' field...")
            cursor.execute("""
                ALTER TABLE m3u_m3uaccount 
                ADD COLUMN proxy varchar(255);
            """)
            print("✅ Added 'proxy' field")
        
        if 'proxy_std_xc' in missing_fields:
            print("Adding 'proxy_std_xc' field...")
            cursor.execute("""
                ALTER TABLE m3u_m3uaccount 
                ADD COLUMN proxy_std_xc varchar(255);
            """)
            print("✅ Added 'proxy_std_xc' field")

def test_proxy_functionality():
    """Test if the proxy functionality works."""
    print("\nTesting proxy functionality...")
    
    # Try to access the fields
    try:
        account = M3UAccount.objects.first()
        if account:
            # Test get_proxy method
            proxy = account.get_proxy()
            print(f"✅ get_proxy() method works: {proxy}")
            
            # Test field access
            mac_proxy = getattr(account, 'proxy', None)
            std_proxy = getattr(account, 'proxy_std_xc', None)
            print(f"✅ proxy field accessible: {mac_proxy}")
            print(f"✅ proxy_std_xc field accessible: {std_proxy}")
        else:
            print("No M3U accounts found to test")
    except Exception as e:
        print(f"❌ Error testing proxy functionality: {e}")

if __name__ == "__main__":
    print("Proxy Migration Fix Script")
    print("=" * 40)
    
    # Check current state
    existing_fields, missing_fields = check_proxy_fields()
    
    # Add missing fields if needed
    if missing_fields:
        print(f"\nAdding missing fields: {missing_fields}")
        add_missing_proxy_fields()
        
        # Check again
        print("\nRechecking after adding fields...")
        check_proxy_fields()
    
    # Test functionality
    test_proxy_functionality()
    
    print("\n✅ Proxy migration fix completed!")
    print("\nYou can now run: python manage.py migrate")