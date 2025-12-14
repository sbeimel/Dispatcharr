"""
EPG and Metadata Client for MAC Portal.

This module provides:
- EPG download from MAC portals
- Short EPG for live channels
- EPG caching
- TMDB integration (optional)
- Extended VOD metadata
- Picon/Logo download and caching

Requirements: 5.1-5.3, 22.1-22.4, 33.1-33.4, 37.1-37.4, 38.1-38.4
"""

import logging
import hashlib
import os
from typing import Optional, Dict, Any, List
from django.core.cache import cache
from django.conf import settings

from .mac_portal_client_extended import ExtendedMacPortalClient

logger = logging.getLogger(__name__)


class EPGClient(ExtendedMacPortalClient):
    """
    Extended client with EPG functionality.
    
    Requirements: 5.1, 5.2, 5.3, 37.1-37.4
    """
    
    # EPG cache duration (hours)
    EPG_CACHE_HOURS = 6
    SHORT_EPG_CACHE_MINUTES = 30
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    # ============== EPG Download (8.1) ==============
    
    def get_epg_for_channel(self, channel_id: str, period: int = 7) -> List[Dict[str, Any]]:
        """
        Get EPG data for a specific channel.
        
        Requirements: 5.1, 5.2
        
        Args:
            channel_id: Channel ID
            period: Number of days to fetch
        
        Returns:
            List of EPG entries
        """
        cache_key = f"epg:{self.original_base_url}:{channel_id}:{period}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "itv",
            "action": "get_epg_info",
            "ch_id": channel_id,
            "period": str(period),
            "JsHttpRequest": "1-xml"
        }
        
        try:
            response = self._request_with_retry(
                "GET",
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                data = response.json()
                epg_data = data.get("js", {}).get("data", [])
                
                if epg_data:
                    cache.set(cache_key, epg_data, self.EPG_CACHE_HOURS * 3600)
                    logger.debug(f"Got {len(epg_data)} EPG entries for channel {channel_id}")
                    return epg_data
        except Exception as e:
            logger.error(f"Failed to get EPG for channel {channel_id}: {e}")
        
        return []
    
    def get_all_epg(self, period: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get EPG data for all channels.
        
        Requirements: 5.1
        
        Returns:
            Dict mapping channel_id to EPG entries
        """
        cache_key = f"epg_all:{self.original_base_url}:{period}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "itv",
            "action": "get_epg_info",
            "period": str(period),
            "JsHttpRequest": "1-xml"
        }
        
        try:
            response = self._request_with_retry(
                "GET",
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                data = response.json()
                epg_data = data.get("js", {}).get("data", {})
                
                if epg_data:
                    cache.set(cache_key, epg_data, self.EPG_CACHE_HOURS * 3600)
                    logger.info(f"Got EPG data for {len(epg_data)} channels")
                    return epg_data
        except Exception as e:
            logger.error(f"Failed to get all EPG: {e}")
        
        return {}
    
    # ============== Short EPG (8.2) ==============
    
    def get_short_epg(self, channel_id: str) -> Dict[str, Any]:
        """
        Get short EPG (current and next program) for a channel.
        
        Requirements: 37.1, 37.2, 37.3, 37.4
        
        Returns:
            Dict with 'current' and 'next' program info
        """
        cache_key = f"short_epg:{self.original_base_url}:{channel_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "itv",
            "action": "get_short_epg",
            "ch_id": channel_id,
            "JsHttpRequest": "1-xml"
        }
        
        try:
            response = self._request_with_retry(
                "GET",
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                data = response.json()
                epg_data = data.get("js", {})
                
                result = {
                    "current": None,
                    "next": None,
                    "channel_id": channel_id,
                }
                
                # Parse current and next programs
                if isinstance(epg_data, dict):
                    programs = epg_data.get("data", [])
                    if programs and len(programs) > 0:
                        result["current"] = self._parse_epg_entry(programs[0])
                    if programs and len(programs) > 1:
                        result["next"] = self._parse_epg_entry(programs[1])
                
                cache.set(cache_key, result, self.SHORT_EPG_CACHE_MINUTES * 60)
                return result
        except Exception as e:
            logger.debug(f"Failed to get short EPG for channel {channel_id}: {e}")
        
        return {"current": None, "next": None, "channel_id": channel_id}
    
    def _parse_epg_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse EPG entry into standardized format."""
        return {
            "title": entry.get("name", entry.get("title", "")),
            "description": entry.get("descr", entry.get("description", "")),
            "start": entry.get("time", entry.get("start", "")),
            "end": entry.get("time_to", entry.get("end", "")),
            "duration": entry.get("duration", 0),
            "category": entry.get("category", ""),
        }
    
    # ============== EPG Caching (8.3) ==============
    
    def clear_epg_cache(self, channel_id: str = None):
        """
        Clear EPG cache.
        
        Requirements: 5.3
        """
        if channel_id:
            cache.delete(f"epg:{self.original_base_url}:{channel_id}:*")
            cache.delete(f"short_epg:{self.original_base_url}:{channel_id}")
        else:
            # Clear all EPG cache for this portal
            cache.delete(f"epg_all:{self.original_base_url}:*")
        
        logger.debug(f"EPG cache cleared for {channel_id or 'all channels'}")



# ============== TMDB Integration (9.1) ==============

class TMDBClient:
    """
    TMDB API client for VOD metadata enrichment.
    
    Requirements: 33.1, 33.2, 33.3, 33.4
    """
    
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
    
    def __init__(self, api_key: str = None):
        """
        Initialize TMDB client.
        
        Args:
            api_key: TMDB API key (optional, uses settings if not provided)
        """
        self.api_key = api_key or getattr(settings, 'TMDB_API_KEY', None)
        self._enabled = bool(self.api_key)
    
    @property
    def is_enabled(self) -> bool:
        """Check if TMDB integration is enabled."""
        return self._enabled
    
    def search_movie(self, title: str, year: int = None) -> Optional[Dict[str, Any]]:
        """
        Search for a movie on TMDB.
        
        Requirements: 33.1, 33.2
        """
        if not self.is_enabled:
            return None
        
        import requests
        
        cache_key = f"tmdb_movie:{hashlib.md5(f'{title}:{year}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "en-US",
        }
        if year:
            params["year"] = year
        
        try:
            response = requests.get(
                f"{self.TMDB_API_BASE}/search/movie",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    movie = results[0]
                    result = self._format_movie_result(movie)
                    cache.set(cache_key, result, 86400)  # Cache 24 hours
                    return result
        except Exception as e:
            logger.debug(f"TMDB search failed for '{title}': {e}")
        
        return None
    
    def search_tv(self, title: str, year: int = None) -> Optional[Dict[str, Any]]:
        """
        Search for a TV show on TMDB.
        
        Requirements: 33.1, 33.2
        """
        if not self.is_enabled:
            return None
        
        import requests
        
        cache_key = f"tmdb_tv:{hashlib.md5(f'{title}:{year}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "en-US",
        }
        if year:
            params["first_air_date_year"] = year
        
        try:
            response = requests.get(
                f"{self.TMDB_API_BASE}/search/tv",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    show = results[0]
                    result = self._format_tv_result(show)
                    cache.set(cache_key, result, 86400)
                    return result
        except Exception as e:
            logger.debug(f"TMDB TV search failed for '{title}': {e}")
        
        return None
    
    def get_movie_details(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed movie information.
        
        Requirements: 33.3
        """
        if not self.is_enabled:
            return None
        
        import requests
        
        cache_key = f"tmdb_movie_detail:{tmdb_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            response = requests.get(
                f"{self.TMDB_API_BASE}/movie/{tmdb_id}",
                params={
                    "api_key": self.api_key,
                    "language": "en-US",
                    "append_to_response": "credits,videos"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                result = self._format_movie_details(data)
                cache.set(cache_key, result, 86400)
                return result
        except Exception as e:
            logger.debug(f"TMDB movie details failed for {tmdb_id}: {e}")
        
        return None
    
    def _format_movie_result(self, movie: Dict) -> Dict[str, Any]:
        """Format TMDB movie search result."""
        return {
            "tmdb_id": movie.get("id"),
            "title": movie.get("title"),
            "original_title": movie.get("original_title"),
            "overview": movie.get("overview"),
            "release_date": movie.get("release_date"),
            "vote_average": movie.get("vote_average"),
            "poster_path": self._get_image_url(movie.get("poster_path"), "w500"),
            "backdrop_path": self._get_image_url(movie.get("backdrop_path"), "w1280"),
            "genre_ids": movie.get("genre_ids", []),
        }
    
    def _format_tv_result(self, show: Dict) -> Dict[str, Any]:
        """Format TMDB TV search result."""
        return {
            "tmdb_id": show.get("id"),
            "name": show.get("name"),
            "original_name": show.get("original_name"),
            "overview": show.get("overview"),
            "first_air_date": show.get("first_air_date"),
            "vote_average": show.get("vote_average"),
            "poster_path": self._get_image_url(show.get("poster_path"), "w500"),
            "backdrop_path": self._get_image_url(show.get("backdrop_path"), "w1280"),
            "genre_ids": show.get("genre_ids", []),
        }
    
    def _format_movie_details(self, data: Dict) -> Dict[str, Any]:
        """Format detailed movie information."""
        result = self._format_movie_result(data)
        result.update({
            "runtime": data.get("runtime"),
            "genres": [g.get("name") for g in data.get("genres", [])],
            "production_companies": [c.get("name") for c in data.get("production_companies", [])],
            "budget": data.get("budget"),
            "revenue": data.get("revenue"),
            "tagline": data.get("tagline"),
            "imdb_id": data.get("imdb_id"),
        })
        
        # Add cast
        credits = data.get("credits", {})
        result["cast"] = [
            {"name": c.get("name"), "character": c.get("character")}
            for c in credits.get("cast", [])[:10]
        ]
        
        # Add trailer
        videos = data.get("videos", {}).get("results", [])
        trailers = [v for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"]
        if trailers:
            result["trailer_key"] = trailers[0].get("key")
        
        return result
    
    def _get_image_url(self, path: str, size: str = "original") -> Optional[str]:
        """Get full TMDB image URL."""
        if not path:
            return None
        return f"{self.TMDB_IMAGE_BASE}/{size}{path}"


# ============== Picon/Logo Manager (9.3) ==============

class PiconManager:
    """
    Manages channel logos/picons download and caching.
    
    Requirements: 22.1, 22.2, 22.3, 22.4
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize PiconManager.
        
        Args:
            cache_dir: Directory for caching logos
        """
        self.cache_dir = cache_dir or os.path.join(
            getattr(settings, 'MEDIA_ROOT', '/tmp'),
            'picons'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_logo_path(self, logo_url: str) -> Optional[str]:
        """
        Get local path for logo, downloading if needed.
        
        Requirements: 22.1, 22.2
        """
        if not logo_url:
            return None
        
        # Generate cache filename from URL hash
        url_hash = hashlib.md5(logo_url.encode()).hexdigest()
        ext = self._get_extension(logo_url)
        cache_path = os.path.join(self.cache_dir, f"{url_hash}{ext}")
        
        # Return cached if exists
        if os.path.exists(cache_path):
            return cache_path
        
        # Download logo
        try:
            return self._download_logo(logo_url, cache_path)
        except Exception as e:
            logger.debug(f"Failed to download logo {logo_url}: {e}")
            return None
    
    def _download_logo(self, url: str, cache_path: str) -> Optional[str]:
        """
        Download logo to cache.
        
        Requirements: 22.3
        """
        import requests
        
        try:
            response = requests.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                with open(cache_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.debug(f"Downloaded logo to {cache_path}")
                return cache_path
        except Exception as e:
            logger.debug(f"Logo download failed: {e}")
        
        return None
    
    def _get_extension(self, url: str) -> str:
        """Get file extension from URL."""
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        
        if path.endswith('.png'):
            return '.png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return '.jpg'
        elif path.endswith('.gif'):
            return '.gif'
        elif path.endswith('.webp'):
            return '.webp'
        else:
            return '.png'  # Default
    
    def clear_cache(self):
        """
        Clear logo cache.
        
        Requirements: 22.4
        """
        import shutil
        try:
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info("Picon cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear picon cache: {e}")
    
    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for root, dirs, files in os.walk(self.cache_dir):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total


# ============== Extended VOD Metadata (9.2) ==============

class VODMetadataEnricher:
    """
    Enriches VOD metadata with TMDB data.
    
    Requirements: 38.1, 38.2, 38.3, 38.4
    """
    
    def __init__(self, tmdb_client: TMDBClient = None):
        """
        Initialize metadata enricher.
        
        Args:
            tmdb_client: Optional TMDB client instance
        """
        self.tmdb = tmdb_client or TMDBClient()
    
    def enrich_vod_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich VOD item with TMDB metadata.
        
        Requirements: 38.1, 38.2
        """
        if not self.tmdb.is_enabled:
            return item
        
        title = item.get("name", item.get("title", ""))
        year = self._extract_year(item)
        
        # Search TMDB
        tmdb_data = self.tmdb.search_movie(title, year)
        
        if tmdb_data:
            item["tmdb"] = tmdb_data
            item["enriched"] = True
            
            # Update missing fields
            if not item.get("description") and tmdb_data.get("overview"):
                item["description"] = tmdb_data["overview"]
            if not item.get("poster") and tmdb_data.get("poster_path"):
                item["poster"] = tmdb_data["poster_path"]
            if not item.get("rating") and tmdb_data.get("vote_average"):
                item["rating"] = tmdb_data["vote_average"]
        
        return item
    
    def enrich_series_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich series item with TMDB metadata.
        
        Requirements: 38.3
        """
        if not self.tmdb.is_enabled:
            return item
        
        title = item.get("name", item.get("title", ""))
        year = self._extract_year(item)
        
        tmdb_data = self.tmdb.search_tv(title, year)
        
        if tmdb_data:
            item["tmdb"] = tmdb_data
            item["enriched"] = True
            
            if not item.get("description") and tmdb_data.get("overview"):
                item["description"] = tmdb_data["overview"]
            if not item.get("poster") and tmdb_data.get("poster_path"):
                item["poster"] = tmdb_data["poster_path"]
        
        return item
    
    def _extract_year(self, item: Dict[str, Any]) -> Optional[int]:
        """Extract year from item metadata."""
        # Try various year fields
        for field in ["year", "release_date", "date", "added"]:
            value = item.get(field)
            if value:
                try:
                    if isinstance(value, int):
                        return value
                    if isinstance(value, str):
                        # Try to extract 4-digit year
                        import re
                        match = re.search(r'(\d{4})', value)
                        if match:
                            return int(match.group(1))
                except Exception:
                    pass
        return None
