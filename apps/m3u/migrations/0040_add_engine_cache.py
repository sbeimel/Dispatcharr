# Generated migration for engine cache field

from django.db import migrations, models


def add_engine_cache_if_not_exists(apps, schema_editor):
    """Add engine_cache column only if it doesn't exist."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'm3u_macportalglobalsettings' AND column_name = 'engine_cache'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE m3u_macportalglobalsettings 
                ADD COLUMN engine_cache jsonb DEFAULT '{}'::jsonb NOT NULL
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0039_add_always_clear_buffer_setting'),
    ]

    operations = [
        migrations.RunPython(add_engine_cache_if_not_exists, migrations.RunPython.noop),
    ]
