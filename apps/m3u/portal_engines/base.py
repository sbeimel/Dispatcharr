"""
Base classes for Portal Engines.

Contains:
- PortalIdentity: MAC-basierte Identität mit generierten Werten
- HandshakeResult: Ergebnis eines Handshake-Versuchs
- BasePortalStrategy: Abstrakte Basisklasse für alle Engines
"""

import hashlib
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from requests.adapters import HTTPAdapter

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

logger = logging.getLogger(__name__)


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
    portal_version: Optional[str] = None
    engine_used: Optional[str] = None
    error: Optional[str] = None
    status: int = 0
    blocked: str = "0"
    expire_date: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


class BasePortalStrategy(ABC):
    """
    Abstrakte Basisklasse für Portal-Strategien.
    
    Jede konkrete Strategie (MacReplay, OB2_2025, EStalker, etc.) 
    erbt von dieser Klasse und implementiert perform_handshake().
    """
    
    NAME = "base"
    
    # Standard User-Agents für verschiedene STB-Modelle
    USER_AGENTS = {
        'MAG200': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
        'MAG250': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3',
        'MAG254': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 254 Safari/533.3',
        'MAG322': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 322 Safari/533.3',
        'MAG324': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG324 stbapp ver: 4 rev: 324 Safari/533.3',
        'MAG349': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG349 stbapp ver: 4 rev: 349 Safari/533.3',
        'MAG351': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG351 stbapp ver: 4 rev: 351 Safari/533.3',
        'MAG410': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG410 stbapp ver: 4 rev: 410 Safari/533.3',
        'MAG420': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG420 stbapp ver: 4 rev: 420 Safari/533.3',
        'MAG424': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 4 rev: 424 Safari/533.3',
        'MAG520': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG520 stbapp ver: 5 rev: 520 Safari/533.3',
        'MAG540': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG540 stbapp ver: 5 rev: 540 Safari/533.3',
        'AURA': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) AURAHD stbapp ver: 2 rev: 250 Safari/533.3',
        'FORMULER': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) Formuler stbapp ver: 2 rev: 250 Safari/533.3',
    }
    
    # Standard Portal-Endpunkte
    PORTAL_ENDPOINTS = [
        '/portal.php',
        '/server/load.php',
        '/stalker_portal/server/load.php',
    ]
    
    # Alias for compatibility
    ENDPOINTS = PORTAL_ENDPOINTS
    
    def __init__(self, portal_url: str, identity: PortalIdentity, 
                 user_agent: str = 'MAG250', timeout: int = 10,
                 proxy: Optional[str] = None, use_cloudscraper: Optional[bool] = None):
        """
        Initialisiere die Strategie.
        
        Args:
            portal_url: Portal-URL (wird normalisiert)
            identity: PortalIdentity mit MAC und generierten Werten
            user_agent: User-Agent Preset oder custom String
            timeout: Request-Timeout in Sekunden
            proxy: Optional Proxy-URL
            use_cloudscraper: Cloudscraper verwenden (None = aus Settings lesen)
        """
        # Normalize portal URL
        portal_url = portal_url.rstrip('/')
        known_endpoints = ['/portal.php', '/load.php', '/server/load.php']
        for endpoint in known_endpoints:
            if portal_url.endswith(endpoint):
                portal_url = portal_url[:-len(endpoint)]
                break
        
        self.portal_url = portal_url.rstrip('/')
        self.identity = identity
        self.user_agent = self.USER_AGENTS.get(user_agent, user_agent)
        self.timeout = timeout
        self.proxy = proxy
        
        # Cloudscraper setting
        if use_cloudscraper is not None:
            self.use_cloudscraper = use_cloudscraper and CLOUDSCRAPER_AVAILABLE
        else:
            self.use_cloudscraper = self._should_use_cloudscraper()
        
        self.session = self._create_session()
        
        if self.use_cloudscraper:
            logger.info(f"{self.NAME}: Cloudscraper ENABLED")
        else:
            logger.debug(f"{self.NAME}: Cloudscraper DISABLED")
        
        # Portal type/version for benchmark detection
        # Default to "stalker" since all MAC portal engines are Stalker-based
        self._detected_portal_type = "stalker"
        self._detected_portal_version = None
    
    @property
    def portal_type(self) -> Optional[str]:
        """Return detected portal type for benchmark (stalker, xtream, xui, etc.)."""
        return self._detected_portal_type
    
    @property
    def portal_version(self) -> Optional[str]:
        """Return detected portal version for benchmark."""
        return self._detected_portal_version
    
    def _should_use_cloudscraper(self) -> bool:
        """Check if cloudscraper should be used based on global settings."""
        if not CLOUDSCRAPER_AVAILABLE:
            return False
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            return settings.cloudscraper_enabled
        except Exception:
            return True  # Default to enabled
    
    def _create_session(self) -> requests.Session:
        """Erstelle HTTP-Session mit optionalem Cloudscraper."""
        if self.use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
            session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'linux',
                    'desktop': True
                }
            )
        else:
            session = requests.Session()
        
        # No automatic retries - handled at higher level
        adapter = HTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration."""
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}
    
    @abstractmethod
    def perform_handshake(self) -> HandshakeResult:
        """
        Führe Handshake mit dem Portal durch.
        
        Returns:
            HandshakeResult mit Token und Status
        """
        pass
    
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
        
        for endpoint in self.PORTAL_ENDPOINTS:
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
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Basis-Headers für alle Requests."""
        from urllib.parse import urlparse
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
    
    @abstractmethod
    def create_link(self, cmd: str) -> Optional[str]:
        """
        Erstelle Stream-Link aus cmd.
        
        Args:
            cmd: Portal-Command (z.B. "ffrt http://...")
            
        Returns:
            Aufgelöste Stream-URL oder None
        """
        pass
    
    @abstractmethod
    def get_all_channels(self) -> list:
        """
        Hole alle Kanäle vom Portal.
        
        Returns:
            Liste von Kanal-Dictionaries
        """
        pass
    
    def _create_link_base(self, cmd: str) -> Optional[str]:
        """
        Base implementation for create_link.
        Can be used by subclasses that don't need custom logic.
        """
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
        
        # Try GET first, then POST
        for method in ["GET", "POST"]:
            data = self._make_request(params, self.identity.token, method)
            if data:
                try:
                    link = data.get("js", {}).get("cmd", "").split()[-1]
                    if link and (link.startswith("http://") or link.startswith("https://")):
                        logger.info(f"{self.NAME}: create_link successful via {method}")
                        return link
                except Exception as e:
                    logger.debug(f"{self.NAME}: create_link parse failed: {e}")
        
        return None
    
    def _get_all_channels_base(self) -> list:
        """
        Base implementation for get_all_channels.
        Can be used by subclasses that don't need custom logic.
        """
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
                        logger.info(f"{self.NAME}: Got {len(channels)} channels via {method}")
                        return channels
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_all_channels parse failed: {e}")
        
        return []

    # ============== VOD Methods ==============
    
    def get_genres(self, token: Optional[str] = None) -> list:
        """
        Get live TV genres/categories from portal.
        
        Args:
            token: Authentication token (optional, will use identity.token if not provided)
            
        Returns:
            List of genre dicts or empty list
        """
        use_token = token or self.identity.token
        if not use_token:
            result = self.perform_handshake()
            if not result.success:
                return []
            use_token = self.identity.token
        
        params = {
            "type": "itv",
            "action": "get_genres",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, use_token, method)
            if data:
                try:
                    genres = data.get("js", [])
                    if genres:
                        logger.info(f"{self.NAME}: Got {len(genres)} genres via {method}")
                        return genres
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_genres parse failed: {e}")
        
        return []
    
    def get_vod_categories(self, token: Optional[str] = None) -> list:
        """
        Get VOD categories from portal.
        
        Args:
            token: Authentication token (optional, will use identity.token if not provided)
            
        Returns:
            List of category dicts or empty list
        """
        use_token = token or self.identity.token
        if not use_token:
            result = self.perform_handshake()
            if not result.success:
                return []
            use_token = self.identity.token
        
        params = {
            "type": "vod",
            "action": "get_categories",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, use_token, method)
            if data:
                try:
                    categories = data.get("js", [])
                    if categories:
                        logger.info(f"{self.NAME}: Got {len(categories)} VOD categories via {method}")
                        return categories
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_vod_categories parse failed: {e}")
        
        return []
    
    def get_vod_items(self, token: Optional[str] = None, category_id: str = "*",
                      page: int = 1, sortby: str = "added") -> dict:
        """
        Get VOD items from portal.
        
        Args:
            token: Authentication token (optional)
            category_id: Category ID or "*" for all
            page: Page number
            sortby: Sort order (added, name, rating)
            
        Returns:
            Dict with 'data' list and 'total_items'
        """
        use_token = token or self.identity.token
        if not use_token:
            result = self.perform_handshake()
            if not result.success:
                return {"data": [], "total_items": 0}
            use_token = self.identity.token
        
        params = {
            "type": "vod",
            "action": "get_ordered_list",
            "category": category_id,
            "p": str(page),
            "sortby": sortby,
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, use_token, method)
            if data:
                try:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    if items:
                        logger.info(f"{self.NAME}: Got {len(items)} VOD items via {method}")
                        return {"data": items, "total_items": total}
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_vod_items parse failed: {e}")
        
        return {"data": [], "total_items": 0}
    
    def get_series_categories(self, token: Optional[str] = None) -> list:
        """
        Get Series categories from portal.
        
        Args:
            token: Authentication token (optional)
            
        Returns:
            List of category dicts or empty list
        """
        use_token = token or self.identity.token
        if not use_token:
            result = self.perform_handshake()
            if not result.success:
                return []
            use_token = self.identity.token
        
        params = {
            "type": "series",
            "action": "get_categories",
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, use_token, method)
            if data:
                try:
                    categories = data.get("js", [])
                    if categories:
                        logger.info(f"{self.NAME}: Got {len(categories)} Series categories via {method}")
                        return categories
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_series_categories parse failed: {e}")
        
        return []
    
    def get_series_items(self, token: Optional[str] = None, category_id: str = "*",
                         page: int = 1, sortby: str = "added") -> dict:
        """
        Get Series items from portal.
        
        Args:
            token: Authentication token (optional)
            category_id: Category ID or "*" for all
            page: Page number
            sortby: Sort order
            
        Returns:
            Dict with 'data' list and 'total_items'
        """
        use_token = token or self.identity.token
        if not use_token:
            result = self.perform_handshake()
            if not result.success:
                return {"data": [], "total_items": 0}
            use_token = self.identity.token
        
        params = {
            "type": "series",
            "action": "get_ordered_list",
            "category": category_id,
            "p": str(page),
            "sortby": sortby,
        }
        
        for method in ["GET", "POST"]:
            data = self._make_request(params, use_token, method)
            if data:
                try:
                    js = data.get("js", {})
                    items = js.get("data", [])
                    total = js.get("total_items", len(items))
                    if items:
                        logger.info(f"{self.NAME}: Got {len(items)} Series items via {method}")
                        return {"data": items, "total_items": total}
                except Exception as e:
                    logger.debug(f"{self.NAME}: get_series_items parse failed: {e}")
        
        return {"data": [], "total_items": 0}
