"""
MacReplay Strategy - Wrapper um MacPortalClient.

Diese Strategie nutzt den bewährten MacPortalClient aus mac_portal_client.py
anstatt die Logik zu duplizieren.
"""

import logging
from typing import Optional

from .base import BasePortalStrategy, PortalIdentity, HandshakeResult

logger = logging.getLogger(__name__)


class MacReplayStrategy(BasePortalStrategy):
    """
    MacReplayXC Strategy - Wrapper um MacPortalClient.
    
    Nutzt den bewährten MacPortalClient für maximale Kompatibilität.
    """
    
    NAME = "macreplay"
    
    def __init__(self, portal_url: str, identity: PortalIdentity,
                 user_agent: str = 'MAG250', timeout: int = 10,
                 proxy: Optional[str] = None, use_cloudscraper: Optional[bool] = None):
        super().__init__(portal_url, identity, user_agent, timeout, proxy, use_cloudscraper)
        
        # Lazy-load MacPortalClient to avoid circular imports
        self._client = None
    
    def _get_client(self):
        """Get or create MacPortalClient instance."""
        if self._client is None:
            from apps.m3u.mac_portal_client import MacPortalClient
            self._client = MacPortalClient(
                base_url=self.portal_url,
                mac=self.identity.mac,
                proxy=self.proxy
            )
        return self._client
    
    def perform_handshake(self) -> HandshakeResult:
        """Führe Handshake über MacPortalClient durch."""
        try:
            client = self._get_client()
            
            # MacPortalClient macht Handshake automatisch bei create_link
            # Wir testen mit einem einfachen get_profile Aufruf
            profile = client.get_profile()
            
            if profile:
                # Update cache on success
                self._update_engine_cache()
                
                return HandshakeResult(
                    success=True,
                    token=client.token,
                    engine_used=self.NAME,
                    portal_type="stalker",
                    expire_date=profile.get('js', {}).get('phone', ''),
                    extra_data=profile
                )
            else:
                return HandshakeResult(
                    success=False,
                    error="Failed to get profile",
                    engine_used=self.NAME
                )
                
        except Exception as e:
            logger.error(f"MacReplayStrategy handshake failed: {e}")
            return HandshakeResult(
                success=False,
                error=str(e),
                engine_used=self.NAME
            )
    
    def create_link(self, cmd: str) -> Optional[str]:
        """Erstelle Stream-Link über MacPortalClient."""
        try:
            client = self._get_client()
            return client.create_link(cmd)
        except Exception as e:
            logger.error(f"MacReplayStrategy create_link failed: {e}")
            return None
    
    def get_all_channels(self) -> list:
        """Hole alle Kanäle über MacPortalClient."""
        try:
            client = self._get_client()
            return client.get_channels()
        except Exception as e:
            logger.error(f"MacReplayStrategy get_all_channels failed: {e}")
            return []
    
    def get_categories(self) -> list:
        """Hole Kategorien über MacPortalClient."""
        try:
            client = self._get_client()
            return client.get_genres()
        except Exception as e:
            logger.error(f"MacReplayStrategy get_categories failed: {e}")
            return []
    
    def get_vod_categories(self, token: Optional[str] = None) -> list:
        """Hole VOD-Kategorien.
        
        Verwendet die Basis-Implementierung da MacPortalClient keine VOD-Methoden hat.
        """
        try:
            # Ensure we have a token
            if not token:
                client = self._get_client()
                if not client.token:
                    client.handshake()
                token = client.token
            
            if not token:
                logger.error("MacReplayStrategy get_vod_categories: No token available")
                return []
            
            params = {
                "type": "vod",
                "action": "get_categories",
            }
            
            data = self._make_request(params, token, "GET")
            if data:
                categories = data.get("js", [])
                if categories:
                    logger.info(f"MacReplayStrategy: Got {len(categories)} VOD categories")
                    return categories
            
            # Try POST if GET failed
            data = self._make_request(params, token, "POST")
            if data:
                categories = data.get("js", [])
                if categories:
                    logger.info(f"MacReplayStrategy: Got {len(categories)} VOD categories via POST")
                    return categories
            
            return []
        except Exception as e:
            logger.error(f"MacReplayStrategy get_vod_categories failed: {e}")
            return []
    
    def get_vod_items(self, token: Optional[str] = None, category_id: str = "*",
                      page: int = 1, sortby: str = "added") -> dict:
        """Hole VOD-Items einer Kategorie."""
        try:
            # Ensure we have a token
            if not token:
                client = self._get_client()
                if not client.token:
                    client.handshake()
                token = client.token
            
            if not token:
                logger.error("MacReplayStrategy get_vod_items: No token available")
                return {"data": [], "total_items": 0}
            
            params = {
                "type": "vod",
                "action": "get_ordered_list",
                "category": category_id,
                "p": str(page),
                "sortby": sortby,
            }
            
            for method in ["GET", "POST"]:
                data = self._make_request(params, token, method)
                if data:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    if items:
                        logger.info(f"MacReplayStrategy: Got {len(items)} VOD items via {method}")
                        return {"data": items, "total_items": total}
            
            return {"data": [], "total_items": 0}
        except Exception as e:
            logger.error(f"MacReplayStrategy get_vod_items failed: {e}")
            return {"data": [], "total_items": 0}
    
    def get_series_categories(self, token: Optional[str] = None) -> list:
        """Hole Serien-Kategorien."""
        try:
            # Ensure we have a token
            if not token:
                client = self._get_client()
                if not client.token:
                    client.handshake()
                token = client.token
            
            if not token:
                logger.error("MacReplayStrategy get_series_categories: No token available")
                return []
            
            params = {
                "type": "series",
                "action": "get_categories",
            }
            
            for method in ["GET", "POST"]:
                data = self._make_request(params, token, method)
                if data:
                    categories = data.get("js", [])
                    if categories:
                        logger.info(f"MacReplayStrategy: Got {len(categories)} series categories via {method}")
                        return categories
            
            return []
        except Exception as e:
            logger.error(f"MacReplayStrategy get_series_categories failed: {e}")
            return []
    
    def get_series_items(self, token: Optional[str] = None, category_id: str = "*",
                         page: int = 1, sortby: str = "added") -> dict:
        """Hole Serien-Items einer Kategorie."""
        try:
            # Ensure we have a token
            if not token:
                client = self._get_client()
                if not client.token:
                    client.handshake()
                token = client.token
            
            if not token:
                logger.error("MacReplayStrategy get_series_items: No token available")
                return {"data": [], "total_items": 0}
            
            params = {
                "type": "series",
                "action": "get_ordered_list",
                "category": category_id,
                "p": str(page),
                "sortby": sortby,
            }
            
            for method in ["GET", "POST"]:
                data = self._make_request(params, token, method)
                if data:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    if items:
                        logger.info(f"MacReplayStrategy: Got {len(items)} series items via {method}")
                        return {"data": items, "total_items": total}
            
            return {"data": [], "total_items": 0}
        except Exception as e:
            logger.error(f"MacReplayStrategy get_series_items failed: {e}")
            return {"data": [], "total_items": 0}
    
    def get_genres(self, token: Optional[str] = None) -> list:
        """Hole Live-TV Genres/Kategorien."""
        try:
            # Ensure we have a token
            if not token:
                client = self._get_client()
                if not client.token:
                    client.handshake()
                token = client.token
            
            if not token:
                logger.error("MacReplayStrategy get_genres: No token available")
                return []
            
            params = {
                "type": "itv",
                "action": "get_genres",
            }
            
            for method in ["GET", "POST"]:
                data = self._make_request(params, token, method)
                if data:
                    genres = data.get("js", [])
                    if genres:
                        logger.info(f"MacReplayStrategy: Got {len(genres)} genres via {method}")
                        return genres
            
            return []
        except Exception as e:
            logger.error(f"MacReplayStrategy get_genres failed: {e}")
            return []
