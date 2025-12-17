#!/usr/bin/env python
"""
Check migration status for proxy fields.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def check_migration_status():
    """Check if migrations are applied."""
    print("🔍 Checking Migration Status")
    print("=" * 30)
    
    try:
        # Check applied migrations
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT app, name 
                FROM django_migrations 
                WHERE app IN ('m3u', 'core') 
                AND name LIKE '%proxy%'
                ORDER BY app, name;
            """)
            
            applied_migrations = cursor.fetchall()
            
            if applied_migrations:
                print("✅ Proxy-related migrations applied:")
                for migration in applied_migrations:
                    print(f"  - {migration[0]}: {migration[1]}")
            else:
                print("❌ No proxy-related migrations found!")
                print("   Expected migrations:")
                print("   - m3u: 0036_add_proxy_field_for_all_account_types")
                print("   - core: 0020_add_proxy_support_stream_profiles")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking migrations: {e}")
        return False

def show_pending_migrations():
    """Show pending migrations."""
    print("\n🔍 Checking Pending Migrations")
    print("=" * 35)
    
    try:
        # This will show pending migrations
        execute_from_command_line(['manage.py', 'showmigrations', '--plan'])
        return True
    except Exception as e:
        print(f"❌ Error showing migrations: {e}")
        return False

def apply_migrations():
    """Apply pending migrations."""
    print("\n🔧 Applying Migrations")
    print("=" * 25)
    
    try:
        print("Applying m3u migrations...")
        execute_from_command_line(['manage.py', 'migrate', 'm3u'])
        
        print("Applying core migrations...")
        execute_from_command_line(['manage.py', 'migrate', 'core'])
        
        print("✅ Migrations applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        return False

def main():
    print("🔧 Migration Check Script")
    print("=" * 40)
    
    # Check current status
    if not check_migration_status():
        print("\n⚠️  Migrations not applied!")
        
        # Show pending migrations
        show_pending_migrations()
        
        # Ask to apply migrations
        response = input("\nApply migrations now? (y/n): ").lower().strip()
        if response == 'y':
            apply_migrations()
        else:
            print("Please run: python manage.py migrate")
    else:
        print("\n✅ All proxy migrations are applied!")

if __name__ == "__main__":
    main()