# Generated manually to convert STD values to Standard

from django.db import migrations


def convert_std_to_standard(apps, schema_editor):
    """Convert any STD account_type values to Standard"""
    M3UAccount = apps.get_model('m3u', 'M3UAccount')
    
    # Convert STD to Standard
    updated_count = M3UAccount.objects.filter(account_type='STD').update(account_type='Standard')
    
    if updated_count > 0:
        print(f"Converted {updated_count} M3U account(s) from 'STD' to 'Standard'")
    else:
        print("No M3U accounts needed conversion from 'STD' to 'Standard'")


def reverse_convert_std_to_standard(apps, schema_editor):
    """Reverse operation - convert Standard back to STD"""
    M3UAccount = apps.get_model('m3u', 'M3UAccount')
    
    # Convert Standard back to STD
    updated_count = M3UAccount.objects.filter(account_type='Standard').update(account_type='STD')
    
    if updated_count > 0:
        print(f"Reverted {updated_count} M3U account(s) from 'Standard' to 'STD'")


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0023_add_proxy_field'),
    ]

    operations = [
        migrations.RunPython(
            convert_std_to_standard,
            reverse_convert_std_to_standard,
        ),
    ]