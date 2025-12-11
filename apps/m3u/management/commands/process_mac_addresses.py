"""
Management command to process existing MAC addresses in M3UAccount.mac_address field
and create corresponding M3UAccountMac objects.
"""

from django.core.management.base import BaseCommand
from apps.m3u.models import M3UAccount


class Command(BaseCommand):
    help = 'Process existing MAC addresses and create M3UAccountMac objects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=int,
            help='Process only specific account ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        dry_run = options.get('dry_run', False)
        
        if account_id:
            accounts = M3UAccount.objects.filter(id=account_id, account_type=M3UAccount.Types.MAC)
        else:
            accounts = M3UAccount.objects.filter(account_type=M3UAccount.Types.MAC)
        
        if not accounts.exists():
            self.stdout.write(self.style.WARNING('No MAC accounts found'))
            return
        
        processed = 0
        for account in accounts:
            if account.mac_address and not account.macs.exists():
                self.stdout.write(f'Processing account: {account.name} (ID: {account.id})')
                self.stdout.write(f'  MAC addresses: {account.mac_address}')
                
                if not dry_run:
                    # Trigger the MAC processing
                    account._process_mac_addresses()
                    
                    # Show results
                    mac_count = account.macs.count()
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created {mac_count} MAC objects')
                    )
                    
                    for mac in account.macs.all():
                        self.stdout.write(f'    - {mac.address} (priority: {mac.priority})')
                else:
                    self.stdout.write(self.style.WARNING('  [DRY RUN] Would process MAC addresses'))
                
                processed += 1
            elif account.macs.exists():
                self.stdout.write(f'Skipping account {account.name} - already has MAC objects')
        
        if processed > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Processed {processed} MAC accounts')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No accounts needed processing')
            )