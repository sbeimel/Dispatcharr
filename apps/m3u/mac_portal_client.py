"""
MAC/STB Portal Client - Enhanced implementation based on macreplayxc-main.
Supports Cloudflare bypass, multiple proxy types (HTTP, SOCKS, Shadowsocks),
and improved endpoint detection.
"""

import logging
import re
import time
import hashlib
import random
import string
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, List, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
    logger.info("cloudscraper successfully imported and available")
except ImportError as e:
    CLOUDSCRAPER_AVAILABLE = False
    logger.warning(f"cloudscraper not available - some portals with Cloudflare protection may not work: {e}")
except Exception as e:
    CLOUDSCRAPER_AVAILABLE = False
    logger.error(f"Error importing cloudscraper: {e}")


class MacPortalError(Exception):
    """Error while accessing MAC/STB portal."""
    pass


# Session management with periodic refresh to prevent memory leaks
_session_cache: Dict[str, Tuple[requests.Session, float]] = {}
_SESSION_MAX_AGE = 300  # Refresh session every 5 minutes


def _get_session(use_cloudscraper: bool = False, session_key: str = "default") -> requests.Session:
    """Get or create a requests session with automatic refresh."""
    global _session_cache
    
    current_time = time.time()
    cache_key = f"{session_key}_{use_cloudscraper}"
    
    # Check if we have a valid cached session
    if cache_key in _session_cache:
        session, created_at = _session_cache[cache_key]
        if (current_time - created_at) < _SESSION_MAX_AGE:
            return session
        # Session too old, close it
        try:
            session.close()
        except:
            pass
    
    # Create new session
    if use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
        session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'linux',
                'desktop': True
            }
        )
        logger.info("Created cloudscraper session for Cloudflare bypass")
    else:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        if use_cloudscraper:
            logger.warning("Cloudscraper requested but not available, using regular requests session")
        else:
            logger.debug("Created new requests session")
    
    _session_cache[cache_key] = (session, current_time)
    return session


def clear_session_cache():
    """Clear all cached sessions to free memory."""
    global _session_cache
    for key, (session, _) in list(_session_cache.items()):
        try:
            session.close()
        except:
            pass
    _session_cache.clear()
    logger.debug("Cleared session cache")


def parse_proxy_url(proxy_url: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Parse proxy URL and determine proxy type and configuration.
    
    Supports:
    - HTTP: http://proxy:port or http://user:pass@proxy:port
    - HTTPS: https://proxy:port or https://user:pass@proxy:port  
    - SOCKS5: socks5://proxy:port or socks5://user:pass@proxy:port
    - SOCKS4: socks4://proxy:port
    - Shadowsocks: ss://method:password@server:port
    """
    if not proxy_url or not isinstance(proxy_url, str):
        return None
    
    proxy_url = proxy_url.strip()
    if not proxy_url:
        return None
    
    # Check for Shadowsocks proxies
    if proxy_url.startswith('ss://'):
        try:
            import base64
            parsed = urlparse(proxy_url)
            if parsed.hostname and parsed.port:
                if parsed.username and parsed.password:
                    method = parsed.username
                    password = parsed.password
                else:
                    if '@' in proxy_url:
                        auth_part = proxy_url.split('://')[1].split('@')[0]
                        try:
                            decoded = base64.b64decode(auth_part).decode('utf-8')
                            if ':' in decoded:
                                method, password = decoded.split(':', 1)
                            else:
                                return None
                        except:
                            return None
                    else:
                        return None
                
                return {
                    'type': 'shadowsocks',
                    'server': parsed.hostname,
                    'port': parsed.port,
                    'method': method,
                    'password': password
                }
        except Exception as e:
            logger.debug(f"Failed to parse Shadowsocks URL: {e}")
            return None
    
    # Check for SOCKS proxies
    if proxy_url.startswith(('socks5://', 'socks4://')):
        return {'http': proxy_url, 'https': proxy_url}
    
    # Check for HTTP/HTTPS proxies
    if proxy_url.startswith(('http://', 'https://')):
        return {'http': proxy_url, 'https': proxy_url}
    
    # If no protocol specified, assume HTTP
    if '://' not in proxy_url:
        http_url = f"http://{proxy_url}"
        return {'http': http_url, 'https': http_url}
    
    return None


def get_proxy_type(proxy_url: Optional[str]) -> str:
    """Get the type of proxy from URL."""
    if not proxy_url:
        return 'none'
    
    proxy_url = proxy_url.strip().lower()
    
    if proxy_url.startswith('ss://'):
        return 'shadowsocks'
    elif proxy_url.startswith('socks5://'):
        return 'socks5'
    elif proxy_url.startswith('socks4://'):
        return 'socks4'
    elif proxy_url.startswith('https://'):
        return 'https'
    elif proxy_url.startswith('http://'):
        return 'http'
    elif '://' not in proxy_url:
        return 'http'
    else:
        return 'unknown'


class MacPortalClient:
    """
    Enhanced client for Stalker-/STB portals with MAC login.
    
    Features:
    - Cloudflare bypass via cloudscraper
    - Multiple proxy types (HTTP, SOCKS4/5, Shadowsocks)
    - Improved endpoint detection with multiple fallback paths
    - GET and POST method support
    - MAG200/MAG254/MAG420 header fallbacks
    """

    def __init__(
        self,
        base_url: str,
        mac: str,
        proxy: Optional[str] = None,
        timezone: str = "Europe/Berlin",
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        
        self.original_base_url = base_url.rstrip("/")
        self.mac = mac
        self.timezone = timezone
        self.proxy = proxy
        self.proxy_type = get_proxy_type(proxy)
        self.proxies = parse_proxy_url(proxy)
        
        self.portal_url: Optional[str] = None
        self.token: Optional[str] = None
        self.genres_by_id: Dict[str, str] = {}
        
        # Parse base URL
        parsed = urlparse(self.original_base_url)
        if not parsed.scheme:
            self.original_base_url = "http://" + self.original_base_url
            parsed = urlparse(self.original_base_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.url_path = parsed.path.rstrip('/')

    def _get_session(self, use_cloudscraper: bool = False) -> requests.Session:
        """Get appropriate session based on proxy type."""
        session_key = f"{self.mac}_{self.proxy or 'direct'}"
        return _get_session(use_cloudscraper, session_key)

    def _get_request_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxies dict for requests, None for Shadowsocks (pre-configured session)."""
        if self.proxy_type == 'shadowsocks':
            return None
        return self.proxies

    def _generate_device_ids(self) -> Dict[str, str]:
        """Generate device IDs based on MAC for enhanced STB emulation."""
        device_id = hashlib.sha256(self.mac.encode()).hexdigest()
        device_id2 = hashlib.sha256((self.mac + "salt").encode()).hexdigest()
        serial_number = hashlib.md5(self.mac.encode()).hexdigest().upper()
        random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        return {
            'device_id': device_id,
            'device_id2': device_id2,
            'serial_number': serial_number,
            'random_id': random_id,
        }

    def _get_enhanced_cookies(self) -> Dict[str, str]:
        """Generate enhanced cookies for STB emulation."""
        ids = self._generate_device_ids()
        return {
            "mac": self.mac,
            "stb_lang": "en",
            "timezone": self.timezone,
            "deviceId": ids['device_id'],
            "deviceId2": ids['device_id2'],
            "serial_number": ids['serial_number'],
            "sn": ids['serial_number'],
            "rand": ids['random_id'],
        }

    def _get_basic_cookies(self) -> Dict[str, str]:
        """Get basic cookies for requests."""
        return {
            "mac": self.mac,
            "stb_lang": "en",
            "timezone": self.timezone,
        }

    def _get_headers(self, with_auth: bool = False, model: str = "MAG250") -> Dict[str, str]:
        """Get headers for requests with optional model variation."""
        if model == "MAG254":
            user_agent = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 2712 Safari/533.3"
            x_user_agent = "Model: MAG254; Link: WiFi"
        elif model == "MAG420":
            user_agent = "Mozilla/5.0 (Linux; Android 7.0; MAG420) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36"
            x_user_agent = "Model: MAG420; Link: WiFi"
        else:  # MAG250 default
            user_agent = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
            x_user_agent = f"Model: MAG250; Link: WiFi; MAC: {self.mac}"
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": self.base_url + "/",
            "X-User-Agent": x_user_agent,
        }
        
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            headers["Authorization"] = "Bearer undefined"
        
        return headers

    # ------------- Portal URL Resolution -------------

    def _parse_xpcom_response(self, url: str, response: requests.Response) -> Optional[str]:
        """Parse xpcom.common.js to extract portal URL."""
        try:
            java = response.text.replace(" ", "").replace("'", "").replace("+", "")
            pattern = re.search(r"varpattern.*\/(\(http.*)\/;", java).group(1)
            result = re.search(pattern, url)
            protocolIndex = re.search(r"this\.portal_protocol.*(\d).*;", java).group(1)
            ipIndex = re.search(r"this\.portal_ip.*(\d).*;", java).group(1)
            pathIndex = re.search(r"this\.portal_path.*(\d).*;", java).group(1)
            protocol = result.group(int(protocolIndex))
            ip = result.group(int(ipIndex))
            path = result.group(int(pathIndex))
            portalPattern = re.search(r"this\.ajax_loader=(.*\.php);", java).group(1)
            portal = (
                portalPattern.replace("this.portal_protocol", protocol)
                .replace("this.portal_ip", ip)
                .replace("this.portal_path", path)
            )
            return portal
        except Exception as e:
            logger.debug(f"Failed to parse xpcom response: {e}")
            return None

    def resolve_portal_url(self) -> str:
        """
        Resolve the portal URL by trying multiple detection methods.
        1. Check if URL already ends with .php
        2. Try xpcom.common.js parsing
        3. Probe common load.php paths
        """
        if self.portal_url:
            return self.portal_url

        # If URL already ends with .php, use it directly
        if self.url_path.endswith('.php'):
            self.portal_url = self.original_base_url
            logger.info("Using direct PHP endpoint: %s", self.portal_url)
            return self.portal_url

        session = self._get_session(use_cloudscraper=True)
        headers = self._get_headers()
        proxies = self._get_request_proxies()

        # Try xpcom.common.js paths first
        xpcom_paths = [
            "/c/xpcom.common.js",
            "/client/xpcom.common.js",
            "/c_/xpcom.common.js",
            "/stalker_portal/c/xpcom.common.js",
            "/stalker_portal/c_/xpcom.common.js",
            "/portal/c/xpcom.common.js",
            "/server/c/xpcom.common.js",
        ]
        
        if self.url_path and self.url_path != '/':
            xpcom_paths.insert(0, f"{self.url_path}/xpcom.common.js")
            xpcom_paths.insert(1, f"{self.url_path}xpcom.common.js")

        for path in xpcom_paths:
            try:
                test_url = self.base_url + path
                logger.debug(f"Trying xpcom.common.js at: {test_url}")
                response = session.get(test_url, headers=headers, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    portal = self._parse_xpcom_response(test_url, response)
                    if portal:
                        self.portal_url = portal
                        logger.info(f"Resolved portal URL via xpcom: {portal}")
                        return self.portal_url
            except Exception as e:
                logger.debug(f"Failed to fetch {path}: {e}")
                continue

        # Fallback: probe common load.php paths
        candidate_paths = [
            "/stalker_portal/server/load.php",
            "/stalker_portal/load.php",
            "/server/load.php",
            "/c/load.php",
            "/portal.php",
            "/load.php",
        ]
        
        if self.url_path and self.url_path != '/':
            candidate_paths.insert(0, f"{self.url_path}/portal.php")
            candidate_paths.insert(1, f"{self.url_path}/server/load.php")

        for path in candidate_paths:
            url = self.base_url + path
            try:
                r = session.get(url, headers=headers, cookies=self._get_basic_cookies(), 
                               proxies=proxies, timeout=5)
                if r.status_code < 400:
                    self.portal_url = url
                    logger.info("MAC portal detected: %s", url)
                    return self.portal_url
            except Exception as e:
                logger.debug("Portal candidate %s failed: %s", url, e)

        # Last resort: use original URL
        self.portal_url = self.original_base_url
        logger.warning("Could not detect portal URL, using base: %s", self.portal_url)
        return self.portal_url

    # ------------- Handshake / Token -------------

    def handshake(self) -> str:
        """
        Perform handshake to get authentication token.
        Tries multiple endpoints and MAG model headers as fallback.
        """
        session = self._get_session(use_cloudscraper=True)
        cookies = self._get_enhanced_cookies()
        proxies = self._get_request_proxies()
        
        parsed = urlparse(self.original_base_url)
        url_path = parsed.path.rstrip('/')
        
        # Build endpoint list
        endpoints = []
        
        if url_path.endswith('.php'):
            endpoints.append(f"{url_path}?type=stb&action=handshake&JsHttpRequest=1-xml")
        elif url_path and url_path != '/':
            endpoints.extend([
                f"{url_path}/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                f"{url_path}/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                f"{url_path}?type=stb&action=handshake&JsHttpRequest=1-xml",
            ])
        
        if not url_path.endswith('.php'):
            endpoints.extend([
                "?type=stb&action=handshake&JsHttpRequest=1-xml",
                "/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                "/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                "/stalker_portal/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",
                "/c/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
            ])
        
        models = ["MAG250", "MAG254", "MAG420"]
        
        for endpoint in endpoints:
            if endpoint.startswith('/') or endpoint.startswith('?'):
                full_url = self.base_url + endpoint
            else:
                full_url = self.original_base_url + endpoint
            
            for model in models:
                headers = self._get_headers(with_auth=False, model=model)
                try:
                    logger.debug(f"Trying handshake: {full_url} with {model}")
                    response = session.get(full_url, cookies=cookies, headers=headers,
                                          proxies=proxies, timeout=20)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if "js" in data and "token" in data["js"]:
                                token = data["js"]["token"]
                                if token:
                                    self.token = token
                                    # Store the working portal URL
                                    self.portal_url = full_url.split('?')[0]
                                    
                                    # Store any cookies from handshake response for future requests
                                    if response.cookies:
                                        logger.debug(f"Storing {len(response.cookies)} cookies from handshake")
                                        for cookie in response.cookies:
                                            session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
                                    
                                    logger.info(f"Handshake successful with {model} at {full_url}")
                                    # Small delay to let portal process the handshake
                                    time.sleep(0.1)
                                    return token
                        except Exception as e:
                            logger.debug(f"Failed to parse handshake response: {e}")
                    elif response.status_code == 403:
                        logger.debug(f"403 on {endpoint} with {model}, trying next model")
                        continue
                        
                except requests.Timeout:
                    logger.debug(f"Timeout on {endpoint}")
                except Exception as e:
                    logger.debug(f"Error on {endpoint}: {e}")
        
        raise MacPortalError(f"Failed to get token for MAC {self.mac} from all endpoints")

    # ------------- Profile & Expiry -------------

    def get_profile(self) -> Dict[str, Any]:
        """Get STB profile information."""
        if not self.token:
            self.handshake()
        
        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        cookies = self._get_enhanced_cookies()
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()
        
        parsed = urlparse(portal)
        url_path = parsed.path.rstrip('/')
        
        if url_path.endswith('.php'):
            profile_url = f"{portal}?type=stb&action=get_profile&JsHttpRequest=1-xml"
        else:
            profile_url = f"{portal}/portal.php?type=stb&action=get_profile&JsHttpRequest=1-xml"
        
        try:
            response = session.get(profile_url, cookies=cookies, headers=headers,
                                  proxies=proxies, timeout=15)
            
            if response.status_code != 200:
                # Try alternative endpoints
                alternatives = [
                    f"{portal}/server/load.php?type=stb&action=get_profile&JsHttpRequest=1-xml",
                    f"{portal}?type=stb&action=get_profile&JsHttpRequest=1-xml"
                ]
                for alt_url in alternatives:
                    try:
                        response = session.get(alt_url, cookies=cookies, headers=headers,
                                              proxies=proxies, timeout=15)
                        if response.status_code == 200:
                            break
                    except:
                        pass
            
            return response.json().get("js", {})
        except Exception as e:
            logger.error(f"Error getting profile for MAC {self.mac}: {e}")
            return {}

    def get_expires(self) -> Optional[str]:
        """Get account expiry information."""
        if not self.token:
            self.handshake()
        
        # Use the SAME session that was used for handshake to maintain cookies/state
        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        
        # Combine enhanced cookies with any session cookies from handshake
        cookies = self._get_enhanced_cookies()
        # Add any session cookies to the request cookies
        for cookie_name, cookie_value in session.cookies.items():
            cookies[cookie_name] = cookie_value
            
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()
        
        parsed = urlparse(portal)
        url_path = parsed.path.rstrip('/')
        
        if url_path.endswith('.php'):
            expires_url = f"{portal}?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
        else:
            expires_url = f"{portal}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
        
        try:
            logger.info(f"Making expiry request with combined cookies: {dict(cookies)}")
            logger.info(f"Session cookies: {dict(session.cookies)}")
            logger.info(f"Expiry request URL: {expires_url}")
            
            # Try without explicit cookies parameter - let session handle cookies
            response = session.get(expires_url, headers=headers,
                                  proxies=proxies, timeout=15)
            
            if response.status_code != 200 and not url_path.endswith('.php'):
                try:
                    response = session.get(
                        f"{portal}/server/load.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
                        headers=headers, proxies=proxies, timeout=15
                    )
                except:
                    pass
            
            data = response.json()
            expires = data.get("js", {}).get("phone", "")
            
            if expires:
                logger.info(f"Got expiry for MAC {self.mac}: {expires}")
                return expires
            return "Unlimited"
            
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Invalid JSON response getting expiry for MAC {self.mac}: {e}")
            if 'response' in locals():
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response content (first 1000 chars): {response.text[:1000]}")
                
                # Check if this is an HTML response (Cloudflare block, etc.)
                if response.text.strip().startswith('<'):
                    logger.error("Portal returned HTML instead of JSON - possible Cloudflare block or portal misconfiguration")
                    if 'cloudflare' in response.text.lower():
                        logger.error("Cloudflare protection detected in response")
                    if 'access denied' in response.text.lower():
                        logger.error("Access denied detected in response")
                
                # Try alternative endpoints if main one fails
                alternatives = [
                    f"{self.base_url}/server/load.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
                    f"{self.base_url}/stalker_portal/server/load.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
                ]
                
                logger.info(f"JSON parsing failed, trying {len(alternatives)} alternative expiry endpoints...")
                for alt_url in alternatives:
                    try:
                        logger.info(f"Trying alternative expiry endpoint: {alt_url}")
                        alt_response = session.get(alt_url, headers=headers,
                                                  proxies=proxies, timeout=15)
                        logger.info(f"Alternative endpoint response status: {alt_response.status_code}")
                        if alt_response.status_code == 200:
                            try:
                                alt_data = alt_response.json()
                                expires = alt_data.get("js", {}).get("phone", "")
                                if expires:
                                    logger.info(f"Got expiry via alternative endpoint: {expires}")
                                    return expires
                            except requests.exceptions.JSONDecodeError as alt_json_e:
                                logger.info(f"Alternative endpoint {alt_url} also returned invalid JSON: {alt_json_e}")
                                logger.info(f"Alternative response content: {alt_response.text[:200]}")
                                continue
                    except Exception as alt_e:
                        logger.info(f"Alternative endpoint {alt_url} failed: {alt_e}")
                        continue
            return None
        except Exception as e:
            logger.error(f"Error getting expiry for MAC {self.mac}: {e}")
            return None

    # ------------- Genres / Categories -------------

    def get_genres_map(self) -> Dict[str, str]:
        """Load mapping of genre/category id -> title from portal."""
        if self.genres_by_id:
            return self.genres_by_id

        if not self.token:
            self.handshake()
        
        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        cookies = self._get_basic_cookies()
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()
        
        params = {
            "action": "get_genres",
            "type": "itv",
            "JsHttpRequest": "1-xml"
        }
        
        # Try GET first, then POST
        for method in ['GET', 'POST']:
            try:
                if method == 'GET':
                    response = session.get(portal, params=params, cookies=cookies,
                                          headers=headers, proxies=proxies, timeout=10)
                else:
                    response = session.post(portal, data=params, cookies=cookies,
                                           headers=headers, proxies=proxies, timeout=10)
                
                genre_data = response.json().get("js")
                if isinstance(genre_data, list) and genre_data:
                    mapping = {}
                    for item in genre_data:
                        gid = item.get("id")
                        title = item.get("title") or item.get("name")
                        if gid is not None and title:
                            mapping[str(gid)] = str(title)
                    
                    if mapping:
                        self.genres_by_id = mapping
                        logger.info(f"Loaded {len(mapping)} MAC genres")
                        return self.genres_by_id
            except Exception as e:
                logger.debug(f"Failed to load genres via {method}: {e}")
        
        logger.warning("Could not load MAC genres mapping")
        return {}

    # ------------- Channels -------------

    def get_all_channels_raw(self) -> List[Dict[str, Any]]:
        """Get raw channel list from portal."""
        if not self.token:
            self.handshake()
        
        # Use the SAME session that was used for handshake to maintain cookies/state
        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        
        # Combine basic cookies with any session cookies from handshake
        cookies = self._get_basic_cookies()
        # Add any session cookies to the request cookies
        for cookie_name, cookie_value in session.cookies.items():
            cookies[cookie_name] = cookie_value
            
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()
        
        params = {
            "type": "itv",
            "action": "get_all_channels",
            "force_ch_link_check": "",
            "JsHttpRequest": "1-xml"
        }
        
        # Try GET first
        try:
            logger.info(f"Making channels request with combined cookies: {dict(cookies)}")
            logger.info(f"Session cookies: {dict(session.cookies)}")
            logger.info(f"Channels request URL: {portal}")
            logger.debug(f"Getting all channels for MAC {self.mac} (GET)")
            
            # Try without explicit cookies parameter - let session handle cookies
            response = session.get(portal, params=params, headers=headers,
                                  proxies=proxies, timeout=30)
            
            if response.status_code == 200:
                try:
                    channels = response.json().get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"Got {len(channels)} channels for MAC {self.mac}")
                        return channels
                except requests.exceptions.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response getting channels (GET): {e}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response content (first 1000 chars): {response.text[:1000]}")
                    
                    # Check if this is an HTML response (Cloudflare block, etc.)
                    if response.text.strip().startswith('<'):
                        logger.error("Portal returned HTML instead of JSON - possible Cloudflare block or portal misconfiguration")
                        if 'cloudflare' in response.text.lower():
                            logger.error("Cloudflare protection detected in response")
                        if 'access denied' in response.text.lower():
                            logger.error("Access denied detected in response")
                    
                    # Try alternative endpoints
                    alternatives = [
                        f"{self.base_url}/server/load.php?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
                        f"{self.base_url}/stalker_portal/server/load.php?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
                        f"{self.base_url}/c/portal.php?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml"
                    ]
                    
                    logger.info(f"JSON parsing failed, trying {len(alternatives)} alternative channel endpoints...")
                    for alt_url in alternatives:
                        try:
                            logger.info(f"Trying alternative channels endpoint: {alt_url}")
                            alt_response = session.get(alt_url, headers=headers,
                                                      proxies=proxies, timeout=30)
                            logger.info(f"Alternative endpoint response status: {alt_response.status_code}")
                            if alt_response.status_code == 200:
                                try:
                                    alt_channels = alt_response.json().get("js", {}).get("data", [])
                                    if alt_channels:
                                        logger.info(f"Got {len(alt_channels)} channels via alternative endpoint")
                                        return alt_channels
                                except requests.exceptions.JSONDecodeError as alt_json_e:
                                    logger.info(f"Alternative endpoint {alt_url} also returned invalid JSON: {alt_json_e}")
                                    logger.info(f"Alternative response content: {alt_response.text[:200]}")
                                    continue
                        except Exception as alt_e:
                            logger.info(f"Alternative endpoint {alt_url} failed: {alt_e}")
                            continue
        except Exception as e:
            logger.debug(f"GET channels failed: {e}, trying POST")
        
        # Try POST as fallback
        try:
            logger.debug(f"Getting all channels for MAC {self.mac} (POST)")
            response = session.post(portal, data=params, headers=headers,
                                   proxies=proxies, timeout=30)
            
            if response.status_code == 200:
                try:
                    channels = response.json().get("js", {}).get("data", [])
                    if channels:
                        logger.info(f"Got {len(channels)} channels via POST")
                        return channels
                except requests.exceptions.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response getting channels (POST): {e}")
                    logger.debug(f"Response content: {response.text[:200]}")
                    
                    # Try alternative POST endpoints
                    alternatives = [
                        f"{self.base_url}/server/load.php",
                        f"{self.base_url}/stalker_portal/server/load.php",
                        f"{self.base_url}/c/portal.php"
                    ]
                    
                    for alt_url in alternatives:
                        try:
                            logger.debug(f"Trying alternative POST channels endpoint: {alt_url}")
                            alt_response = session.post(alt_url, data=params, headers=headers,
                                                       proxies=proxies, timeout=30)
                            if alt_response.status_code == 200:
                                try:
                                    alt_channels = alt_response.json().get("js", {}).get("data", [])
                                    if alt_channels:
                                        logger.info(f"Got {len(alt_channels)} channels via alternative POST endpoint")
                                        return alt_channels
                                except requests.exceptions.JSONDecodeError as alt_json_e:
                                    logger.debug(f"Alternative POST endpoint {alt_url} also returned invalid JSON: {alt_json_e}")
                                    logger.debug(f"Alternative response content: {alt_response.text[:200]}")
                                    continue
                        except Exception as alt_e:
                            logger.debug(f"Alternative POST endpoint {alt_url} failed: {alt_e}")
                            continue
        except Exception as e:
            logger.error(f"Error getting channels for MAC {self.mac}: {e}")
        
        return []

    # ------------- Create Link -------------

    def create_link(self, cmd: str) -> str:
        """
        Resolve a portal channel command into a final stream URL.
        Tries GET first, then POST as fallback.
        """
        if not cmd:
            raise MacPortalError("Missing cmd for create_link")

        if not self.token:
            self.handshake()

        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        cookies = self._get_basic_cookies()
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()

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
            response = session.get(portal, params=params, cookies=cookies,
                                  headers=headers, proxies=proxies, timeout=10)
            data = response.json()
            cmd_value = data.get("js", {}).get("cmd", "")
            if cmd_value:
                link = cmd_value.split()[-1]
                if link.startswith("http"):
                    return link
        except Exception as e:
            logger.debug(f"GET create_link failed: {e}, trying POST")

        # Try POST as fallback
        try:
            response = session.post(portal, data=params, cookies=cookies,
                                   headers=headers, proxies=proxies, timeout=10)
            data = response.json()
            cmd_value = data.get("js", {}).get("cmd", "")
            if cmd_value:
                link = cmd_value.split()[-1]
                if link.startswith("http"):
                    return link
        except Exception as e:
            logger.debug(f"POST create_link failed: {e}")

        raise MacPortalError("Could not extract stream URL from create_link response")

    # ------------- EPG -------------

    def get_epg(self, period: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Get EPG data for channels."""
        if not self.token:
            self.handshake()
        
        session = self._get_session(use_cloudscraper=True)  # Enable cloudscraper
        cookies = self._get_basic_cookies()
        headers = self._get_headers(with_auth=True)
        proxies = self._get_request_proxies()
        portal = self.resolve_portal_url()
        
        params = {
            "type": "itv",
            "action": "get_epg_info",
            "period": str(period),
            "JsHttpRequest": "1-xml"
        }
        
        # Try GET first
        try:
            response = session.get(portal, params=params, cookies=cookies,
                                  headers=headers, proxies=proxies, timeout=30)
            data = response.json().get("js", {}).get("data")
            if data:
                logger.debug(f"Got EPG data for {len(data)} channels via GET")
                return data
        except Exception as e:
            logger.debug(f"GET EPG failed: {e}, trying POST")
        
        # Try POST as fallback
        try:
            response = session.post(portal, data=params, cookies=cookies,
                                   headers=headers, proxies=proxies, timeout=30)
            data = response.json().get("js", {}).get("data")
            if data:
                logger.debug(f"Got EPG data for {len(data)} channels via POST")
                return data
        except Exception as e:
            logger.debug(f"POST EPG failed: {e}")
        
        return None

    # ------------- Helper Methods -------------

    def _extract_stream_url(self, cmd: str) -> Optional[str]:
        """Extract HTTP URL from command string."""
        if not cmd:
            return None
        parts = cmd.split()
        for p in parts:
            if p.startswith("http://") or p.startswith("https://"):
                return p
        return None

    def _detect_group_title(self, ch: Dict[str, Any]) -> str:
        """Best-effort detection of group/category name for a channel."""
        # Common keys used by many portals
        candidates = [
            "tv_genre_title", "genre_title", "category_name",
            "cat_name", "group_name", "group_title", "genre_name",
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
        genre_id = ch.get("tv_genre_id") or ch.get("genre_id") or ch.get("cat_id")
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

    def get_channels(self) -> List[Dict[str, Any]]:
        """Return normalized channels list with group detection."""
        raw_list = self.get_all_channels_raw()
        normalized = []
        
        for ch in raw_list:
            ch_id = ch.get("id")
            name = ch.get("name") or f"Channel {ch_id}"
            group_title = self._detect_group_title(ch)
            
            cmd = ch.get("cmd") or ""
            url = self._extract_stream_url(cmd)
            if not url:
                continue

            normalized.append({
                "id": ch_id,
                "name": name,
                "group": group_title,
                "url": url,
                "cmd": cmd,  # Keep original cmd for create_link
                "raw": ch,
            })
        
        logger.info(f"Normalized {len(normalized)} MAC channels into groups")
        return normalized
