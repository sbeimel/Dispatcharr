# Generated manually for performance optimization
from django.db import migrations, connection


def add_indexes_if_not_exist(apps, schema_editor):
    """Add indexes only if they don't already exist."""
    with connection.cursor() as cursor:
        # Check and create m3u_mac_acc_status_idx
        cursor.execute("""
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'm3u_mac_acc_status_idx'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX "m3u_mac_acc_status_idx" 
                ON "m3u_m3uaccountmac" ("account_id", "status")
            """)
        
        # Check and create m3u_mac_acc_st_prio_idx
        cursor.execute("""
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'm3u_mac_acc_st_prio_idx'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX "m3u_mac_acc_st_prio_idx" 
                ON "m3u_m3uaccountmac" ("account_id", "status", "priority")
            """)
        
        # Check and create m3u_mac_acc_checked_idx
        cursor.execute("""
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'm3u_mac_acc_checked_idx'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX "m3u_mac_acc_checked_idx" 
                ON "m3u_m3uaccountmac" ("account_id", "last_checked")
            """)


def remove_indexes(apps, schema_editor):
    """Remove indexes (for rollback)."""
    with connection.cursor() as cursor:
        cursor.execute('DROP INDEX IF EXISTS "m3u_mac_acc_status_idx"')
        cursor.execute('DROP INDEX IF EXISTS "m3u_mac_acc_st_prio_idx"')
        cursor.execute('DROP INDEX IF EXISTS "m3u_mac_acc_checked_idx"')


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0041_remove_fastest_engine'),
    ]

    operations = [
        migrations.RunPython(add_indexes_if_not_exist, remove_indexes),
    ]
