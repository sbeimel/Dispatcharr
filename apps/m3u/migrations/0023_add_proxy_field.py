# Generated manually for proxy field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0022_m3uaccountmac'),
    ]

    operations = [
        # Use RunSQL to safely add proxy field if it doesn't exist
        migrations.RunSQL(
            sql="""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'm3u_m3uaccount' 
                        AND column_name = 'proxy'
                    ) THEN
                        ALTER TABLE m3u_m3uaccount 
                        ADD COLUMN proxy varchar(255);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                ALTER TABLE m3u_m3uaccount DROP COLUMN IF EXISTS proxy;
            """,
        ),
    ]