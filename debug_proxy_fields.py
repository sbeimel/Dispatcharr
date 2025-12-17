#!/usr/bin/env python
"""
Debug script to check proxy field status in database and WebUI.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from django.db import connection
from apps.m3u.models import M3UAccount
from apps.m3u.forms import M3UAccountForm
from apps.m3u.admin import M3UAccountAdmin
from django.contrib import admin

def check_database_fields():
    """Check if proxy fields exist in database."""
    print("🔍 Checking Database Fields")
    print("=" * 30)
    
    with connection.cursor() as cursor:
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'm3u_m3uaccount' 
            AND column_name LIKE '%proxy%'
            ORDER BY column_name;
        """)
        
        proxy_fields = cursor.fetchall()
        
        if proxy_fields:
            print("✅ Proxy fields found in database:")
            for field in proxy_fields:
                print(f"  - {field[0]} ({field[1]}, nullable: {field[2]})")
        else:
            print("❌ No proxy fields found in database!")
            print("   Run migration: python manage.py migrate m3u")
            return False
    
    return True

def check_model_fields():
    """Check if proxy fields exist in Django model."""
    print("\n🔍 Checking Django Model Fields")
    print("=" * 35)
    
    try:
        # Check if fields exist in model
        proxy_field = M3UAccount._meta.get_field('proxy')
        proxy_std_xc_field = M3UAccount._meta.get_field('proxy_std_xc')
        account_type_field = M3UAccount._meta.get_field('account_type')
        
        print("✅ Model fields exist:")
        print(f"  - proxy: {proxy_field.verbose_name} ({proxy_field.__class__.__name__})")
        print(f"  - proxy_std_xc: {proxy_std_xc_field.verbose_name} ({proxy_std_xc_field.__class__.__name__})")
        print(f"  - account_type: {account_type_field.verbose_name} ({account_type_field.__class__.__name__})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing model fields: {e}")
        return False

def check_form_fields():
    """Check if proxy fields are in the form."""
    print("\n🔍 Checking Form Fields")
    print("=" * 25)
    
    try:
        form = M3UAccountForm()
        
        print("✅ Form fields:")
        for field_name in form.fields:
            field = form.fields[field_name]
            print(f"  - {field_name}: {field.label or field_name}")
        
        # Check specifically for proxy fields
        proxy_fields = ['proxy', 'proxy_std_xc']
        missing_fields = [f for f in proxy_fields if f not in form.fields]
        
        if missing_fields:
            print(f"\n❌ Missing proxy fields in form: {missing_fields}")
            return False
        else:
            print("\n✅ All proxy fields are included in form")
            return True
            
    except Exception as e:
        print(f"❌ Error checking form fields: {e}")
        return False

def check_admin_config():
    """Check admin configuration."""
    print("\n🔍 Checking Admin Configuration")
    print("=" * 30)
    
    try:
        # Get admin instance
        admin_instance = admin.site._registry.get(M3UAccount)
        
        if admin_instance:
            print("✅ M3UAccountAdmin is registered")
            
            # Check if form is configured
            if hasattr(admin_instance, 'form'):
                print(f"✅ Custom form configured: {admin_instance.form}")
            else:
                print("⚠️  No custom form configured - using default")
            
            # Check fieldsets
            if hasattr(admin_instance, 'fieldsets'):
                print("✅ Fieldsets configured:")
                for fieldset in admin_instance.fieldsets:
                    print(f"  - {fieldset[0]}: {fieldset[1]['fields']}")
            else:
                print("⚠️  No fieldsets configured")
            
            return True
        else:
            print("❌ M3UAccountAdmin is not registered")
            return False
            
    except Exception as e:
        print(f"❌ Error checking admin config: {e}")
        return False

def test_account_proxy():
    """Test proxy functionality with existing accounts."""
    print("\n🔍 Testing Account Proxy Functionality")
    print("=" * 40)
    
    try:
        accounts = M3UAccount.objects.all()[:3]  # Test first 3 accounts
        
        if not accounts:
            print("⚠️  No accounts found to test")
            return True
        
        for account in accounts:
            print(f"\n📋 Account: {account.name}")
            print(f"   Type: {account.get_account_type_display()}")
            
            # Test get_proxy method
            try:
                proxy = account.get_proxy()
                print(f"   get_proxy(): {proxy if proxy else 'None'}")
                
                # Check raw field values
                if hasattr(account, 'proxy'):
                    print(f"   proxy field: '{account.proxy}'")
                if hasattr(account, 'proxy_std_xc'):
                    print(f"   proxy_std_xc field: '{account.proxy_std_xc}'")
                    
            except Exception as e:
                print(f"   ❌ Error testing get_proxy(): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing account proxy: {e}")
        return False

def main():
    print("🔧 Proxy Fields Debug Script")
    print("=" * 50)
    
    success = True
    
    # Check database
    if not check_database_fields():
        success = False
    
    # Check model
    if not check_model_fields():
        success = False
    
    # Check form
    if not check_form_fields():
        success = False
    
    # Check admin
    if not check_admin_config():
        success = False
    
    # Test functionality
    if not test_account_proxy():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All checks passed!")
        print("\nIf WebUI still doesn't show proxy fields:")
        print("1. Restart Django server")
        print("2. Clear browser cache")
        print("3. Check Django admin at /admin/m3u/m3uaccount/")
    else:
        print("❌ Some checks failed!")
        print("\nNext steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Restart Django server")
        print("3. Run this script again")

if __name__ == "__main__":
    main()