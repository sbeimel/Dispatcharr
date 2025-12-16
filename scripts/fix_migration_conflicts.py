#!/usr/bin/env python
"""
Fix migration conflicts by removing ghost entries from django_migrations table.

This script detects and removes migration entries in the database that don't have
corresponding migration files on disk. This commonly happens when migrations are
renamed or reorganized.

Run this BEFORE `python manage.py migrate` to prevent conflicts.

NOTE: This script does NOT use Django to avoid Redis/cache dependencies.
It connects directly to PostgreSQL.
"""
import os
import sys
from pathlib import Path

# Get database connection info from environment
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'dispatcharr')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'dispatch')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'secret')

# App directory (in Docker container)
APP_DIR = Path('/app')


def get_migration_files_for_app(app_path: Path) -> set:
    """Get all migration file names (without .py) for an app."""
    migrations = set()
    migrations_dir = app_path / 'migrations'
    
    if migrations_dir.exists():
        for f in migrations_dir.glob('*.py'):
            if f.name != '__init__.py':
                migrations.add(f.stem)
    
    return migrations


def find_all_app_migrations() -> dict:
    """Find all migration files for all Django apps."""
    app_migrations = {}
    
    # Check apps directory
    apps_dir = APP_DIR / 'apps'
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                migrations = get_migration_files_for_app(app_dir)
                if migrations:
                    app_migrations[app_dir.name] = migrations
    
    # Check core directory
    core_dir = APP_DIR / 'core'
    if core_dir.exists():
        migrations = get_migration_files_for_app(core_dir)
        if migrations:
            app_migrations['core'] = migrations
    
    # Check plugins directory
    plugins_dir = APP_DIR / 'plugins'
    if plugins_dir.exists():
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                migrations = get_migration_files_for_app(plugin_dir)
                if migrations:
                    app_migrations[plugin_dir.name] = migrations
    
    return app_migrations


def fix_ghost_migrations():
    """Find and remove ghost migration entries using direct PostgreSQL connection."""
    try:
        import psycopg2
    except ImportError:
        print("⚠️  psycopg2 not available, trying psycopg2-binary...")
        try:
            import psycopg2
        except ImportError:
            print("❌ psycopg2 not installed - skipping migration fix")
            return 0
    
    print("🔍 Checking for ghost migration entries...")
    
    # Get all migration files from disk
    app_migrations = find_all_app_migrations()
    print(f"   Found migrations for apps: {list(app_migrations.keys())}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if django_migrations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'django_migrations'
            )
        """)
        if not cursor.fetchone()[0]:
            print("   ℹ️  django_migrations table doesn't exist yet - fresh install")
            conn.close()
            return 0
        
        # Get all migrations from database
        cursor.execute("SELECT id, app, name FROM django_migrations")
        db_migrations = cursor.fetchall()
        
        total_removed = 0
        
        for migration_id, app_name, migration_name in db_migrations:
            # Check if this app has migrations on disk
            if app_name in app_migrations:
                # Check if this specific migration exists on disk
                if migration_name not in app_migrations[app_name]:
                    print(f"  ⚠️  Ghost migration found: {app_name}.{migration_name}")
                    cursor.execute(
                        "DELETE FROM django_migrations WHERE id = %s",
                        (migration_id,)
                    )
                    print(f"  ✅ Removed ghost migration: {app_name}.{migration_name}")
                    total_removed += 1
            # If app not found on disk but has DB entries, it might be a third-party app
            # Don't remove those
        
        conn.close()
        
        if total_removed > 0:
            print(f"\n🧹 Cleaned up {total_removed} ghost migration(s)")
        else:
            print("✅ No ghost migrations found - database is clean")
        
        return total_removed
        
    except psycopg2.OperationalError as e:
        print(f"⚠️  Could not connect to database: {e}")
        print("   Continuing anyway - migrations may fail")
        return 0
    except Exception as e:
        print(f"⚠️  Error checking migrations: {e}")
        print("   Continuing anyway - migrations may fail")
        return 0


if __name__ == '__main__':
    print("=" * 60)
    print("Migration Conflict Fixer (Direct DB Access)")
    print("=" * 60)
    
    removed = fix_ghost_migrations()
    
    if removed > 0:
        print("\n💡 Migration issues were found and fixed.")
    
    print("=" * 60)
    sys.exit(0)
