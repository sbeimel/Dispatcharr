# Generated migration for HTTP Proxy API control
# Adds proxy_for_api boolean field to M3UAccount model
# Date: 2026-06-18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0020_m3uaccount_proxy'),
    ]

    operations = [
        # Use RunSQL for idempotent migration (safe to run multiple times)
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'm3u_m3uaccount' AND column_name = 'proxy_for_api'
                ) THEN
                    ALTER TABLE m3u_m3uaccount ADD COLUMN proxy_for_api BOOLEAN DEFAULT FALSE;
                END IF;
            END
            $$;
            """,
            reverse_sql="ALTER TABLE m3u_m3uaccount DROP COLUMN IF EXISTS proxy_for_api;",
        ),
    ]
