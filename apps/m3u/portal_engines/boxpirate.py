"""
BoxPirate Portal Engine - Dreambox Style mit Signature.

Basiert auf BoxPirate Plugin für Dreambox.
Features:
- Signature-basierte Authentifizierung
- Random-String für Metriken
- MAG250 Style
"""

import json
import logging
import random
from typing import Dict, Any, Optional, List

from .base import BasePortalStrategy, PortalIdentity, HandshakeResult

logger = logging.getLogger(__name__)


class BoxPirateStrategy(BasePortalStrategy):
    """BoxPirate Dreambox Strategie."""
    
    NAME = "boxpirate"
    DESCRIPTION = "BoxPirate (Dreambox Style mit Signature)"
    
    # Kürzere Timeouts für schnellere Failover
    DEFAULT_TIMEOUT = 8  # 8s statt 10s
    
    def __init__(self, *args, **kwargs):
        # Override default timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.DEFAULT_TIMEOUT
        super().__init__(*args, **kwargs)
    
    def perform_handshake(self) -> HandshakeResult:
        """BoxPirate Handshake."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        params = {
            "type": "stb",
            "action": "handshake",
            "token": "",
            "JsHttpRequest": "1-xml",
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
                        logger.info(f"BoxPirate: Handshake successful via {endpoint}")
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                        
            except Exception as e:
                logger.debug(f"BoxPirate handshake failed for {endpoint}: {e}")
                continue
        
        return HandshakeResult(success=False, error="All endpoints failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """BoxPirate Profil mit Signature."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        # BoxPirate verwendet random für Metriken
        random_str = ''.join(random.sample('0123456789abcdef' * 3, 40))
        
        metrics = {
            "mac": self.identity.mac,
            "sn": self.identity.serial_number,
            "type": "STB",
            "model": "MAG250",
            "random": random_str
        }
        
        params = {
            "type": "stb",
            "action": "get_profile",
            "JsHttpRequest": "1-xml",
            "auth_second_step": "1",
            "not_valid_token": "0",
            "sn": self.identity.serial_number,
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "signature": self.identity.signature,
            "stb_type": "MAG250",
            "ver": "ImageDescription: 0.2.16-250; ImageDate: 18 Mar 2013 19:56:53 GMT+0200; PORTAL version: 4.9.9; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566",
            "hd": "1",
            "num_banks": "1",
            "image_version": "216",
            "hw_version": "2.17-IB-00",
            "hw_version_2": "62",
            "metrics": json.dumps(metrics),
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"BoxPirate get_profile failed for {endpoint}: {e}")
                continue
        
        return {}
    
    def create_link(self, cmd: str) -> Optional[str]:
        """Create stream link with Referer header."""
        if not self.identity.token:
            result = self.perform_handshake()
            if not result.success:
                return None
            self.identity.token = result.token
        
        from urllib.parse import urlparse
        parsed = urlparse(self.portal_url)
        
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {self.identity.token}"
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        
        params = {
            "type": "itv",
            "action": "create_link",
            "cmd": cmd,
            "series": "0",
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
            "force_ch_link_check": "false",
            "JsHttpRequest": "1-xml",
        }
        
        proxies = self._get_proxies()
        cookies = self._get_cookies()
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            
            # Try GET first
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    
                    # Handle empty list response (channel not found/disabled)
                    if isinstance(js, list):
                        if not js:
                            logger.debug(f"BoxPirate: Portal returned empty list for cmd={cmd}")
                        continue
                    
                    link = js.get("cmd", "").split()[-1]
                    if link and link.startswith("http"):
                        logger.info(f"BoxPirate: create_link successful via GET")
                        return link
            except Exception as e:
                logger.debug(f"BoxPirate create_link GET failed: {e}")
            
            # Try POST
            try:
                response = self.session.post(
                    url,
                    data=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    
                    # Handle empty list response (channel not found/disabled)
                    if isinstance(js, list):
                        if not js:
                            logger.debug(f"BoxPirate: Portal returned empty list for cmd={cmd}")
                        continue
                    
                    link = js.get("cmd", "").split()[-1]
                    if link and link.startswith("http"):
                        logger.info(f"BoxPirate: create_link successful via POST")
                        return link
            except Exception as e:
                logger.debug(f"BoxPirate create_link POST failed: {e}")
        
        return None
    
    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels."""
        if not self.identity.token:
            result = self.perform_handshake()
            if not result.success:
                return []
            self.identity.token = result.token
        
        params = {
            "type": "itv",
            "action": "get_all_channels",
            "force_ch_link_check": "",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, self.identity.token, method)
            if data:
                try:
                    channels = data.get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"BoxPirate: Got {len(channels)} channels via {method}")
                        return channels
                except Exception:
                    pass
        
        return []
