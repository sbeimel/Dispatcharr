#!/usr/bin/env python
"""
Script to test proxy fields in WebUI after fixes.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from apps.m3u.models import M3UAccount

def test_proxy_fields():
    """Test if proxy fields are accessible and working."""
    print("Testing Proxy Fields in M3UAccount Model")
    print("=" * 50)
    
    # Test model fields
    try:
        # Check if fields exist in model
        proxy_field = M3UAccount._meta.get_field('proxy')
        proxy_std_xc_field = M3UAccount._meta.get_field('proxy_std_xc')
        account_type_field = M3UAccount._meta.get_field('account_type')
        
        print("✅ Model fields exist:")
        print(f"  - proxy: {proxy_field.verbose_name}")
        print(f"  - proxy_std_xc: {proxy_std_xc_field.verbose_name}")
        print(f"  - account_type: {account_type_field.verbose_name}")
        
    except Exception as e:
        print(f"❌ Error accessing model fields: {e}")
        return False
    
    # Test get_proxy method
    try:
        account = M3UAccount.objects.first()
        if account:
            proxy = account.get_proxy()
            print(f"\n✅ get_proxy() method works:")
            print(f"  - Account: {account.name}")
            print(f"  - Type: {account.get_account_type_display()}")
            print(f"  - Proxy: {proxy if proxy else 'None configured'}")
        else:
            print("\n⚠️  No accounts found to test get_proxy() method")
            
    except Exception as e:
        print(f"\n❌ Error testing get_proxy() method: {e}")
        return False
    
    # Test account types
    try:
        print(f"\n✅ Account type choices:")
        for choice in M3UAccount.Types.choices:
            print(f"  - {choice[0]}: {choice[1]}")
            
    except Exception as e:
        print(f"\n❌ Error accessing account types: {e}")
        return False
    
    return True

def test_admin_configuration():
    """Test admin configuration."""
    print("\nTesting Admin Configuration")
    print("=" * 30)
    
    try:
        from apps.m3u.admin import M3UAccountAdmin
        from django.contrib import admin
        
        # Get admin instance
        admin_instance = admin.site._registry.get(M3UAccount)
        
        if admin_instance:
            print("✅ M3UAccountAdmin is registered")
            
            # Check fieldsets
            if hasattr(admin_instance, 'fieldsets'):
                print("✅ Fieldsets are configured:")
                for fieldset in admin_instance.fieldsets:
                    print(f"  - {fieldset[0]}: {fieldset[1]['fields']}")
            else:
                print("⚠️  No fieldsets configured (will show all fields)")
                
            # Check list_display
            if hasattr(admin_instance, 'list_display'):
                print(f"✅ List display fields: {admin_instance.list_display}")
            
        else:
            print("❌ M3UAccountAdmin is not registered")
            return False
            
    except Exception as e:
        print(f"❌ Error testing admin configuration: {e}")
        return False
    
    return True

def test_form_configuration():
    """Test form configuration."""
    print("\nTesting Form Configuration")
    print("=" * 25)
    
    try:
        from apps.m3u.forms import M3UAccountForm
        
        # Create form instance
        form = M3UAccountForm()
        
        print("✅ M3UAccountForm fields:")
        for field_name in form.fields:
            field = form.fields[field_name]
            print(f"  - {field_name}: {field.label or field_name}")
            
        # Check if proxy fields are included
        proxy_fields = ['proxy', 'proxy_std_xc']
        missing_fields = [f for f in proxy_fields if f not in form.fields]
        
        if missing_fields:
            print(f"❌ Missing proxy fields in form: {missing_fields}")
            return False
        else:
            print("✅ All proxy fields are included in form")
            
    except Exception as e:
        print(f"❌ Error testing form configuration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Proxy WebUI Test Script")
    print("=" * 40)
    
    success = True
    
    # Test model fields
    if not test_proxy_fields():
        success = False
    
    # Test admin configuration
    if not test_admin_configuration():
        success = False
    
    # Test form configuration
    if not test_form_configuration():
        success = False
    
    if success:
        print("\n🎉 All tests passed! Proxy fields should be visible in WebUI.")
        print("\nNext steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Restart Django server")
        print("3. Check M3U Account admin page")
    else:
        print("\n❌ Some tests failed. Check the errors above.")