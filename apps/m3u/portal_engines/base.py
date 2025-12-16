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
