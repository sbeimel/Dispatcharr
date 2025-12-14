"""
Cloudflare Bypass Manager - Modulares System für Cloudflare-Umgehung.

Kombiniert verschiedene Bypass-Strategien mit Failover-Kette:
1. Cloudscraper - Automatische Challenge-Lösung
2. Proxy-Rotation - Pool von getesteten Proxies
3. User-Agent Rotation - Verschiedene MAG User-Agents
4. Request-Timing - Zufällige Verzögerungen
5. Session Persistence - Cookie-Speicherung

Alle Strategien sind modular aktivierbar/deaktivierbar.
"""

import logging
import random
import time
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class CloudflareBlockedException(Exception):
    """Raised when Cloudflare blocks the request."""
    pass


class CloudflareBypassFailedException(Exception):
    """Raised when all bypass strategies fail."""
    pass


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class CloudflareBypassConfig:
    """Configuration for Cloudflare Bypass Manager."""
    enable_cloudflare_bypass: bool = True
    enable_cloudscraper: bool = True
    enable_proxy_rotation: bool = False
    enable_user_agent_rotation: bool = True
    enable_request_timing: bool = True
    enable_session_persistence: bool = True
    proxy_list: List[str] = None
    request_delay_min: float = 0.5
    request_delay_max: float = 2.0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.proxy_list is None:
            self.proxy_list = []


# ============================================================================
# User-Agent Pool
# ============================================================================

USER_AGENTS = {
    'MAG200': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
    'MAG250': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3',
    'MAG254': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 250 Safari/533.3',
    'MAG322': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 2721 Safari/533.3',
    'MAG324': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG324 stbapp ver: 4 rev: 2721 Safari/533.3',
    'MAG410': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG410 stbapp ver: 4 rev: 2721 Safari/533.3',
    'MAG424': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 4 rev: 2721 Safari/533.3',
    'MAG520': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG520 stbapp ver: 5 rev: 3000 Safari/533.3',
}


# ============================================================================
# Bypass Strategies
# ============================================================================

class BypassStrategy(ABC):
    """Abstract base class for bypass strategies."""
    
    name: str = "base"
    
    @abstractmethod
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        """Check if this strategy is enabled."""
        pass
    
    @abstractmethod
    def prepare_request(
        self, 
        url: str, 
        config: CloudflareBypassConfig,
        session: Optional[requests.Session] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Prepare request parameters for this strategy."""
        pass
    
    @abstractmethod
    def execute(
        self, 
        url: str, 
        config: CloudflareBypassConfig,
        session: Optional[requests.Session] = None,
        **kwargs
    ) -> requests.Response:
        """Execute the request with this strategy."""
        pass


class CloudscraperStrategy(BypassStrategy):
    """Uses cloudscraper library for automatic challenge solving."""
    
    name = "cloudscraper"
    
    def __init__(self):
        self._scraper = None
    
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        return config.enable_cloudscraper
    
    def _get_scraper(self):
        if self._scraper is None:
            try:
                import cloudscraper
                self._scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'linux',
                        'mobile': False
                    }
                )
            except ImportError:
                logger.warning("cloudscraper not installed, falling back to requests")
                self._scraper = requests.Session()
        return self._scraper
    
    def prepare_request(self, url: str, config: CloudflareBypassConfig, 
                       session: Optional[requests.Session] = None, **kwargs) -> Dict[str, Any]:
        return kwargs
    
    def execute(self, url: str, config: CloudflareBypassConfig,
               session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        scraper = self._get_scraper()
        method = kwargs.pop('method', 'GET').upper()
        
        if method == 'GET':
            return scraper.get(url, **kwargs)
        elif method == 'POST':
            return scraper.post(url, **kwargs)
        else:
            return scraper.request(method, url, **kwargs)


class ProxyRotationStrategy(BypassStrategy):
    """Rotates through a pool of proxies."""
    
    name = "proxy_rotation"
    
    def __init__(self):
        self._current_proxy_index = 0
        self._failed_proxies = set()
    
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        return config.enable_proxy_rotation and len(config.proxy_list) > 0
    
    def _get_next_proxy(self, config: CloudflareBypassConfig) -> Optional[str]:
        available = [p for p in config.proxy_list if p not in self._failed_proxies]
        if not available:
            self._failed_proxies.clear()
            available = config.proxy_list
        
        if not available:
            return None
        
        proxy = random.choice(available)
        return proxy
    
    def mark_proxy_failed(self, proxy: str):
        self._failed_proxies.add(proxy)
    
    def prepare_request(self, url: str, config: CloudflareBypassConfig,
                       session: Optional[requests.Session] = None, **kwargs) -> Dict[str, Any]:
        proxy = self._get_next_proxy(config)
        if proxy:
            kwargs['proxies'] = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return kwargs
    
    def execute(self, url: str, config: CloudflareBypassConfig,
               session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        kwargs = self.prepare_request(url, config, session, **kwargs)
        sess = session or requests.Session()
        method = kwargs.pop('method', 'GET').upper()
        
        try:
            if method == 'GET':
                return sess.get(url, **kwargs)
            elif method == 'POST':
                return sess.post(url, **kwargs)
            else:
                return sess.request(method, url, **kwargs)
        except Exception:
            if 'proxies' in kwargs:
                proxy = list(kwargs['proxies'].values())[0].replace('http://', '')
                self.mark_proxy_failed(proxy)
            raise


class UserAgentRotationStrategy(BypassStrategy):
    """Rotates through different MAG device user agents."""
    
    name = "user_agent_rotation"
    
    def __init__(self):
        self._last_user_agent = None
    
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        return config.enable_user_agent_rotation
    
    def _get_random_user_agent(self) -> str:
        agents = list(USER_AGENTS.values())
        agent = random.choice(agents)
        while agent == self._last_user_agent and len(agents) > 1:
            agent = random.choice(agents)
        self._last_user_agent = agent
        return agent
    
    def prepare_request(self, url: str, config: CloudflareBypassConfig,
                       session: Optional[requests.Session] = None, **kwargs) -> Dict[str, Any]:
        headers = kwargs.get('headers', {})
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self._get_random_user_agent()
        kwargs['headers'] = headers
        return kwargs
    
    def execute(self, url: str, config: CloudflareBypassConfig,
               session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        kwargs = self.prepare_request(url, config, session, **kwargs)
        sess = session or requests.Session()
        method = kwargs.pop('method', 'GET').upper()
        
        if method == 'GET':
            return sess.get(url, **kwargs)
        elif method == 'POST':
            return sess.post(url, **kwargs)
        else:
            return sess.request(method, url, **kwargs)


class RequestTimingStrategy(BypassStrategy):
    """Adds random delays between requests to simulate human behavior."""
    
    name = "request_timing"
    
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        return config.enable_request_timing
    
    def prepare_request(self, url: str, config: CloudflareBypassConfig,
                       session: Optional[requests.Session] = None, **kwargs) -> Dict[str, Any]:
        delay = random.uniform(config.request_delay_min, config.request_delay_max)
        time.sleep(delay)
        return kwargs
    
    def execute(self, url: str, config: CloudflareBypassConfig,
               session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        self.prepare_request(url, config, session, **kwargs)
        sess = session or requests.Session()
        method = kwargs.pop('method', 'GET').upper()
        
        if method == 'GET':
            return sess.get(url, **kwargs)
        elif method == 'POST':
            return sess.post(url, **kwargs)
        else:
            return sess.request(method, url, **kwargs)


class SessionPersistenceStrategy(BypassStrategy):
    """Maintains session cookies across requests."""
    
    name = "session_persistence"
    
    def __init__(self):
        self._sessions: Dict[str, requests.Session] = {}
    
    def is_enabled(self, config: CloudflareBypassConfig) -> bool:
        return config.enable_session_persistence
    
    def _get_session_key(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def get_session(self, url: str) -> requests.Session:
        key = self._get_session_key(url)
        if key not in self._sessions:
            self._sessions[key] = requests.Session()
        return self._sessions[key]
    
    def clear_session(self, url: str):
        key = self._get_session_key(url)
        if key in self._sessions:
            del self._sessions[key]
    
    def prepare_request(self, url: str, config: CloudflareBypassConfig,
                       session: Optional[requests.Session] = None, **kwargs) -> Dict[str, Any]:
        return kwargs
    
    def execute(self, url: str, config: CloudflareBypassConfig,
               session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        sess = self.get_session(url)
        method = kwargs.pop('method', 'GET').upper()
        
        if method == 'GET':
            return sess.get(url, **kwargs)
        elif method == 'POST':
            return sess.post(url, **kwargs)
        else:
            return sess.request(method, url, **kwargs)


# ============================================================================
# Main Manager
# ============================================================================

class CloudflareBypassManager:
    """
    Modularer Cloudflare-Bypass mit Failover-Kette.
    
    Kombiniert verschiedene Strategien und führt Failover durch,
    wenn eine Strategie fehlschlägt.
    """
    
    def __init__(self, config: Optional[CloudflareBypassConfig] = None):
        self.config = config or CloudflareBypassConfig()
        self._strategies: List[BypassStrategy] = []
        self._init_strategies()
    
    def _init_strategies(self):
        """Initialize enabled strategies in priority order."""
        self._strategies = [
            CloudscraperStrategy(),
            ProxyRotationStrategy(),
            UserAgentRotationStrategy(),
            RequestTimingStrategy(),
            SessionPersistenceStrategy(),
        ]
    
    def _is_cloudflare_challenge(self, response: requests.Response) -> bool:
        """Detect Cloudflare challenge response."""
        if response.status_code in [403, 503]:
            return True
        
        headers = {k.lower(): v for k, v in response.headers.items()}
        if 'cf-ray' in headers:
            return True
        
        text = response.text.lower()
        cf_indicators = [
            'cloudflare',
            'cf-browser-verification',
            'checking your browser',
            'ddos-guard',
            'please wait',
            'just a moment',
        ]
        return any(ind in text for ind in cf_indicators)
    
    def _is_rate_limited(self, response: requests.Response) -> bool:
        """Detect rate limiting."""
        return response.status_code == 429
    
    def make_request(
        self, 
        url: str, 
        method: str = 'GET',
        **kwargs
    ) -> requests.Response:
        """
        Make a request with automatic Cloudflare bypass.
        
        Tries each enabled strategy in order until one succeeds.
        
        Args:
            url: Target URL
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            CloudflareBypassFailedException: If all strategies fail
        """
        if not self.config.enable_cloudflare_bypass:
            sess = requests.Session()
            return sess.request(method, url, **kwargs)
        
        kwargs['method'] = method
        last_error = None
        last_response = None
        
        for strategy in self._strategies:
            if not strategy.is_enabled(self.config):
                continue
            
            for attempt in range(self.config.max_retries):
                try:
                    logger.debug(f"Trying strategy {strategy.name}, attempt {attempt + 1}")
                    response = strategy.execute(url, self.config, **kwargs.copy())
                    
                    if response.status_code == 200:
                        return response
                    
                    if self._is_cloudflare_challenge(response):
                        logger.debug(f"Cloudflare challenge detected with {strategy.name}")
                        last_response = response
                        break
                    
                    if self._is_rate_limited(response):
                        logger.debug("Rate limited, waiting before retry")
                        time.sleep(5)
                        continue
                    
                    return response
                    
                except Exception as e:
                    logger.debug(f"Strategy {strategy.name} failed: {e}")
                    last_error = e
                    continue
        
        if last_response is not None:
            return last_response
        
        raise CloudflareBypassFailedException(
            f"All bypass strategies failed. Last error: {last_error}"
        )
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for GET requests."""
        return self.make_request(url, method='GET', **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for POST requests."""
        return self.make_request(url, method='POST', **kwargs)


# ============================================================================
# Proxy Utilities (from MacAttack)
# ============================================================================

class ProxyFetcher:
    """
    Fetches and tests proxies from public sources.
    Based on MacAttack's ProxyFetcher implementation.
    """
    
    PROXY_SOURCES = [
        "https://spys.me/proxy.txt",
        "https://free-proxy-list.net/",
        "https://www.us-proxy.org/",
        "https://www.sslproxies.org/",
    ]
    
    @classmethod
    def fetch_proxies(cls) -> List[str]:
        """Fetch proxies from public sources."""
        proxies = []
        
        for source in cls.PROXY_SOURCES:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    found = cls._extract_proxies(response.text, source)
                    proxies.extend(found)
            except Exception as e:
                logger.debug(f"Failed to fetch from {source}: {e}")
        
        return list(set(proxies))
    
    @classmethod
    def _extract_proxies(cls, text: str, source: str) -> List[str]:
        """Extract proxy addresses from response text."""
        proxies = []
        
        if "spys.me" in source:
            pattern = r"[0-9]+(?:\.[0-9]+){3}:[0-9]+"
            matches = re.findall(pattern, text)
            proxies.extend(matches)
        else:
            pattern = r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>"
            matches = re.findall(pattern, text)
            proxies.extend([f"{ip}:{port}" for ip, port in matches])
        
        return proxies
    
    @classmethod
    def test_proxy(cls, proxy: str, timeout: int = 10) -> bool:
        """Test if a proxy is working."""
        test_url = "http://httpbin.org/ip"
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        
        try:
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False
    
    @classmethod
    def get_working_proxies(cls, max_workers: int = 10) -> List[str]:
        """Fetch and test proxies, returning only working ones."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_proxies = cls.fetch_proxies()
        working = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(cls.test_proxy, p): p for p in all_proxies}
            for future in as_completed(futures):
                proxy = futures[future]
                try:
                    if future.result():
                        working.append(proxy)
                except Exception:
                    pass
        
        return working


# ============================================================================
# Integration Helper
# ============================================================================

def get_bypass_manager_from_settings() -> CloudflareBypassManager:
    """
    Create a CloudflareBypassManager from Django settings.
    
    Reads configuration from MACPortalGlobalSettings model.
    """
    try:
        from .mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        
        config = CloudflareBypassConfig(
            enable_cloudflare_bypass=getattr(settings, 'enable_cloudflare_bypass', True),
            enable_cloudscraper=getattr(settings, 'enable_cloudscraper', True),
            enable_proxy_rotation=getattr(settings, 'enable_proxy_rotation', False),
            enable_user_agent_rotation=getattr(settings, 'enable_user_agent_rotation', True),
            enable_request_timing=getattr(settings, 'enable_request_timing', True),
            enable_session_persistence=getattr(settings, 'enable_session_persistence', True),
            proxy_list=getattr(settings, 'proxy_list', '').split('\n') if getattr(settings, 'proxy_list', '') else [],
            request_delay_min=getattr(settings, 'request_delay_min', 0.5),
            request_delay_max=getattr(settings, 'request_delay_max', 2.0),
        )
        
        return CloudflareBypassManager(config)
    except Exception as e:
        logger.warning(f"Could not load settings, using defaults: {e}")
        return CloudflareBypassManager()
