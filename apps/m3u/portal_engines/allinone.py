"""
AllinOne Portal Engine - Best-of-All kombiniert.

Kombiniert die besten Techniken aus allen Engines:
- MacAttack: X-Random Header, Portal-Typ-Erkennung
- iSTB: api_signature 263
- EStalker: Prehash-Support, adid Cookie
- BoxPirate: Signature, Referer Header
- OB2_2025: Erweiterte Metriken

Da AllinOne am längsten dauert, ist es als umfassender Fallback gedacht,
der ALLES versucht um eine Verbindung herzustellen.
"""

import hashlib
import json
import logging
import random
import re
import string
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, quote

from .base import BasePortalStrategy, PortalIdentity, HandshakeResult

logger = logging.getLogger(__name__)


class AllinOneStrategy(BasePortalStrategy):
    """
    AllinOne Best-of-All Strategy - Kombiniert die besten Techniken aus allen Engines.
    
    Features:
    - Alle Cookies: mac, stb_lang, timezone, adid
    - Vollständige Metriken: serial_number, device_id, device_id2, signature, hw_version_2, prehash
    - api_signature: 262, 263 (beide versuchen)
    - X-Random Header Support (MacAttack)
    - Portal-Typ-Erkennung via version.js
    - Prehash-Support für "missing" Responses
    - GET/POST Fallback für alle Operationen
    - User-Agent Rotation bei Fehlern
    - Referer Header für create_link
    """
    
    NAME = "allinone"
    DESCRIPTION = "AllinOne Best-of-All (Kombiniert alle Techniken)"
    
    # User-Agent Pool für Rotation
    USER_AGENT_POOL = [
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 369 Safari/533.3',
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3',
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 2721 Safari/533.3',
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 5 rev: 3116 Safari/533.3',
    ]
    
    # Erweiterte Endpoints
    ENDPOINTS = [
        '/portal.php',
        '/stalker_portal/server/load.php',
        '/server/load.php',
        '/c/',
    ]
    
    # API Signatures to try
    API_SIGNATURES = [263, 262, 261]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_ua_index = 0
        self._token_random = None
        self._detected_portal_type = None
        self._portal_version = "5.3.1"
    
    def _get_cookies(self) -> Dict[str, str]:
        """AllinOne Cookies - Alle wichtigen Cookies kombiniert."""
        return {
            "mac": self.identity.mac,
            "stb_lang": self.identity.lang,
            "timezone": self.identity.timezone,
            "adid": self.identity.adid,
            "debug": "1",
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "hw_version": "1.7-BD-00",
            "sn": self.identity.serial_number,
        }
    
    def _get_base_headers(self) -> Dict[str, str]:
        """AllinOne Headers - Erweiterte Headers mit Rotation und X-Random."""
        parsed = urlparse(self.portal_url)
        
        # Rotiere User-Agent
        ua = self.USER_AGENT_POOL[self._current_ua_index % len(self.USER_AGENT_POOL)]
        
        # Bestimme STB-Modell aus User-Agent
        if "MAG254" in ua:
            model = "MAG254"
        elif "MAG322" in ua:
            model = "MAG322"
        elif "MAG424" in ua:
            model = "MAG424"
        else:
            model = "MAG250"
        
        headers = {
            "Host": parsed.netloc,
            "Accept": "*/*",
            "User-Agent": ua,
            "Accept-Encoding": "gzip, deflate, identity",
            "X-User-Agent": f"Model: {model}; Link: WiFi",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        }
        
        # MacAttack X-Random Header wenn verfügbar
        if self._token_random:
            headers["X-Random"] = self._token_random
        
        return headers
    
    def _rotate_user_agent(self):
        """Rotiere zum nächsten User-Agent."""
        self._current_ua_index = (self._current_ua_index + 1) % len(self.USER_AGENT_POOL)
        logger.debug(f"AllinOne: Rotated to User-Agent index {self._current_ua_index}")
    
    def _detect_portal_type(self) -> str:
        """Detect portal type via version.js (MacAttack style)."""
        if self._detected_portal_type:
            return self._detected_portal_type
        
        parsed = urlparse(self.portal_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        proxies = self._get_proxies()
        
        # Check for type "portal" via /c/version.js
        try:
            version_url = f"{base_url}/c/version.js"
            response = self.session.get(version_url, timeout=5, proxies=proxies, verify=False)
            if response.status_code == 200:
                match = re.search(r"var ver = ['\"](.*?)['\"];", response.text)
                if match:
                    self._portal_version = match.group(1)
                    self._detected_portal_type = "/portal.php"
                    logger.debug(f"AllinOne: Detected portal type: PORTAL version: {self._portal_version}")
                    return self._detected_portal_type
        except Exception:
            pass
        
        # Check for type "stalker_portal"
        try:
            version_url = f"{base_url}/stalker_portal/c/version.js"
            response = self.session.get(version_url, timeout=5, proxies=proxies, verify=False)
            if response.status_code == 200:
                match = re.search(r"var ver = ['\"](.*?)['\"];", response.text)
                if match:
                    self._portal_version = match.group(1)
                    self._detected_portal_type = "/stalker_portal/server/load.php"
                    logger.debug(f"AllinOne: Detected portal type: STALKER_PORTAL version: {self._portal_version}")
                    return self._detected_portal_type
        except Exception:
            pass
        
        # Default
        self._detected_portal_type = "/portal.php"
        return self._detected_portal_type
    
    def _prehash_handshake(self, url: str, headers: Dict, cookies: Dict, 
                           proxies: Optional[Dict]) -> HandshakeResult:
        """Prehash-Methode für Portale die "missing" zurückgeben."""
        try:
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
                    logger.info(f"AllinOne: Prehash handshake successful")
                    return HandshakeResult(
                        success=True,
                        token=token,
                        token_random=js.get("random", ""),
                        portal_type="stalker",
                        engine_used=self.NAME,
                    )
        except Exception as e:
            logger.debug(f"AllinOne prehash handshake failed: {e}")
        
        return HandshakeResult(success=False, error="Prehash failed", engine_used=self.NAME)
    
    def perform_handshake(self) -> HandshakeResult:
        """
        AllinOne Handshake - Versucht ALLE Methoden.
        
        Ablauf:
        1. Portal-Typ-Erkennung via version.js
        2. Standard Handshake mit GET
        3. Standard Handshake mit POST
        4. Bei "missing" Response: Prehash-Methode
        5. Bei Fehler: User-Agent rotieren und wiederholen
        """
        # Detect portal type first
        detected_endpoint = self._detect_portal_type()
        
        # Sortiere Endpoints - detected zuerst
        endpoints_to_try = [detected_endpoint] + [e for e in self.ENDPOINTS if e != detected_endpoint]
        
        proxies = self._get_proxies()
        
        # Versuche mit allen User-Agents
        for ua_attempt in range(len(self.USER_AGENT_POOL)):
            headers = self._get_base_headers()
            cookies = self._get_cookies()
            
            for endpoint in endpoints_to_try:
                url = f"{self.portal_url}{endpoint}"
                params = {
                    "type": "stb",
                    "action": "handshake",
                    "token": "",
                    "JsHttpRequest": "1-xml",
                }
                
                # Try GET
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
                        
                        # Prüfe auf "missing" Nachricht
                        if "msg" in js and "missing" in js.get("msg", "").lower():
                            logger.debug(f"AllinOne: Got 'missing' response, trying prehash method")
                            result = self._prehash_handshake(url, headers, cookies, proxies)
                            if result.success:
                                return result
                            continue
                        
                        token = js.get("token")
                        if token:
                            self._token_random = js.get("random", "")
                            logger.info(f"AllinOne: Handshake successful via GET on {endpoint}")
                            return HandshakeResult(
                                success=True,
                                token=token,
                                token_random=self._token_random,
                                portal_type="stalker",
                                portal_version=self._portal_version,
                                engine_used=self.NAME,
                            )
                except Exception as e:
                    logger.debug(f"AllinOne GET handshake failed for {endpoint}: {e}")
                
                # Try POST
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
                        
                        if "msg" in js and "missing" in js.get("msg", "").lower():
                            result = self._prehash_handshake(url, headers, cookies, proxies)
                            if result.success:
                                return result
                            continue
                        
                        token = js.get("token")
                        if token:
                            self._token_random = js.get("random", "")
                            logger.info(f"AllinOne: Handshake successful via POST on {endpoint}")
                            return HandshakeResult(
                                success=True,
                                token=token,
                                token_random=self._token_random,
                                portal_type="stalker",
                                portal_version=self._portal_version,
                                engine_used=self.NAME,
                            )
                except Exception as e:
                    logger.debug(f"AllinOne POST handshake failed for {endpoint}: {e}")
            
            # Rotiere User-Agent für nächsten Versuch
            self._rotate_user_agent()
        
        return HandshakeResult(success=False, error="All methods failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """AllinOne Profil mit allen Metriken."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        dt = datetime.now()
        timestamp = str(int(dt.timestamp()))
        
        metrics = {
            "type": "stb",
            "model": "MAG254",
            "mac": self.identity.mac,
            "sn": self.identity.serial_number,
            "uid": "",
            "random": self._token_random or ""
        }
        
        # Versuche verschiedene api_signatures
        for api_sig in self.API_SIGNATURES:
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
                "signature": self.identity.signature,
                "hw_version": "1.7-BD-00",
                "hw_version_2": self.identity.hw_version_2,
                "metrics": quote(json.dumps(metrics)),
                "timestamp": timestamp,
                "api_signature": str(api_sig),
                "prehash": self.identity.prehash,
                "auth_second_step": "1",
                "not_valid_token": "0",
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
                        data = response.json()
                        if data.get("js"):
                            logger.debug(f"AllinOne: get_profile successful with api_sig {api_sig}")
                            return data
                except Exception as e:
                    logger.debug(f"AllinOne get_profile failed for {endpoint}: {e}")
                    continue
        
        return {}
    
    def create_link(self, cmd: str) -> Optional[str]:
        """Create stream link - versucht alle Methoden."""
        if not self.identity.token:
            result = self.perform_handshake()
            if not result.success:
                return None
            self.identity.token = result.token
        
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
            
            # Try GET
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
                            logger.debug(f"AllinOne: Portal returned empty list for cmd={cmd}")
                        continue
                    
                    link = js.get("cmd", "").split()[-1]
                    if link and link.startswith("http"):
                        logger.info(f"AllinOne: create_link successful via GET")
                        return link
            except Exception as e:
                logger.debug(f"AllinOne create_link GET failed: {e}")
            
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
                            logger.debug(f"AllinOne: Portal returned empty list for cmd={cmd}")
                        continue
                    
                    link = js.get("cmd", "").split()[-1]
                    if link and link.startswith("http"):
                        logger.info(f"AllinOne: create_link successful via POST")
                        return link
            except Exception as e:
                logger.debug(f"AllinOne create_link POST failed: {e}")
        
        return None
    
    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels - versucht alle Methoden."""
        if not self.identity.token:
            result = self.perform_handshake()
            if not result.success:
                return []
            self.identity.token = result.token
        
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {self.identity.token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        params = {
            "type": "itv",
            "action": "get_all_channels",
            "force_ch_link_check": "",
            "JsHttpRequest": "1-xml",
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            
            # Try GET
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=30,  # Längerer Timeout für Channel-Liste
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    channels = data.get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"AllinOne: Got {len(channels)} channels via GET")
                        return channels
            except Exception as e:
                logger.debug(f"AllinOne get_all_channels GET failed: {e}")
            
            # Try POST
            try:
                response = self.session.post(
                    url,
                    data=params,
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    timeout=30,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    channels = data.get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"AllinOne: Got {len(channels)} channels via POST")
                        return channels
            except Exception as e:
                logger.debug(f"AllinOne get_all_channels POST failed: {e}")
        
        return []
