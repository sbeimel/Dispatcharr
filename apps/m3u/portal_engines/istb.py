"""
iSTB Strategy - Basierend auf iSTB.app iOS Stalker Portal Emulator.

Diese Strategie implementiert die erweiterte Authentifizierung aus iSTB.app:
- prehash: Hardware-Hash aus Model + Version
- api_signature: Anzahl der gSTB API Methoden (263 für echte MAG Boxen)
- signature: Device-ID signiert mit Random-Token
- metrics: JSON mit mac, sn, model, type, uid, random
- hw_version_2: Hash von metrics + random

Besonders effektiv für Portale die erweiterte STB-Validierung durchführen.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .base import BasePortalStrategy, HandshakeResult, PortalIdentity

logger = logging.getLogger(__name__)


class iSTBStrategy(BasePortalStrategy):
    """
    iSTB Strategy - iOS STB Emulator Authentifizierung.
    
    Implementiert die vollständige Authentifizierungslogik aus iSTB.app
    mit prehash, api_signature, metrics und hw_version_2.
    """
    
    NAME = "istb"
    DESCRIPTION = "iSTB iOS Emulator Style - Extended STB validation with prehash, metrics, hw_version_2"
    
    # Standard MAG250 Werte (wie in iSTB.app)
    DEFAULT_MODEL = "MAG250"
    DEFAULT_VERSION = "ImageDescription: 0.2.18-r23-250; ImageDate: Wed Aug 29 10:49:53 EEST 2018"
    DEFAULT_SERIAL = "0000000000000"
    DEFAULT_HW_VERSION = "2.6-BD-00"
    
    # api_signature für echte MAG Boxen (Anzahl gSTB Methoden)
    API_SIGNATURE_MAG = 263
    
    def __init__(self, portal_url: str, identity: PortalIdentity,
                 user_agent: str = 'MAG250', timeout: int = 10,
                 proxy: Optional[str] = None, use_cloudscraper: Optional[bool] = None):
        super().__init__(portal_url, identity, user_agent, timeout, proxy, use_cloudscraper)
        
        self._token = None
        self._random = None
        self._session = None
        
        # STB Identifikation
        self._model = self.DEFAULT_MODEL
        self._version = self.DEFAULT_VERSION
        self._serial = self.DEFAULT_SERIAL
        self._hw_version = self.DEFAULT_HW_VERSION
    
    def _get_session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            if self._use_cloudscraper:
                try:
                    import cloudscraper
                    self._session = cloudscraper.create_scraper(
                        browser={'browser': 'chrome', 'platform': 'linux', 'desktop': True}
                    )
                except ImportError:
                    self._session = requests.Session()
            else:
                self._session = requests.Session()
        return self._session
    
    def _get_headers(self, with_auth: bool = False) -> Dict[str, str]:
        """Get request headers like iSTB.app."""
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "X-User-Agent": f"Model: {self._model}; Link: WiFi",
        }
        
        if with_auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        # Add Referer
        parsed = urlparse(self.portal_url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        
        return headers
    
    def _get_cookies(self) -> Dict[str, str]:
        """Get cookies like iSTB.app."""
        return {
            "mac": self.identity.mac,
            "stb_lang": "en",
            "timezone": self.identity.timezone,
        }
    
    def _compute_prehash(self) -> str:
        """
        Compute prehash like iSTB.app: GetHashVersion1(model, version[:56])
        
        This is a simplified version - real MAG boxes use hardware-based hashing.
        We simulate it with MD5.
        """
        data = f"{self._model}{self._version[:56]}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _compute_signature(self, random_token: str) -> str:
        """
        Compute signature like iSTB.app: GetUID(random)
        
        Simulates device signature with random token.
        """
        data = f"{self.identity.mac}{random_token}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _compute_device_id(self) -> str:
        """Compute device_id like iSTB.app: GetUID()"""
        return hashlib.md5(self.identity.mac.encode()).hexdigest()
    
    def _compute_device_id2(self, token: str) -> str:
        """
        Compute device_id2 like iSTB.app.
        
        GetUID('device_id', access_token) if GetUID(token) != GetUID(token, token)
        """
        data = f"device_id{token}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _compute_hw_version_2(self, metrics: Dict, random_token: str) -> str:
        """
        Compute hw_version_2 like iSTB.app: GetHashVersion1(JSON.stringify(metrics), random)
        """
        data = f"{json.dumps(metrics, separators=(',', ':'))}{random_token}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _build_metrics(self, device_id2: str) -> Dict[str, str]:
        """Build metrics object like iSTB.app."""
        return {
            "mac": self.identity.mac,
            "sn": self._serial,
            "model": self._model,
            "type": "STB",
            "uid": device_id2,
            "random": self._random or ""
        }
    
    def _resolve_portal_url(self) -> str:
        """Resolve the actual portal load.php URL."""
        # If already ends with load.php or portal.php, use as-is
        if self.portal_url.endswith(("load.php", "portal.php")):
            return self.portal_url
        
        # Try common paths
        parsed = urlparse(self.portal_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        paths = [
            "/stalker_portal/server/load.php",
            "/c/portal.php",
            "/portal.php",
            "/server/load.php",
        ]
        
        session = self._get_session()
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        
        for path in paths:
            url = base + path
            try:
                r = session.get(url, headers=self._get_headers(), 
                               cookies=self._get_cookies(), proxies=proxies, timeout=5)
                if r.status_code < 400:
                    logger.info(f"iSTBStrategy: Resolved portal URL to {url}")
                    return url
            except Exception as e:
                logger.debug(f"iSTBStrategy: Path {path} failed: {e}")
        
        return self.portal_url
    
    def perform_handshake(self) -> HandshakeResult:
        """
        Perform handshake like iSTB.app with full STB emulation.
        
        1. First handshake to get token and random
        2. Then get_profile with all extended parameters
        """
        try:
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            # Step 1: Initial handshake
            prehash = self._compute_prehash()
            
            handshake_params = {
                "type": "stb",
                "action": "handshake",
                "token": "",
                "prehash": prehash,
                "JsHttpRequest": "1-xml"
            }
            
            logger.info(f"iSTBStrategy: Handshake with prehash={prehash[:16]}...")
            
            response = session.get(
                portal_url,
                params=handshake_params,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return HandshakeResult(
                    success=False,
                    error=f"Handshake failed with status {response.status_code}",
                    engine_used=self.NAME
                )
            
            data = response.json()
            js = data.get("js", {})
            
            self._token = js.get("token", "")
            self._random = js.get("random", "")
            
            if not self._token:
                return HandshakeResult(
                    success=False,
                    error="No token received from handshake",
                    engine_used=self.NAME
                )
            
            logger.info(f"iSTBStrategy: Got token, random={self._random[:8] if self._random else 'none'}...")
            
            # Step 2: Get profile with extended parameters
            device_id = self._compute_device_id()
            device_id2 = self._compute_device_id2(self._token)
            signature = self._compute_signature(self._random) if self._random else ""
            metrics = self._build_metrics(device_id2)
            hw_version_2 = self._compute_hw_version_2(metrics, self._random) if self._random else ""
            
            profile_params = {
                "type": "stb",
                "action": "get_profile",
                "hd": "1",
                "ver": self._version,
                "num_banks": "2",
                "sn": self._serial,
                "stb_type": self._model,
                "client_type": "STB",
                "image_version": "218",
                "video_out": "hdmi",
                "device_id": device_id,
                "device_id2": device_id2,
                "signature": signature,
                "auth_second_step": "0",
                "hw_version": self._hw_version,
                "not_valid_token": "0",
                "metrics": json.dumps(metrics, separators=(',', ':')),
                "hw_version_2": hw_version_2,
                "timestamp": str(int(time.time())),
                "api_signature": str(self.API_SIGNATURE_MAG),
                "prehash": prehash,
                "JsHttpRequest": "1-xml"
            }
            
            logger.info(f"iSTBStrategy: get_profile with api_signature={self.API_SIGNATURE_MAG}")
            
            response = session.get(
                portal_url,
                params=profile_params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                # Token might still be valid even if profile fails
                logger.warning(f"iSTBStrategy: get_profile returned {response.status_code}, but token may be valid")
            
            profile_data = {}
            try:
                profile_data = response.json().get("js", {})
            except Exception:
                pass
            
            # Extract expiry info
            expire_date = profile_data.get("phone", "") or profile_data.get("expire_billing_date", "")
            
            return HandshakeResult(
                success=True,
                token=self._token,
                engine_used=self.NAME,
                portal_type="stalker",
                expire_date=expire_date,
                extra_data={
                    "random": self._random,
                    "profile": profile_data,
                    "prehash": prehash,
                    "api_signature": self.API_SIGNATURE_MAG
                }
            )
            
        except Exception as e:
            logger.error(f"iSTBStrategy handshake failed: {e}")
            return HandshakeResult(
                success=False,
                error=str(e),
                engine_used=self.NAME
            )
    
    def create_link(self, cmd: str, token: Optional[str] = None, 
                    content_type: str = "itv") -> Optional[str]:
        """Create stream link like iSTB.app."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return None
                use_token = result.token
            
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": content_type,
                "action": "create_link",
                "cmd": cmd,
                "forced_storage": "undefined",
                "disable_ad": "0",
                "download": "0",
                "force_ch_link_check": "0",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", {})
                
                if isinstance(js, dict):
                    cmd_result = js.get("cmd", "")
                    if cmd_result:
                        # Remove "ffmpeg " prefix if present
                        if cmd_result.startswith("ffmpeg "):
                            cmd_result = cmd_result[7:]
                        logger.info(f"iSTBStrategy: Created link: {cmd_result[:60]}...")
                        return cmd_result
            
            return None
            
        except Exception as e:
            logger.error(f"iSTBStrategy create_link failed: {e}")
            return None
    
    def get_all_channels(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all channels like iSTB.app."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
                use_token = result.token
            
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": "itv",
                "action": "get_all_channels",
                "force_ch_link_check": "",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", {})
                
                if isinstance(js, dict) and "data" in js:
                    channels = js["data"]
                    logger.info(f"iSTBStrategy: Got {len(channels)} channels")
                    return channels
                elif isinstance(js, list):
                    logger.info(f"iSTBStrategy: Got {len(js)} channels")
                    return js
            
            return []
            
        except Exception as e:
            logger.error(f"iSTBStrategy get_all_channels failed: {e}")
            return []
    
    def get_genres(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get channel genres/categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": "itv",
                "action": "get_genres",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", [])
                if isinstance(js, list):
                    return js
            
            return []
            
        except Exception as e:
            logger.error(f"iSTBStrategy get_genres failed: {e}")
            return []
    
    def get_vod_categories(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get VOD categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": "vod",
                "action": "get_categories",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", [])
                if isinstance(js, list):
                    return js
            
            return []
            
        except Exception as e:
            logger.error(f"iSTBStrategy get_vod_categories failed: {e}")
            return []
    
    def get_series_categories(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Series categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._resolve_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": "series",
                "action": "get_categories",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_headers(with_auth=True),
                cookies=self._get_cookies(),
                proxies=proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", [])
                if isinstance(js, list):
                    return js
            
            return []
            
        except Exception as e:
            logger.error(f"iSTBStrategy get_series_categories failed: {e}")
            return []
