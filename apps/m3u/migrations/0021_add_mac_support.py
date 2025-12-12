# Generated manually for MAC support integration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0018_add_profile_custom_properties'),  # Correct latest migration
    ]

    operations = [
        # Add MAC account type to existing Types choices
        migrations.AlterField(
            model_name='m3uaccount',
            name='account_type',
            field=models.CharField(
                choices=[
                    ('Standard', 'Standard'),
                    ('XC', 'Xtream Codes'),
                    ('MAC', 'MAC/STB Portal'),
                ],
                default='Standard',
                max_length=20,
            ),
        ),
        
        # Use RunSQL to safely add mac_address field if it doesn't exist
        migrations.RunSQL(
            sql="""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'm3u_m3uaccount' 
                        AND column_name = 'mac_address'
                    ) THEN
                        ALTER TABLE m3u_m3uaccount 
                        ADD COLUMN mac_address varchar(255);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                ALTER TABLE m3u_m3uaccount DROP COLUMN IF EXISTS mac_address;
            """,
        ),
    ]