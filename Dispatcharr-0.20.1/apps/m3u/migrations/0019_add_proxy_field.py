# Generated migration for proxy field
# This migration checks if the column exists before adding it
# Safe for both fresh installations and updates

from django.db import migrations, models


def add_proxy_field_safe(apps, schema_editor):
    """
    Add proxy field only if it doesn't exist yet.
    This allows the migration to work on both:
    - Fresh installations (column doesn't exist)
    - Updates from older versions (column might already exist)
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if column exists in m3u_m3uaccount table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
              AND table_name = 'm3u_m3uaccount' 
              AND column_name = 'proxy'
        """)
        
        column_exists = cursor.fetchone() is not None
        
        if not column_exists:
            # Column doesn't exist, add it
            cursor.execute("""
                ALTER TABLE m3u_m3uaccount 
                ADD COLUMN proxy varchar(500) NULL
            """)
            print("✅ Added 'proxy' column to m3u_m3uaccount table")
        else:
            print("ℹ️  'proxy' column already exists in m3u_m3uaccount table, skipping")


def remove_proxy_field(apps, schema_editor):
    """
    Remove proxy field on rollback.
    Only removes if it exists.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE m3u_m3uaccount 
            DROP COLUMN IF EXISTS proxy
        """)
        print("✅ Removed 'proxy' column from m3u_m3uaccount table")


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0018_add_profile_custom_properties'),
    ]

    operations = [
        migrations.RunPython(
            add_proxy_field_safe, 
            remove_proxy_field,
            elidable=True  # Can be optimized away if squashing migrations
        ),
    ]
