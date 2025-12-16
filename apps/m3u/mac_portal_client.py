"""
MAC/STB Portal Client for Dispatcharr
Based on MacReplayXC v2.2.1 stb.py - Ported to Django

This module provides a comprehensive client for communicating with MAC/STB portals
(Stalker middleware) for IPTV services.
"""

import json
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse
import re
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def _is_debug_enabled():
    """Check if debug logging is enabled in MAC Portal settings."""
    try:
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        return getattr(settings, 'debug_logging_enabled', False)
    except Exception:
        return False


def _debug_log(message, *args, **kwargs):
    """Log debug message only if debug logging is enabled in settings."""
    if _is_debug_enabled():
        logger.info(f"[MAC-DEBUG] {message}", *args, **kwargs)
    else:
        logger.debug(message, *args, **kwargs)


# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    logger.info("cloudscraper not available - some portals with Cloudflare protection may not work")

# Session management with periodic refresh to prevent memory leaks
_session = None
_session_created = 0
_SESSION_MAX_AGE = 300  # Refresh session every 5 minutes
_session_uses_cloudscraper = False  # Track if current session uses cloudscraper


def _should_use_cloudscraper_global():
    """Check if cloudscraper should be used based on global settings."""
    if not CLOUDSCRAPER_AVAILABLE:
        return False
    try:
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        return settings.cloudscraper_enabled
    except Exception:
        # Default to True if settings can't be loaded
        return True


def _get_session(use_cloudscraper=None):
    """Get or create a requests session with automatic refresh.
    
    Args:
        use_cloudscraper: Override cloudscraper setting. 
                         None = check global settings
                         True = force cloudscraper
                         False = force standard session
    """
    global _session, _session_created, _session_uses_cloudscraper
    
    current_time = time.time()
    
    # Determine if we should use cloudscraper
    if use_cloudscraper is None:
        should_use_cloudscraper = _should_use_cloudscraper_global()
    else:
        should_use_cloudscraper = use_cloudscraper and CLOUDSCRAPER_AVAILABLE
    
    # Create new session if none exists, too old, or cloudscraper setting changed
    needs_new_session = (
        _session is None or 
        (current_time - _session_created) > _SESSION_MAX_AGE or
        _session_uses_cloudscraper != should_use_cloudscraper
    )
    
    if needs_new_session:
        if _session is not None:
            try:
                _session.close()
            except Exception as e:
                logger.debug(f"Error closing old session: {e}")
        
        # Use cloudscraper if enabled (for Cloudflare bypass)
        if should_use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
            _session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'linux',
                    'desktop': True
                }
            )
            _session_uses_cloudscraper = True
            logger.info("MacPortalClient: Created cloudscraper session for Cloudflare bypass")
        else:
            _session = requests.Session()
            # NO automatic retries - we handle retries manually at a higher level
            # This prevents urllib3 from retrying on timeouts which causes long waits
            _session.mount("http://", HTTPAdapter(max_retries=0))
            _session.mount("https://", HTTPAdapter(max_retries=0))
            _session_uses_cloudscraper = False
            logger.debug("MacPortalClient: Created standard requests session (no cloudscraper)")
        
        _session_created = current_time
    
    return _session


def clear_session():
    """Clear the session to free memory."""
    global _session, _session_created, _session_uses_cloudscraper
    if _session is not None:
        try:
            _session.close()
        except Exception as e:
            logger.debug(f"Error closing session during clear: {e}")
        _session = None
        _session_created = 0
        _session_uses_cloudscraper = False
        logger.debug("Cleared requests session")
        logger.debug("Cleared requests session")


class MacPortalError(Exception):
    """Error while accessing MAC/STB portal."""
    pass


class MacPortalClient:
    """
    Client for Stalker-/STB portals with MAC login.
    Handles:
      - resolving portal URL
      - handshake (token)
      - expiry info
      - channel list (get_all_channels)
    """

    def __init__(
        self,
        base_url: str,
        mac: str,
        proxy: Optional[str] = None,
        timezone: str = "Europe/London",
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.original_base_url = base_url.rstrip("/")
        self.mac = mac
        self.timezone = timezone
        self.proxy = proxy

        self.portal_url: Optional[str] = None
        self.token: Optional[str] = None
        # cache for genre/category mapping
        self.genres_by_id: Dict[str, str] = {}
        
        # Log initialization with proxy info
        if self.proxy:
            logger.info(f"MacPortalClient initialized for {self.original_base_url} with MAC {self.mac[:8]}... using proxy: {self.proxy}")
        else:
            logger.info(f"MacPortalClient initialized for {self.original_base_url} with MAC {self.mac[:8]}... (no proxy)")

    # ------------- helpers -------------

    def _get_proxies(self) -> Optional[dict]:
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def _default_headers(self, with_auth: bool = False, enhanced: bool = False) -> dict:
        # Standard STB headers
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        # Enhanced headers for problematic portals
        if enhanced:
            headers.update({
                "X-User-Agent": "Model: MAG250; Link: WiFi",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            })
            
            # Add referer if we have portal URL
            if self.portal_url:
                from urllib.parse import urlparse
                parsed = urlparse(self.portal_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                headers["Referer"] = base_url + "/"
        
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _cookies(self) -> dict:
        return {
            "mac": self.mac,
            "stb_lang": "en",
            "timezone": self.timezone,
        }

    # ------------- step 1: resolve portal url -------------

    def resolve_portal_url(self) -> str:
        """
        Try to detect the portal URL using MacReplay's advanced discovery method.
        First tries to find xpcom.common.js and parse it, then falls back to common paths.
        """
        cache_key = f"portal_url:{self.original_base_url}"
        cached_url = cache.get(cache_key)
        if cached_url:
            self.portal_url = cached_url
            return self.portal_url

        if self.portal_url:
            return self.portal_url

        # If URL already ends with load.php or portal.php, use it as-is
        if self.original_base_url.endswith(("load.php", "portal.php")):
            self.portal_url = self.original_base_url
            cache.set(cache_key, self.portal_url, 3600)  # Cache for 1 hour
            return self.portal_url

        # Try MacReplay's advanced portal discovery method
        discovered_url = self._discover_portal_via_xpcom()
        if discovered_url:
            self.portal_url = discovered_url
            cache.set(cache_key, self.portal_url, 3600)  # Cache for 1 hour
            logger.info("MAC portal discovered via xpcom.common.js: %s", discovered_url)
            return self.portal_url

        # Fallback to simple path probing
        parsed = urlparse(self.original_base_url)
        if not parsed.scheme:
            self.original_base_url = "http://" + self.original_base_url
            parsed = urlparse(self.original_base_url)

        base = f"{parsed.scheme}://{parsed.netloc}"
        candidate_paths = [
            "/stalker_portal/server/load.php",
            "/stalker_portal/load.php", 
            "/c/load.php",
            "/portal.php",
            "/server/load.php",
        ]

        proxies = self._get_proxies()
        headers = self._default_headers()

        for path in candidate_paths:
            url = base + path
            try:
                r = _get_session().get(
                    url,
                    headers=headers,
                    cookies=self._cookies(),
                    proxies=proxies,
                    timeout=5,
                )
                if r.status_code < 400:
                    self.portal_url = url
                    cache.set(cache_key, self.portal_url, 3600)  # Cache for 1 hour
                    logger.info("MAC portal load.php detected: %s", url)
                    return self.portal_url
            except Exception as e:
                logger.debug("Portal candidate %s failed: %s", url, e)

        self.portal_url = self.original_base_url
        cache.set(cache_key, self.portal_url, 3600)  # Cache for 1 hour
        logger.warning(
            "Could not positively identify load.php, using base URL: %s",
            self.portal_url,
        )
        return self.portal_url

    def _discover_portal_via_xpcom(self) -> Optional[str]:
        """
        Advanced portal discovery using xpcom.common.js parsing (from MacReplay).
        """
        def parse_xpcom_response(url, data):
            try:
                java = data.text.replace(" ", "").replace("'", "").replace("+", "")
                pattern = re.search(r"varpattern.*\/(\(http.*)\/;", java).group(1)
                result = re.search(pattern, url)
                protocol_index = re.search(r"this\.portal_protocol.*(\d).*;", java).group(1)
                ip_index = re.search(r"this\.portal_ip.*(\d).*;", java).group(1)
                path_index = re.search(r"this\.portal_path.*(\d).*;", java).group(1)
                protocol = result.group(int(protocol_index))
                ip = result.group(int(ip_index))
                path = result.group(int(path_index))
                portal_pattern = re.search(r"this\.ajax_loader=(.*\.php);", java).group(1)
                portal = (
                    portal_pattern.replace("this.portal_protocol", protocol)
                    .replace("this.portal_ip", ip)
                    .replace("this.portal_path", path)
                )
                return portal
            except Exception as e:
                logger.debug(f"Failed to parse xpcom.common.js response: {e}")
                return None

        # Parse the base URL
        parsed = urlparse(self.original_base_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # If URL already has a path, try to use it
        url_path = parsed.path.rstrip('/')
        
        # Extended list of paths to try (from MacReplay)
        urls = [
            "/c/xpcom.common.js",
            "/client/xpcom.common.js", 
            "/c_/xpcom.common.js",
            "/stalker_portal/c/xpcom.common.js",
            "/stalker_portal/c_/xpcom.common.js",
            "/portal/c/xpcom.common.js",
            "/server/c/xpcom.common.js",
        ]
        
        # If URL has a path component, try it first
        if url_path and url_path != '/':
            urls.insert(0, f"{url_path}/xpcom.common.js")
            urls.insert(1, f"{url_path}xpcom.common.js")

        proxies = self._get_proxies()
        
        # Enhanced headers to bypass Cloudflare and other protections (from MacReplay)
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": base_url + "/",
        }

        # Try with proxy first (use cloudscraper for Cloudflare bypass)
        session = _get_session(use_cloudscraper=True)
        for path in urls:
            try:
                test_url = base_url + path
                logger.debug(f"Trying xpcom.common.js at: {test_url}")
                response = session.get(test_url, headers=headers, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    logger.debug(f"Found xpcom.common.js at: {test_url}")
                    portal = parse_xpcom_response(test_url, response)
                    if portal:
                        logger.info(f"Successfully parsed portal URL: {portal}")
                        return portal
            except Exception as e:
                logger.debug(f"Failed to fetch {path}: {e}")
                continue

        # Try without proxy (some portals don't like proxies)
        logger.debug("Retrying xpcom.common.js discovery without proxy...")
        for path in urls:
            try:
                test_url = base_url + path
                logger.debug(f"Trying xpcom.common.js at: {test_url} (no proxy)")
                response = session.get(test_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    logger.debug(f"Found xpcom.common.js at: {test_url}")
                    portal = parse_xpcom_response(test_url, response)
                    if portal:
                        logger.info(f"Successfully parsed portal URL: {portal}")
                        return portal
            except Exception as e:
                logger.debug(f"Failed to fetch {path} without proxy: {e}")
                continue
        
        logger.debug(f"Could not find xpcom.common.js for {self.original_base_url}")
        return None

    # ------------- step 2: handshake / token -------------

    def handshake(self) -> str:
        """Get authentication token from portal with robust fallback mechanisms."""
        cache_key = f"mac_token:{self.mac}:{self.original_base_url}"
        cached_token = cache.get(cache_key)
        if cached_token:
            self.token = cached_token
            return self.token
        
        # Try different authentication methods
        methods = [
            self._handshake_standard,
            self._handshake_with_profile_check,
            self._handshake_with_session_reset
        ]
        
        for method in methods:
            try:
                token = method()
                if token:
                    self.token = token
                    cache.set(cache_key, token, 1800)  # Cache for 30 minutes
                    return token
            except Exception as e:
                logger.debug(f"Handshake method {method.__name__} failed: {e}")
                continue
        
        raise MacPortalError(f"Failed to get token for MAC {self.mac} from all methods")
    
    def _handshake_standard(self) -> str:
        """Standard handshake method."""

        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        
        # Enhanced headers to bypass protections (from original MacReplay)
        from urllib.parse import urlparse
        parsed = urlparse(portal)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept": "*/*",
            "Referer": base_url + "/",
            "X-User-Agent": "Model: MAG250; Link: WiFi",
        }
        
        # If URL already contains a path (like /c/ or /stalker_portal/), use it
        url_path = parsed.path.rstrip('/')
        
        # Try different endpoint variations (from original MacReplay)
        endpoints = []
        
        # If URL has a specific path, try it first
        if url_path and url_path != '/':
            # Check if path already ends with portal.php or load.php - don't duplicate!
            if url_path.endswith('/portal.php') or url_path.endswith('/load.php'):
                # URL already has the endpoint, just add query params
                endpoints.append(f"{url_path}?type=stb&action=handshake&JsHttpRequest=1-xml")
            else:
                # Path is a directory (like /c/ or /stalker_portal/), add endpoints
                endpoints.extend([
                    f"{url_path}/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                    f"{url_path}/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                    f"{url_path}?type=stb&action=handshake&JsHttpRequest=1-xml",
                ])
        
        # Standard endpoints
        endpoints.extend([
            "?type=stb&action=handshake&JsHttpRequest=1-xml",  # Root
            "/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",  # Standard portal.php
            "/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",  # Standard load.php
            "/stalker_portal/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",  # Stalker path
            "/c/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",  # /c/ path
        ])
        
        for endpoint in endpoints:
            try:
                # Build full URL
                if endpoint.startswith('/') or endpoint.startswith('?'):
                    full_url = base_url + endpoint
                else:
                    full_url = portal + endpoint
                
                _debug_log(f"Trying token endpoint: {full_url}")
                response = _get_session().get(
                    full_url,
                    cookies=self._cookies(),
                    headers=headers,
                    proxies=proxies,
                    timeout=10,  # Reduced for faster failover (was 20)
                )
                _debug_log(f"Token request status: {response.status_code}")
                
                # Try to parse response
                if response.status_code == 200:
                    try:
                        # Check if response has content
                        if not response.text or response.text.strip() == "":
                            logger.debug(f"Empty response from {endpoint}")
                            continue
                        
                        # Check if response looks like JSON
                        response_text = response.text.strip()
                        if not (response_text.startswith('{') or response_text.startswith('[')):
                            logger.debug(f"Non-JSON response from {endpoint}: {response_text[:200]}")
                            continue
                        
                        data = response.json()
                        if "js" in data and "token" in data["js"]:
                            token = data["js"]["token"]
                            if token:
                                logger.info(f"Successfully got token for MAC {self.mac} using endpoint: {full_url}")
                                return token
                    except ValueError as e:
                        logger.debug(f"JSON decode error from {endpoint}: {e}")
                        logger.debug(f"Raw response: {response.text[:500]}")
                        continue
                    except Exception as e:
                        logger.debug(f"Failed to parse response from {endpoint}: {e}")
                        logger.debug(f"Raw response: {response.text[:500]}")
                        continue
            except requests.Timeout:
                logger.debug(f"Timeout on endpoint {endpoint}")
                continue
            except requests.RequestException as e:
                logger.debug(f"Request error on endpoint {endpoint}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error on endpoint {endpoint}: {e}")
                continue
        
        return None
    
    def _handshake_with_profile_check(self) -> str:
        """Handshake with profile check - some portals require this."""
        token = self._handshake_standard()
        if not token:
            return None
        
        # Try to get profile to validate token
        try:
            profile = self.get_profile()
            if profile:
                logger.debug(f"Token validated with profile check for MAC {self.mac}")
                return token
        except Exception as e:
            logger.debug(f"Profile check failed for MAC {self.mac}: {e}")
        
        return None
    
    def _handshake_with_session_reset(self) -> str:
        """Handshake with session reset - clear session and try again."""
        # Clear session to force new connection
        clear_session()
        
        # Try standard handshake with fresh session
        return self._handshake_standard()

    # ------------- step 3: profile / account info -------------

    def get_profile(self) -> Optional[Dict]:
        """Get profile information from portal."""
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
            "Authorization": f"Bearer {self.token}",
        }
        
        try:
            response = _get_session().get(
                portal + "?type=stb&action=get_profile&JsHttpRequest=1-xml",
                cookies=self._cookies(),
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                profile = data.get("js")
                if profile:
                    logger.debug(f"Got profile for MAC {self.mac}")
                    return profile
        except Exception as e:
            logger.debug(f"Failed to get profile for MAC {self.mac}: {e}")
        
        return None

    def get_expires(self) -> Optional[str]:
        """
        Fetch expiry-like info from account_info/get_main_info with robust error handling.
        STB-Proxy uses 'phone' field for that.
        """
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
            "Authorization": f"Bearer {self.token}",
        }
        
        try:
            _debug_log(f"Getting expiry for MAC {self.mac}")
            response = _get_session().get(
                portal + "?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
                cookies=self._cookies(),
                headers=headers,
                proxies=proxies,
                timeout=15,
            )
            logger.debug(f"Expiry request status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                expires = data["js"]["phone"]
                if expires:
                    logger.info(f"Got expiry for MAC {self.mac}: {expires}")
                    return expires
        except requests.Timeout:
            logger.error(f"Timeout getting expiry for MAC {self.mac}")
        except requests.RequestException as e:
            logger.error(f"Request error getting expiry for MAC {self.mac}: {e}")
        except Exception as e:
            logger.error(f"Error getting expiry for MAC {self.mac}: {e}")
        
        return None

    # ------------- step 4: genres / categories -------------

    def get_genres_map(self) -> Dict[str, str]:
        """Load mapping of genre/category id -> title from portal, if available."""
        if self.genres_by_id:
            return self.genres_by_id

        cache_key = f"mac_genres:{self.original_base_url}"
        cached_genres = cache.get(cache_key)
        if cached_genres:
            self.genres_by_id = cached_genres
            return self.genres_by_id

        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        for action in ("get_genres", "get_genres_short"):
            try:
                r = _get_session().get(
                    portal,
                    params={
                        "type": "itv",
                        "action": action,
                        "JsHttpRequest": "1-xml",
                    },
                    headers=headers,
                    cookies=self._cookies(),
                    proxies=proxies,
                    timeout=10,
                )
                r.raise_for_status()
                js = r.json().get("js")
                if not isinstance(js, list):
                    continue

                mapping: Dict[str, str] = {}
                for item in js:
                    try:
                        gid = item.get("id")
                        title = item.get("title") or item.get("name")
                        if gid is None or not title:
                            continue
                        mapping[str(gid)] = str(title)
                    except Exception:
                        continue

                if mapping:
                    self.genres_by_id = mapping
                    cache.set(cache_key, mapping, 3600)  # Cache for 1 hour
                    logger.info(
                        "Loaded %s MAC genres via %s", len(mapping), action
                    )
                    return self.genres_by_id
            except Exception as e:
                logger.debug("Failed to load MAC genres via %s: %s", action, e)

        logger.warning(
            "Could not load MAC genres mapping; will fall back to numeric Group IDs"
        )
        self.genres_by_id = {}
        return self.genres_by_id

    # ------------- step 5: channels -------------

    def get_all_channels_raw(self):
        """Get all channels with support for GET and POST methods - EXACT MacReplayXC copy."""
        if not self.token:
            self.handshake()

        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        cookies = self._cookies()
        
        # Enhanced headers - EXACT MacReplayXC copy
        parsed = urlparse(portal)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Authorization": "Bearer " + self.token,
            "Accept": "*/*",
            "Referer": base_url + "/",
            "X-User-Agent": "Model: MAG250; Link: WiFi",
        }
        
        params = {
            "type": "itv",
            "action": "get_all_channels",
            "force_ch_link_check": "",
            "JsHttpRequest": "1-xml"
        }
        
        # Try GET first (standard) - EXACT MacReplayXC copy
        try:
            _debug_log(f"Getting all channels for MAC {self.mac} (GET)")
            response = _get_session().get(
                portal,
                params=params,
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=30,
            )
            logger.debug(f"Channels request status: {response.status_code}")
            
            # Check for empty response before parsing JSON
            if not response.text or response.text.strip() == "":
                logger.debug(f"Empty response from GET channels for MAC {self.mac}")
                raise ValueError("Empty response")
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict):
                if "js" in data and isinstance(data["js"], dict):
                    channels = data["js"].get("data", [])
                elif "data" in data:
                    channels = data["data"]
                else:
                    channels = []
            elif isinstance(data, list):
                channels = data
            else:
                channels = []
            
            if channels:
                logger.info(f"Got {len(channels)} channels for MAC {self.mac}")
                return channels
        except Exception as e:
            logger.debug(f"GET request failed: {e}, trying POST")
        
        # Try POST as fallback (some portals require this) - EXACT MacReplayXC copy
        try:
            _debug_log(f"Getting all channels for MAC {self.mac} (POST)")
            response = _get_session().post(
                portal,
                data=params,
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=30,
            )
            logger.debug(f"Channels request status: {response.status_code}")
            
            # Check for empty response before parsing JSON
            if not response.text or response.text.strip() == "":
                logger.warning(f"Empty response from POST channels for MAC {self.mac}")
                return None
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict):
                if "js" in data and isinstance(data["js"], dict):
                    channels = data["js"].get("data", [])
                elif "data" in data:
                    channels = data["data"]
                else:
                    channels = []
            elif isinstance(data, list):
                channels = data
            else:
                channels = []
            
            if channels:
                logger.info(f"Got {len(channels)} channels for MAC {self.mac} via POST")
                return channels
        except requests.Timeout:
            logger.error(f"Timeout getting channels for MAC {self.mac}")
        except requests.RequestException as e:
            logger.error(f"Request error getting channels for MAC {self.mac}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response getting channels for MAC {self.mac}: {e}")
        except Exception as e:
            logger.error(f"Error getting channels for MAC {self.mac}: {e}")
        
        return None

    def create_link(self, cmd: str) -> str:
        """
        Resolve a portal channel command into a final stream URL using itv/create_link with robust fallback mechanisms.
        """
        if not cmd:
            raise MacPortalError("Missing cmd for create_link")

        if not self.token:
            self.handshake()

        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        
        # Enhanced headers (from original MacReplay)
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
            "Authorization": f"Bearer {self.token}",
        }
        
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
        
        # Try GET first
        try:
            response = _get_session().get(
                portal,
                params=params,
                cookies=self._cookies(),
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            
            if response.status_code == 200:
                try:
                    # Check if response has content
                    if not response.text or response.text.strip() == "":
                        logger.debug("Empty response from create_link (GET)")
                        raise ValueError("Empty response")
                    
                    # Check if response looks like JSON
                    response_text = response.text.strip()
                    if not (response_text.startswith('{') or response_text.startswith('[')):
                        logger.debug(f"Non-JSON response from create_link (GET): {response_text[:200]}")
                        raise ValueError("Non-JSON response")
                    
                    data = response.json()
                    link = data["js"]["cmd"].split()[-1]
                    if link and (link.startswith("http://") or link.startswith("https://")):
                        return link
                except ValueError as e:
                    logger.debug(f"JSON decode error in create_link (GET): {e}")
                    logger.debug(f"Raw response: {response.text[:500]}")
                except Exception as e:
                    logger.debug(f"GET create_link failed to parse: {e}")
                    logger.debug(f"Raw response: {response.text[:500]}")
        except Exception as e:
            logger.debug(f"GET create_link failed: {e}, trying POST")
        
        # Try POST as fallback
        try:
            response = _get_session().post(
                portal,
                data=params,
                cookies=self._cookies(),
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            
            if response.status_code == 200:
                try:
                    # Check if response has content
                    if not response.text or response.text.strip() == "":
                        logger.debug("Empty response from create_link (POST)")
                        raise ValueError("Empty response")
                    
                    # Check if response looks like JSON
                    response_text = response.text.strip()
                    if not (response_text.startswith('{') or response_text.startswith('[')):
                        logger.debug(f"Non-JSON response from create_link (POST): {response_text[:200]}")
                        raise ValueError("Non-JSON response")
                    
                    data = response.json()
                    link = data["js"]["cmd"].split()[-1]
                    if link and (link.startswith("http://") or link.startswith("https://")):
                        return link
                except ValueError as e:
                    logger.debug(f"JSON decode error in create_link (POST): {e}")
                    logger.debug(f"Raw response: {response.text[:500]}")
                except Exception as e:
                    logger.debug(f"POST create_link failed to parse: {e}")
                    logger.debug(f"Raw response: {response.text[:500]}")
        except Exception as e:
            logger.debug(f"POST create_link failed: {e}")
        
        raise MacPortalError(f"Could not create link for cmd: {cmd}")

    def _extract_stream_url(self, cmd: str) -> Optional[str]:
        """Extract stream URL from command string."""
        if not cmd:
            return None
        
        parts = cmd.split()
        
        # First, look for absolute URLs
        for p in parts:
            if p.startswith("http://") or p.startswith("https://"):
                return p
        
        # Get the base URL from the portal (use original_base_url, not base_url)
        parsed = urlparse(self.original_base_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # If no absolute URL found, look for relative paths and convert them
        for p in parts:
            if p.startswith("/ch/") or p.startswith("ch/"):
                # Convert relative path to absolute URL using portal base URL
                if p.startswith("/"):
                    return f"{base_url}{p}"
                else:
                    return f"{base_url}/{p}"
        
        # Look for other common relative patterns
        for p in parts:
            if "/" in p and not p.startswith("ffmpeg"):
                # Likely a relative URL path
                if p.startswith("/"):
                    return f"{base_url}{p}"
                else:
                    return f"{base_url}/{p}"
        
        return None

    def _detect_group_title(self, ch: Dict[str, Any]) -> str:
        """Best-effort detection of group/category name for a channel."""
        # Common keys used by many portals
        candidates = [
            "tv_genre_title",
            "genre_title",
            "category_name",
            "cat_name",
            "group_name",
            "group_title",
            "genre_name",
        ]
        for key in candidates:
            val = ch.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

        # Some portals use nested 'genres' / 'categories' arrays
        genres = ch.get("genres") or ch.get("categories")
        if isinstance(genres, list) and genres:
            first = genres[0]
            if isinstance(first, dict):
                for key in ("title", "name", "genre_title", "category_name"):
                    val = first.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()

        # Fallback: numeric ids with optional mapping
        genre_id = (
            ch.get("tv_genre_id")
            or ch.get("genre_id")
            or ch.get("cat_id")
        )
        if genre_id is not None:
            try:
                genres = self.get_genres_map()
            except MacPortalError:
                genres = self.genres_by_id or {}
            label = genres.get(str(genre_id))
            if label:
                return label
            return f"Group {genre_id}"

        return "MAC"

    def get_channels(self):
        """Return normalized channels list.

        We try to map provider categories/groups onto our 'group' field.

        Different portals use different keys for the group/category, so we
        check several common ones in order.
        
        NOTE: URLs are stored as special mac:// URLs that will be resolved
        at playback time via create_link API. This is much faster than
        resolving all URLs during import.
        """
        raw_list = self.get_all_channels_raw()
        if not raw_list:
            logger.warning(f"No channels returned for MAC {self.mac}")
            return []
        
        normalized = []
        
        for ch in raw_list:
            ch_id = ch.get("id")
            name = ch.get("name") or f"Channel {ch_id}"

            group_title = self._detect_group_title(ch)

            cmd = ch.get("cmd") or ""
            if not cmd:
                continue
            
            # Create a special MAC URL that encodes the portal info, cmd, and proxy
            # Format: mac://base64(portal_url|mac|cmd|proxy)
            # This will be resolved at playback time
            import base64
            proxy_str = self.proxy or ""
            mac_data = f"{self.original_base_url}|{self.mac}|{cmd}|{proxy_str}"
            encoded_data = base64.urlsafe_b64encode(mac_data.encode()).decode()
            url = f"mac://{encoded_data}"

            # Extract logo URL if available
            logo = ch.get("logo") or ch.get("logo_url") or ""
            
            normalized.append(
                {
                    "id": ch_id,
                    "name": name,
                    "group": group_title,
                    "url": url,
                    "logo": logo,
                    "cmd": cmd,
                    "raw": ch,
                }
            )
        
        logger.info(f"Normalized {len(normalized)} MAC channels into groups")
        return normalized
    
    @staticmethod
    def resolve_mac_url(mac_url: str, proxy: Optional[str] = None, portal_engine: Optional[str] = None) -> str:
        """Resolve a mac:// URL to a real stream URL.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            proxy: Optional proxy to use (overrides encoded proxy)
            portal_engine: Optional portal engine to use (auto, macreplay, estalker, boxpirate, ob2_2025)
            
        Returns:
            Real stream URL from create_link API
        """
        if not mac_url.startswith("mac://"):
            return mac_url
        
        import base64
        try:
            encoded_data = mac_url[6:]  # Remove "mac://" prefix
            decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
            parts = decoded_data.split("|", 3)  # Now supports 4 parts with proxy
            if len(parts) < 3:
                raise ValueError(f"Invalid mac:// URL format: expected at least 3 parts, got {len(parts)}")
            
            portal_url = parts[0]
            mac = parts[1]
            cmd = parts[2]
            encoded_proxy = parts[3] if len(parts) > 3 else None
            
            # Use provided proxy, or fall back to encoded proxy
            use_proxy = proxy or encoded_proxy
            
            # Get portal_engine from settings if not provided
            if not portal_engine:
                try:
                    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
                    settings = MACPortalGlobalSettings.get_settings()
                    portal_engine = getattr(settings, 'portal_engine', 'auto')
                except Exception:
                    portal_engine = 'auto'
            
            logger.info(f"Resolving MAC URL for portal {portal_url}, MAC {mac[:8]}..., engine: {portal_engine}, proxy: {use_proxy or 'none'}")
            
            # Use direct MacPortalClient for 'auto' and 'macreplay' (fast path)
            # Only use UnifiedPortalEngine for other engines (estalker, boxpirate, ob2_2025)
            if portal_engine in ('auto', 'macreplay', '', None):
                # Fast path: Direct MacPortalClient (original MacReplay behavior)
                client = MacPortalClient(base_url=portal_url, mac=mac, proxy=use_proxy)
                resolved_url = client.create_link(cmd)
                logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
                return resolved_url
            else:
                # Slow path: UnifiedPortalEngine for other engines
                try:
                    from apps.m3u.unified_portal_engine import create_portal_client
                    unified_client = create_portal_client(
                        portal_url=portal_url,
                        mac=mac,
                        engine=portal_engine,
                        proxy=use_proxy
                    )
                    resolved_url = unified_client.create_link(cmd)
                    logger.info(f"Resolved MAC URL via {portal_engine} to: {resolved_url[:80]}...")
                    return resolved_url
                except Exception as e:
                    logger.warning(f"UnifiedPortalEngine ({portal_engine}) failed, falling back to standard: {e}")
                    # Fallback to standard MacPortalClient
                    client = MacPortalClient(base_url=portal_url, mac=mac, proxy=use_proxy)
                    resolved_url = client.create_link(cmd)
                    logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
                    return resolved_url
        except Exception as e:
            logger.error(f"Failed to resolve mac:// URL: {e}")
            raise MacPortalError(f"Failed to resolve MAC URL: {e}")

    @staticmethod
    def resolve_mac_url_with_busy_check(mac_url: str, proxy: Optional[str] = None, portal_engine: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Resolve a mac:// URL to a real stream URL, preferring non-busy MACs.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            proxy: Optional proxy to use (overrides encoded proxy)
            portal_engine: Optional portal engine to use (auto, macreplay, estalker, boxpirate, ob2_2025)
            
        Returns:
            Tuple[str, Optional[str]]: (resolved_url, selected_mac) or raises MacPortalError
        """
        if not mac_url.startswith("mac://"):
            return mac_url, None
        
        import base64
        try:
            encoded_data = mac_url[6:]  # Remove "mac://" prefix
            decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
            parts = decoded_data.split("|", 3)
            if len(parts) < 3:
                raise ValueError(f"Invalid mac:// URL format")
            
            portal_url = parts[0]
            original_mac = parts[1]
            cmd = parts[2]
            encoded_proxy = parts[3] if len(parts) > 3 else None
            use_proxy = proxy or encoded_proxy
            
            # Get portal_engine from settings if not provided
            if not portal_engine:
                try:
                    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
                    settings = MACPortalGlobalSettings.get_settings()
                    portal_engine = getattr(settings, 'portal_engine', 'auto')
                except Exception:
                    portal_engine = 'auto'
            
            # Try to find the M3U account for this MAC to check for alternatives
            from apps.m3u.models import M3UAccountMac
            try:
                mac_entry = M3UAccountMac.objects.filter(address__iexact=original_mac).first()
                if mac_entry and mac_entry.account:
                    # Get all candidate MACs for this account
                    candidates = mac_entry.account.get_candidate_macs_for_streaming()
                    
                    # Check Redis for busy status and prefer free MACs
                    try:
                        from core.utils import RedisClient
                        from ..proxy.ts_proxy.redis_keys import RedisKeys
                        redis_client = RedisClient.get_client()
                        
                        free_macs = []
                        busy_macs = []
                        
                        for mac in candidates:
                            busy_key = RedisKeys.mac_busy(mac.id)
                            if redis_client.exists(busy_key):
                                busy_macs.append(mac)
                            else:
                                free_macs.append(mac)
                        
                        # Prefer free MACs, fallback to busy ones if needed
                        selected_candidates = free_macs if free_macs else busy_macs
                        
                        if not selected_candidates:
                            raise MacPortalError("All MACs busy")
                            
                        # Use the first available MAC (highest priority)
                        selected_mac = selected_candidates[0].address
                        
                    except Exception:
                        # Fallback to original MAC if Redis check fails
                        selected_mac = original_mac
                else:
                    selected_mac = original_mac
                    
            except Exception:
                selected_mac = original_mac
            
            logger.info(f"Resolving MAC URL with MAC {selected_mac[:8]}... (original: {original_mac[:8]}...), engine: {portal_engine}")
            
            # Use direct MacPortalClient for 'auto' and 'macreplay' (fast path)
            # Only use UnifiedPortalEngine for other engines (estalker, boxpirate, ob2_2025)
            if portal_engine in ('auto', 'macreplay', '', None):
                # Fast path: Direct MacPortalClient (original MacReplay behavior)
                client = MacPortalClient(base_url=portal_url, mac=selected_mac, proxy=use_proxy)
                resolved_url = client.create_link(cmd)
                logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
                return resolved_url, selected_mac
            else:
                # Slow path: UnifiedPortalEngine for other engines
                try:
                    from apps.m3u.unified_portal_engine import create_portal_client
                    unified_client = create_portal_client(
                        portal_url=portal_url,
                        mac=selected_mac,
                        engine=portal_engine,
                        proxy=use_proxy
                    )
                    resolved_url = unified_client.create_link(cmd)
                    logger.info(f"Resolved MAC URL via {portal_engine} to: {resolved_url[:80]}...")
                    return resolved_url, selected_mac
                except Exception as e:
                    logger.warning(f"UnifiedPortalEngine ({portal_engine}) failed, falling back to standard: {e}")
                    # Fallback to standard MacPortalClient
                    client = MacPortalClient(base_url=portal_url, mac=selected_mac, proxy=use_proxy)
                    resolved_url = client.create_link(cmd)
                    logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
                    return resolved_url, selected_mac
            
        except Exception as e:
            logger.error(f"Failed to resolve mac:// URL with busy check: {e}")
            raise MacPortalError(f"Failed to resolve MAC URL: {e}")
    
    @staticmethod
    def resolve_mac_url_with_failover_mac(mac_url: str, failover_mac: str, proxy: Optional[str] = None, portal_engine: Optional[str] = None) -> str:
        """Resolve a mac:// URL to a real stream URL using a different MAC address for failover.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            failover_mac: MAC address to use instead of the one encoded in the URL
            proxy: Optional proxy to use (overrides encoded proxy)
            portal_engine: Optional portal engine to use (auto, macreplay, estalker, boxpirate, ob2_2025)
            
        Returns:
            Real stream URL from create_link API
        """
        if not mac_url.startswith("mac://"):
            return mac_url
        
        import base64
        try:
            encoded_data = mac_url[6:]  # Remove "mac://" prefix
            decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
            parts = decoded_data.split("|", 3)  # Now supports 4 parts with proxy
            if len(parts) < 3:
                raise ValueError(f"Invalid mac:// URL format: expected at least 3 parts, got {len(parts)}")
            
            portal_url = parts[0]
            # Use failover MAC instead of encoded MAC
            cmd = parts[2]
            encoded_proxy = parts[3] if len(parts) > 3 else None
            
            # Use provided proxy, or fall back to encoded proxy
            use_proxy = proxy or encoded_proxy
            
            # Get portal_engine from settings if not provided
            if not portal_engine:
                try:
                    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
                    settings = MACPortalGlobalSettings.get_settings()
                    portal_engine = getattr(settings, 'portal_engine', 'auto')
                except Exception:
                    portal_engine = 'auto'
            
            logger.info(f"Resolving MAC URL for failover - portal {portal_url}, failover MAC {failover_mac[:8]}..., engine: {portal_engine}, proxy: {use_proxy or 'none'}")
            
            # Use direct MacPortalClient for 'auto' and 'macreplay' (fast path)
            # Only use UnifiedPortalEngine for other engines (estalker, boxpirate, ob2_2025)
            if portal_engine in ('auto', 'macreplay', '', None):
                # Fast path: Direct MacPortalClient (original MacReplay behavior)
                client = MacPortalClient(base_url=portal_url, mac=failover_mac, proxy=use_proxy)
                resolved_url = client.create_link(cmd)
                logger.info(f"Resolved MAC URL with failover MAC to: {resolved_url[:80]}...")
                return resolved_url
            else:
                # Slow path: UnifiedPortalEngine for other engines
                try:
                    from apps.m3u.unified_portal_engine import create_portal_client
                    unified_client = create_portal_client(
                        portal_url=portal_url,
                        mac=failover_mac,
                        engine=portal_engine,
                        proxy=use_proxy
                    )
                    resolved_url = unified_client.create_link(cmd)
                    logger.info(f"Resolved MAC URL via {portal_engine} with failover MAC to: {resolved_url[:80]}...")
                    return resolved_url
                except Exception as e:
                    logger.warning(f"UnifiedPortalEngine ({portal_engine}) failed, falling back to standard: {e}")
                    # Fallback to standard MacPortalClient
                    client = MacPortalClient(base_url=portal_url, mac=failover_mac, proxy=use_proxy)
                    resolved_url = client.create_link(cmd)
                    logger.info(f"Resolved MAC URL with failover MAC to: {resolved_url[:80]}...")
                    return resolved_url
        except Exception as e:
            logger.error(f"Failed to resolve mac:// URL with failover MAC: {e}")
            raise MacPortalError(f"Failed to resolve MAC URL with failover MAC: {e}")

    def get_epg_data(self, period: int = 7) -> Optional[Dict]:
        """Get EPG data for specified period (days)."""
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        params = {
            "type": "itv",
            "action": "get_epg_info",
            "period": str(period),
            "JsHttpRequest": "1-xml"
        }

        try:
            _debug_log(f"Getting EPG for MAC {self.mac}")
            response = _get_session().get(
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
                proxies=proxies,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json().get("js", {}).get("data")
            if data:
                logger.debug(f"Got EPG data for {len(data)} channels")
                return data
        except Exception as e:
            logger.debug(f"EPG request failed: {e}")
        
        return None


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format."""
    if not mac or not isinstance(mac, str):
        return False
    
    pattern = r'^([0-9A-Fa-f]{2}[:-]?){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac.strip()))


def normalize_mac_address(mac: str) -> str:
    """Normalize MAC address to standard format (XX:XX:XX:XX:XX:XX)."""
    if not validate_mac_address(mac):
        return mac
    
    # Remove all separators
    clean_mac = re.sub(r'[:-]', '', mac.strip())
    
    # Add colons every 2 characters
    normalized = ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
    
    return normalized.upper()


def get_portal_client(base_url: str, mac: str, proxy: Optional[str] = None):
    """
    Factory function to get the appropriate portal client based on global settings.
    
    For 'auto' and 'macreplay' engines, returns the fast MacPortalClient.
    For other engines (estalker, boxpirate, ob2_2025), returns UnifiedPortalEngine.
    
    Args:
        base_url: Portal base URL
        mac: MAC address
        proxy: Optional proxy URL
        
    Returns:
        Either UnifiedPortalEngine or MacPortalClient instance
    """
    try:
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        portal_engine = getattr(settings, 'portal_engine', 'auto')
    except Exception:
        portal_engine = 'auto'
    
    # Use direct MacPortalClient for 'auto' and 'macreplay' (fast path)
    # Only use UnifiedPortalEngine for other engines (estalker, boxpirate, ob2_2025)
    if portal_engine in ('auto', 'macreplay', '', None, 'unified'):
        # Fast path: Direct MacPortalClient (original MacReplay behavior)
        return MacPortalClient(base_url=base_url, mac=mac, proxy=proxy)
    else:
        # Slow path: UnifiedPortalEngine for other engines
        try:
            from apps.m3u.unified_portal_engine import create_portal_client
            logger.info(f"Using UnifiedPortalEngine with engine: {portal_engine}")
            return create_portal_client(
                portal_url=base_url,
                mac=mac,
                engine=portal_engine,
                proxy=proxy
            )
        except Exception as e:
            logger.warning(f"Failed to create UnifiedPortalEngine, falling back to MacPortalClient: {e}")
            return MacPortalClient(base_url=base_url, mac=mac, proxy=proxy)


class UnifiedMacPortalClient:
    """
    Wrapper class that provides MacPortalClient-compatible interface
    but uses portal_engines internally when configured.
    
    This allows existing code to use the same interface while benefiting
    from the engine selection feature.
    
    For 'auto' engine: Tries all engines in priority order until one succeeds:
    MacAttack → iSTB → OB2_2025 → BoxPirate → EStalker → MacReplay → AllinOne
    
    ENGINE CACHING:
    - AUTO mode remembers which engine worked for each portal URL
    - Cached for 24 hours to avoid re-testing on every request
    - Cache key: "portal_engine:{portal_url_hash}"
    
    ARCHITEKTUR:
    - Jede Engine ist in einer eigenen Datei unter portal_engines/
    - Die Registry in portal_engines/__init__.py verwaltet alle Engines
    - UnifiedMacPortalClient ist der einheitliche Einstiegspunkt
    """
    
    # Engine priority order for AUTO mode (best performers first)
    AUTO_ENGINE_ORDER = [
        'macattack',   # Best: Fast, reliable, 14k+ channels
        'istb',        # Good: iOS emulator style
        'ob2_2025',    # Good: Alternative handshake
        'boxpirate',   # Good: Dreambox style (optimized timeout)
        'estalker',    # Good: Enigma2 style (optimized timeout)
        'macreplay',   # Standard: Original MacReplay
        'allinone',    # Fallback: Tries everything
    ]
    
    # Cache timeout for successful engine - UNLIMITED (until manual refresh)
    # None means no expiration in Django cache
    ENGINE_CACHE_TIMEOUT = None
    
    # Cache timeout for fastest engine benchmark - UNLIMITED (until new benchmark)
    FASTEST_ENGINE_CACHE_TIMEOUT = None
    
    @staticmethod
    def _get_engine_cache_key(portal_url: str) -> str:
        """Generate cache key for portal engine."""
        import hashlib
        url_hash = hashlib.md5(portal_url.encode()).hexdigest()[:16]
        return f"portal_engine:{url_hash}"
    
    @staticmethod
    def _get_fastest_engine_cache_key(portal_url: str) -> str:
        """Generate cache key for fastest benchmarked engine."""
        import hashlib
        url_hash = hashlib.md5(portal_url.encode()).hexdigest()[:16]
        return f"fastest_engine:{url_hash}"
    
    @staticmethod
    def get_cached_engine(portal_url: str) -> Optional[str]:
        """Get cached successful engine for portal URL."""
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        return cache.get(cache_key)
    
    @staticmethod
    def set_cached_engine(portal_url: str, engine_name: str):
        """Cache successful engine for portal URL (unlimited duration until manual refresh)."""
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        # None = unlimited cache duration (until manually cleared)
        cache.set(cache_key, engine_name, UnifiedMacPortalClient.ENGINE_CACHE_TIMEOUT)
        logger.info(f"Cached engine '{engine_name}' for portal {portal_url[:50]}... (unlimited)")
    
    @staticmethod
    def clear_cached_engine(portal_url: str):
        """Clear cached engine for portal URL (e.g., when it stops working)."""
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        cache.delete(cache_key)
        logger.info(f"Cleared cached engine for portal {portal_url[:50]}...")
    
    @staticmethod
    def get_fastest_engine(portal_url: str) -> Optional[Dict[str, Any]]:
        """Get fastest benchmarked engine for portal URL.
        
        Returns:
            Dict with 'engine', 'time_ms', 'channels', 'tested_at' or None
        """
        cache_key = UnifiedMacPortalClient._get_fastest_engine_cache_key(portal_url)
        return cache.get(cache_key)
    
    @staticmethod
    def set_fastest_engine(portal_url: str, engine_name: str, time_ms: float, channels: int,
                          stream_link_ok: bool = False, full_success: bool = False):
        """Cache fastest benchmarked engine for portal URL (unlimited duration until new benchmark)."""
        from django.utils import timezone
        
        cache_key = UnifiedMacPortalClient._get_fastest_engine_cache_key(portal_url)
        data = {
            'engine': engine_name,
            'time_ms': time_ms,
            'channels': channels,
            'stream_link_ok': stream_link_ok,
            'full_success': full_success,
            'tested_at': timezone.now().isoformat(),
        }
        # None = unlimited cache duration (until manually cleared or new benchmark)
        cache.set(cache_key, data, UnifiedMacPortalClient.FASTEST_ENGINE_CACHE_TIMEOUT)
        logger.info(f"Cached fastest engine '{engine_name}' ({time_ms:.0f}ms, {channels} ch, link={stream_link_ok}) for portal {portal_url[:50]}...")
    
    @staticmethod
    def benchmark_all_engines(portal_url: str, mac: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive benchmark of ALL engines for a portal.
        
        Tests each engine through the COMPLETE workflow:
        1. Handshake (token acquisition)
        2. Get Genres/Groups
        3. Get All Channels
        4. Create Stream Link (MOST IMPORTANT for failover!)
        5. Detect Portal Type (XUI, Xtream, Stalker, etc.)
        
        The engine that completes ALL steps fastest wins.
        Stream link creation is prioritized - engines that fail this step are penalized.
        
        Returns:
            Dict with 'results' (list of engine results), 'fastest' (best engine), 'summary', 'portal_info'
        """
        from apps.m3u.portal_engines import create_engine
        import time
        
        results = []
        fastest_engine = None
        fastest_time = float('inf')
        portal_info = {
            'portal_type': 'unknown',
            'portal_version': None,
            'detected_by': None,
        }
        
        logger.info(f"Starting COMPREHENSIVE engine benchmark for {portal_url[:50]}...")
        logger.info("Testing: Handshake → Genres → Channels → Stream Link → Portal Type")
        
        for engine_name in UnifiedMacPortalClient.AUTO_ENGINE_ORDER:
            result = {
                'engine': engine_name,
                'success': False,
                'full_success': False,  # All 4 steps passed
                'time_ms': 0,
                'channels': 0,
                'genres': 0,
                'stream_link_ok': False,
                'steps': {
                    'handshake': {'success': False, 'time_ms': 0, 'error': None},
                    'genres': {'success': False, 'time_ms': 0, 'count': 0, 'error': None},
                    'channels': {'success': False, 'time_ms': 0, 'count': 0, 'error': None},
                    'stream_link': {'success': False, 'time_ms': 0, 'error': None},
                },
                'error': None,
            }
            
            try:
                logger.info(f"Benchmark: Testing engine '{engine_name}'...")
                
                client = create_engine(
                    engine_name=engine_name,
                    portal_url=portal_url,
                    mac=mac,
                    proxy=proxy
                )
                
                if not client:
                    result['error'] = 'Engine not found'
                    results.append(result)
                    continue
                
                total_start = time.time()
                token = None
                channels = []
                test_cmd = None
                
                # Step 1: Handshake
                step_start = time.time()
                try:
                    handshake_result = client.perform_handshake()
                    step_time = (time.time() - step_start) * 1000
                    result['steps']['handshake']['time_ms'] = round(step_time, 1)
                    
                    if handshake_result and handshake_result.success:
                        result['steps']['handshake']['success'] = True
                        token = handshake_result.token
                        logger.debug(f"  Handshake OK ({step_time:.0f}ms)")
                    else:
                        result['steps']['handshake']['error'] = 'No token received'
                        result['error'] = 'Handshake failed'
                        results.append(result)
                        continue
                except Exception as e:
                    result['steps']['handshake']['error'] = str(e)[:50]
                    result['error'] = f'Handshake: {str(e)[:50]}'
                    results.append(result)
                    continue
                
                # Step 2: Get Genres
                step_start = time.time()
                try:
                    genres = client.get_genres()
                    step_time = (time.time() - step_start) * 1000
                    result['steps']['genres']['time_ms'] = round(step_time, 1)
                    
                    if genres and len(genres) > 0:
                        result['steps']['genres']['success'] = True
                        result['steps']['genres']['count'] = len(genres)
                        result['genres'] = len(genres)
                        logger.debug(f"  Genres OK: {len(genres)} ({step_time:.0f}ms)")
                    else:
                        # Genres optional - some portals don't have them
                        result['steps']['genres']['error'] = 'No genres'
                        logger.debug(f"  Genres: None ({step_time:.0f}ms)")
                except Exception as e:
                    result['steps']['genres']['error'] = str(e)[:50]
                    logger.debug(f"  Genres failed: {e}")
                
                # Step 3: Get Channels (REQUIRED)
                step_start = time.time()
                try:
                    channels = client.get_all_channels()
                    step_time = (time.time() - step_start) * 1000
                    result['steps']['channels']['time_ms'] = round(step_time, 1)
                    
                    if channels and len(channels) > 0:
                        result['steps']['channels']['success'] = True
                        result['steps']['channels']['count'] = len(channels)
                        result['channels'] = len(channels)
                        # Get a test cmd for stream link test
                        for ch in channels:
                            cmd = ch.get('cmd')
                            if cmd:
                                test_cmd = cmd
                                break
                        logger.debug(f"  Channels OK: {len(channels)} ({step_time:.0f}ms)")
                    else:
                        result['steps']['channels']['error'] = 'No channels'
                        result['error'] = 'No channels returned'
                        results.append(result)
                        continue
                except Exception as e:
                    result['steps']['channels']['error'] = str(e)[:50]
                    result['error'] = f'Channels: {str(e)[:50]}'
                    results.append(result)
                    continue
                
                # Step 4: Create Stream Link (MOST IMPORTANT!)
                step_start = time.time()
                if test_cmd:
                    try:
                        stream_link = client.create_link(test_cmd)
                        step_time = (time.time() - step_start) * 1000
                        result['steps']['stream_link']['time_ms'] = round(step_time, 1)
                        
                        if stream_link and len(stream_link) > 10:
                            result['steps']['stream_link']['success'] = True
                            result['stream_link_ok'] = True
                            logger.debug(f"  Stream Link OK ({step_time:.0f}ms)")
                        else:
                            result['steps']['stream_link']['error'] = 'Invalid link'
                            logger.debug(f"  Stream Link: Invalid ({step_time:.0f}ms)")
                    except Exception as e:
                        result['steps']['stream_link']['error'] = str(e)[:50]
                        logger.debug(f"  Stream Link failed: {e}")
                else:
                    result['steps']['stream_link']['error'] = 'No cmd to test'
                
                # Calculate total time
                total_time = (time.time() - total_start) * 1000
                result['time_ms'] = round(total_time, 1)
                
                # Determine success level
                result['success'] = result['steps']['channels']['success']
                result['full_success'] = (
                    result['steps']['handshake']['success'] and
                    result['steps']['channels']['success'] and
                    result['steps']['stream_link']['success']
                )
                
                # Step 5: Detect Portal Type (only on first successful engine)
                # Based on ob2_2025 scripts analysis:
                # - XUI: Uses GET, /c/ path, PORTAL version in profile
                # - Xtream: Uses POST, has player_api.php, live.php in stream URLs, can extract login/password
                # - Stalker: Uses GET, /stalker_portal/c/ path, traditional middleware
                # - NXT: Newer Xtream variant
                if result['full_success'] and portal_info['portal_type'] == 'unknown':
                    try:
                        # First check if engine detected portal type/version
                        if hasattr(client, 'portal_type') and client.portal_type:
                            portal_info['portal_type'] = client.portal_type.lower()
                            portal_info['detected_by'] = engine_name
                        if hasattr(client, 'portal_version') and client.portal_version:
                            portal_info['portal_version'] = client.portal_version
                        
                        # Detect from URL patterns (most reliable)
                        url_lower = portal_url.lower()
                        if portal_info['portal_type'] == 'unknown':
                            if '/stalker_portal/' in url_lower:
                                portal_info['portal_type'] = 'stalker'
                                portal_info['detected_by'] = 'url_pattern'
                            elif '/c/' in url_lower and 'stalker' not in url_lower:
                                # XUI typically uses /c/ path without stalker_portal
                                portal_info['portal_type'] = 'xui'
                                portal_info['detected_by'] = 'url_pattern'
                            elif 'nxt' in url_lower:
                                portal_info['portal_type'] = 'nxt'
                                portal_info['detected_by'] = 'url_pattern'
                        
                        # Detect from stream URL pattern (from create_link result)
                        if portal_info['portal_type'] == 'unknown' and result.get('stream_link_ok'):
                            # Get the actual stream link if available
                            stream_link = None
                            if test_cmd:
                                try:
                                    stream_link = client.create_link(test_cmd)
                                except Exception:
                                    pass
                            
                            if stream_link:
                                stream_lower = stream_link.lower()
                                # Xtream pattern: /live/username/password/channel.ts or live.php
                                if 'live.php' in stream_lower:
                                    portal_info['portal_type'] = 'xtream'
                                    portal_info['detected_by'] = 'stream_url'
                                elif re.search(r'/live/[^/]+/[^/]+/', stream_lower):
                                    portal_info['portal_type'] = 'xtream'
                                    portal_info['detected_by'] = 'stream_url'
                                # XUI pattern: direct stream without /live/ path
                                elif re.search(r':\d+/[^/]+\.(ts|m3u8)', stream_lower):
                                    portal_info['portal_type'] = 'xui'
                                    portal_info['detected_by'] = 'stream_url'
                        
                        # Detect from channel cmd pattern
                        if channels and len(channels) > 0 and portal_info['portal_type'] == 'unknown':
                            first_ch = channels[0]
                            cmd = first_ch.get('cmd', '')
                            
                            # Stalker pattern: ffmpeg http://localhost/ch/ID_
                            if 'ffmpeg' in cmd.lower() or 'http://localhost' in cmd:
                                portal_info['portal_type'] = 'stalker'
                                portal_info['detected_by'] = 'cmd_pattern'
                            # Xtream pattern: /live/ in cmd
                            elif '/live/' in cmd and re.search(r'/live/[^/]+/[^/]+/', cmd):
                                portal_info['portal_type'] = 'xtream'
                                portal_info['detected_by'] = 'cmd_pattern'
                        
                        # Try to get profile for version and additional detection
                        if hasattr(client, 'get_profile'):
                            try:
                                profile = client.get_profile(token) if token else None
                                if profile:
                                    js = profile.get('js', {})
                                    
                                    # Version detection from profile
                                    if not portal_info.get('portal_version'):
                                        for key in ['portal_version', 'version', 'PORTAL version']:
                                            if js.get(key):
                                                portal_info['portal_version'] = js.get(key)
                                                break
                                    
                                    # XUI detection: has login/password in profile (Xtream-based)
                                    if portal_info['portal_type'] == 'unknown':
                                        if js.get('login') and js.get('password'):
                                            # Has credentials = Xtream-based (XUI or Xtream)
                                            # Check if it's XUI by URL pattern
                                            if '/c/' in url_lower:
                                                portal_info['portal_type'] = 'xui'
                                            else:
                                                portal_info['portal_type'] = 'xtream'
                                            portal_info['detected_by'] = 'profile_credentials'
                                        elif js.get('ls'):
                                            # Has ls (license server) = traditional Stalker
                                            portal_info['portal_type'] = 'stalker'
                                            portal_info['detected_by'] = 'profile_ls'
                            except Exception:
                                pass
                        
                        # Final fallback based on URL
                        if portal_info['portal_type'] == 'unknown':
                            portal_info['portal_type'] = 'stalker'  # Most MAC portals are Stalker-based
                            portal_info['detected_by'] = 'default'
                        
                        logger.debug(f"  Portal Type: {portal_info['portal_type']} (detected by: {portal_info.get('detected_by')}), Version: {portal_info.get('portal_version')}")
                    except Exception as e:
                        logger.debug(f"  Portal type detection failed: {e}")
                
                # Track fastest - PRIORITIZE engines with stream_link success!
                # Engines with stream_link get a 50% time bonus (lower is better)
                effective_time = total_time
                if not result['stream_link_ok']:
                    # Penalize engines that can't create stream links
                    effective_time = total_time * 2
                
                if result['success'] and effective_time < fastest_time:
                    fastest_time = effective_time
                    fastest_engine = engine_name
                
                status = "FULL SUCCESS" if result['full_success'] else "PARTIAL"
                logger.info(f"Benchmark: '{engine_name}' {status} - {len(channels)} ch, link={result['stream_link_ok']}, {total_time:.0f}ms")
                    
            except Exception as e:
                result['error'] = str(e)[:100]
                logger.warning(f"Benchmark: '{engine_name}' failed: {e}")
            
            results.append(result)
        
        # Save fastest engine if found
        if fastest_engine:
            fastest_result = next(r for r in results if r['engine'] == fastest_engine)
            UnifiedMacPortalClient.set_fastest_engine(
                portal_url, 
                fastest_engine, 
                fastest_result['time_ms'],
                fastest_result['channels'],
                fastest_result.get('stream_link_ok', False),
                fastest_result.get('full_success', False)
            )
        
        # Build summary
        successful = [r for r in results if r['success']]
        full_success = [r for r in results if r.get('full_success', False)]
        with_stream_link = [r for r in results if r.get('stream_link_ok', False)]
        
        summary = {
            'total_tested': len(results),
            'successful': len(successful),
            'full_success': len(full_success),
            'with_stream_link': len(with_stream_link),
            'failed': len(results) - len(successful),
            'fastest_engine': fastest_engine,
            'fastest_time_ms': round(fastest_time, 1) if fastest_engine and fastest_time != float('inf') else None,
            'fastest_has_stream_link': fastest_result.get('stream_link_ok', False) if fastest_engine else False,
        }
        
        logger.info(f"Benchmark complete: {summary['successful']}/{summary['total_tested']} engines worked, "
                   f"{summary['with_stream_link']} with stream link, fastest: {fastest_engine}, "
                   f"portal_type: {portal_info['portal_type']}")
        
        return {
            'results': results,
            'fastest': fastest_engine,
            'summary': summary,
            'portal_info': portal_info,
        }
    
    def __init__(self, base_url: str, mac: str, proxy: Optional[str] = None,
                 timezone: str = "Europe/London", portal_engine: Optional[str] = None):
        self.base_url = base_url
        self.mac = mac
        self.proxy = proxy
        self.timezone = timezone
        
        # Get portal engine setting - priority: parameter > global settings
        if portal_engine:
            self.portal_engine = portal_engine
            logger.debug(f"UnifiedMacPortalClient using provided portal_engine: {portal_engine}")
        else:
            try:
                from apps.m3u.mac_portal_models import MACPortalGlobalSettings
                settings = MACPortalGlobalSettings.get_settings()
                self.portal_engine = getattr(settings, 'portal_engine', 'auto')
            except Exception:
                self.portal_engine = 'auto'
        
        # Create the appropriate client
        self._engine_client = None  # New: Uses portal_engines registry
        self._mac_client = None
        self._successful_engine = None  # Track which engine worked
        self._original_engine_mode = self.portal_engine  # Remember original setting
        self._is_fastest_mode = False  # Track if we're using fastest mode
        
        # Handle "fastest" mode - use benchmarked engine if available, else fall back to auto
        if self.portal_engine == 'fastest':
            self._is_fastest_mode = True
            fastest_data = self.get_fastest_engine(base_url)
            if fastest_data:
                # Use the benchmarked fastest engine
                self.portal_engine = fastest_data['engine']
                logger.info(f"FASTEST mode: Using benchmarked engine '{self.portal_engine}' for {base_url[:50]}...")
            else:
                # No benchmark data - fall back to auto
                self.portal_engine = 'auto'
                logger.info(f"FASTEST mode: No benchmark data for {base_url[:50]}..., falling back to auto")
        
        # For specific engines (not auto), create engine from registry
        if self.portal_engine and self.portal_engine not in ('auto', '', None):
            try:
                from apps.m3u.portal_engines import create_engine
                self._engine_client = create_engine(
                    engine_name=self.portal_engine,
                    portal_url=base_url,
                    mac=mac,
                    proxy=proxy
                )
                if self._engine_client:
                    logger.info(f"UnifiedMacPortalClient using engine: {self.portal_engine}")
                else:
                    logger.warning(f"Engine '{self.portal_engine}' not found in registry")
            except Exception as e:
                logger.warning(f"Failed to create engine from registry: {e}")
                # Fallback to unified_portal_engine for backwards compatibility
                try:
                    from apps.m3u.unified_portal_engine import create_portal_client
                    self._engine_client = create_portal_client(
                        portal_url=base_url,
                        mac=mac,
                        engine=self.portal_engine,
                        proxy=proxy
                    )
                except Exception as e2:
                    logger.warning(f"Fallback to unified_portal_engine also failed: {e2}")
        
        # Always create MacPortalClient as fallback
        self._mac_client = MacPortalClient(
            base_url=base_url,
            mac=mac,
            proxy=proxy,
            timezone=timezone
        )
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get all channels using the configured engine.
        
        For AUTO mode: Tries all engines in priority order until one succeeds.
        For FASTEST mode: Uses benchmarked engine, falls back to AUTO if it fails.
        """
        # AUTO mode: Try all engines in order
        if self.portal_engine in ('auto', '', None):
            return self._get_channels_auto_mode()
        
        # Specific engine mode (including fastest mode with resolved engine)
        if self._engine_client:
            try:
                raw_channels = self._engine_client.get_all_channels()
                if raw_channels:
                    self._successful_engine = self.portal_engine
                    logger.info(f"Engine {self.portal_engine} returned {len(raw_channels)} channels")
                    return self._normalize_channels(raw_channels)
                else:
                    logger.warning(f"Engine {self.portal_engine} returned no channels")
            except Exception as e:
                logger.warning(f"Engine.get_all_channels failed: {e}")
            
            # FASTEST mode fallback: If benchmarked engine fails, try AUTO mode
            if self._is_fastest_mode:
                logger.warning(f"FASTEST mode: Benchmarked engine '{self.portal_engine}' failed, falling back to AUTO mode")
                return self._get_channels_auto_mode()
        
        # Fallback to MacPortalClient
        return self._mac_client.get_channels()
    
    def _get_channels_auto_mode(self) -> List[Dict[str, Any]]:
        """AUTO mode: Try all engines in priority order until one succeeds.
        
        ENGINE CACHING:
        - First checks if we have a cached successful engine for this portal
        - If cached engine works, use it directly (fast path)
        - If cached engine fails, clear cache and try all engines
        - Successful engine is cached INDEFINITELY until manual refresh
        
        Uses the new portal_engines registry for cleaner architecture.
        """
        from apps.m3u.portal_engines import create_engine
        
        # Check for cached successful engine first (fast path)
        cached_engine = self.get_cached_engine(self.base_url)
        if cached_engine:
            logger.info(f"AUTO: Using cached engine '{cached_engine}' for {self.base_url[:50]}...")
            try:
                client = create_engine(
                    engine_name=cached_engine,
                    portal_url=self.base_url,
                    mac=self.mac,
                    proxy=self.proxy
                )
                if client:
                    raw_channels = client.get_all_channels()
                    if raw_channels and len(raw_channels) > 0:
                        self._successful_engine = cached_engine
                        self._engine_client = client
                        logger.info(f"AUTO: Cached engine '{cached_engine}' SUCCESS - {len(raw_channels)} channels")
                        return self._normalize_channels(raw_channels)
                    else:
                        logger.warning(f"AUTO: Cached engine '{cached_engine}' returned no channels, clearing cache")
                        self.clear_cached_engine(self.base_url)
            except Exception as e:
                logger.warning(f"AUTO: Cached engine '{cached_engine}' failed: {e}, clearing cache")
                self.clear_cached_engine(self.base_url)
        
        # No cache or cache failed - try all engines in order
        logger.info(f"AUTO mode: Trying engines in order: {self.AUTO_ENGINE_ORDER}")
        
        for engine_name in self.AUTO_ENGINE_ORDER:
            try:
                logger.info(f"AUTO: Trying engine '{engine_name}'...")
                
                # Create client from new registry
                client = create_engine(
                    engine_name=engine_name,
                    portal_url=self.base_url,
                    mac=self.mac,
                    proxy=self.proxy
                )
                
                if not client:
                    logger.warning(f"AUTO: Engine '{engine_name}' not found in registry")
                    continue
                
                # Try to get channels
                raw_channels = client.get_all_channels()
                
                if raw_channels and len(raw_channels) > 0:
                    self._successful_engine = engine_name
                    self._engine_client = client  # Keep for later use (genres, expiry)
                    
                    # Cache successful engine for future requests
                    self.set_cached_engine(self.base_url, engine_name)
                    
                    logger.info(f"AUTO: Engine '{engine_name}' SUCCESS - {len(raw_channels)} channels")
                    return self._normalize_channels(raw_channels)
                else:
                    logger.warning(f"AUTO: Engine '{engine_name}' returned no channels")
                    
            except Exception as e:
                logger.warning(f"AUTO: Engine '{engine_name}' failed: {e}")
                continue
        
        # All engines failed - try MacPortalClient as last resort
        logger.warning("AUTO: All engines failed, trying MacPortalClient fallback")
        try:
            channels = self._mac_client.get_channels()
            if channels:
                self._successful_engine = 'macreplay_fallback'
                # Cache the fallback too
                self.set_cached_engine(self.base_url, 'macreplay')
                logger.info(f"AUTO: MacPortalClient fallback SUCCESS - {len(channels)} channels")
                return channels
        except Exception as e:
            logger.error(f"AUTO: MacPortalClient fallback also failed: {e}")
        
        logger.error("AUTO: All engines and fallback failed - no channels retrieved")
        return []
    
    def _normalize_channels(self, raw_channels: List[Dict]) -> List[Dict]:
        """Normalize raw channel data to MacPortalClient format."""
        import base64
        normalized = []
        
        # Get genres map for group names
        genres_map = {}
        if self._engine_client:
            try:
                # Try get_genres method (available on most engines)
                if hasattr(self._engine_client, 'get_genres'):
                    genres = self._engine_client.get_genres()
                    if genres:
                        for g in genres:
                            gid = g.get('id')
                            title = g.get('title') or g.get('name')
                            if gid and title:
                                genres_map[str(gid)] = title
                        logger.info(f"Loaded {len(genres_map)} genres for group mapping")
            except Exception as e:
                logger.warning(f"Could not load genres for group mapping: {e}")
        
        # If no genres loaded, try to build map from channel data itself
        if not genres_map:
            logger.info("Building genres map from channel data...")
            for ch in raw_channels:
                # Try to extract genre info from channel
                genre_id = ch.get('tv_genre_id') or ch.get('genre_id')
                genre_title = (
                    ch.get('tv_genre_title') or 
                    ch.get('genre_title') or 
                    ch.get('category_name') or
                    ch.get('cat_name') or
                    ch.get('group_name') or
                    ch.get('group_title')
                )
                if genre_id and genre_title:
                    genres_map[str(genre_id)] = genre_title
            if genres_map:
                logger.info(f"Built genres map with {len(genres_map)} entries from channel data")
        
        for ch in raw_channels:
            ch_id = ch.get('id')
            name = ch.get('name') or f"Channel {ch_id}"
            cmd = ch.get('cmd') or ''
            
            if not cmd:
                continue
            
            # Detect group title - try multiple sources
            group_title = None
            
            # First try direct title fields
            for key in ['tv_genre_title', 'genre_title', 'category_name', 'cat_name', 
                        'group_name', 'group_title', 'genre_name']:
                val = ch.get(key)
                if val and isinstance(val, str) and val.strip():
                    group_title = val.strip()
                    break
            
            # If no direct title, try to look up by ID
            if not group_title:
                genre_id = ch.get('tv_genre_id') or ch.get('genre_id') or ch.get('cat_id')
                if genre_id:
                    group_title = genres_map.get(str(genre_id))
                    if not group_title:
                        # Use numeric ID as fallback group name
                        group_title = f"Group {genre_id}"
            
            # Final fallback
            if not group_title:
                group_title = 'MAC'
            
            # Create mac:// URL
            proxy_str = self.proxy or ""
            mac_data = f"{self.base_url}|{self.mac}|{cmd}|{proxy_str}"
            encoded_data = base64.urlsafe_b64encode(mac_data.encode()).decode()
            url = f"mac://{encoded_data}"
            
            normalized.append({
                'id': ch_id,
                'name': name,
                'group': group_title,
                'url': url,
                'logo': ch.get('logo') or ch.get('logo_url') or '',
                'cmd': cmd,
                'raw': ch,
            })
        
        # Log group distribution for debugging
        group_counts = {}
        for ch in normalized:
            g = ch.get('group', 'Unknown')
            group_counts[g] = group_counts.get(g, 0) + 1
        logger.info(f"Normalized {len(normalized)} channels into {len(group_counts)} groups")
        if len(group_counts) <= 5:
            logger.info(f"Group distribution: {group_counts}")
        
        return normalized
    
    def get_expires(self) -> Optional[str]:
        """Get account expiry info."""
        if self._engine_client:
            try:
                # Try get_account_info if available (unified_portal_engine style)
                if hasattr(self._engine_client, 'get_account_info'):
                    info = self._engine_client.get_account_info()
                    if info:
                        return info.get('phone') or info.get('tariff_expired_date')
                # Try get_profile for portal_engines style
                elif hasattr(self._engine_client, 'get_profile') and hasattr(self._engine_client, 'identity'):
                    if self._engine_client.identity.token:
                        profile = self._engine_client.get_profile(self._engine_client.identity.token)
                        if profile:
                            js = profile.get('js', {})
                            return js.get('phone') or js.get('tariff_expired_date')
            except Exception:
                pass
        
        return self._mac_client.get_expires()
    
    def create_link(self, cmd: str) -> str:
        """Create stream link for a channel command."""
        if self._engine_client:
            try:
                link = self._engine_client.create_link(cmd)
                if link:
                    return link
            except Exception as e:
                logger.warning(f"Engine.create_link failed: {e}")
        
        return self._mac_client.create_link(cmd)
    
    def handshake(self) -> str:
        """Perform handshake and get token."""
        if self._engine_client:
            try:
                result = self._engine_client.perform_handshake()
                if result.success:
                    return result.token
            except Exception:
                pass
        
        return self._mac_client.handshake()
    
    def get_genres_map(self) -> Dict[str, str]:
        """Get genre ID to name mapping."""
        if self._engine_client:
            try:
                if hasattr(self._engine_client, 'get_genres'):
                    genres = self._engine_client.get_genres()
                    if genres:
                        return {str(g.get('id')): g.get('title') or g.get('name') 
                                for g in genres if g.get('id')}
            except Exception:
                pass
        
        return self._mac_client.get_genres_map()
