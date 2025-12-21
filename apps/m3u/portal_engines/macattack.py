"""
MacAttack Strategy - Basierend auf MacAttack v4.7.6 MAC Checker Tool.

Diese Strategie implementiert die Authentifizierung aus MacAttack:
- Portal-Typ-Erkennung via version.js
- api_sig=262 (vs iSTB's 263)
- X-Random Header für erweiterte Authentifizierung
- auth_second_step=1 (vs iSTB's 0)
- URL-encoded metrics

Unterschiede zu iSTB:
- api_sig: 262 vs 263
- auth_second_step: 1 vs 0
- X-Random Header: Ja vs Nein
- Portal-Erkennung: version.js vs path probing
"""

import hashlib
import json
import logging
import time
import urllib.parse
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .base import BasePortalStrategy, HandshakeResult, PortalIdentity

logger = logging.getLogger(__name__)


class MacAttackStrategy(BasePortalStrategy):
    """
    MacAttack Strategy - MAC Checker Tool Authentifizierung.
    
    Implementiert die Authentifizierungslogik aus MacAttack v4.7.6
    mit X-Random Header, api_sig=262 und auth_second_step=1.
    """
    
    NAME = "macattack"
    DESCRIPTION = "MacAttack Style - X-Random header, api_sig 262, auth_second_step 1"
    
    # Standard MAG250 Werte (wie in MacAttack)
    DEFAULT_MODEL = "MAG250"
    DEFAULT_VERSION = "ImageDescription: 0.2.18-r23-250; ImageDate: Wed Aug 29 10:49:53 EEST 2018"
    DEFAULT_HW_VERSION = "1.7-BD-00"
    
    # api_sig für MacAttack (262 vs iSTB's 263)
    API_SIG = 262
    
    def __init__(self, portal_url: str, identity: PortalIdentity,
                 user_agent: str = 'MAG250', timeout: int = 10,
                 proxy: Optional[str] = None, use_cloudscraper: Optional[bool] = None):
        super().__init__(portal_url, identity, user_agent, timeout, proxy, use_cloudscraper)
        
        self._token = None
        self._token_random = None
        self._session = None
        self._portal_type = None  # "portal.php" or "stalker_portal/server/load.php"
        self._portal_version = "5.3.1"
        
        # Computed values (like MacAttack)
        self._sn = hashlib.md5(self.identity.mac.encode()).hexdigest().upper()[:13]
        self._device_id = hashlib.sha256(self._sn.encode()).hexdigest().upper()
        self._device_id2 = hashlib.sha256(self.identity.mac.encode()).hexdigest().upper()
        self._hw_version_2 = hashlib.sha1(self.identity.mac.encode()).hexdigest()
        
        # Override base class portal detection
        self._detected_portal_type = "stalker"
    
    @property
    def portal_type(self) -> str:
        """Return detected portal type for benchmark."""
        return "stalker"
    
    @property
    def portal_version(self) -> str:
        """Return detected portal version for benchmark."""
        return self._portal_version
    
    def _get_session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            if self.use_cloudscraper:
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
    
    def _get_base_cookies(self) -> Dict[str, str]:
        """Get base cookies like MacAttack."""
        return {
            "adid": self._hw_version_2,
            "debug": "1",
            "device_id2": self._device_id2,
            "device_id": self._device_id,
            "hw_version": self.DEFAULT_HW_VERSION,
            "mac": self.identity.mac,
            "sn": self._sn,
            "stb_lang": "en",
            "timezone": self.identity.timezone or "America/Los_Angeles",
        }
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Get base headers like MacAttack."""
        return {
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept-Encoding": "identity",
            "Accept": "*/*",
        }
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = self._get_base_headers()
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._token_random:
            headers["X-Random"] = self._token_random
        return headers
    
    def _detect_portal_type(self) -> str:
        """
        Detect portal type via version.js like MacAttack.
        
        Returns portal endpoint: "portal.php" or "stalker_portal/server/load.php"
        """
        parsed = urlparse(self.portal_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        session = self._get_session()
        headers = self._get_base_headers()
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        
        # Check for type "portal" via /c/version.js
        try:
            version_url = f"{base_url}/c/version.js"
            response = session.get(version_url, headers=headers, proxies=proxies, timeout=5)
            if response.status_code == 200:
                import re
                match = re.search(r"var ver = ['\"](.*?)['\"];", response.text)
                if match:
                    self._portal_version = match.group(1)
                    logger.info(f"MacAttackStrategy: Detected portal type: PORTAL version: {self._portal_version}")
                    return "portal.php"
        except Exception as e:
            logger.debug(f"MacAttackStrategy: Not type PORTAL: {e}")
        
        # Check for type "stalker_portal" via /stalker_portal/c/version.js
        try:
            version_url = f"{base_url}/stalker_portal/c/version.js"
            response = session.get(version_url, headers=headers, proxies=proxies, timeout=5)
            if response.status_code == 200:
                import re
                match = re.search(r"var ver = ['\"](.*?)['\"];", response.text)
                if match:
                    self._portal_version = match.group(1)
                    logger.info(f"MacAttackStrategy: Detected portal type: STALKER_PORTAL version: {self._portal_version}")
                    return "stalker_portal/server/load.php"
        except Exception as e:
            logger.debug(f"MacAttackStrategy: Not type STALKER_PORTAL: {e}")
        
        # Default to portal.php
        logger.info("MacAttackStrategy: Defaulting to portal.php")
        return "portal.php"
    
    def _get_portal_url(self) -> str:
        """Get the full portal URL with detected endpoint."""
        if self._portal_type is None:
            self._portal_type = self._detect_portal_type()
        
        parsed = urlparse(self.portal_url)
        base_path = parsed.path.rstrip('/')
        
        # Remove trailing endpoint if present
        for endpoint in ['/portal.php', '/load.php', '/server/load.php', '/stalker_portal/server/load.php']:
            if base_path.endswith(endpoint):
                base_path = base_path[:-len(endpoint)]
                break
        
        # Avoid double stalker_portal
        if "stalker_portal" in base_path and "stalker_portal" in self._portal_type:
            base_path = base_path.replace("/stalker_portal", "")
        
        base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}"
        return f"{base_url}/{self._portal_type}"

    def perform_handshake(self) -> HandshakeResult:
        """
        Perform handshake like MacAttack with X-Random header support.
        
        1. Handshake to get token and random
        2. If random present, use X-Random header for get_profile
        """
        try:
            portal_url = self._get_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            # Step 1: Initial handshake
            handshake_url = f"{portal_url}?action=handshake&type=stb&token=&JsHttpRequest=1-xml"
            
            logger.info(f"MacAttackStrategy: Handshake to {portal_url}")
            
            response = session.get(
                handshake_url,
                headers=self._get_base_headers(),
                cookies=self._get_base_cookies(),
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
            self._token_random = js.get("random", "")
            
            if not self._token:
                return HandshakeResult(
                    success=False,
                    error="No token received from handshake",
                    engine_used=self.NAME
                )
            
            logger.info(f"MacAttackStrategy: Got token, random={'yes' if self._token_random else 'no'}")
            
            # Step 2: Get profile with extended parameters
            # If we have token_random, use X-Random header (MacAttack specific)
            if self._token_random:
                sig = hashlib.sha256(self._token_random.encode()).hexdigest().upper()
                
                metrics = {
                    "mac": self.identity.mac,
                    "sn": self._sn,
                    "type": "STB",
                    "model": self.DEFAULT_MODEL,
                    "uid": self._device_id,
                    "random": self._token_random,
                }
                metrics_encoded = urllib.parse.quote(json.dumps(metrics))
                
                profile_url = (
                    f"{portal_url}?type=stb&action=get_profile&hd=1"
                    f"&ver={self.DEFAULT_VERSION}; PORTAL version: {self._portal_version}; "
                    f"API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c"
                    f"&num_banks=2&sn={self._sn}&stb_type={self.DEFAULT_MODEL}&client_type=STB"
                    f"&image_version=218&video_out=hdmi&device_id={self._device_id2}"
                    f"&device_id2={self._device_id2}&sig={sig}&auth_second_step=1"
                    f"&hw_version={self.DEFAULT_HW_VERSION}&not_valid_token=0"
                    f"&metrics={metrics_encoded}&hw_version_2={self._hw_version_2}"
                    f"&timestamp={round(time.time())}&api_sig={self.API_SIG}&prehash=0"
                )
                
                logger.info(f"MacAttackStrategy: get_profile with X-Random header, api_sig={self.API_SIG}")
                
                response = session.get(
                    profile_url,
                    headers=self._get_auth_headers(),
                    cookies=self._get_base_cookies(),
                    proxies=proxies,
                    timeout=self.timeout
                )
            else:
                # Simple get_profile without X-Random
                profile_url = (
                    f"{portal_url}?type=stb&action=get_profile&hd=1"
                    f"&sn={self._sn}&stb_type={self.DEFAULT_MODEL}&client_type=STB"
                    f"&device_id={self._device_id}&device_id2={self._device_id2}"
                    f"&hw_version={self.DEFAULT_HW_VERSION}"
                    f"&JsHttpRequest=1-xml"
                )
                
                headers = self._get_base_headers()
                headers["Authorization"] = f"Bearer {self._token}"
                
                response = session.get(
                    profile_url,
                    headers=headers,
                    cookies=self._get_base_cookies(),
                    proxies=proxies,
                    timeout=self.timeout
                )
            
            profile_data = {}
            try:
                profile_data = response.json().get("js", {})
            except Exception:
                pass
            
            # Extract expiry info
            expire_date = profile_data.get("phone", "") or profile_data.get("expire_billing_date", "")
            
            # Update cache on success
            self._update_engine_cache()
            
            return HandshakeResult(
                success=True,
                token=self._token,
                token_random=self._token_random,
                engine_used=self.NAME,
                portal_type="stalker",
                portal_version=self._portal_version,
                expire_date=expire_date,
                extra_data={
                    "profile": profile_data,
                    "api_sig": self.API_SIG,
                    "has_x_random": bool(self._token_random),
                }
            )
            
        except Exception as e:
            logger.error(f"MacAttackStrategy handshake failed: {e}")
            return HandshakeResult(
                success=False,
                error=str(e),
                engine_used=self.NAME
            )
    
    def create_link(self, cmd: str, token: Optional[str] = None, 
                    content_type: str = "itv") -> Optional[str]:
        """Create stream link like MacAttack."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return None
                use_token = result.token
            
            portal_url = self._get_portal_url()
            session = self._get_session()
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            
            params = {
                "type": content_type,
                "action": "create_link",
                "cmd": cmd,
                "forced_storage": "false",
                "disable_ad": "false",
                "download": "false",
                "force_ch_link_check": "false",
                "JsHttpRequest": "1-xml"
            }
            
            response = session.get(
                portal_url,
                params=params,
                headers=self._get_auth_headers(),
                cookies=self._get_base_cookies(),
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
                        logger.info(f"MacAttackStrategy: Created link: {cmd_result[:60]}...")
                        return cmd_result
            
            return None
            
        except Exception as e:
            logger.error(f"MacAttackStrategy create_link failed: {e}")
            return None
    
    def get_all_channels(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all channels like MacAttack."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
                use_token = result.token
            
            portal_url = self._get_portal_url()
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
                headers=self._get_auth_headers(),
                cookies=self._get_base_cookies(),
                proxies=proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                js = data.get("js", {})
                
                if isinstance(js, dict) and "data" in js:
                    channels = js["data"]
                    logger.info(f"MacAttackStrategy: Got {len(channels)} channels")
                    return channels
                elif isinstance(js, list):
                    logger.info(f"MacAttackStrategy: Got {len(js)} channels")
                    return js
            
            return []
            
        except Exception as e:
            logger.error(f"MacAttackStrategy get_all_channels failed: {e}")
            return []
    
    def get_genres(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get channel genres/categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._get_portal_url()
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
                headers=self._get_auth_headers(),
                cookies=self._get_base_cookies(),
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
            logger.error(f"MacAttackStrategy get_genres failed: {e}")
            return []
    
    def get_vod_categories(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get VOD categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._get_portal_url()
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
                headers=self._get_auth_headers(),
                cookies=self._get_base_cookies(),
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
            logger.error(f"MacAttackStrategy get_vod_categories failed: {e}")
            return []
    
    def get_series_categories(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Series categories."""
        try:
            use_token = token or self._token
            if not use_token:
                result = self.perform_handshake()
                if not result.success:
                    return []
            
            portal_url = self._get_portal_url()
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
                headers=self._get_auth_headers(),
                cookies=self._get_base_cookies(),
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
            logger.error(f"MacAttackStrategy get_series_categories failed: {e}")
            return []
