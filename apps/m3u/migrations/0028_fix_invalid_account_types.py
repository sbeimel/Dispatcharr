# Migration to fix any remaining invalid account_type values
# This is a more comprehensive fix that catches all edge cases

from django.db import migrations


def fix_invalid_account_types(apps, schema_editor):
    """
    Fix any account_type values that are not in the valid set ['STD', 'XC', 'MAC'].
    
    This migration catches:
    - Any value not in ['STD', 'XC', 'MAC']
    - Empty strings
    - NULL values
    - Whitespace-only values
    - Case variations (e.g., 'std', 'Xc', 'mac')
    """
    M3UAccount = apps.get_model('m3u', 'M3UAccount')
    
    valid_types = {'STD', 'XC', 'MAC'}
    
    # Get all accounts
    all_accounts = M3UAccount.objects.all()
    accounts_to_fix = []
    
    for account in all_accounts:
        current_type = account.account_type
        
        # Check if the value needs fixing
        needs_fix = False
        
        if current_type is None:
            needs_fix = True
        elif not isinstance(current_type, str):
            needs_fix = True
        elif current_type.strip() == '':
            needs_fix = True
        elif current_type not in valid_types:
            # Check if it's a case variation
            upper_type = current_type.upper().strip()
            if upper_type in valid_types:
                account.account_type = upper_type
                accounts_to_fix.append(account)
                print(f"  Account {account.id} ({account.name}): '{current_type}' -> '{upper_type}' (case fix)")
                continue
            else:
                needs_fix = True
        
        if needs_fix:
            account.account_type = 'STD'
            accounts_to_fix.append(account)
            print(f"  Account {account.id} ({account.name}): '{current_type}' -> 'STD' (invalid value)")
    
    # Bulk update
    if accounts_to_fix:
        M3UAccount.objects.bulk_update(accounts_to_fix, ['account_type'])
        print(f"  Fixed {len(accounts_to_fix)} accounts with invalid account_type values")
    else:
        print("  No accounts needed fixing")


def reverse_migration(apps, schema_editor):
    """
    Reverse is a no-op since we don't know what the original values were.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0027_convert_legacy_account_types'),
    ]

    operations = [
        migrations.RunPython(
            fix_invalid_account_types,
            reverse_migration,
            elidable=True,
        ),
    ]
