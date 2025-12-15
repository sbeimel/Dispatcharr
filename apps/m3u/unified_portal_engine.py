"""
Unified Portal Engine - Superlösung für MAC/STB Portal-Kommunikation.

Kombiniert die besten Strategien aus:
- MacReplayXC (Standard)
- OB2_2025 (Alternative Handshake-Logik)
- EStalker (Enigma2 Stalker Client)
- BoxPirate (Dreambox Stalker Client)
- AJPan (Enigma2 Panel)

Requirements: 100.1-100.4
"""

import hashlib
import json
import logging
import random
import string
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlencode, quote

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


class PortalEngine(Enum):
    """Verfügbare Portal-Engines."""
    MACREPLAY = "macreplay"          # Standard MacReplayXC
    OB2_2025 = "ob2_2025"            # OB2_2025 Prüflogik
    ESTALKER = "estalker"            # EStalker Enigma2
    BOXPIRATE = "boxpirate"          # BoxPirate Dreambox
    UNIFIED = "unified"              # Unified (alle kombiniert)
    AUTO = "auto"                    # Automatische Erkennung


@dataclass
class PortalIdentity:
    """Portal-Identität mit allen notwendigen Parametern."""
    mac: str
    lang: str = "en_GB.utf8"
    timezone: str = "Europe/Berlin"
    token: Optional[str] = None
    token_random: Optional[str] = None
    play_token: Optional[str] = None
    
    # Generierte Werte
    serial_number: str = field(init=False)
    device_id: str = field(init=False)
    device_id2: str = field(init=False)
    adid: str = field(init=False)
    signature: str = field(init=False)
    hw_version_2: str = field(init=False)
    prehash: str = field(init=False)
    
    # Status
    status: str = ""
    blocked: str = ""
    expire_date: str = ""
    
    def __post_init__(self):
        """Generiere alle abgeleiteten Werte."""
        mac_clean = self.mac.replace(":", "").upper()
        
        self.serial_number = hashlib.md5(mac_clean.encode()).hexdigest().upper()[:13]
        self.device_id = hashlib.sha256(mac_clean.encode()).hexdigest().upper()
        self.device_id2 = hashlib.sha256(mac_clean.encode()).hexdigest().upper()
        self.adid = hashlib.md5((self.serial_number + self.mac).encode()).hexdigest()
        self.signature = hashlib.sha256((self.serial_number + mac_clean).encode()).hexdigest().upper()
        self.hw_version_2 = hashlib.sha1(mac_clean.encode()).hexdigest()
        self.prehash = hashlib.sha1((self.serial_number + self.mac).encode()).hexdigest()


@dataclass
class HandshakeResult:
    """Ergebnis eines Handshake-Versuchs."""
    success: bool
    token: Optional[str] = None
    token_random: Optional[str] = None
    play_token: Optional[str] = None
    portal_type: Optional[str] = None
    engine_used: Optional[str] = None
    error: Optional[str] = None
    status: int = 0
    blocked: str = "0"
    expire_date: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


class BasePortalStrategy:
    """Basis-Klasse für Portal-Strategien."""
    
    NAME = "base"
    DESCRIPTION = "Base Strategy"
    
    # Standard User-Agents
    USER_AGENTS = {
        'MAG250': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
        'MAG254': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 369 Safari/533.3',
        'MAG322': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 2721 Safari/533.3',
        'MAG424': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 5 rev: 3116 Safari/533.3',
    }
    
    # Standard Endpoints
    ENDPOINTS = [
        '/server/load.php',
        '/portal.php',
        '/stalker_portal/server/load.php',
        '/c/server/load.php',
    ]
    
    def __init__(self, portal_url: str, identity: PortalIdentity, 
                 user_agent: str = 'MAG250', timeout: int = 30):
        self.portal_url = portal_url.rstrip('/')
        self.identity = identity
        self.user_agent = self.USER_AGENTS.get(user_agent, user_agent)
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Erstelle HTTP-Session mit Retry-Logik."""
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Basis-Headers für alle Requests."""
        parsed = urlparse(self.portal_url)
        return {
            "Host": parsed.netloc,
            "Accept": "*/*",
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "X-User-Agent": "Model: MAG250; Link: WiFi",
            "Connection": "close",
            "Pragma": "no-cache",
            "Cache-Control": "no-store, no-cache, must-revalidate",
        }
    
    def _get_cookies(self) -> Dict[str, str]:
        """Standard-Cookies."""
        return {
            "mac": self.identity.mac,
            "stb_lang": self.identity.lang,
            "timezone": self.identity.timezone,
        }
    
    def perform_handshake(self) -> HandshakeResult:
        """Führe Handshake durch - muss überschrieben werden."""
        raise NotImplementedError
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """Hole Profil-Daten - muss überschrieben werden."""
        raise NotImplementedError


class MacReplayStrategy(BasePortalStrategy):
    """MacReplayXC Standard-Strategie."""
    
    NAME = "macreplay"
    DESCRIPTION = "MacReplayXC Standard (GET/POST Fallback)"
    
    def perform_handshake(self) -> HandshakeResult:
        """Standard MacReplay Handshake."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            params = {
                "type": "stb",
                "action": "handshake",
                "JsHttpRequest": "1-xml",
            }
            
            try:
                # Versuche GET
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                
                # Fallback: POST
                response = self.session.post(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
                        return HandshakeResult(
                            success=True,
                            token=token,
                            token_random=js.get("random", ""),
                            portal_type="stalker",
                            engine_used=self.NAME,
                        )
                        
            except Exception as e:
                logger.debug(f"MacReplay handshake failed for {endpoint}: {e}")
                continue
        
        return HandshakeResult(success=False, error="All endpoints failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """Hole Profil mit MacReplay-Parametern."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        
        params = {
            "type": "stb",
            "action": "get_profile",
            "JsHttpRequest": "1-xml",
            "hd": "1",
            "sn": self.identity.serial_number,
            "stb_type": "MAG250",
            "client_type": "STB",
            "image_version": "218",
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "hw_version": "1.7-BD-00",
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            try:
                response = self.session.post(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"MacReplay get_profile failed for {endpoint}: {e}")
                continue
        
        return {}


class EStalkerStrategy(BasePortalStrategy):
    """EStalker Enigma2 Strategie - basiert auf EStalker Plugin."""
    
    NAME = "estalker"
    DESCRIPTION = "EStalker (Enigma2 Style mit erweiterten Metriken)"
    
    def _get_cookies(self) -> Dict[str, str]:
        """EStalker-spezifische Cookies mit adid."""
        cookies = super()._get_cookies()
        cookies["adid"] = self.identity.adid
        return cookies
    
    def perform_handshake(self) -> HandshakeResult:
        """EStalker Handshake mit Prehash-Support."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        
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
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    
                    # EStalker: Prüfe auf "missing" Nachricht
                    if "msg" in js and "missing" in js.get("msg", "").lower():
                        # Generiere Fake-Token für Prehash
                        fake_token = ''.join(random.choices(
                            string.ascii_uppercase + string.digits, k=32
                        ))
                        prehash = hashlib.sha1(fake_token.encode()).hexdigest()
                        
                        headers["Authorization"] = f"Bearer {fake_token}"
                        params["mac"] = self.identity.mac
                        params["prehash"] = prehash
                        
                        response = self.session.post(
                            url,
                            params=params,
                            headers=headers,
                            cookies=cookies,
                            timeout=self.timeout,
                            verify=False
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            js = data.get("js", {})
                    
                    token = js.get("token")
                    if token:
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
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """EStalker Profil mit erweiterten Metriken (MAG254 Style)."""
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        
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
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"EStalker get_profile failed for {endpoint}: {e}")
                continue
        
        return {}


class BoxPirateStrategy(BasePortalStrategy):
    """BoxPirate Dreambox Strategie."""
    
    NAME = "boxpirate"
    DESCRIPTION = "BoxPirate (Dreambox Style mit Signature)"
    
    def perform_handshake(self) -> HandshakeResult:
        """BoxPirate Handshake."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        
        params = {
            "type": "stb",
            "action": "handshake",
            "token": "",
        }
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
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
            "auth_second_step": True,
            "not_valid_token": False,
            "sn": self.identity.serial_number,
            "device_id": self.identity.device_id,
            "device_id2": self.identity.device_id2,
            "signature": self.identity.signature,
            "stb_type": "MAG250",
            "ver": "ImageDescription: 0.2.16-250; ImageDate: 18 Mar 2013 19:56:53 GMT+0200; PORTAL version: 4.9.9; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566",
            "hd": True,
            "num_banks": 1,
            "image_version": 216,
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
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"BoxPirate get_profile failed for {endpoint}: {e}")
                continue
        
        return {}


class OB2_2025Strategy(BasePortalStrategy):
    """OB2_2025 Strategie mit erweiterter Handshake-Logik."""
    
    NAME = "ob2_2025"
    DESCRIPTION = "OB2_2025 (Erweiterte Prüflogik mit api_signature 263)"
    
    def perform_handshake(self) -> HandshakeResult:
        """OB2_2025 Handshake mit api_signature."""
        headers = self._get_base_headers()
        cookies = self._get_cookies()
        cookies["adid"] = self.identity.adid
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            params = {
                "type": "stb",
                "action": "handshake",
                "JsHttpRequest": "1-xml",
            }
            
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    js = data.get("js", {})
                    token = js.get("token")
                    
                    if token:
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
        cookies["adid"] = self.identity.adid
        
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
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            try:
                response = self.session.post(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=False
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"OB2_2025 get_profile failed for {endpoint}: {e}")
                continue
        
        return {}


class UnifiedPortalEngine:
    """
    Unified Portal Engine - Kombiniert alle Strategien.
    
    Versucht automatisch verschiedene Engines und wählt die beste.
    """
    
    # Verfügbare Strategien in Prioritätsreihenfolge
    STRATEGIES = {
        PortalEngine.MACREPLAY: MacReplayStrategy,
        PortalEngine.ESTALKER: EStalkerStrategy,
        PortalEngine.BOXPIRATE: BoxPirateStrategy,
        PortalEngine.OB2_2025: OB2_2025Strategy,
    }
    
    # Cache für erfolgreiche Strategien pro Portal
    _strategy_cache: Dict[str, PortalEngine] = {}
    
    def __init__(self, portal_url: str, mac: str, 
                 engine: PortalEngine = PortalEngine.AUTO,
                 user_agent: str = 'MAG250',
                 timeout: int = 30):
        self.portal_url = portal_url.rstrip('/')
        self.mac = mac
        self.engine = engine
        self.user_agent = user_agent
        self.timeout = timeout
        self.identity = PortalIdentity(mac=mac)
        self._last_result: Optional[HandshakeResult] = None
    
    def _get_cache_key(self) -> str:
        """Cache-Key für Portal."""
        return f"{self.portal_url}:{self.mac}"
    
    def _get_strategy(self, engine: PortalEngine) -> BasePortalStrategy:
        """Erstelle Strategie-Instanz."""
        strategy_class = self.STRATEGIES.get(engine)
        if not strategy_class:
            raise ValueError(f"Unknown engine: {engine}")
        
        return strategy_class(
            portal_url=self.portal_url,
            identity=self.identity,
            user_agent=self.user_agent,
            timeout=self.timeout
        )
    
    def perform_handshake(self) -> HandshakeResult:
        """
        Führe Handshake durch.
        
        Bei AUTO: Versuche alle Strategien und cache die erfolgreiche.
        """
        if self.engine == PortalEngine.AUTO or self.engine == PortalEngine.UNIFIED:
            return self._auto_handshake()
        else:
            strategy = self._get_strategy(self.engine)
            result = strategy.perform_handshake()
            self._last_result = result
            return result
    
    def _auto_handshake(self) -> HandshakeResult:
        """Automatischer Handshake mit allen Strategien."""
        cache_key = self._get_cache_key()
        
        # Prüfe Cache
        if cache_key in self._strategy_cache:
            cached_engine = self._strategy_cache[cache_key]
            logger.info(f"Using cached strategy: {cached_engine.value}")
            strategy = self._get_strategy(cached_engine)
            result = strategy.perform_handshake()
            if result.success:
                self._last_result = result
                return result
            # Cache war nicht mehr gültig
            del self._strategy_cache[cache_key]
        
        # Versuche alle Strategien
        errors = []
        for engine, strategy_class in self.STRATEGIES.items():
            logger.info(f"Trying strategy: {engine.value}")
            try:
                strategy = self._get_strategy(engine)
                result = strategy.perform_handshake()
                
                if result.success:
                    # Cache erfolgreiche Strategie
                    self._strategy_cache[cache_key] = engine
                    self._last_result = result
                    logger.info(f"Handshake successful with: {engine.value}")
                    return result
                else:
                    errors.append(f"{engine.value}: {result.error}")
            except Exception as e:
                errors.append(f"{engine.value}: {str(e)}")
                logger.debug(f"Strategy {engine.value} failed: {e}")
        
        # Alle fehlgeschlagen
        return HandshakeResult(
            success=False,
            error=f"All strategies failed: {'; '.join(errors)}",
            engine_used="unified"
        )
    
    def get_profile(self) -> Dict[str, Any]:
        """Hole Profil mit der zuletzt erfolgreichen Strategie."""
        if not self._last_result or not self._last_result.success:
            return {}
        
        engine = PortalEngine(self._last_result.engine_used) if self._last_result.engine_used in [e.value for e in PortalEngine] else PortalEngine.MACREPLAY
        
        try:
            strategy = self._get_strategy(engine)
            return strategy.get_profile(self._last_result.token)
        except Exception as e:
            logger.error(f"get_profile failed: {e}")
            return {}
    
    def full_login(self) -> HandshakeResult:
        """
        Vollständiger Login: Handshake + Profil.
        
        Returns:
            HandshakeResult mit allen Daten inkl. Status/Blocked.
        """
        result = self.perform_handshake()
        
        if not result.success:
            return result
        
        # Hole Profil
        profile_data = self.get_profile()
        
        if profile_data:
            js = profile_data.get("js", {})
            result.play_token = js.get("play_token")
            result.status = js.get("status", 0)
            result.blocked = js.get("blocked", "0")
            result.expire_date = js.get("tariff_expired_date", "")
            result.extra_data = js
        
        return result
    
    @classmethod
    def get_available_engines(cls) -> List[Dict[str, str]]:
        """Liste aller verfügbaren Engines."""
        engines = [
            {
                "id": PortalEngine.AUTO.value,
                "name": "Auto-Detect",
                "description": "Automatische Erkennung der besten Strategie"
            },
            {
                "id": PortalEngine.UNIFIED.value,
                "name": "Unified",
                "description": "Alle Strategien kombiniert"
            },
        ]
        
        for engine, strategy_class in cls.STRATEGIES.items():
            engines.append({
                "id": engine.value,
                "name": strategy_class.NAME.upper(),
                "description": strategy_class.DESCRIPTION
            })
        
        return engines
    
    @classmethod
    def clear_cache(cls):
        """Lösche Strategy-Cache."""
        cls._strategy_cache.clear()


# ============== Hilfsfunktionen ==============

def create_portal_client(portal_url: str, mac: str, 
                         engine: str = "auto",
                         user_agent: str = "MAG250") -> UnifiedPortalEngine:
    """
    Factory-Funktion für UnifiedPortalEngine.
    
    Args:
        portal_url: Portal-URL
        mac: MAC-Adresse
        engine: Engine-Name (auto, macreplay, estalker, boxpirate, ob2_2025)
        user_agent: User-Agent Preset
    
    Returns:
        UnifiedPortalEngine Instanz
    """
    try:
        engine_enum = PortalEngine(engine.lower())
    except ValueError:
        engine_enum = PortalEngine.AUTO
    
    return UnifiedPortalEngine(
        portal_url=portal_url,
        mac=mac,
        engine=engine_enum,
        user_agent=user_agent
    )


def test_portal_connection(portal_url: str, mac: str, 
                           engine: str = "auto") -> Dict[str, Any]:
    """
    Teste Portal-Verbindung mit allen Engines.
    
    Returns:
        Dict mit Testergebnissen pro Engine.
    """
    results = {}
    identity = PortalIdentity(mac=mac)
    
    for engine_enum, strategy_class in UnifiedPortalEngine.STRATEGIES.items():
        try:
            strategy = strategy_class(
                portal_url=portal_url,
                identity=identity
            )
            result = strategy.perform_handshake()
            results[engine_enum.value] = {
                "success": result.success,
                "token": result.token[:20] + "..." if result.token else None,
                "error": result.error,
            }
        except Exception as e:
            results[engine_enum.value] = {
                "success": False,
                "error": str(e)
            }
    
    return results
