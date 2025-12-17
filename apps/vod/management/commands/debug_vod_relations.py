"""
Django management command to debug VOD relations and their custom_properties.
Usage: python manage.py debug_vod_relations
"""

from django.core.management.base import BaseCommand
from apps.vod.models import M3UMovieRelation, M3USeriesRelation


class Command(BaseCommand):
    help = 'Debug VOD relation records and their custom_properties'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of records to show',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS('=== VOD Relations Debug ==='))
        
        # Debug Movie Relations
        self.stdout.write('\n=== M3UMovieRelation Records ===')
        movie_relations = M3UMovieRelation.objects.select_related(
            'movie', 'm3u_account'
        ).order_by('-created_at')[:limit]
        
        for relation in movie_relations:
            self.stdout.write(f'\nMovie: {relation.movie.name}')
            self.stdout.write(f'Account: {relation.m3u_account.name} ({relation.m3u_account.account_type})')
            self.stdout.write(f'Stream ID: {relation.stream_id}')
            self.stdout.write(f'Custom Properties: {relation.custom_properties}')
            
            # Check if cmd exists
            if relation.custom_properties:
                cmd = relation.custom_properties.get('cmd')
                self.stdout.write(f'CMD: {cmd}')
                if cmd:
                    self.stdout.write(self.style.SUCCESS('✅ CMD found'))
                else:
                    self.stdout.write(self.style.ERROR('❌ CMD missing'))
            else:
                self.stdout.write(self.style.ERROR('❌ No custom_properties'))
        
        # Debug Series Relations
        self.stdout.write('\n=== M3USeriesRelation Records ===')
        series_relations = M3USeriesRelation.objects.select_related(
            'series', 'm3u_account'
        ).order_by('-created_at')[:limit]
        
        for relation in series_relations:
            self.stdout.write(f'\nSeries: {relation.series.name}')
            self.stdout.write(f'Account: {relation.m3u_account.name} ({relation.m3u_account.account_type})')
            self.stdout.write(f'External Series ID: {relation.external_series_id}')
            self.stdout.write(f'Custom Properties: {relation.custom_properties}')
            
            # Check if cmd exists
            if relation.custom_properties:
                cmd = relation.custom_properties.get('cmd')
                self.stdout.write(f'CMD: {cmd}')
                if cmd:
                    self.stdout.write(self.style.SUCCESS('✅ CMD found'))
                else:
                    self.stdout.write(self.style.ERROR('❌ CMD missing'))
            else:
                self.stdout.write(self.style.ERROR('❌ No custom_properties'))
        
        # Summary
        total_movies = M3UMovieRelation.objects.count()
        total_series = M3USeriesRelation.objects.count()
        
        movies_with_cmd = M3UMovieRelation.objects.filter(
            custom_properties__cmd__isnull=False
        ).exclude(custom_properties__cmd='').count()
        
        series_with_cmd = M3USeriesRelation.objects.filter(
            custom_properties__cmd__isnull=False
        ).exclude(custom_properties__cmd='').count()
        
        self.stdout.write(f'\n=== Summary ===')
        self.stdout.write(f'Total Movie Relations: {total_movies}')
        self.stdout.write(f'Movies with CMD: {movies_with_cmd}')
        self.stdout.write(f'Total Series Relations: {total_series}')
        self.stdout.write(f'Series with CMD: {series_with_cmd}')
        
        if movies_with_cmd == 0 and total_movies > 0:
            self.stdout.write(self.style.ERROR('⚠️  No movie relations have CMD - VOD playback will fail!'))
        
        if series_with_cmd == 0 and total_series > 0:
            self.stdout.write(self.style.ERROR('⚠️  No series relations have CMD - Series playback will fail!'))