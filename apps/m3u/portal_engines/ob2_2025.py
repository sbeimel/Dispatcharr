"""
OB2_2025 Strategy - Erweiterte Handshake-Logik mit api_signature 263.

Basiert auf OB2_2025 Prüflogik für erweiterte STB-Validierung.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote

from .base import BasePortalStrategy, HandshakeResult, PortalIdentity

logger = logging.getLogger(__name__)


class OB2_2025Strategy(BasePortalStrategy):
    """OB2_2025 Strategie mit erweiterter Handshake-Logik."""
    
    NAME = "ob2_2025"
    DESCRIPTION = "OB2_2025 (Erweiterte Prüflogik mit api_signature 263)"
    
    # Optimized: Shorter timeout
    DEFAULT_TIMEOUT = 8
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.timeout > self.DEFAULT_TIMEOUT:
            self.timeout = self.DEFAULT_TIMEOUT
    
    def _get_cookies(self) -> Dict[str, str]:
        """OB2_2025 Cookies mit adid."""
        cookies = super()._get_cookies()
        cookies["adid"] = self.identity.adid
        return cookies
    
    def perform_handshake(self) -> HandshakeResult:
        """OB2_2025 Handshake mit api_signature."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        
        for endpoint in self.PORTAL_ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            params = {
                "type": "stb",
                "action": "handshake",
                "JsHttpRequest": "1-xml",
            }
            
            try:
                # Try GET first
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=self._get_proxies(),
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
                        logger.info(f"OB2_2025: Handshake successful via GET on {endpoint}")
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                
                # Fallback to POST
                response = self.session.post(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=self._get_proxies(),
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
                        logger.info(f"OB2_2025: Handshake successful via POST on {endpoint}")
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                        
            except Exception as e:
                logger.debug(f"OB2_2025 handshake failed for {endpoint}: {e}")
                continue
        
        return HandshakeResult(success=False, error="All endpoints failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """OB2_2025 Profil mit api_signature 263."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        
        dt = datetime.now()
        timestamp = str(int(dt.timestamp()))
        
        metrics = {
            "type": "stb",
            "model": "MAG254",
            "mac": self.identity.mac,
            "sn": self.identity.serial_number,
            "uid": "",
            "random": self.identity.token_random or ""
        }
        
        params = {
            "type": "stb",
            "action": "get_profile",
            "JsHttpRequest": "1-xml",
            "hd": "1",
            "sn": self.identity.serial_number,
            "stb_type": "MAG254",
            "client_type": "STB",
            "image_version": "218",
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "hw_version": "1.7-BD-00",
            "hw_version_2": self.identity.hw_version_2,
            "metrics": quote(json.dumps(metrics)),
            "timestamp": timestamp,
            "api_signature": "263",  # OB2_2025 spezifisch
            "prehash": self.identity.prehash,
        }
        
        for endpoint in self.PORTAL_ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            try:
                response = self.session.post(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=self._get_proxies(),
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"OB2_2025 get_profile failed for {endpoint}: {e}")
                continue
        
        return {}
    
    def create_link(self, cmd: str) -> Optional[str]:
        """Create stream link."""
        return self._create_link_base(cmd)
    
    def get_all_channels(self) -> list:
        """Get all channels."""
        return self._get_all_channels_base()
