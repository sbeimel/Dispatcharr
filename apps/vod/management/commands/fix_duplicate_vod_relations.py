"""
Django management command to fix duplicate M3UMovieRelation and M3USeriesRelation records.
Usage: python manage.py fix_duplicate_vod_relations
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import transaction
from apps.vod.models import M3UMovieRelation, M3USeriesRelation


class Command(BaseCommand):
    help = 'Fix duplicate VOD relation records with empty stream_id/external_series_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.fix_duplicate_movie_relations(dry_run)
        self.fix_duplicate_series_relations(dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETED - Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('Cleanup completed successfully!'))

    def fix_duplicate_movie_relations(self, dry_run=False):
        """Fix duplicate M3UMovieRelation records with empty stream_id"""
        self.stdout.write('Checking for duplicate M3UMovieRelation records...')
        
        # Find accounts with multiple empty stream_id records
        duplicates = (M3UMovieRelation.objects
                     .filter(stream_id='')
                     .values('m3u_account_id')
                     .annotate(count=Count('id'))
                     .filter(count__gt=1))
        
        self.stdout.write(f'Found {len(duplicates)} accounts with duplicate empty stream_id records')
        
        total_deleted = 0
        for duplicate in duplicates:
            account_id = duplicate['m3u_account_id']
            count = duplicate['count']
            self.stdout.write(f'Account {account_id} has {count} duplicate records')
            
            # Get all duplicate records for this account
            duplicate_records = M3UMovieRelation.objects.filter(
                m3u_account_id=account_id,
                stream_id=''
            ).order_by('created_at')
            
            # Keep the first record, delete the rest
            records_to_delete = duplicate_records[1:]
            
            if not dry_run:
                with transaction.atomic():
                    for record in records_to_delete:
                        self.stdout.write(f'  Deleting duplicate record: {record.id} - {record.movie.name}')
                        record.delete()
            else:
                for record in records_to_delete:
                    self.stdout.write(f'  Would delete: {record.id} - {record.movie.name}')
            
            total_deleted += len(records_to_delete)
            self.stdout.write(f'  {"Would clean up" if dry_run else "Cleaned up"} {len(records_to_delete)} duplicate records for account {account_id}')
        
        self.stdout.write(f'Total movie relations {"that would be" if dry_run else ""} deleted: {total_deleted}')

    def fix_duplicate_series_relations(self, dry_run=False):
        """Fix duplicate M3USeriesRelation records with empty external_series_id"""
        self.stdout.write('\nChecking for duplicate M3USeriesRelation records...')
        
        # Find accounts with multiple empty external_series_id records
        duplicates = (M3USeriesRelation.objects
                     .filter(external_series_id='')
                     .values('m3u_account_id')
                     .annotate(count=Count('id'))
                     .filter(count__gt=1))
        
        self.stdout.write(f'Found {len(duplicates)} accounts with duplicate empty external_series_id records')
        
        total_deleted = 0
        for duplicate in duplicates:
            account_id = duplicate['m3u_account_id']
            count = duplicate['count']
            self.stdout.write(f'Account {account_id} has {count} duplicate series records')
            
            # Get all duplicate records for this account
            duplicate_records = M3USeriesRelation.objects.filter(
                m3u_account_id=account_id,
                external_series_id=''
            ).order_by('created_at')
            
            # Keep the first record, delete the rest
            records_to_delete = duplicate_records[1:]
            
            if not dry_run:
                with transaction.atomic():
                    for record in records_to_delete:
                        self.stdout.write(f'  Deleting duplicate series record: {record.id} - {record.series.name}')
                        record.delete()
            else:
                for record in records_to_delete:
                    self.stdout.write(f'  Would delete: {record.id} - {record.series.name}')
            
            total_deleted += len(records_to_delete)
            self.stdout.write(f'  {"Would clean up" if dry_run else "Cleaned up"} {len(records_to_delete)} duplicate series records for account {account_id}')
        
        self.stdout.write(f'Total series relations {"that would be" if dry_run else ""} deleted: {total_deleted}')