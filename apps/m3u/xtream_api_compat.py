"""
Xtream Codes API Compatibility Layer
Requirements: 25.1, 25.2, 25.3, 25.4
"""

import json
from typing import Dict, List, Optional
from datetime import datetime


class XtreamAPICompat:
    """
    Provides Xtream Codes API compatible endpoints.
    Translates Stalker Portal data to Xtream format.
    """
    
    def __init__(self, portal_client):
        self.portal_client = portal_client
    
    def get_user_info(self) -> Dict:
        """
        Get user info in Xtream format.
        Endpoint: player_api.php?action=get_user_info
        """
        profile = self.portal_client.get_profile()
        
        # Map Stalker profile to Xtream format
        exp_date = profile.get('expire_billing_date', profile.get('phone', ''))
        
        # Try to parse expiry date
        exp_timestamp = None
        if exp_date:
            try:
                if isinstance(exp_date, str):
                    dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    exp_timestamp = int(dt.timestamp())
            except Exception:
                pass
        
        return {
            'user_info': {
                'username': self.portal_client.mac,
                'password': '',
                'message': profile.get('msg', ''),
                'auth': 1 if profile.get('status', 0) == 0 else 0,
                'status': 'Active' if profile.get('status', 0) == 0 else 'Expired',
                'exp_date': exp_timestamp,
                'is_trial': '0',
                'active_cons': str(profile.get('active_cons', 0)),
                'created_at': '',
                'max_connections': str(profile.get('max_connections', 1)),
                'allowed_output_formats': ['m3u8', 'ts'],
            },
            'server_info': {
                'url': self.portal_client.portal_url,
                'port': '80',
                'https_port': '443',
                'server_protocol': 'http',
                'rtmp_port': '',
                'timezone': profile.get('timezone', 'UTC'),
                'timestamp_now': int(datetime.now().timestamp()),
                'time_now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        }
    
    def get_live_categories(self) -> List[Dict]:
        """
        Get live TV categories in Xtream format.
        Endpoint: player_api.php?action=get_live_categories
        """
        categories = self.portal_client.get_genres()
        
        return [
            {
                'category_id': str(cat.get('id', cat.get('genre_id', ''))),
                'category_name': cat.get('title', cat.get('name', '')),
                'parent_id': 0,
            }
            for cat in categories
        ]
    
    def get_vod_categories(self) -> List[Dict]:
        """
        Get VOD categories in Xtream format.
        Endpoint: player_api.php?action=get_vod_categories
        """
        categories = self.portal_client.get_vod_categories()
        
        return [
            {
                'category_id': str(cat.get('id', cat.get('category_id', ''))),
                'category_name': cat.get('title', cat.get('name', '')),
                'parent_id': 0,
            }
            for cat in categories
        ]
    
    def get_series_categories(self) -> List[Dict]:
        """
        Get series categories in Xtream format.
        Endpoint: player_api.php?action=get_series_categories
        """
        categories = self.portal_client.get_series_categories()
        
        return [
            {
                'category_id': str(cat.get('id', cat.get('category_id', ''))),
                'category_name': cat.get('title', cat.get('name', '')),
                'parent_id': 0,
            }
            for cat in categories
        ]
    
    def get_live_streams(self, category_id: str = None) -> List[Dict]:
        """
        Get live streams in Xtream format.
        Endpoint: player_api.php?action=get_live_streams
        """
        channels = self.portal_client.get_channels(genre_id=category_id)
        
        return [
            {
                'num': idx + 1,
                'name': ch.get('name', ''),
                'stream_type': 'live',
                'stream_id': str(ch.get('id', ch.get('cmd', ''))),
                'stream_icon': ch.get('logo', ch.get('icon', '')),
                'epg_channel_id': ch.get('epg_id', ''),
                'added': ch.get('added', ''),
                'category_id': str(ch.get('genre_id', category_id or '')),
                'custom_sid': '',
                'tv_archive': ch.get('archive', 0),
                'direct_source': '',
                'tv_archive_duration': ch.get('archive_duration', 0),
            }
            for idx, ch in enumerate(channels)
        ]
    
    def get_vod_streams(self, category_id: str = None) -> List[Dict]:
        """
        Get VOD streams in Xtream format.
        Endpoint: player_api.php?action=get_vod_streams
        """
        vod_items = self.portal_client.get_vod_items(category_id=category_id)
        
        return [
            {
                'num': idx + 1,
                'name': item.get('name', ''),
                'stream_type': 'movie',
                'stream_id': str(item.get('id', item.get('cmd', ''))),
                'stream_icon': item.get('cover', item.get('screenshot_uri', '')),
                'rating': item.get('rating', ''),
                'rating_5based': float(item.get('rating', 0)) / 2 if item.get('rating') else 0,
                'added': item.get('added', ''),
                'category_id': str(item.get('category_id', category_id or '')),
                'container_extension': 'mp4',
                'custom_sid': '',
                'direct_source': '',
            }
            for idx, item in enumerate(vod_items.get('data', []))
        ]
    
    def get_series(self, category_id: str = None) -> List[Dict]:
        """
        Get series in Xtream format.
        Endpoint: player_api.php?action=get_series
        """
        series_items = self.portal_client.get_series_items(category_id=category_id)
        
        return [
            {
                'num': idx + 1,
                'name': item.get('name', ''),
                'series_id': str(item.get('id', item.get('series_id', ''))),
                'cover': item.get('cover', item.get('screenshot_uri', '')),
                'plot': item.get('description', ''),
                'cast': item.get('actors', ''),
                'director': item.get('director', ''),
                'genre': item.get('genre', ''),
                'releaseDate': item.get('year', ''),
                'last_modified': item.get('last_modified', ''),
                'rating': item.get('rating', ''),
                'rating_5based': float(item.get('rating', 0)) / 2 if item.get('rating') else 0,
                'backdrop_path': [],
                'youtube_trailer': item.get('trailer', ''),
                'episode_run_time': '',
                'category_id': str(item.get('category_id', category_id or '')),
            }
            for idx, item in enumerate(series_items.get('data', []))
        ]
    
    def get_series_info(self, series_id: str) -> Dict:
        """
        Get series info with seasons and episodes.
        Endpoint: player_api.php?action=get_series_info&series_id=X
        """
        series_info = self.portal_client.get_series_info(series_id)
        
        # Build episodes dict by season
        episodes = {}
        for ep in series_info.get('episodes', []):
            season = str(ep.get('season', ep.get('season_number', 1)))
            if season not in episodes:
                episodes[season] = []
            
            episodes[season].append({
                'id': str(ep.get('id', ep.get('episode_id', ''))),
                'episode_num': ep.get('episode_number', ep.get('episode_num', 0)),
                'title': ep.get('name', ep.get('title', '')),
                'container_extension': 'mp4',
                'info': {
                    'plot': ep.get('plot', ep.get('description', '')),
                    'duration_secs': ep.get('duration', 0),
                    'duration': ep.get('duration_str', ''),
                    'movie_image': ep.get('cover', ''),
                    'releasedate': ep.get('air_date', ''),
                },
                'custom_sid': '',
                'added': ep.get('added', ''),
                'season': int(season),
                'direct_source': '',
            })
        
        return {
            'seasons': [
                {'season_number': int(s), 'name': f'Season {s}'}
                for s in sorted(episodes.keys(), key=int)
            ],
            'info': {
                'name': series_info.get('name', ''),
                'cover': series_info.get('cover', ''),
                'plot': series_info.get('description', ''),
                'cast': series_info.get('actors', ''),
                'director': series_info.get('director', ''),
                'genre': series_info.get('genre', ''),
                'releaseDate': series_info.get('year', ''),
                'rating': series_info.get('rating', ''),
                'youtube_trailer': series_info.get('trailer', ''),
            },
            'episodes': episodes,
        }
    
    def get_vod_info(self, vod_id: str) -> Dict:
        """
        Get VOD info.
        Endpoint: player_api.php?action=get_vod_info&vod_id=X
        """
        vod_info = self.portal_client.get_vod_info(vod_id)
        
        return {
            'info': {
                'movie_image': vod_info.get('cover', vod_info.get('screenshot_uri', '')),
                'tmdb_id': vod_info.get('tmdb_id', ''),
                'name': vod_info.get('name', ''),
                'o_name': vod_info.get('original_name', vod_info.get('name', '')),
                'cover_big': vod_info.get('cover', ''),
                'releasedate': vod_info.get('year', ''),
                'episode_run_time': vod_info.get('duration', ''),
                'youtube_trailer': vod_info.get('trailer', ''),
                'director': vod_info.get('director', ''),
                'actors': vod_info.get('actors', vod_info.get('cast', '')),
                'cast': vod_info.get('cast', ''),
                'description': vod_info.get('description', ''),
                'plot': vod_info.get('description', ''),
                'age': vod_info.get('age', ''),
                'country': vod_info.get('country', ''),
                'genre': vod_info.get('genre', ''),
                'duration_secs': vod_info.get('duration_seconds', 0),
                'duration': vod_info.get('duration', ''),
                'rating': vod_info.get('rating', ''),
            },
            'movie_data': {
                'stream_id': str(vod_id),
                'name': vod_info.get('name', ''),
                'added': vod_info.get('added', ''),
                'category_id': str(vod_info.get('category_id', '')),
                'container_extension': 'mp4',
                'custom_sid': '',
                'direct_source': '',
            }
        }
    
    def get_short_epg(self, stream_id: str, limit: int = 4) -> Dict:
        """
        Get short EPG for a stream.
        Endpoint: player_api.php?action=get_short_epg&stream_id=X
        """
        epg_data = self.portal_client.get_short_epg(stream_id)
        
        return {
            'epg_listings': [
                {
                    'id': str(ep.get('id', '')),
                    'epg_id': str(stream_id),
                    'title': ep.get('name', ep.get('title', '')),
                    'lang': '',
                    'start': ep.get('start', ep.get('time', '')),
                    'end': ep.get('stop', ep.get('time_to', '')),
                    'description': ep.get('descr', ep.get('description', '')),
                    'channel_id': str(stream_id),
                    'start_timestamp': ep.get('start_timestamp', ''),
                    'stop_timestamp': ep.get('stop_timestamp', ''),
                    'now_playing': ep.get('now_playing', 0),
                    'has_archive': ep.get('has_archive', 0),
                }
                for ep in epg_data[:limit]
            ]
        }
    
    def generate_m3u_playlist(self, include_vod: bool = True, include_series: bool = True) -> str:
        """
        Generate M3U playlist in Xtream format.
        Endpoint: get.php?type=m3u_plus
        """
        lines = ['#EXTM3U']
        
        # Add live channels
        categories = self.get_live_categories()
        cat_map = {c['category_id']: c['category_name'] for c in categories}
        
        streams = self.get_live_streams()
        for stream in streams:
            cat_name = cat_map.get(stream['category_id'], 'Uncategorized')
            lines.append(
                f'#EXTINF:-1 tvg-id="{stream["epg_channel_id"]}" '
                f'tvg-name="{stream["name"]}" '
                f'tvg-logo="{stream["stream_icon"]}" '
                f'group-title="{cat_name}",{stream["name"]}'
            )
            # Generate stream URL
            stream_url = self.portal_client.create_link(stream['stream_id'])
            lines.append(stream_url)
        
        if include_vod:
            vod_categories = self.get_vod_categories()
            vod_cat_map = {c['category_id']: c['category_name'] for c in vod_categories}
            
            vod_streams = self.get_vod_streams()
            for vod in vod_streams:
                cat_name = vod_cat_map.get(vod['category_id'], 'VOD')
                lines.append(
                    f'#EXTINF:-1 tvg-name="{vod["name"]}" '
                    f'tvg-logo="{vod["stream_icon"]}" '
                    f'group-title="VOD: {cat_name}",{vod["name"]}'
                )
                vod_url = self.portal_client.get_vod_link(vod['stream_id'])
                lines.append(vod_url)
        
        return '\n'.join(lines)
