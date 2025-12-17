"""
VOD and Series Client for MAC Portal.

This module provides VOD and Series functionality:
- VOD categories and items retrieval
- Series categories, items, and episodes
- VOD/Series search
- Resume points and watched status
- Efficient import strategy (single MAC for VOD scan)

Requirements: 4.1-4.5, 13.1-13.4, 28.1-28.4, 31.1-31.4, 32.1-32.4, 39.1-39.4, 40.1-40.4, 91.1-91.5, 92.1-92.4
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from django.core.cache import cache

from .mac_portal_client_extended import ExtendedMacPortalClient, MacPortalError

logger = logging.getLogger(__name__)


class VODSeriesClient(ExtendedMacPortalClient):
    """
    Extended client with VOD and Series support.
    
    Requirements: 4.1-4.5, 13.1-13.4, 91.1-91.5, 92.1-92.4
    """
    
    # Pagination defaults (Requirement 40.1)
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vod_categories_cache = None
        self._series_categories_cache = None
    
    # ============== VOD Categories (6.1) ==============
    
    def get_vod_categories(self) -> List[Dict[str, Any]]:
        """
        Get VOD categories from portal.
        
        Requirements: 4.1, 91.2
        """
        cache_key = f"vod_categories:{self.original_base_url}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "vod",
            "action": "get_categories",
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
                categories = data.get("js", [])
                if isinstance(categories, list):
                    cache.set(cache_key, categories, 3600)  # Cache 1 hour
                    logger.info(f"Got {len(categories)} VOD categories")
                    return categories
        except Exception as e:
            logger.error(f"Failed to get VOD categories: {e}")
        
        return []
    
    # ============== VOD Items with Pagination (6.2) ==============
    
    def get_vod_items(
        self, 
        category_id: str = "*",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "added",
        search: str = ""
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get VOD items with pagination.
        
        Requirements: 4.2, 40.1, 40.2, 40.3, 40.4
        
        Args:
            category_id: Category ID or "*" for all
            page: Page number (1-indexed)
            page_size: Items per page
            sort_by: Sort field (added, name, rating)
            search: Search query
        
        Returns:
            Tuple of (items_list, total_count)
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        # Ensure page_size is within bounds
        page_size = min(max(1, page_size), self.MAX_PAGE_SIZE)
        
        params = {
            "type": "vod",
            "action": "get_ordered_list",
            "category": category_id,
            "p": str(page),
            "sortby": sort_by,
            "JsHttpRequest": "1-xml"
        }
        
        if search:
            params["search"] = search
        
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
                js = data.get("js", {})
                items = js.get("data", [])
                total = js.get("total_items", len(items))
                
                logger.debug(f"Got {len(items)} VOD items (page {page}, total {total})")
                return items, int(total)
        except Exception as e:
            logger.error(f"Failed to get VOD items: {e}")
        
        return [], 0


    # ============== VOD Link (6.3) ==============
    
    def get_vod_link(self, vod_id: str, series: int = 0) -> str:
        """
        Get playback link for VOD item.
        
        Requirements: 4.5
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "vod",
            "action": "create_link",
            "cmd": f"/media/{vod_id}.mpg",
            "series": str(series),
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
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
                cmd = data.get("js", {}).get("cmd", "")
                if cmd:
                    # Extract URL from cmd
                    url = self.extract_stream_url_ffmpeg(cmd)
                    if url:
                        return url
                    # Fallback: return last part of cmd
                    return cmd.split()[-1]
        except Exception as e:
            logger.error(f"Failed to get VOD link for {vod_id}: {e}")
        
        raise MacPortalError(f"Could not get VOD link for {vod_id}")
    
    # ============== VOD Search (6.4) ==============
    
    def search_vod(self, query: str, page: int = 1) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search VOD content.
        
        Requirements: 28.1, 28.3, 28.4
        """
        return self.get_vod_items(category_id="*", page=page, search=query)
    
    # ============== Series Categories (7.1) ==============
    
    def get_series_categories(self) -> List[Dict[str, Any]]:
        """
        Get series categories from portal.
        
        Requirements: 13.1
        """
        cache_key = f"series_categories:{self.original_base_url}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "series",
            "action": "get_categories",
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
                categories = data.get("js", [])
                if isinstance(categories, list):
                    cache.set(cache_key, categories, 3600)
                    logger.info(f"Got {len(categories)} series categories")
                    return categories
        except Exception as e:
            logger.error(f"Failed to get series categories: {e}")
        
        return []
    
    # ============== Series Items with Pagination (7.2) ==============
    
    def get_series_items(
        self,
        category_id: str = "*",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "added",
        search: str = ""
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get series items with pagination.
        
        Requirements: 13.2
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "series",
            "action": "get_ordered_list",
            "category": category_id,
            "p": str(page),
            "sortby": sort_by,
            "JsHttpRequest": "1-xml"
        }
        
        if search:
            params["search"] = search
        
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
                js = data.get("js", {})
                items = js.get("data", [])
                total = js.get("total_items", len(items))
                
                logger.debug(f"Got {len(items)} series items (page {page}, total {total})")
                return items, int(total)
        except Exception as e:
            logger.error(f"Failed to get series items: {e}")
        
        return [], 0
    
    # ============== Series Info (7.3) ==============
    
    def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """
        Get series info including seasons and episodes.
        
        Requirements: 13.3
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "series",
            "action": "get_ordered_list",
            "movie_id": series_id,
            "season_id": "0",
            "episode_id": "0",
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
                return data.get("js", {})
        except Exception as e:
            logger.error(f"Failed to get series info for {series_id}: {e}")
        
        return {}
    
    # ============== Series Link (7.4) ==============
    
    def get_series_link(self, series_id: str, season_id: str, episode_id: str) -> str:
        """
        Get playback link for series episode.
        
        Requirements: 13.4
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        params = {
            "type": "series",
            "action": "create_link",
            "cmd": f"/media/{series_id}.mpg",
            "series": episode_id,
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
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
                cmd = data.get("js", {}).get("cmd", "")
                if cmd:
                    url = self.extract_stream_url_ffmpeg(cmd)
                    if url:
                        return url
                    return cmd.split()[-1]
        except Exception as e:
            logger.error(f"Failed to get series link: {e}")
        
        raise MacPortalError(f"Could not get series link for {series_id}/{season_id}/{episode_id}")
    
    # ============== Series Search (7.5) ==============
    
    def search_series(self, query: str, page: int = 1) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search series content.
        
        Requirements: 28.2
        """
        return self.get_series_items(category_id="*", page=page, search=query)



# ============== VOD Import Manager (92.1-92.4) ==============

class VODImportManager:
    """
    Manages efficient VOD import using a single MAC address.
    
    Requirements: 91.4, 92.1, 92.2, 92.3, 92.4
    
    Key principle: VOD content is account-wide, not MAC-specific.
    We use only ONE MAC for the entire VOD import to avoid redundant requests.
    """
    
    def __init__(self, account_id: int):
        """
        Initialize VODImportManager.
        
        Args:
            account_id: The M3UAccount ID
        """
        self.account_id = account_id
        self._client: Optional[VODSeriesClient] = None
        self._selected_mac = None
    
    def _get_account(self):
        """Get the M3UAccount instance."""
        from .models import M3UAccount
        return M3UAccount.objects.get(pk=self.account_id)
    
    def _select_mac_for_vod(self) -> Optional[str]:
        """
        Select a single MAC for VOD scanning.
        
        Requirements: 92.1, 92.2
        
        Strategy:
        1. Use first available healthy MAC
        2. Fallback to next MAC on failure
        """
        from .mac_rotation_manager import MACRotationManagerRegistry
        
        manager = MACRotationManagerRegistry.get_or_create(self.account_id)
        mac = manager.get_next_mac()
        
        if mac:
            self._selected_mac = mac.address
            logger.info(f"Selected MAC {mac.address[:8]}... for VOD scanning")
            return mac.address
        
        logger.warning(f"No available MAC for VOD scanning in account {self.account_id}")
        return None
    
    def _get_client(self) -> Optional[VODSeriesClient]:
        """
        Get or create VOD client with selected MAC.
        
        Requirements: 92.1
        """
        if self._client:
            return self._client
        
        account = self._get_account()
        
        # Check if VOD scanning is enabled
        if not account.enable_vod_scanning:
            logger.debug(f"VOD scanning disabled for account {self.account_id}")
            return None
        
        # Select MAC for VOD
        mac = self._select_mac_for_vod()
        if not mac:
            return None
        
        # Create client
        self._client = VODSeriesClient(
            base_url=account.server_url,
            mac=mac,
            proxy=account.proxy_url,
        )
        
        return self._client
    
    def import_vod_categories(self) -> List[Dict[str, Any]]:
        """
        Import VOD categories.
        
        Requirements: 91.2, 92.3
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            categories = client.get_vod_categories()
            logger.info(f"Imported {len(categories)} VOD categories for account {self.account_id}")
            return categories
        except Exception as e:
            logger.error(f"Failed to import VOD categories: {e}")
            # Try with different MAC on failure
            self._client = None
            self._selected_mac = None
            return self._retry_with_fallback_mac(self.import_vod_categories)
    
    def import_series_categories(self) -> List[Dict[str, Any]]:
        """
        Import series categories.
        
        Requirements: 91.2, 92.3
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            categories = client.get_series_categories()
            logger.info(f"Imported {len(categories)} series categories for account {self.account_id}")
            return categories
        except Exception as e:
            logger.error(f"Failed to import series categories: {e}")
            self._client = None
            self._selected_mac = None
            return self._retry_with_fallback_mac(self.import_series_categories)
    
    def import_all_vod_items(self, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Import all VOD items with pagination.
        
        Requirements: 92.3, 40.1-40.4
        """
        client = self._get_client()
        if not client:
            return []
        
        all_items = []
        page = 1
        total_pages = 1
        
        try:
            while page <= total_pages:
                items, total = client.get_vod_items(category_id="*", page=page)
                all_items.extend(items)
                
                # Calculate total pages
                if total > 0:
                    total_pages = (total + client.DEFAULT_PAGE_SIZE - 1) // client.DEFAULT_PAGE_SIZE
                
                if progress_callback:
                    progress_callback(page, total_pages, len(all_items), total)
                
                page += 1
                
                # Safety limit
                if page > 1000:
                    logger.warning("VOD import reached page limit")
                    break
            
            logger.info(f"Imported {len(all_items)} VOD items for account {self.account_id}")
            return all_items
            
        except Exception as e:
            logger.error(f"Failed to import VOD items: {e}")
            return all_items  # Return what we have so far
    
    def import_all_series_items(self, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Import all series items with pagination.
        
        Requirements: 92.3
        """
        client = self._get_client()
        if not client:
            return []
        
        all_items = []
        page = 1
        total_pages = 1
        
        try:
            while page <= total_pages:
                items, total = client.get_series_items(category_id="*", page=page)
                all_items.extend(items)
                
                if total > 0:
                    total_pages = (total + client.DEFAULT_PAGE_SIZE - 1) // client.DEFAULT_PAGE_SIZE
                
                if progress_callback:
                    progress_callback(page, total_pages, len(all_items), total)
                
                page += 1
                
                if page > 1000:
                    logger.warning("Series import reached page limit")
                    break
            
            logger.info(f"Imported {len(all_items)} series items for account {self.account_id}")
            return all_items
            
        except Exception as e:
            logger.error(f"Failed to import series items: {e}")
            return all_items
    
    def _retry_with_fallback_mac(self, func, max_retries: int = 2):
        """
        Retry operation with a different MAC on failure.
        
        Requirements: 92.4
        """
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                logger.warning(f"Retry {attempt + 1}/{max_retries} failed: {e}")
                self._client = None
                self._selected_mac = None
        
        return []


# ============== Resume Point Manager (6.5) ==============

class ResumePointManager:
    """
    Manages VOD resume points.
    
    Requirements: 31.1, 31.2, 31.3, 31.4
    """
    
    def __init__(self, account_id: int):
        self.account_id = account_id
    
    def save_position(
        self, 
        vod_id: str, 
        position_seconds: int,
        duration_seconds: int = None,
        content_type: str = "vod"
    ) -> None:
        """
        Save playback position.
        
        Requirements: 31.1, 31.2
        """
        from .mac_portal_models import VODResumePoint
        from .models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        
        resume_point, created = VODResumePoint.objects.update_or_create(
            m3u_account=account,
            vod_id=vod_id,
            content_type=content_type,
            defaults={
                'position_seconds': position_seconds,
                'duration_seconds': duration_seconds,
            }
        )
        
        logger.debug(f"Saved resume point for {vod_id}: {position_seconds}s")
    
    def get_position(self, vod_id: str, content_type: str = "vod") -> Optional[int]:
        """
        Get saved playback position.
        
        Requirements: 31.3
        """
        from .mac_portal_models import VODResumePoint
        
        try:
            resume_point = VODResumePoint.objects.get(
                m3u_account_id=self.account_id,
                vod_id=vod_id,
                content_type=content_type
            )
            return resume_point.position_seconds
        except VODResumePoint.DoesNotExist:
            return None
    
    def clear_position(self, vod_id: str, content_type: str = "vod") -> None:
        """
        Clear saved playback position.
        
        Requirements: 31.4
        """
        from .mac_portal_models import VODResumePoint
        
        VODResumePoint.objects.filter(
            m3u_account_id=self.account_id,
            vod_id=vod_id,
            content_type=content_type
        ).delete()
    
    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently watched items."""
        from .mac_portal_models import VODResumePoint
        
        resume_points = VODResumePoint.objects.filter(
            m3u_account_id=self.account_id
        ).order_by('-last_watched')[:limit]
        
        return [
            {
                'vod_id': rp.vod_id,
                'content_type': rp.content_type,
                'position_seconds': rp.position_seconds,
                'duration_seconds': rp.duration_seconds,
                'last_watched': rp.last_watched,
            }
            for rp in resume_points
        ]


# ============== Watched Status Manager (6.6) ==============

class WatchedStatusManager:
    """
    Manages VOD watched status.
    
    Requirements: 32.1, 32.2, 32.3, 32.4
    """
    
    def __init__(self, account_id: int):
        self.account_id = account_id
    
    def mark_watched(self, vod_id: str, content_type: str = "vod") -> None:
        """
        Mark content as watched.
        
        Requirements: 32.1
        """
        from .mac_portal_models import VODWatchedStatus
        from .models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        
        status, created = VODWatchedStatus.objects.update_or_create(
            m3u_account=account,
            vod_id=vod_id,
            content_type=content_type,
            defaults={'watched': True}
        )
    
    def mark_unwatched(self, vod_id: str, content_type: str = "vod") -> None:
        """
        Mark content as unwatched.
        
        Requirements: 32.2
        """
        from .mac_portal_models import VODWatchedStatus
        
        VODWatchedStatus.objects.filter(
            m3u_account_id=self.account_id,
            vod_id=vod_id,
            content_type=content_type
        ).update(watched=False)
    
    def is_watched(self, vod_id: str, content_type: str = "vod") -> bool:
        """
        Check if content is watched.
        
        Requirements: 32.3
        """
        from .mac_portal_models import VODWatchedStatus
        
        try:
            status = VODWatchedStatus.objects.get(
                m3u_account_id=self.account_id,
                vod_id=vod_id,
                content_type=content_type
            )
            return status.watched
        except VODWatchedStatus.DoesNotExist:
            return False
    
    def get_watched_list(self, content_type: str = None) -> List[str]:
        """
        Get list of watched VOD IDs.
        
        Requirements: 32.4
        """
        from .mac_portal_models import VODWatchedStatus
        
        queryset = VODWatchedStatus.objects.filter(
            m3u_account_id=self.account_id,
            watched=True
        )
        
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        return list(queryset.values_list('vod_id', flat=True))
