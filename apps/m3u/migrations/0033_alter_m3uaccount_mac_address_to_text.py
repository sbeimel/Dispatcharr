# Migration to ensure mac_address field exists and is TextField
# This allows storing many MAC addresses without length limit

from django.db import migrations, models


def ensure_mac_address_field(apps, schema_editor):
    """Ensure mac_address field exists before altering it."""
    from django.db import connection
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'm3u_m3uaccount' AND column_name = 'mac_address'
        """)
        if not cursor.fetchone():
            # Column doesn't exist, create it as TEXT
            cursor.execute("""
                ALTER TABLE m3u_m3uaccount ADD COLUMN mac_address TEXT NULL
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0032_fix_health_scores_for_bad_macs'),
    ]

    operations = [
        # First ensure the field exists
        migrations.RunPython(ensure_mac_address_field, migrations.RunPython.noop),
        # Then alter it to match the model definition
        migrations.RunSQL(
            sql="""
                ALTER TABLE m3u_m3uaccount 
                ALTER COLUMN mac_address TYPE TEXT;
            """,
            reverse_sql="""
                ALTER TABLE m3u_m3uaccount 
                ALTER COLUMN mac_address TYPE VARCHAR(255);
            """,
        ),
    ]
