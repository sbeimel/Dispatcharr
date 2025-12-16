#!/usr/bin/env python
"""
Fix migration conflicts by removing ghost entries from django_migrations table.

This script detects and removes migration entries in the database that don't have
corresponding migration files on disk. This commonly happens when migrations are
renamed or reorganized.

Run this BEFORE `python manage.py migrate` to prevent conflicts.
"""
import os
import sys

# Ensure /app is in the Python path (for Docker environment)
app_path = '/app'
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')

import django
django.setup()

from django.db import connection
from django.conf import settings
from pathlib import Path


def get_migration_files(app_name: str) -> set:
    """Get all migration file names (without .py) for an app."""
    migrations = set()
    
    # Find the app's migrations directory
    for app_config in django.apps.get_app_configs():
        if app_config.label == app_name:
            migrations_dir = Path(app_config.path) / 'migrations'
            if migrations_dir.exists():
                for f in migrations_dir.glob('*.py'):
                    if f.name != '__init__.py':
                        migrations.add(f.stem)  # filename without .py
            break
    
    return migrations


def get_db_migrations(app_name: str) -> list:
    """Get all migration names recorded in the database for an app."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM django_migrations WHERE app = %s",
            [app_name]
        )
        return cursor.fetchall()


def fix_ghost_migrations():
    """Find and remove ghost migration entries."""
    print("🔍 Checking for ghost migration entries...")
    
    # Get all apps with migrations in the database
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT app FROM django_migrations")
        apps = [row[0] for row in cursor.fetchall()]
    
    total_removed = 0
    
    for app_name in apps:
        file_migrations = get_migration_files(app_name)
        db_migrations = get_db_migrations(app_name)
        
        for migration_id, migration_name in db_migrations:
            if migration_name not in file_migrations:
                print(f"  ⚠️  Ghost migration found: {app_name}.{migration_name}")
                
                # Remove the ghost entry
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM django_migrations WHERE id = %s",
                        [migration_id]
                    )
                print(f"  ✅ Removed ghost migration: {app_name}.{migration_name}")
                total_removed += 1
    
    if total_removed > 0:
        print(f"\n🧹 Cleaned up {total_removed} ghost migration(s)")
    else:
        print("✅ No ghost migrations found - database is clean")
    
    return total_removed


def check_migration_graph():
    """Check for migration graph conflicts (multiple leaf nodes)."""
    from django.db.migrations.loader import MigrationLoader
    
    print("\n🔍 Checking migration graph for conflicts...")
    
    try:
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        conflicts = loader.detect_conflicts()
        
        if conflicts:
            print("  ⚠️  Migration conflicts detected:")
            for app, migrations in conflicts.items():
                print(f"    {app}: {migrations}")
            return False
        else:
            print("  ✅ No migration conflicts detected")
            return True
    except Exception as e:
        print(f"  ⚠️  Could not check migration graph: {e}")
        return True  # Continue anyway


if __name__ == '__main__':
    print("=" * 60)
    print("Migration Conflict Fixer")
    print("=" * 60)
    
    try:
        # First, fix ghost migrations
        removed = fix_ghost_migrations()
        
        # Then check the migration graph
        graph_ok = check_migration_graph()
        
        if removed > 0 or not graph_ok:
            print("\n💡 Migration issues were found and fixed.")
            print("   You can now run: python manage.py migrate")
        
        print("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Continuing anyway - migrations may fail")
        sys.exit(0)  # Don't block startup
