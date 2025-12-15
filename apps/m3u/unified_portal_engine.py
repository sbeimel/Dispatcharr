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

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

logger = logging.getLogger(__name__)


class PortalEngine(Enum):
    """Verfügbare Portal-Engines."""
    MACREPLAY = "macreplay"          # Standard MacReplayXC
    OB2_2025 = "ob2_2025"            # OB2_2025 Prüflogik
    ESTALKER = "estalker"            # EStalker Enigma2
    BOXPIRATE = "boxpirate"          # BoxPirate Dreambox
    ALLINONE = "allinone"            # Best-of-All kombiniert
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
    portal_type: Optional[str] = None  # stalker, xtream, xui
    portal_version: Optional[str] = None  # z.B. "5.3.0", "XUI 1.5.12"
    engine_used: Optional[str] = None
    error: Optional[str] = None
    status: int = 0
    blocked: str = "0"
    expire_date: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


def detect_portal_type_and_version(profile_data: Dict[str, Any], response_headers: Dict[str, str] = None) -> Tuple[str, str]:
    """
    Erkennt Portal-Typ und Version aus Profil-Daten und Response-Headers.
    
    Returns:
        Tuple[portal_type, portal_version]
        portal_type: "stalker", "xtream", "xui", "ministra", "unknown"
        portal_version: Version string oder "unknown"
    """
    portal_type = "unknown"
    portal_version = "unknown"
    
    # Check response headers for server info
    if response_headers:
        server = response_headers.get('Server', '').lower()
        x_powered_by = response_headers.get('X-Powered-By', '').lower()
        
        if 'nginx' in server:
            portal_type = "stalker"  # Most Stalker portals use nginx
        if 'xui' in x_powered_by or 'xtream' in x_powered_by:
            portal_type = "xui"
    
    # Check profile data for portal type indicators
    js_data = profile_data.get('js', profile_data)
    
    # XUI/Xtream indicators
    if js_data.get('panel_type') or js_data.get('xui_version'):
        portal_type = "xui"
        portal_version = js_data.get('xui_version', js_data.get('panel_version', 'unknown'))
    
    # Ministra/Stalker indicators
    if js_data.get('portal_version'):
        portal_version = js_data.get('portal_version')
        portal_type = "ministra" if 'ministra' in str(portal_version).lower() else "stalker"
    
    # Check for version in various fields
    version_fields = ['version', 'api_version', 'server_version', 'portal_version']
    for field in version_fields:
        if js_data.get(field) and portal_version == "unknown":
            portal_version = str(js_data.get(field))
    
    # Check for Xtream Codes specific fields
    if js_data.get('server_info', {}).get('xui'):
        portal_type = "xui"
        portal_version = js_data.get('server_info', {}).get('version', portal_version)
    
    # Check for exp_date format (Xtream uses Unix timestamp, Stalker uses date string)
    exp_date = js_data.get('exp_date') or js_data.get('expire_billing_date')
    if exp_date:
        try:
            # If it's a large number, it's likely Xtream (Unix timestamp)
            if isinstance(exp_date, (int, float)) or (isinstance(exp_date, str) and exp_date.isdigit() and len(exp_date) > 8):
                if portal_type == "unknown":
                    portal_type = "xtream"
        except Exception:
            pass
    
    return portal_type, portal_version


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
    
    # Standard Endpoints - optimized order (most common first)
    ENDPOINTS = [
        '/portal.php',
        '/server/load.php',
        '/stalker_portal/server/load.php',
    ]
    
    def __init__(self, portal_url: str, identity: PortalIdentity, 
                 user_agent: str = 'MAG250', timeout: int = 10,
                 proxy: Optional[str] = None, use_cloudscraper: Optional[bool] = None):
        # Normalize portal URL - remove trailing slash and extract base URL
        # Default timeout 10s for fast failover
        portal_url = portal_url.rstrip('/')
        
        # If URL ends with a known endpoint file, extract the base URL
        # This prevents double paths like /portal.php/portal.php
        known_endpoints = ['/portal.php', '/load.php', '/server/load.php']
        for endpoint in known_endpoints:
            if portal_url.endswith(endpoint):
                portal_url = portal_url[:-len(endpoint)]
                logger.debug(f"Normalized portal URL: removed {endpoint} suffix")
                break
        
        self.portal_url = portal_url.rstrip('/')
        self.identity = identity
        self.user_agent = self.USER_AGENTS.get(user_agent, user_agent)
        self.timeout = timeout
        self.proxy = proxy
        # Allow explicit override of cloudscraper setting, otherwise check global settings
        if use_cloudscraper is not None:
            self.use_cloudscraper = use_cloudscraper and CLOUDSCRAPER_AVAILABLE
        else:
            self.use_cloudscraper = self._should_use_cloudscraper()
        self.session = self._create_session()
        
        if self.use_cloudscraper:
            logger.info(f"{self.NAME}: Using cloudscraper for Cloudflare bypass")
    
    def _should_use_cloudscraper(self) -> bool:
        """Check if cloudscraper should be used based on global settings."""
        if not CLOUDSCRAPER_AVAILABLE:
            logger.debug("Cloudscraper not available (not installed)")
            return False
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            enabled = settings.cloudscraper_enabled
            logger.debug(f"Cloudscraper setting from DB: {enabled}")
            return enabled
        except Exception as e:
            # Default to True if settings can't be loaded
            logger.debug(f"Could not load cloudscraper setting, defaulting to True: {e}")
            return True
    
    def _create_session(self) -> requests.Session:
        """Erstelle HTTP-Session mit optionalem Cloudscraper für Cloudflare-Bypass."""
        if self.use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
            # Use cloudscraper for Cloudflare bypass - same config as original MacReplay
            session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'linux',  # Match original MacReplay
                    'desktop': True
                }
            )
            logger.debug(f"{self.NAME}: Created cloudscraper session for Cloudflare bypass")
        else:
            session = requests.Session()
            logger.debug(f"{self.NAME}: Created standard requests session (no cloudscraper)")
        
        # NO automatic retries - we handle retries manually at a higher level
        # This prevents urllib3 from retrying on timeouts which causes long waits
        adapter = HTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration."""
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}
    
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
    
    def _make_request(self, params: Dict[str, Any], token: str, 
                       method: str = "GET") -> Optional[Dict[str, Any]]:
        """
        Make a request to the portal with proper headers/cookies for this engine.
        
        Args:
            params: Request parameters (type, action, etc.)
            token: Authentication token
            method: HTTP method (GET or POST)
            
        Returns:
            JSON response or None
        """
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        params["JsHttpRequest"] = "1-xml"
        
        for endpoint in self.ENDPOINTS:
            url = f"{self.portal_url}{endpoint}"
            
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url, params=params, headers=headers,
                        cookies=cookies, proxies=proxies,
                        timeout=self.timeout, verify=False
                    )
                else:
                    response = self.session.post(
                        url, data=params, headers=headers,
                        cookies=cookies, proxies=proxies,
                        timeout=self.timeout, verify=False
                    )
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"{self.NAME}: Request failed for {endpoint}: {e}")
        
        return None

    def create_link(self, cmd: str, token: str, content_type: str = "itv", 
                    series: str = "0") -> Optional[str]:
        """
        Resolve a portal channel command into a final stream URL.
        
        Args:
            cmd: Channel command (e.g., "ffmpeg http://...")
            token: Authentication token
            content_type: "itv" for live TV, "vod" for VOD
            series: Episode number for series (default "0")
            
        Returns:
            Resolved stream URL or None
        """
        params = {
            "type": content_type,
            "action": "create_link",
            "cmd": cmd,
            "series": series,
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
            "force_ch_link_check": "false",
        }
        
        # Try GET first, then POST
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    link = data.get("js", {}).get("cmd", "").split()[-1]
                    if link and (link.startswith("http://") or link.startswith("https://")):
                        logger.info(f"{self.NAME}: create_link successful via {method}")
                        return link
                except Exception as e:
                    logger.debug(f"{self.NAME}: create_link parse failed: {e}")
        
        return None

    def get_all_channels(self, token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all live TV channels from portal.
        
        Args:
            token: Authentication token
            
        Returns:
            List of channel dicts or None
        """
        params = {
            "type": "itv",
            "action": "get_all_channels",
            "force_ch_link_check": "",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    channels = data.get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"{self.NAME}: Got {len(channels)} channels via {method}")
                        return channels
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_all_channels parse failed: {e}")
        
        return None

    def get_genres(self, token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get live TV genres/categories from portal.
        
        Args:
            token: Authentication token
            
        Returns:
            List of genre dicts or None
        """
        params = {
            "type": "itv",
            "action": "get_genres",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    genres = data.get("js", [])
                    if genres:
                        logger.info(f"{self.NAME}: Got {len(genres)} genres via {method}")
                        return genres
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_genres parse failed: {e}")
        
        return None

    def get_vod_categories(self, token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get VOD categories from portal.
        
        Args:
            token: Authentication token
            
        Returns:
            List of category dicts or None
        """
        params = {
            "type": "vod",
            "action": "get_categories",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    categories = data.get("js", [])
                    if categories:
                        logger.info(f"{self.NAME}: Got {len(categories)} VOD categories via {method}")
                        return categories
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_vod_categories parse failed: {e}")
        
        return None

    def get_vod_items(self, token: str, category_id: str = "*", 
                      page: int = 1, sortby: str = "added") -> Optional[Dict[str, Any]]:
        """
        Get VOD items from portal.
        
        Args:
            token: Authentication token
            category_id: Category ID or "*" for all
            page: Page number
            sortby: Sort order (added, name, rating)
            
        Returns:
            Dict with 'data' list and 'total_items' or None
        """
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
                try:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    logger.info(f"{self.NAME}: Got {len(items)} VOD items via {method}")
                    return {"data": items, "total_items": total}
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_vod_items parse failed: {e}")
        
        return None

    def get_series_categories(self, token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get Series categories from portal.
        
        Args:
            token: Authentication token
            
        Returns:
            List of category dicts or None
        """
        params = {
            "type": "series",
            "action": "get_categories",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    categories = data.get("js", [])
                    if categories:
                        logger.info(f"{self.NAME}: Got {len(categories)} Series categories via {method}")
                        return categories
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_series_categories parse failed: {e}")
        
        return None

    def get_series_items(self, token: str, category_id: str = "*",
                         page: int = 1, sortby: str = "added") -> Optional[Dict[str, Any]]:
        """
        Get Series items from portal.
        
        Args:
            token: Authentication token
            category_id: Category ID or "*" for all
            page: Page number
            sortby: Sort order
            
        Returns:
            Dict with 'data' list and 'total_items' or None
        """
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
                try:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    logger.info(f"{self.NAME}: Got {len(items)} Series items via {method}")
                    return {"data": items, "total_items": total}
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_series_items parse failed: {e}")
        
        return None

    def get_epg(self, token: str, period: int = 24) -> Optional[Dict[str, Any]]:
        """
        Get EPG data from portal.
        
        Args:
            token: Authentication token
            period: EPG period in hours
            
        Returns:
            EPG data dict or None
        """
        params = {
            "type": "itv",
            "action": "get_epg_info",
            "period": str(period),
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    epg = data.get("js", {}).get("data", {})
                    if epg:
                        logger.info(f"{self.NAME}: Got EPG data via {method}")
                        return epg
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_epg parse failed: {e}")
        
        return None

    def get_short_epg(self, token: str, channel_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get short EPG for a specific channel.
        
        Args:
            token: Authentication token
            channel_id: Channel ID
            
        Returns:
            List of EPG entries or None
        """
        params = {
            "type": "itv",
            "action": "get_short_epg",
            "ch_id": channel_id,
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    epg = data.get("js", {}).get("data", [])
                    if epg:
                        logger.info(f"{self.NAME}: Got short EPG for channel {channel_id}")
                        return epg
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_short_epg parse failed: {e}")
        
        return None

    def get_account_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get account info (expiry, etc.) from portal.
        
        Args:
            token: Authentication token
            
        Returns:
            Account info dict or None
        """
        params = {
            "type": "account_info",
            "action": "get_main_info",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, token, method)
            if data:
                try:
                    info = data.get("js", {})
                    if info:
                        logger.info(f"{self.NAME}: Got account info")
                        return info
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_account_info parse failed: {e}")
        
        return None


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


class AllinOneStrategy(BasePortalStrategy):
    """
    AllinOne Best-of-All Strategy - Kombiniert die besten Techniken aus allen Engines.
    
    Features:
    - Alle Cookies: mac, stb_lang, timezone, adid (EStalker/OB2_2025)
    - Vollständige Metriken: serial_number, device_id, device_id2, signature, hw_version_2, prehash
    - api_signature: 263 (OB2_2025)
    - Prehash-Support für "missing" Responses (EStalker)
    - GET/POST Fallback für alle Operationen
    - User-Agent Rotation bei Fehlern (limited to 2 attempts for speed)
    - Referer Header für create_link (BoxPirate)
    """
    
    NAME = "allinone"
    DESCRIPTION = "AllinOne Best-of-All (Kombiniert alle Techniken)"
    
    # User-Agent Rotation Pool - MAG254 first (most compatible)
    USER_AGENT_POOL = [
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 369 Safari/533.3',
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3',
    ]
    
    # Optimized Endpoints - most common first for speed
    ENDPOINTS = [
        '/portal.php',
        '/server/load.php',
        '/stalker_portal/server/load.php',
        '/c/',
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_ua_index = 0
        self._failed_attempts = 0
    
    def _get_cookies(self) -> Dict[str, str]:
        """AllinOne Cookies - Alle wichtigen Cookies kombiniert."""
        return {
            "mac": self.identity.mac,
            "stb_lang": self.identity.lang,
            "timezone": self.identity.timezone,
            "adid": self.identity.adid,  # EStalker/OB2_2025
        }
    
    def _get_base_headers(self) -> Dict[str, str]:
        """AllinOne Headers - Erweiterte Headers mit Rotation."""
        parsed = urlparse(self.portal_url)
        
        # Rotiere User-Agent bei Fehlern
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
        
        return {
            "Host": parsed.netloc,
            "Accept": "*/*",
            "User-Agent": ua,
            "Accept-Encoding": "gzip, deflate",
            "X-User-Agent": f"Model: {model}; Link: WiFi",
            "Connection": "close",
            "Pragma": "no-cache",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        }
    
    def _rotate_user_agent(self):
        """Rotiere zum nächsten User-Agent."""
        self._current_ua_index = (self._current_ua_index + 1) % len(self.USER_AGENT_POOL)
        logger.debug(f"AllinOne: Rotated to User-Agent index {self._current_ua_index}")
    
    def perform_handshake(self) -> HandshakeResult:
        """
        AllinOne Handshake - Kombiniert alle Techniken.
        
        1. Standard Handshake versuchen
        2. Bei "missing" Response: Prehash-Methode (EStalker)
        3. Bei Fehler: User-Agent rotieren und erneut versuchen
        """
        max_ua_attempts = len(self.USER_AGENT_POOL)
        
        for ua_attempt in range(max_ua_attempts):
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
                    # Versuche POST zuerst (wie EStalker)
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
                        
                        # Prüfe auf "missing" Nachricht (EStalker Prehash-Methode)
                        if "msg" in js and "missing" in js.get("msg", "").lower():
                            logger.debug(f"AllinOne: Got 'missing' response, trying prehash method")
                            result = self._prehash_handshake(url, headers, cookies)
                            if result.success:
                                return result
                            continue
                        
                        token = js.get("token")
                        if token:
                            return HandshakeResult(
                                success=True,
                                token=token,
                                token_random=js.get("random", ""),
                                portal_type="stalker",
                                engine_used=self.NAME,
                            )
                    
                    # Fallback: GET (wie MacReplay)
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
                        
                        if "msg" in js and "missing" in js.get("msg", "").lower():
                            result = self._prehash_handshake(url, headers, cookies)
                            if result.success:
                                return result
                            continue
                        
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
                    logger.debug(f"AllinOne handshake failed for {endpoint}: {e}")
                    continue
            
            # Rotiere User-Agent für nächsten Versuch
            if ua_attempt < max_ua_attempts - 1:
                self._rotate_user_agent()
                logger.info(f"AllinOne: Rotating User-Agent, attempt {ua_attempt + 2}/{max_ua_attempts}")
        
        return HandshakeResult(success=False, error="All endpoints and User-Agents failed", engine_used=self.NAME)
    
    def _prehash_handshake(self, url: str, headers: Dict[str, str], 
                           cookies: Dict[str, str]) -> HandshakeResult:
        """
        Prehash-Handshake Methode (aus EStalker).
        
        Generiert Fake-Token und Prehash für Portale die "missing" zurückgeben.
        """
        # Generiere Fake-Token
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
                token = js.get("token")
                
                if token:
                    logger.info("AllinOne: Prehash handshake successful")
                    return HandshakeResult(
                        success=True,
                        token=token,
                        token_random=js.get("random", ""),
                        portal_type="stalker",
                        engine_used=self.NAME,
                    )
        except Exception as e:
            logger.debug(f"AllinOne prehash handshake failed: {e}")
        
        return HandshakeResult(success=False, error="Prehash handshake failed", engine_used=self.NAME)
    
    def get_profile(self, token: str) -> Dict[str, Any]:
        """
        AllinOne Profil - Kombiniert alle Metriken.
        
        Verwendet:
        - MAG254 Metriken (EStalker)
        - api_signature 263 (OB2_2025)
        - Signature (BoxPirate)
        - Prehash (EStalker/OB2_2025)
        """
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        
        dt = datetime.now()
        timestamp = str(int(dt.timestamp()))
        
        # Vollständige Metriken (kombiniert aus allen Engines)
        metrics = {
            "type": "stb",
            "model": "MAG254",
            "mac": self.identity.mac,
            "sn": self.identity.serial_number,
            "uid": "",
            "random": self.identity.token_random or ""
        }
        
        # Vollständige Parameter (Best-of-All)
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
            "signature": self.identity.signature,  # BoxPirate
            "auth_second_step": "1",
            "hw_version": "1.7-BD-00",
            "hw_version_2": self.identity.hw_version_2,
            "not_valid_token": "0",
            "metrics": quote(json.dumps(metrics)),
            "timestamp": timestamp,
            "api_signature": "263",  # OB2_2025
            "prehash": self.identity.prehash,  # EStalker/OB2_2025
        }
        
        # Versuche POST zuerst, dann GET
        for method in ["POST", "GET"]:
            for endpoint in self.ENDPOINTS:
                url = f"{self.portal_url}{endpoint}"
                try:
                    if method == "POST":
                        response = self.session.post(
                            url,
                            params=params,
                            headers=headers,
                            cookies=cookies,
                            timeout=self.timeout,
                            verify=False
                        )
                    else:
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
                        if data.get("js"):
                            logger.info(f"AllinOne: get_profile successful via {method}")
                            return data
                except Exception as e:
                    logger.debug(f"AllinOne get_profile failed for {endpoint} via {method}: {e}")
                    continue
        
        return {}
    
    def _make_request(self, params: Dict[str, Any], token: str, 
                       method: str = "GET") -> Optional[Dict[str, Any]]:
        """
        AllinOne Request - Mit allen erweiterten Features.
        
        - Alle Cookies (inkl. adid)
        - Erweiterte Headers (inkl. Referer)
        - GET/POST Fallback
        """
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        params["JsHttpRequest"] = "1-xml"
        
        # Versuche beide Methoden
        methods_to_try = [method.upper()]
        if method.upper() == "GET":
            methods_to_try.append("POST")
        else:
            methods_to_try.append("GET")
        
        for try_method in methods_to_try:
            for endpoint in self.ENDPOINTS:
                url = f"{self.portal_url}{endpoint}"
                
                try:
                    if try_method == "GET":
                        response = self.session.get(
                            url, params=params, headers=headers,
                            cookies=cookies, proxies=proxies,
                            timeout=self.timeout, verify=False
                        )
                    else:
                        response = self.session.post(
                            url, data=params, headers=headers,
                            cookies=cookies, proxies=proxies,
                            timeout=self.timeout, verify=False
                        )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if data:
                                return data
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"AllinOne: Request failed for {endpoint} via {try_method}: {e}")
        
        return None
    
    def create_link(self, cmd: str, token: str, content_type: str = "itv", 
                    series: str = "0") -> Optional[str]:
        """
        AllinOne create_link - Mit Referer Header (BoxPirate Style).
        """
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {token}"
        # Referer für create_link (BoxPirate)
        parsed = urlparse(self.portal_url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/c/"
        
        cookies = self._get_cookies()
        proxies = self._get_proxies()
        
        params = {
            "type": content_type,
            "action": "create_link",
            "cmd": cmd,
            "series": series,
            "forced_storage": "false",
            "disable_ad": "false",
            "download": "false",
            "force_ch_link_check": "false",
            "JsHttpRequest": "1-xml",
        }
        
        # Versuche GET und POST
        for method in ["GET", "POST"]:
            for endpoint in self.ENDPOINTS:
                url = f"{self.portal_url}{endpoint}"
                
                try:
                    if method == "GET":
                        response = self.session.get(
                            url, params=params, headers=headers,
                            cookies=cookies, proxies=proxies,
                            timeout=self.timeout, verify=False
                        )
                    else:
                        response = self.session.post(
                            url, data=params, headers=headers,
                            cookies=cookies, proxies=proxies,
                            timeout=self.timeout, verify=False
                        )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            link = data.get("js", {}).get("cmd", "").split()[-1]
                            if link and (link.startswith("http://") or link.startswith("https://")):
                                logger.info(f"AllinOne: create_link successful via {method}")
                                return link
                        except Exception as e:
                            logger.debug(f"AllinOne: create_link parse failed: {e}")
                except Exception as e:
                    logger.debug(f"AllinOne: create_link failed for {endpoint} via {method}: {e}")
        
        return None


class UnifiedPortalEngine:
    """
    Unified Portal Engine - Kombiniert alle Strategien.
    
    Versucht automatisch verschiedene Engines und wählt die beste.
    Cloudscraper wird automatisch für alle Engines verwendet wenn aktiviert.
    """
    
    # Verfügbare Strategien in Prioritätsreihenfolge
    STRATEGIES = {
        PortalEngine.MACREPLAY: MacReplayStrategy,
        PortalEngine.ESTALKER: EStalkerStrategy,
        PortalEngine.BOXPIRATE: BoxPirateStrategy,
        PortalEngine.OB2_2025: OB2_2025Strategy,
        PortalEngine.ALLINONE: AllinOneStrategy,
    }
    
    # Optimized order for AUTO mode - fastest strategies first, skip allinone (redundant)
    AUTO_STRATEGY_ORDER = [
        PortalEngine.MACREPLAY,   # Fastest, most common
        PortalEngine.OB2_2025,    # Fast, good compatibility
        PortalEngine.ESTALKER,    # Medium speed
        PortalEngine.BOXPIRATE,   # Medium speed
        # AllinOne skipped in AUTO - it's redundant and slow
    ]
    
    # Cache für erfolgreiche Strategien pro Portal
    _strategy_cache: Dict[str, PortalEngine] = {}
    
    def __init__(self, portal_url: str, mac: str, 
                 engine: PortalEngine = PortalEngine.AUTO,
                 user_agent: str = 'MAG250',
                 timeout: int = 10,
                 use_cloudscraper: Optional[bool] = None):  # Fast timeout for quick failover
        self.portal_url = portal_url.rstrip('/')
        self.mac = mac
        self.engine = engine
        self.user_agent = user_agent
        self.timeout = timeout
        self.identity = PortalIdentity(mac=mac)
        self._last_result: Optional[HandshakeResult] = None
        
        # Determine cloudscraper setting - check global settings if not explicitly set
        if use_cloudscraper is not None:
            self._use_cloudscraper = use_cloudscraper
        else:
            self._use_cloudscraper = self._check_cloudscraper_setting()
        
        if self._use_cloudscraper:
            logger.info(f"UnifiedPortalEngine: Cloudscraper ENABLED for {portal_url}")
        else:
            logger.info(f"UnifiedPortalEngine: Cloudscraper DISABLED for {portal_url}")
    
    def _check_cloudscraper_setting(self) -> bool:
        """Check global cloudscraper setting."""
        if not CLOUDSCRAPER_AVAILABLE:
            logger.debug("Cloudscraper not available (not installed)")
            return False
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            return settings.cloudscraper_enabled
        except Exception as e:
            logger.debug(f"Could not load cloudscraper setting: {e}")
            return True  # Default to enabled
    
    def _get_cache_key(self) -> str:
        """Cache-Key für Portal."""
        return f"{self.portal_url}:{self.mac}"
    
    def _get_strategy(self, engine: PortalEngine) -> BasePortalStrategy:
        """Erstelle Strategie-Instanz mit cloudscraper setting."""
        strategy_class = self.STRATEGIES.get(engine)
        if not strategy_class:
            raise ValueError(f"Unknown engine: {engine}")
        
        return strategy_class(
            portal_url=self.portal_url,
            identity=self.identity,
            user_agent=self.user_agent,
            timeout=self.timeout,
            proxy=getattr(self, 'proxy', None),
            use_cloudscraper=self._use_cloudscraper  # Pass cloudscraper setting to strategy
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
        """Automatischer Handshake mit optimierter Strategie-Reihenfolge."""
        cache_key = self._get_cache_key()
        
        # Prüfe Cache - use cached strategy if available
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
            logger.info(f"Cached strategy {cached_engine.value} failed, trying others")
        
        # Versuche Strategien in optimierter Reihenfolge (schnellste zuerst)
        errors = []
        for engine in self.AUTO_STRATEGY_ORDER:
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
            HandshakeResult mit allen Daten inkl. Status/Blocked und Portal-Version.
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
            
            # Erkenne Portal-Typ und Version
            portal_type, portal_version = detect_portal_type_and_version(profile_data)
            if portal_type != "unknown":
                result.portal_type = portal_type
            if portal_version != "unknown":
                result.portal_version = portal_version
            
            logger.info(f"Portal detected: type={result.portal_type}, version={result.portal_version}")
        
        return result
    
    def create_link(self, cmd: str, content_type: str = "itv") -> Optional[str]:
        """
        Resolve a portal channel command into a final stream URL.
        Uses the configured/cached engine strategy.
        
        Args:
            cmd: Channel command (e.g., "ffmpeg http://...")
            content_type: "itv" for live TV, "vod" for VOD
            
        Returns:
            Resolved stream URL or raises exception
        """
        # Ensure we have a valid token
        if not self._last_result or not self._last_result.success:
            result = self.perform_handshake()
            if not result.success:
                raise ValueError(f"Handshake failed: {result.error}")
        
        token = self._last_result.token
        engine_used = self._last_result.engine_used
        
        # Determine which engine to use
        if engine_used and engine_used in [e.value for e in PortalEngine]:
            engine = PortalEngine(engine_used)
        elif self.engine != PortalEngine.AUTO and self.engine != PortalEngine.UNIFIED:
            engine = self.engine
        else:
            # Use cached strategy or default to MacReplay
            cache_key = self._get_cache_key()
            engine = self._strategy_cache.get(cache_key, PortalEngine.MACREPLAY)
        
        logger.info(f"UnifiedPortalEngine.create_link using engine: {engine.value}")
        
        try:
            strategy = self._get_strategy(engine)
            link = strategy.create_link(cmd, token, content_type)
            
            if link:
                return link
        except Exception as e:
            logger.debug(f"create_link with {engine.value} failed: {e}")
        
        # Fallback: Try all strategies if specific one failed
        if self.engine == PortalEngine.AUTO or self.engine == PortalEngine.UNIFIED:
            for fallback_engine in self.STRATEGIES.keys():
                if fallback_engine == engine:
                    continue
                try:
                    strategy = self._get_strategy(fallback_engine)
                    link = strategy.create_link(cmd, token, content_type)
                    if link:
                        logger.info(f"create_link fallback successful with {fallback_engine.value}")
                        return link
                except Exception as e:
                    logger.debug(f"create_link fallback with {fallback_engine.value} failed: {e}")
        
        raise ValueError(f"Could not create link for cmd: {cmd}")

    def _get_active_strategy_and_token(self):
        """Get the active strategy and token, performing handshake if needed."""
        if not self._last_result or not self._last_result.success:
            result = self.perform_handshake()
            if not result.success:
                raise ValueError(f"Handshake failed: {result.error}")
        
        token = self._last_result.token
        engine_used = self._last_result.engine_used
        
        if engine_used and engine_used in [e.value for e in PortalEngine]:
            engine = PortalEngine(engine_used)
        elif self.engine != PortalEngine.AUTO and self.engine != PortalEngine.UNIFIED:
            engine = self.engine
        else:
            cache_key = self._get_cache_key()
            engine = self._strategy_cache.get(cache_key, PortalEngine.MACREPLAY)
        
        strategy = self._get_strategy(engine)
        return strategy, token, engine

    def get_all_channels(self) -> Optional[List[Dict[str, Any]]]:
        """Get all live TV channels using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_all_channels using engine: {engine.value}")
        return strategy.get_all_channels(token)

    def get_genres(self) -> Optional[List[Dict[str, Any]]]:
        """Get live TV genres/categories using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_genres using engine: {engine.value}")
        return strategy.get_genres(token)

    def get_vod_categories(self) -> Optional[List[Dict[str, Any]]]:
        """Get VOD categories using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_vod_categories using engine: {engine.value}")
        return strategy.get_vod_categories(token)

    def get_vod_items(self, category_id: str = "*", page: int = 1, 
                      sortby: str = "added") -> Optional[Dict[str, Any]]:
        """Get VOD items using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_vod_items using engine: {engine.value}")
        return strategy.get_vod_items(token, category_id, page, sortby)

    def get_series_categories(self) -> Optional[List[Dict[str, Any]]]:
        """Get Series categories using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_series_categories using engine: {engine.value}")
        return strategy.get_series_categories(token)

    def get_series_items(self, category_id: str = "*", page: int = 1,
                         sortby: str = "added") -> Optional[Dict[str, Any]]:
        """Get Series items using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_series_items using engine: {engine.value}")
        return strategy.get_series_items(token, category_id, page, sortby)

    def get_epg(self, period: int = 24) -> Optional[Dict[str, Any]]:
        """Get EPG data using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_epg using engine: {engine.value}")
        return strategy.get_epg(token, period)

    def get_short_epg(self, channel_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get short EPG for a channel using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_short_epg using engine: {engine.value}")
        return strategy.get_short_epg(token, channel_id)

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account info using the configured engine."""
        strategy, token, engine = self._get_active_strategy_and_token()
        logger.info(f"UnifiedPortalEngine.get_account_info using engine: {engine.value}")
        return strategy.get_account_info(token)
    
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
                         user_agent: str = "MAG250",
                         proxy: Optional[str] = None,
                         use_cloudscraper: Optional[bool] = None) -> UnifiedPortalEngine:
    """
    Factory-Funktion für UnifiedPortalEngine.
    
    Args:
        portal_url: Portal-URL
        mac: MAC-Adresse
        engine: Engine-Name (auto, macreplay, estalker, boxpirate, ob2_2025)
        user_agent: User-Agent Preset
        proxy: Optional proxy URL
        use_cloudscraper: Override cloudscraper setting (None = use global setting)
    
    Returns:
        UnifiedPortalEngine Instanz
    """
    try:
        engine_enum = PortalEngine(engine.lower())
    except ValueError:
        engine_enum = PortalEngine.AUTO
    
    client = UnifiedPortalEngine(
        portal_url=portal_url,
        mac=mac,
        engine=engine_enum,
        user_agent=user_agent,
        use_cloudscraper=use_cloudscraper
    )
    client.proxy = proxy  # Set proxy for create_link
    return client


def test_portal_connection(portal_url: str, mac: str, 
                           engine: str = "auto",
                           use_cloudscraper: Optional[bool] = None) -> Dict[str, Any]:
    """
    Teste Portal-Verbindung mit allen Engines.
    
    Args:
        portal_url: Portal URL
        mac: MAC address
        engine: Engine to test (or "auto" for all)
        use_cloudscraper: Override cloudscraper setting (None = use global setting)
    
    Returns:
        Dict mit Testergebnissen pro Engine.
    """
    results = {}
    identity = PortalIdentity(mac=mac)
    
    # Determine cloudscraper setting
    if use_cloudscraper is None:
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            use_cloudscraper = settings.cloudscraper_enabled
        except Exception:
            use_cloudscraper = True
    
    logger.info(f"test_portal_connection: cloudscraper={use_cloudscraper}")
    
    for engine_enum, strategy_class in UnifiedPortalEngine.STRATEGIES.items():
        try:
            strategy = strategy_class(
                portal_url=portal_url,
                identity=identity,
                use_cloudscraper=use_cloudscraper  # Pass cloudscraper setting
            )
            result = strategy.perform_handshake()
            results[engine_enum.value] = {
                "success": result.success,
                "token": result.token[:20] + "..." if result.token else None,
                "error": result.error,
                "cloudscraper_used": use_cloudscraper and CLOUDSCRAPER_AVAILABLE,
            }
        except Exception as e:
            results[engine_enum.value] = {
                "success": False,
                "error": str(e)
            }
    
    return results
