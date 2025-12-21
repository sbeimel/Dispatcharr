"""
Migration for Extended Features Models (Phase 15)
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0024_mac_portal_improvements'),
    ]

    operations = [
        # MACFavorite Model
        migrations.CreateModel(
            name='MACFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.CharField(help_text='Item ID from portal', max_length=50)),
                ('item_type', models.CharField(choices=[('channel', 'Channel'), ('vod', 'VOD'), ('series', 'Series')], default='channel', help_text='Type of favorite item', max_length=20)),
                ('added_at', models.DateTimeField(auto_now_add=True, help_text='When this item was added to favorites')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this favorite belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'MAC Favorite',
                'verbose_name_plural': 'MAC Favorites',
                'ordering': ['-added_at'],
                'unique_together': {('m3u_account', 'item_id', 'item_type')},
            },
        ),
        
        # MACRecentlyWatched Model
        migrations.CreateModel(
            name='MACRecentlyWatched',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.CharField(help_text='Item ID from portal', max_length=50)),
                ('item_type', models.CharField(choices=[('channel', 'Channel'), ('vod', 'VOD'), ('series_episode', 'Series Episode')], default='channel', help_text='Type of watched item', max_length=20)),
                ('watched_at', models.DateTimeField(auto_now=True, help_text='When this item was last watched')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this entry belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='recently_watched', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Recently Watched',
                'verbose_name_plural': 'Recently Watched',
                'ordering': ['-watched_at'],
                'unique_together': {('m3u_account', 'item_id', 'item_type')},
            },
        ),
        
        # MACHiddenCategory Model
        migrations.CreateModel(
            name='MACHiddenCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_id', models.CharField(help_text='Category ID from portal', max_length=50)),
                ('hidden_at', models.DateTimeField(auto_now_add=True, help_text='When this category was hidden')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this hidden category belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='hidden_categories', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Hidden Category',
                'verbose_name_plural': 'Hidden Categories',
                'unique_together': {('m3u_account', 'category_id')},
            },
        ),
        
        # MACPlaylistSettings Model
        migrations.CreateModel(
            name='MACPlaylistSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stream_type', models.CharField(choices=[('iptv', 'IPTV'), ('dvb', 'DVB'), ('gstreamer', 'GStreamer'), ('exteplayer', 'ExtePlayer')], default='iptv', help_text='Preferred stream type', max_length=20)),
                ('show_adult_content', models.BooleanField(default=False, help_text='Show adult content categories')),
                ('country_filter', models.CharField(blank=True, help_text='Country code filter for genres', max_length=10)),
                ('excluded_keywords', models.JSONField(default=list, help_text='Keywords to exclude from categories')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account these settings belong to', on_delete=django.db.models.deletion.CASCADE, related_name='playlist_settings', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Playlist Settings',
                'verbose_name_plural': 'Playlist Settings',
            },
        ),
        
        # MACDebugLog Model
        migrations.CreateModel(
            name='MACDebugLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_address', models.CharField(blank=True, help_text='MAC address if applicable', max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True, help_text='When this log was created')),
                ('level', models.CharField(choices=[('DEBUG', 'Debug'), ('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')], default='INFO', help_text='Log level', max_length=10)),
                ('message', models.TextField(help_text='Log message')),
                ('context', models.JSONField(blank=True, default=dict, help_text='Additional context data')),
                ('m3u_account', models.ForeignKey(blank=True, help_text='The M3U account this log belongs to', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='debug_logs', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Debug Log',
                'verbose_name_plural': 'Debug Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='macdebuglog',
            index=models.Index(fields=['m3u_account', 'timestamp'], name='m3u_macdebuglog_account_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='macdebuglog',
            index=models.Index(fields=['level', 'timestamp'], name='m3u_macdebuglog_level_ts_idx'),
        ),
        
        # SeriesEpisodeTracking Model
        migrations.CreateModel(
            name='SeriesEpisodeTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('series_id', models.CharField(help_text='Series ID from portal', max_length=50)),
                ('season_number', models.IntegerField(help_text='Season number')),
                ('episode_id', models.CharField(help_text='Episode ID from portal', max_length=50)),
                ('episode_number', models.IntegerField(blank=True, help_text='Episode number', null=True)),
                ('watched', models.BooleanField(default=False, help_text='Whether episode has been watched')),
                ('watched_at', models.DateTimeField(blank=True, help_text='When episode was watched', null=True)),
                ('resume_position', models.IntegerField(default=0, help_text='Resume position in seconds')),
                ('m3u_account', models.ForeignKey(help_text='The M3U account this tracking belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='episode_tracking', to='m3u.m3uaccount')),
            ],
            options={
                'verbose_name': 'Episode Tracking',
                'verbose_name_plural': 'Episode Tracking',
                'ordering': ['series_id', 'season_number', 'episode_number'],
                'unique_together': {('m3u_account', 'series_id', 'season_number', 'episode_id')},
            },
        ),
        
        # Add parental_pin to MACPortalGlobalSettings
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='parental_pin',
            field=models.CharField(blank=True, default='', help_text='PIN for parental control', max_length=10),
        ),
    ]
