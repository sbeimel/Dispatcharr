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
    
    def get_vod_categories(self) -> list:
        """Hole VOD-Kategorien über MacPortalClient."""
        try:
            client = self._get_client()
            return client.get_vod_categories()
        except Exception as e:
            logger.error(f"MacReplayStrategy get_vod_categories failed: {e}")
            return []
    
    def get_vod_items(self, category_id: str) -> list:
        """Hole VOD-Items einer Kategorie."""
        try:
            client = self._get_client()
            return client.get_vod_items(category_id)
        except Exception as e:
            logger.error(f"MacReplayStrategy get_vod_items failed: {e}")
            return []
    
    def get_series_categories(self) -> list:
        """Hole Serien-Kategorien über MacPortalClient."""
        try:
            client = self._get_client()
            return client.get_series_categories()
        except Exception as e:
            logger.error(f"MacReplayStrategy get_series_categories failed: {e}")
            return []
