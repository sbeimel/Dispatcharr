"""
EStalker Portal Engine - Enigma2 Style mit erweiterten Metriken.

Basiert auf EStalker Plugin für Enigma2.
Features:
- adid Cookie für erweiterte Authentifizierung
- Prehash-Support für "missing" Responses
- MAG254 Style Metriken
- api_signature 261
"""

import hashlib
import json
import logging
import random
import string
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from .base import BasePortalStrategy, PortalIdentity, HandshakeResult

logger = logging.getLogger(__name__)


class EStalkerStrategy(BasePortalStrategy):
    """EStalker Enigma2 Strategie - basiert auf EStalker Plugin."""
    
    NAME = "estalker"
    DESCRIPTION = "EStalker (Enigma2 Style mit erweiterten Metriken)"
    
    # Kürzere Timeouts für schnellere Failover
    DEFAULT_TIMEOUT = 8  # 8s statt 10s
    
    def __init__(self, *args, **kwargs):
        # Override default timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.DEFAULT_TIMEOUT
        super().__init__(*args, **kwargs)
    
    def _get_cookies(self) -> Dict[str, str]:
        """EStalker-spezifische Cookies mit adid."""
        cookies = super()._get_cookies()
        cookies["adid"] = self.identity.adid
        return cookies
    
    def perform_handshake(self) -> HandshakeResult:
        """EStalker Handshake mit Prehash-Support."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            params = {
                "type": "stb",
                "action": "handshake",
                "JsHttpRequest": "1-xml",
            }
            
            try:
                response = self.session.post(
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
                    
                    # EStalker: Prüfe auf "missing" Nachricht
                    if "msg" in js and "missing" in js.get("msg", "").lower():
                        result = self._prehash_handshake(url, headers, cookies, proxies)
                        if result.success:
                            return result
                        continue
                    
                    token = js.get("token")
                    if token:
                        logger.info(f"EStalker: Handshake successful via {endpoint}")
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                        
            except Exception as e:
                logger.debug(f"EStalker handshake failed for {endpoint}: {e}")
                continue
        
        return HandshakeResult(success=False, error="All endpoints failed", engine_used=self.NAME)
    
    def _prehash_handshake(self, url: str, headers: Dict, cookies: Dict, 
                           proxies: Optional[Dict]) -> HandshakeResult:
        """Prehash-Methode für Portale die "missing" zurückgeben."""
        try:
            # Generiere Fake-Token für Prehash
            fake_token = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=32
            ))
            prehash = hashlib.sha1(fake_token.encode()).hexdigest()
            
            headers = headers.copy()
            headers["Authorization"] = f"Bearer {fake_token}"
            
            params = {
                "type": "stb",
                "action": "handshake",
                "JsHttpRequest": "1-xml",
                "mac": self.identity.mac,
                "prehash": prehash,
            }
            
            response = self.session.post(
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
                    logger.info(f"EStalker: Prehash handshake successful")
                    return HandshakeResult(
                        success=True,
                        token=token,
                        token_random=js.get("random", ""),
                        portal_type="stalker",
                        engine_used=self.NAME,
                    )
        except Exception as e:
            logger.debug(f"EStalker prehash handshake failed: {e}")
        
        return HandshakeResult(success=False, error="Prehash failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """EStalker Profil mit erweiterten Metriken (MAG254 Style)."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        dt = datetime.now()
        timestamp = str(int(dt.timestamp()))
        
        # EStalker verwendet erweiterte Metriken für stalker_portal
        if "/stalker_portal/" in self.portal_url:
            metrics = {
                "type": "stb",
                "model": "MAG254",
                "mac": self.identity.mac,
                "sn": self.identity.serial_number,
                "uid": "",
                "random": self.identity.token_random or ""
            }
        else:
            metrics = {
                "mac": self.identity.mac,
                "sn": self.identity.serial_number,
                "type": "STB",
                "model": "MAG250",
                "uid": "",
                "random": ""
            }
        
        params = {
            "type": "stb",
            "action": "get_profile",
            "JsHttpRequest": "1-xml",
            "mac": self.identity.mac,
            "hd": "1",
            "ver": "ImageDescription: 0.2.18-r14-pub-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.3.0; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566",
            "num_banks": "2",
            "sn": self.identity.serial_number,
            "stb_type": "MAG254",
            "client_type": "STB",
            "image_version": "218",
            "video_out": "hdmi",
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "signature": "",
            "auth_second_step": "1",
            "hw_version": "1.7-BD-00",
            "hw_version_2": self.identity.hw_version_2,
            "not_valid_token": "0",
            "metrics": quote(json.dumps(metrics)),
            "timestamp": timestamp,
            "api_signature": "261",
            "prehash": self.identity.prehash,
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            try:
                response = self.session.post(
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
                logger.debug(f"EStalker get_profile failed for {endpoint}: {e}")
                continue
        
        return {}
    
    def create_link(self, cmd: str) -> Optional[str]:
        """Create stream link."""
        if not self.identity.token:
            result = self.perform_handshake()
            if not result.success:
                return None
            self.identity.token = result.token
        
        params = {
            "type": "itv",
            "action": "create_link",
            "cmd": cmd,
            "series": "0",
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
            "force_ch_link_check": "false",
        }
        
        data = self._make_request(params, self.identity.token, "GET")
        if data:
            try:
                link = data.get("js", {}).get("cmd", "").split()[-1]
                if link and link.startswith("http"):
                    return link
            except Exception:
                pass
        
        # Try POST
        data = self._make_request(params, self.identity.token, "POST")
        if data:
            try:
                link = data.get("js", {}).get("cmd", "").split()[-1]
                if link and link.startswith("http"):
                    return link
            except Exception:
                pass
        
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
                        logger.info(f"EStalker: Got {len(channels)} channels via {method}")
                        return channels
                except Exception:
                    pass
        
        return []
