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
                    js = data.get("js", {})
                    
                    # Handle case where portal returns empty list instead of dict
                    if isinstance(js, list):
                        if not js:
                            logger.debug(f"Portal returned empty list for cmd={cmd} (channel may not exist)")
                        raise ValueError("Portal returned list instead of dict")
                    
                    link = js.get("cmd", "").split()[-1]
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
                    js = data.get("js", {})
                    
                    # Handle empty list response (channel not found/disabled)
                    if isinstance(js, list):
                        if not js:
                            logger.debug(f"Portal returned empty list for cmd={cmd}")
                        else:
                            logger.debug(f"Portal returned non-empty list instead of dict: {js}")
                        raise ValueError("Portal returned list instead of dict")
                    
                    link = js.get("cmd", "").split()[-1]
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
                        
                        # Use MACStateManager to check BUSY status
                        from apps.proxy.ts_proxy.mac_state_manager import MACStateManager
                        mac_state = MACStateManager(redis_client)
                        
                        for mac in candidates:
                            if mac_state.is_busy(mac.id):
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
    
    @staticmethod
    def _get_engine_cache_key(portal_url: str) -> str:
        """Generate cache key for portal engine."""
        import hashlib
        url_hash = hashlib.md5(portal_url.encode()).hexdigest()[:16]
        return f"portal_engine:{url_hash}"
    
    @staticmethod
    def get_cached_engine(portal_url: str) -> Optional[str]:
        """Get cached successful engine for portal URL.
        
        Uses persistent DB cache (MACPortalGlobalSettings.engine_cache) for reliability.
        Falls back to Django cache if DB not available.
        """
        # Try persistent DB cache first (survives restarts)
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            if settings.engine_cache:
                engine = settings.engine_cache.get(portal_url)
                if engine:
                    logger.debug(f"Found cached engine '{engine}' for {portal_url[:50]}... (from DB)")
                    return engine
        except Exception as e:
            logger.debug(f"Could not read engine cache from DB: {e}")
        
        # Fallback to Django cache
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        return cache.get(cache_key)
    
    @staticmethod
    def set_cached_engine(portal_url: str, engine_name: str):
        """Cache successful engine for portal URL.
        
        Writes to both persistent DB cache and Django cache for reliability.
        """
        # Write to persistent DB cache
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            if not settings.engine_cache:
                settings.engine_cache = {}
            settings.engine_cache[portal_url] = engine_name
            settings.save(update_fields=['engine_cache'])
            logger.info(f"Cached engine '{engine_name}' for {portal_url[:50]}... (persistent)")
        except Exception as e:
            logger.warning(f"Could not write engine cache to DB: {e}")
        
        # Also write to Django cache as backup
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        cache.set(cache_key, engine_name, UnifiedMacPortalClient.ENGINE_CACHE_TIMEOUT)
    
    @staticmethod
    def clear_cached_engine(portal_url: str):
        """Clear cached engine for portal URL (e.g., when it stops working).
        
        Clears from both persistent DB cache and Django cache.
        """
        # Clear from persistent DB cache
        try:
            from apps.m3u.mac_portal_models import MACPortalGlobalSettings
            settings = MACPortalGlobalSettings.get_settings()
            if settings.engine_cache and portal_url in settings.engine_cache:
                del settings.engine_cache[portal_url]
                settings.save(update_fields=['engine_cache'])
                logger.info(f"Cleared cached engine for {portal_url[:50]}... (from DB)")
        except Exception as e:
            logger.warning(f"Could not clear engine cache from DB: {e}")
        
        # Also clear from Django cache
        cache_key = UnifiedMacPortalClient._get_engine_cache_key(portal_url)
        cache.delete(cache_key)
    
    # Benchmark methods removed - use AUTO mode instead
    # AUTO mode automatically tests all engines and selects the fastest
    
    def __init__(self, base_url: str, mac: str, proxy: Optional[str] = None,
                 timezone: str = "Europe/London", portal_engine: Optional[str] = None):
        """Initialize UnifiedMacPortalClient."""
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
        
        # Create the actual engine client
        self._client = self._create_client()
    
    def _create_client(self):
        """Create the appropriate engine client based on portal_engine setting."""
        from .portal_engines import create_engine
        
        # For AUTO mode: try cached engine first, then try all engines
        if self.portal_engine == 'auto':
            # Check cache first
            cached_engine = self.get_cached_engine(self.base_url)
            if cached_engine:
                logger.debug(f"Using cached engine '{cached_engine}' for {self.base_url[:50]}...")
                client = create_engine(cached_engine, self.base_url, self.mac, proxy=self.proxy)
                if client:
                    return client
                else:
                    # Cached engine failed, clear cache and try all
                    logger.warning(f"Cached engine '{cached_engine}' failed, trying all engines...")
                    self.clear_cached_engine(self.base_url)
            
            # Try all engines in priority order
            for engine_name in self.AUTO_ENGINE_ORDER:
                try:
                    logger.debug(f"Trying engine '{engine_name}' for {self.base_url[:50]}...")
                    client = create_engine(engine_name, self.base_url, self.mac, proxy=self.proxy)
                    if client:
                        # Test if engine works with a simple handshake
                        try:
                            result = client.perform_handshake()
                            if result and result.success:
                                logger.info(f"Engine '{engine_name}' works! Caching for future use.")
                                self.set_cached_engine(self.base_url, engine_name)
                                return client
                        except Exception as e:
                            logger.debug(f"Engine '{engine_name}' handshake failed: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Engine '{engine_name}' creation failed: {e}")
                    continue
            
            # All engines failed - fallback to macreplay
            logger.warning(f"All engines failed for {self.base_url[:50]}, using macreplay as fallback")
            return create_engine('macreplay', self.base_url, self.mac, proxy=self.proxy)
        
        # Specific engine requested
        client = create_engine(self.portal_engine, self.base_url, self.mac, proxy=self.proxy)
        if not client:
            logger.error(f"Failed to create engine '{self.portal_engine}', falling back to macreplay")
            client = create_engine('macreplay', self.base_url, self.mac, proxy=self.proxy)
        return client
    
    # Delegate all methods to the underlying client
    def perform_handshake(self):
        """Perform handshake with portal."""
        return self._client.perform_handshake() if self._client else None
    
    def get_profile(self):
        """Get user profile."""
        return self._client.get_profile() if self._client else None
    
    def get_expires(self):
        """Get expiry information."""
        return self._client.get_expires() if self._client else None
    
    def get_genres(self):
        """Get available genres."""
        return self._client.get_genres() if self._client else []
    
    def get_channels_by_genre(self, genre_id):
        """Get channels for a specific genre."""
        return self._client.get_channels_by_genre(genre_id) if self._client else []
    
    def get_all_channels(self):
        """Get all channels (raw, without normalization)."""
        return self._client.get_all_channels() if self._client else []
    
    def get_channels(self):
        """Get all channels with normalization (groups, mac:// URLs).
        
        This method normalizes raw channel data to include:
        - group: Genre/category name (from get_genres or channel data)
        - url: mac:// encoded URL for proxy resolution
        - name, cmd, logo, etc.
        """
        raw_channels = self.get_all_channels()
        if not raw_channels:
            return []
        
        return self._normalize_channels(raw_channels)
    
    def _normalize_channels(self, raw_channels):
        """Normalize raw channel data to MacPortalClient format.
        
        If channels are already normalized (have 'group' and 'url' keys with proper format),
        they are returned as-is to avoid double-normalization.
        """
        import base64
        
        if not raw_channels:
            return []
        
        # Check if channels are already normalized by the engine
        first_ch = raw_channels[0] if raw_channels else {}
        is_already_normalized = (
            'group' in first_ch and 
            'url' in first_ch and 
            isinstance(first_ch.get('url', ''), str) and
            first_ch.get('url', '').startswith('mac://')
        )
        
        if is_already_normalized:
            group_counts = {}
            for ch in raw_channels:
                g = ch.get('group', 'Unknown')
                group_counts[g] = group_counts.get(g, 0) + 1
            logger.info(f"Channels already normalized: {len(raw_channels)} channels in {len(group_counts)} groups")
            return raw_channels
        
        # Get genres map for group names
        genres_map = {}
        
        # Try to load genres from engine client
        if self._client:
            try:
                if hasattr(self._client, 'get_genres'):
                    genres = self._client.get_genres()
                    if genres:
                        for g in genres:
                            gid = g.get('id')
                            title = g.get('title') or g.get('name')
                            if gid and title:
                                genres_map[str(gid)] = title
                        logger.info(f"Loaded {len(genres_map)} genres for group mapping")
            except Exception as e:
                logger.warning(f"Could not load genres: {e}")
        
        # If no genres loaded, try to build map from channel data
        if not genres_map:
            for ch in raw_channels:
                genre_id = ch.get('tv_genre_id') or ch.get('genre_id')
                genre_title = (
                    ch.get('tv_genre_title') or 
                    ch.get('genre_title') or 
                    ch.get('category_name') or
                    ch.get('group_name')
                )
                if genre_id and genre_title:
                    genres_map[str(genre_id)] = genre_title
            if genres_map:
                logger.info(f"Built genres map with {len(genres_map)} entries from channel data")
        
        normalized = []
        for ch in raw_channels:
            ch_id = ch.get('id')
            name = ch.get('name') or f"Channel {ch_id}"
            cmd = ch.get('cmd') or ''
            
            if not cmd:
                continue
            
            # Detect group title
            group_title = None
            
            # First try direct title fields
            for key in ['tv_genre_title', 'genre_title', 'category_name', 'group_name', 'group_title']:
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
        
        # Log group distribution
        group_counts = {}
        for ch in normalized:
            g = ch.get('group', 'Unknown')
            group_counts[g] = group_counts.get(g, 0) + 1
        logger.info(f"Normalized {len(normalized)} channels into {len(group_counts)} groups")
        
        return normalized
    
    def create_link(self, cmd):
        """Create stream link."""
        return self._client.create_link(cmd) if self._client else None
    
    def get_vod_categories(self):
        """Get VOD categories."""
        return self._client.get_vod_categories() if self._client else []
    
    def get_vod_items(self, category_id):
        """Get VOD items for a category."""
        return self._client.get_vod_items(category_id) if self._client else []
    
    def create_vod_link(self, cmd):
        """Create VOD stream link."""
        return self._client.create_vod_link(cmd) if self._client else None
    
    # OLD BENCHMARK CODE REMOVED - was incorrectly placed in __init__
    # If benchmark functionality is needed, it should be a separate method
    # For now, AUTO mode with caching provides the same benefit


# SEPARATE CLASS BELOW - MACPortalStrategy
# This is a different class, not part of UnifiedMacPortalClient


class MACPortalStrategy:
    """
    Strategy pattern for MAC Portal access with engine selection.
    This class is DEPRECATED - use UnifiedMacPortalClient instead.
    """
    
    # OLD BENCHMARK CODE REMOVED FROM HERE (was ~300 lines)
    # It was incorrectly placed between class declaration and __init__
    # The benchmark functionality is now handled by AUTO mode in UnifiedMacPortalClient
    
    # REMOVED: Duplicate __init__ that was overriding the correct one above
    # The correct __init__ is defined earlier in UnifiedMacPortalClient class (around line 1511)
    # This duplicate was causing UnifiedMacPortalClient to not work properly
    
    def __init__(self, base_url: str, mac: str, proxy: Optional[str] = None,
                 timezone: str = "Europe/London", portal_engine: Optional[str] = None):
        """Initialize MACPortalStrategy (DEPRECATED - use UnifiedMacPortalClient instead)."""
        self.base_url = base_url
        self.mac = mac
        self.proxy = proxy
        self.timezone = timezone
        
        # Get portal engine setting
        if portal_engine:
            self.portal_engine = portal_engine
        else:
            try:
                from apps.m3u.mac_portal_models import MACPortalGlobalSettings
                settings = MACPortalGlobalSettings.get_settings()
                self.portal_engine = getattr(settings, 'portal_engine', 'auto')
            except Exception:
                self.portal_engine = 'auto'
        
        # Create the appropriate client
        self._engine_client = None
        self._successful_engine = None
        self._original_engine_mode = self.portal_engine
        self._is_fastest_mode = False
        
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
                    logger.info(f"MACPortalStrategy using engine: {self.portal_engine}")
                else:
                    logger.warning(f"Engine '{self.portal_engine}' not found in registry")
            except Exception as e:
                logger.warning(f"Failed to create engine from registry: {e}")
        
        # ALWAYS create MacPortalClient as fallback (required for _normalize_channels)
        self._mac_client = MacPortalClient(
            base_url=base_url,
            mac=mac,
            proxy=proxy,
            timezone=timezone
        )
    
    # REMOVED: ~300 lines of old benchmark code that was incorrectly placed here
    # The benchmark functionality is now handled by AUTO mode in UnifiedMacPortalClient

    def __del__(self):
        """Cleanup strategy session on destruction to prevent memory leaks."""
        self.close()
    
    def close(self):
        """Explicitly close strategy session to free resources."""
        if self._engine_client and hasattr(self._engine_client, 'close'):
            try:
                self._engine_client.close()
                logger.debug("UnifiedMacPortalClient: Closed engine strategy session")
            except Exception as e:
                logger.debug(f"UnifiedMacPortalClient: Error closing engine session: {e}")
        elif self._engine_client and hasattr(self._engine_client, 'session'):
            try:
                self._engine_client.session.close()
                logger.debug("UnifiedMacPortalClient: Closed engine strategy session")
            except Exception as e:
                logger.debug(f"UnifiedMacPortalClient: Error closing engine session: {e}")
        self._engine_client = None
        
        # Close fallback client if it exists
        if self._mac_client and hasattr(self._mac_client, 'close'):
            try:
                self._mac_client.close()
                logger.debug("UnifiedMacPortalClient: Closed fallback MAC client")
            except Exception as e:
                logger.debug(f"UnifiedMacPortalClient: Error closing fallback client: {e}")
        self._mac_client = None
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get all channels using the configured engine.
        
        For AUTO mode: Tries all engines in priority order until one succeeds.
        For FASTEST mode: Uses benchmarked engine, falls back to AUTO if it fails.
        """
        # AUTO mode: Try all engines in order
        if self.portal_engine in ('auto', '', None):
            return self._get_channels_auto_mode()
        
        # Specific engine mode - engine client was created in __init__
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
        
        # Fallback to MacPortalClient (always available, created in __init__)
        return self._mac_client.get_channels()
    
    def _get_channels_auto_mode(self) -> List[Dict[str, Any]]:
        """AUTO mode: Intelligente Engine-Auswahl mit Caching.
        
        STRATEGIE:
        - Wenn Cache existiert: Verwende gecachte Engine (schneller Pfad)
        - Wenn kein Cache: Teste ALLE Engines und wähle die SCHNELLSTE
        - Cache wird persistent gespeichert (überlebt Server-Neustarts)
        - Cache wird nur manuell gelöscht (via "Calibrate AUTO")
        
        GESCHWINDIGKEITSTEST:
        - Misst Zeit für Handshake + Channels
        - Wählt Engine mit niedrigster Gesamtzeit
        - Cached die schnellste Engine für zukünftige Requests
        """
        from apps.m3u.portal_engines import create_engine
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        import time
        
        # Check persistent cache first (fast path)
        try:
            settings = MACPortalGlobalSettings.get_settings()
            cached_engine = settings.engine_cache.get(self.base_url) if settings.engine_cache else None
        except Exception:
            cached_engine = None
        
        if cached_engine:
            logger.info(f"AUTO: Verwende gecachte Engine '{cached_engine}' für {self.base_url[:50]}...")
            client = None
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
                        client = None  # Don't delete successful client
                        logger.info(f"AUTO: Gecachte Engine '{cached_engine}' ERFOLG - {len(raw_channels)} Kanäle")
                        return self._normalize_channels(raw_channels)
                    else:
                        logger.warning(f"AUTO: Gecachte Engine '{cached_engine}' lieferte keine Kanäle, lösche Cache")
                        # Clear from persistent cache
                        if settings.engine_cache and self.base_url in settings.engine_cache:
                            del settings.engine_cache[self.base_url]
                            settings.save(update_fields=['engine_cache'])
            except Exception as e:
                logger.warning(f"AUTO: Gecachte Engine '{cached_engine}' fehlgeschlagen: {e}, lösche Cache")
                # Clear from persistent cache
                try:
                    if settings.engine_cache and self.base_url in settings.engine_cache:
                        del settings.engine_cache[self.base_url]
                        settings.save(update_fields=['engine_cache'])
                except Exception:
                    pass
            finally:
                # MEMORY FIX: Close failed cached engine session
                if client and hasattr(client, 'close'):
                    try:
                        client.close()
                        logger.debug(f"AUTO: Geschlossene fehlgeschlagene Session für '{cached_engine}'")
                    except Exception:
                        pass
                elif client and hasattr(client, 'session'):
                    try:
                        client.session.close()
                        logger.debug(f"AUTO: Geschlossene fehlgeschlagene Session für '{cached_engine}'")
                    except Exception:
                        pass
                del client
        
        # Kein Cache oder Cache fehlgeschlagen - teste ALLE Engines und wähle die SCHNELLSTE
        logger.info(f"AUTO: Kein Cache gefunden - teste ALLE Engines und wähle die schnellste")
        logger.info(f"AUTO: Teste Engines: {self.AUTO_ENGINE_ORDER}")
        
        engine_results = []
        
        for engine_name in self.AUTO_ENGINE_ORDER:
            client = None
            try:
                logger.info(f"AUTO: Teste Engine '{engine_name}'...")
                
                start_time = time.time()
                
                # Create client from registry
                client = create_engine(
                    engine_name=engine_name,
                    portal_url=self.base_url,
                    mac=self.mac,
                    proxy=self.proxy
                )
                
                if not client:
                    logger.warning(f"AUTO: Engine '{engine_name}' nicht in Registry gefunden")
                    continue
                
                # Try to get channels
                raw_channels = client.get_all_channels()
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                if raw_channels and len(raw_channels) > 0:
                    engine_results.append({
                        'engine': engine_name,
                        'time_ms': elapsed_ms,
                        'channels': len(raw_channels),
                        'client': client,
                        'raw_channels': raw_channels,
                        'success': True
                    })
                    logger.info(f"AUTO: Engine '{engine_name}' ERFOLG - {len(raw_channels)} Kanäle in {elapsed_ms:.0f}ms")
                    # Don't delete client yet - we might use it
                    client = None
                else:
                    logger.warning(f"AUTO: Engine '{engine_name}' lieferte keine Kanäle ({elapsed_ms:.0f}ms)")
                    
            except Exception as e:
                logger.warning(f"AUTO: Engine '{engine_name}' fehlgeschlagen: {e}")
                continue
            finally:
                # MEMORY FIX: Close failed strategy session
                if client and hasattr(client, 'close'):
                    try:
                        client.close()
                        logger.debug(f"AUTO: Geschlossene fehlgeschlagene Session für '{engine_name}'")
                    except Exception:
                        pass
                elif client and hasattr(client, 'session'):
                    try:
                        client.session.close()
                        logger.debug(f"AUTO: Geschlossene fehlgeschlagene Session für '{engine_name}'")
                    except Exception:
                        pass
                del client
        
        # Wähle die SCHNELLSTE erfolgreiche Engine
        if engine_results:
            # Sortiere nach Zeit (schnellste zuerst)
            engine_results.sort(key=lambda x: x['time_ms'])
            fastest = engine_results[0]
            
            logger.info(f"AUTO: SCHNELLSTE Engine gefunden: '{fastest['engine']}' "
                       f"({fastest['time_ms']:.0f}ms, {fastest['channels']} Kanäle)")
            
            # Zeige alle getesteten Engines
            for result in engine_results:
                logger.info(f"  - {result['engine']}: {result['time_ms']:.0f}ms, {result['channels']} Kanäle")
            
            # Cache die schnellste Engine persistent
            try:
                settings = MACPortalGlobalSettings.get_settings()
                if not settings.engine_cache:
                    settings.engine_cache = {}
                settings.engine_cache[self.base_url] = fastest['engine']
                settings.save(update_fields=['engine_cache'])
                logger.info(f"AUTO: Engine '{fastest['engine']}' persistent gecacht für {self.base_url[:50]}...")
            except Exception as e:
                logger.warning(f"AUTO: Fehler beim Cachen der Engine: {e}")
            
            # Verwende die schnellste Engine
            self._successful_engine = fastest['engine']
            self._engine_client = fastest['client']
            
            # PORTAL-INFO ERKENNUNG: Nutze die gewählte Engine um Portal-Details zu ermitteln
            try:
                portal_info = self._detect_portal_info(fastest['client'])
                if portal_info:
                    logger.info(f"AUTO: Portal-Info erkannt - Typ: {portal_info.get('portal_type')}, "
                               f"Version: {portal_info.get('portal_version')}, "
                               f"Max Connections: {portal_info.get('max_connections')}")
                    # Speichere in custom_properties (wird vom Aufrufer gespeichert)
                    self._portal_info = portal_info
            except Exception as e:
                logger.warning(f"AUTO: Portal-Info-Erkennung fehlgeschlagen: {e}")
            
            # Schließe alle anderen Clients (Memory Cleanup)
            for result in engine_results[1:]:  # Skip fastest (index 0)
                if result.get('client') and hasattr(result['client'], 'close'):
                    try:
                        result['client'].close()
                        logger.debug(f"AUTO: Geschlossene Session für nicht-gewählte Engine '{result['engine']}'")
                    except Exception:
                        pass
            
            # MEMORY CLEANUP: Force garbage collection after testing all engines
            try:
                from core.utils import cleanup_memory
                cleanup_memory(log_usage=True, force_collection=True)
                logger.info(f"AUTO: Memory cleanup abgeschlossen nach Test von {len(engine_results)} Engines")
            except Exception as e:
                logger.debug(f"AUTO: Memory cleanup fehlgeschlagen: {e}")
            
            return self._normalize_channels(fastest['raw_channels'])
        
        # Alle Engines fehlgeschlagen - versuche MacPortalClient als letzten Ausweg
        logger.warning("AUTO: Alle Engines fehlgeschlagen, versuche MacPortalClient Fallback")
        try:
            channels = self._mac_client.get_channels()
            if channels:
                self._successful_engine = 'macreplay_fallback'
                logger.info(f"AUTO: MacPortalClient Fallback ERFOLG - {len(channels)} Kanäle")
                return channels
        except Exception as e:
            logger.error(f"AUTO: MacPortalClient Fallback ebenfalls fehlgeschlagen: {e}")
        
        logger.error("AUTO: Alle Engines und Fallback fehlgeschlagen - keine Kanäle abgerufen")
        return []
    
    def _detect_portal_info(self, client) -> Optional[Dict[str, Any]]:
        """
        Erkenne Portal-Typ, Version und Max Connections.
        
        Nutzt die gewählte Engine um Portal-Details zu ermitteln.
        Basiert auf der Logik aus BasePortalStrategy.
        
        Returns:
            Dict mit portal_type, portal_version, max_connections oder None
        """
        portal_info = {
            'portal_type': 'STALKER',  # Default
            'portal_version': None,
            'max_connections': 1,  # Default
            'detected_by': 'default'
        }
        
        try:
            # 1. Prüfe URL-Pattern
            url_lower = self.base_url.lower()
            
            if '/magload.php' in url_lower or '/client/' in url_lower:
                portal_info['portal_type'] = 'MAGLOAD'
                portal_info['detected_by'] = 'url_pattern'
            elif '/stalker_portal/' in url_lower:
                portal_info['portal_type'] = 'STALKER'
                portal_info['detected_by'] = 'url_pattern'
            elif '/c/' in url_lower and '/stalker_portal/' not in url_lower:
                portal_info['portal_type'] = 'XUI'
                portal_info['detected_by'] = 'url_pattern'
            
            # 2. Hole Profil-Daten für detaillierte Info
            if hasattr(client, 'get_profile'):
                try:
                    profile = client.get_profile()
                    if profile:
                        js = profile.get('js', {})
                        
                        # Portal-Version
                        for key in ['portal_version', 'version', 'PORTAL version']:
                            if js.get(key):
                                portal_info['portal_version'] = str(js.get(key))
                                break
                        
                        # Max Connections
                        for key in ['max_connections', 'max_streams', 'max_concurrent_streams']:
                            if js.get(key):
                                try:
                                    portal_info['max_connections'] = int(js.get(key))
                                    break
                                except (ValueError, TypeError):
                                    pass
                        
                        # XTREAM/XUI Erkennung via Credentials
                        if js.get('login') and js.get('password'):
                            if '/c/' in url_lower:
                                portal_info['portal_type'] = 'XUI'
                            else:
                                portal_info['portal_type'] = 'XTREAM'
                            portal_info['detected_by'] = 'profile_credentials'
                        
                        # NXT Erkennung (hat spezielle Felder)
                        if js.get('nxt_version') or js.get('is_nxt'):
                            portal_info['portal_type'] = 'NXT'
                            portal_info['detected_by'] = 'profile_nxt'
                        
                        logger.debug(f"Portal-Info aus Profil: {portal_info}")
                except Exception as e:
                    logger.debug(f"Fehler beim Lesen des Profils: {e}")
            
            # 3. Prüfe portal_type und portal_version Properties (falls vorhanden)
            if hasattr(client, 'portal_type') and client.portal_type:
                detected_type = client.portal_type.upper()
                if detected_type != 'UNKNOWN':
                    portal_info['portal_type'] = detected_type
                    portal_info['detected_by'] = 'engine_property'
            
            if hasattr(client, 'portal_version') and client.portal_version:
                portal_info['portal_version'] = client.portal_version
            
            return portal_info
            
        except Exception as e:
            logger.warning(f"Portal-Info-Erkennung fehlgeschlagen: {e}")
            return portal_info  # Return default values
    
    def _normalize_channels(self, raw_channels: List[Dict]) -> List[Dict]:
        """Normalize raw channel data to MacPortalClient format.
        
        If channels are already normalized (have 'group' and 'url' keys with proper format),
        they are returned as-is to avoid double-normalization.
        """
        import base64
        
        if not raw_channels:
            return []
        
        # Check if channels are already normalized by the engine
        # Normalized channels have: 'group', 'url' (mac:// format), 'name', 'cmd'
        first_ch = raw_channels[0] if raw_channels else {}
        is_already_normalized = (
            'group' in first_ch and 
            'url' in first_ch and 
            isinstance(first_ch.get('url', ''), str) and
            first_ch.get('url', '').startswith('mac://')
        )
        
        if is_already_normalized:
            # Channels are already normalized by the engine (e.g., macreplay)
            # Just return them as-is
            group_counts = {}
            for ch in raw_channels:
                g = ch.get('group', 'Unknown')
                group_counts[g] = group_counts.get(g, 0) + 1
            logger.info(f"Channels already normalized: {len(raw_channels)} channels in {len(group_counts)} groups")
            if len(group_counts) <= 10:
                logger.info(f"Group distribution: {group_counts}")
            return raw_channels
        
        normalized = []
        
        # Get genres map for group names
        genres_map = {}
        
        # Try multiple sources for genres
        genres = None
        
        # 1. Try engine client first
        if self._engine_client:
            try:
                if hasattr(self._engine_client, 'get_genres'):
                    logger.info(f"Trying to load genres from engine client: {type(self._engine_client).__name__}")
                    genres = self._engine_client.get_genres()
                    if genres:
                        logger.info(f"Loaded {len(genres)} genres from engine client")
                        # Debug: Log first few genres
                        if len(genres) > 0:
                            sample = genres[:3]
                            logger.debug(f"Sample genres: {sample}")
                    else:
                        logger.warning(f"Engine client get_genres returned empty list")
                else:
                    logger.warning(f"Engine client {type(self._engine_client).__name__} has no get_genres method")
            except Exception as e:
                logger.warning(f"Engine client get_genres failed: {e}")
        
        # 2. Try MacPortalClient.get_genres_map() as fallback (returns dict directly)
        if not genres and self._mac_client:
            try:
                genres_map = self._mac_client.get_genres_map()
                if genres_map:
                    logger.info(f"Loaded {len(genres_map)} genres from MacPortalClient.get_genres_map()")
            except Exception as e:
                logger.debug(f"MacPortalClient get_genres_map failed: {e}")
        
        # 3. Build genres map from loaded genres
        if genres:
            for g in genres:
                gid = g.get('id')
                title = g.get('title') or g.get('name')
                if gid and title:
                    genres_map[str(gid)] = title
            logger.info(f"Built genres map with {len(genres_map)} entries")
        
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
        
        # Debug: Log first channel structure to understand available fields
        if raw_channels:
            first_ch = raw_channels[0]
            logger.info(f"First channel keys: {list(first_ch.keys())}")
            logger.debug(f"First channel data: {first_ch}")
        
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
