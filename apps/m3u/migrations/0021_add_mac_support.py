# Generated manually for MAC support integration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0020_alter_m3uaccount_mac_address'),  # Adjust to your latest migration
    ]

    operations = [
        # Add MAC account type to existing Types choices
        migrations.AlterField(
            model_name='m3uaccount',
            name='account_type',
            field=models.CharField(
                choices=[
                    ('STD', 'Standard'),
                    ('XC', 'Xtream Codes'),
                    ('MAC', 'MAC/STB Portal'),
                ],
                default='STD',
                max_length=3,
            ),
        ),
        
        # Add mac_address field if it doesn't exist
        migrations.AddField(
            model_name='m3uaccount',
            name='mac_address',
            field=models.CharField(
                blank=True,
                help_text='MAC address(es) for STB/MAC portal accounts. Multiple MACs can be separated by spaces or commas.',
                max_length=255,
                null=True,
            ),
        ),
    ]