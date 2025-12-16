"""
MAC/STB Portal Client for Dispatcharr
Based on MacReplayXC v2.2.1 stb.py - Ported to Django

This module provides a comprehensive client for communicating with MAC/STB portals
(Stalker middleware) for IPTV services.
"""

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


def _get_session(use_cloudscraper=False):
    """Get or create a requests session with automatic refresh."""
    global _session, _session_created
    
    current_time = time.time()
    
    # Create new session if none exists or if too old
    if _session is None or (current_time - _session_created) > _SESSION_MAX_AGE:
        if _session is not None:
            try:
                _session.close()
            except:
                pass
        
        # Use cloudscraper if available and requested (for Cloudflare bypass)
        if use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
            _session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'linux',
                    'desktop': True
                }
            )
            logger.debug("Created cloudscraper session for Cloudflare bypass")
        else:
            _session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
            _session.mount("http://", HTTPAdapter(max_retries=retries))
            _session.mount("https://", HTTPAdapter(max_retries=retries))
            logger.debug("Created new requests session")
        
        _session_created = current_time
    
    return _session


def clear_session():
    """Clear the session to free memory."""
    global _session, _session_created
    if _session is not None:
        try:
            _session.close()
        except:
            pass
        _session = None
        _session_created = 0
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
                
                logger.debug(f"Trying token endpoint: {full_url}")
                response = _get_session().get(
                    full_url,
                    cookies=self._cookies(),
                    headers=headers,
                    proxies=proxies,
                    timeout=20,
                )
                logger.debug(f"Token request status: {response.status_code}")
                
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
            logger.debug(f"Getting expiry for MAC {self.mac}")
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
            logger.debug(f"Getting all channels for MAC {self.mac} (GET)")
            response = _get_session().get(
                portal,
                params=params,
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=30,
            )
            logger.debug(f"Channels request status: {response.status_code}")
            channels = response.json()["js"]["data"]
            if channels:
                logger.info(f"Got {len(channels)} channels for MAC {self.mac}")
                return channels
        except Exception as e:
            logger.debug(f"GET request failed: {e}, trying POST")
        
        # Try POST as fallback (some portals require this) - EXACT MacReplayXC copy
        try:
            logger.debug(f"Getting all channels for MAC {self.mac} (POST)")
            response = _get_session().post(
                portal,
                data=params,
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=30,
            )
            logger.debug(f"Channels request status: {response.status_code}")
            channels = response.json()["js"]["data"]
            if channels:
                logger.info(f"Got {len(channels)} channels for MAC {self.mac} via POST")
                return channels
        except requests.Timeout:
            logger.error(f"Timeout getting channels for MAC {self.mac}")
        except requests.RequestException as e:
            logger.error(f"Request error getting channels for MAC {self.mac}: {e}")
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
    def resolve_mac_url(mac_url: str, proxy: Optional[str] = None) -> str:
        """Resolve a mac:// URL to a real stream URL.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            proxy: Optional proxy to use (overrides encoded proxy)
            
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
            
            logger.info(f"Resolving MAC URL for portal {portal_url}, MAC {mac[:8]}..., proxy: {use_proxy or 'none'}")
            
            # Create client and resolve URL
            client = MacPortalClient(base_url=portal_url, mac=mac, proxy=use_proxy)
            resolved_url = client.create_link(cmd)
            logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
            return resolved_url
        except Exception as e:
            logger.error(f"Failed to resolve mac:// URL: {e}")
            raise MacPortalError(f"Failed to resolve MAC URL: {e}")

    @staticmethod
    def resolve_mac_url_with_busy_check(mac_url: str, proxy: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Resolve a mac:// URL to a real stream URL, preferring non-busy MACs.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            proxy: Optional proxy to use (overrides encoded proxy)
            
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
            
            logger.info(f"Resolving MAC URL with MAC {selected_mac[:8]}... (original: {original_mac[:8]}...)")
            
            # Create client and resolve URL with selected MAC
            client = MacPortalClient(base_url=portal_url, mac=selected_mac, proxy=use_proxy)
            resolved_url = client.create_link(cmd)
            logger.info(f"Resolved MAC URL to: {resolved_url[:80]}...")
            return resolved_url, selected_mac
            
        except Exception as e:
            logger.error(f"Failed to resolve mac:// URL with busy check: {e}")
            raise MacPortalError(f"Failed to resolve MAC URL: {e}")
    
    @staticmethod
    def resolve_mac_url_with_failover_mac(mac_url: str, failover_mac: str, proxy: Optional[str] = None) -> str:
        """Resolve a mac:// URL to a real stream URL using a different MAC address for failover.
        
        Args:
            mac_url: URL in format mac://base64(portal_url|mac|cmd|proxy)
            failover_mac: MAC address to use instead of the one encoded in the URL
            proxy: Optional proxy to use (overrides encoded proxy)
            
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
            
            logger.info(f"Resolving MAC URL for failover - portal {portal_url}, failover MAC {failover_mac[:8]}..., proxy: {use_proxy or 'none'}")
            
            # Create client with failover MAC and resolve URL
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
            logger.debug(f"Getting EPG for MAC {self.mac}")
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