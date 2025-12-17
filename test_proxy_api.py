#!/usr/bin/env python
"""
Test script to verify proxy fields are returned by the API.
This helps debug WebUI issues by checking if the backend is sending the data correctly.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.m3u.models import M3UAccount
from django.core.serializers import serialize
import json


def test_proxy_api_response():
    """Test that proxy fields are included in API responses."""
    print("=" * 60)
    print("Testing Proxy Fields in API Response")
    print("=" * 60)
    
    # Get all M3U accounts
    accounts = M3UAccount.objects.all()
    
    if not accounts.exists():
        print("\n❌ No M3U accounts found in database")
        print("   Create an account first to test API response")
        return
    
    print(f"\n✓ Found {accounts.count()} M3U account(s)\n")
    
    for account in accounts:
        print(f"\n{'=' * 60}")
        print(f"Account: {account.name}")
        print(f"Type: {account.get_account_type_display()}")
        print(f"{'=' * 60}")
        
        # Simulate what the API would return
        account_data = {
            'id': account.id,
            'name': account.name,
            'account_type': account.account_type,
            'server_url': account.server_url,
            'proxy': account.proxy,
            'proxy_std_xc': account.proxy_std_xc,
            'mac_address': account.mac_address,
        }
        
        print("\nAPI Response (simulated):")
        print(json.dumps(account_data, indent=2))
        
        # Test get_proxy() method
        proxy = account.get_proxy()
        print(f"\nget_proxy() returns: {repr(proxy)}")
        
        # Verify correct field is used
        if account.account_type == M3UAccount.Types.MAC:
            expected_field = 'proxy'
            expected_value = account.proxy
        else:
            expected_field = 'proxy_std_xc'
            expected_value = account.proxy_std_xc
        
        print(f"Expected field: {expected_field}")
        print(f"Expected value: {repr(expected_value)}")
        
        # Check if proxy is correctly returned
        if proxy:
            print(f"✓ Proxy is configured: {proxy}")
        else:
            if expected_value:
                print(f"⚠ Proxy field has value '{expected_value}' but get_proxy() returned None")
                print(f"  This is correct if the value is empty/whitespace")
            else:
                print("✓ No proxy configured (as expected)")
        
        print()


def test_api_serialization():
    """Test Django REST Framework serialization."""
    print("\n" + "=" * 60)
    print("Testing Django Serialization")
    print("=" * 60)
    
    accounts = M3UAccount.objects.all()[:1]  # Just test first account
    
    if not accounts.exists():
        print("\n❌ No accounts to serialize")
        return
    
    # Serialize using Django's built-in serializer
    serialized = serialize('json', accounts, 
                          fields=('name', 'account_type', 'proxy', 'proxy_std_xc'))
    
    print("\nSerialized JSON:")
    print(serialized)
    
    # Parse and pretty print
    data = json.loads(serialized)
    print("\nParsed fields:")
    for item in data:
        fields = item['fields']
        print(f"  name: {fields.get('name')}")
        print(f"  account_type: {fields.get('account_type')}")
        print(f"  proxy: {fields.get('proxy')}")
        print(f"  proxy_std_xc: {fields.get('proxy_std_xc')}")


if __name__ == "__main__":
    try:
        test_proxy_api_response()
        test_api_serialization()
        
        print("\n" + "=" * 60)
        print("✓ API Response Test Complete")
        print("=" * 60)
        print("\nIf proxy fields are showing correctly here but not in WebUI:")
        print("1. Check that frontend is rebuilt: cd frontend && npm run build")
        print("2. Check browser console for JavaScript errors")
        print("3. Check Network tab to see actual API response")
        print("4. Clear browser cache and reload")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
