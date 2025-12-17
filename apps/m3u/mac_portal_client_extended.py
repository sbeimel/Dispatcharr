"""
Extended MAC Portal Client with Phase 5 improvements.

This module extends MacPortalClient with:
- Multi-Endpoint Support (5.1)
- User-Agent Presets (5.2)
- Improved Cloudscraper Integration (5.3)
- Retry Logic with Exponential Backoff (5.4)
- FFmpeg Stream URL Extraction (5.5)
- Stream Link Validation (5.6)

Requirements: 1.1, 2.1-2.4, 3.1-3.4, 7.1-7.5, 11.1-11.4, 26.1-26.4, 27.1-27.4
"""

import logging
import time
import re
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import requests

from .mac_portal_client import (
    MacPortalClient, 
    MacPortalError, 
    _get_session, 
    clear_session,
    CLOUDSCRAPER_AVAILABLE
)
from .token_manager import TokenManager, KeepAliveManager, TokenManagerRegistry

logger = logging.getLogger(__name__)


# User-Agent Presets (Requirement 2.1, 2.2, 2.3, 2.4)
USER_AGENT_PRESETS = {
    "MAG200": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
    "MAG250": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3",
    "MAG254": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 254 Safari/533.3",
    "MAG322": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 322 Safari/533.3",
    "MAG424": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 5 rev: 424 Safari/533.3",
}

# Default endpoint priority (Requirement 11.1, 11.2, 11.3, 11.4)
DEFAULT_ENDPOINTS = [
    "/server/load.php",
    "/stalker_portal/server/load.php",
    "/portal.php",
    "/c/portal.php",
    "/c/load.php",
    "/stalker_portal/load.php",
]


class ExtendedMacPortalClient(MacPortalClient):
    """
    Extended MAC Portal Client with improved features.
    
    Requirements: 1.1, 2.1-2.4, 3.1-3.4, 7.1-7.5, 11.1-11.4, 26.1-26.4, 27.1-27.4
    """
    
    def __init__(
        self,
        base_url: str,
        mac: str,
        proxy: Optional[str] = None,
        timezone: str = "Europe/London",
        user_agent_preset: str = "MAG250",
        use_cloudscraper: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        exponential_backoff: bool = True,
        connection_timeout: int = 30,
        read_timeout: int = 60,
    ) -> None:
        """
        Initialize ExtendedMacPortalClient.
        
        Args:
            base_url: Portal base URL
            mac: MAC address
            proxy: Optional proxy URL
            timezone: Timezone string
            user_agent_preset: User-Agent preset name (MAG200, MAG250, MAG254, MAG322, MAG424)
            use_cloudscraper: Whether to use cloudscraper for Cloudflare bypass
            max_retries: Maximum retry attempts
            retry_delay: Base retry delay in seconds
            exponential_backoff: Use exponential backoff for retries
            connection_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
        """
        super().__init__(base_url, mac, proxy, timezone)
        
        # User-Agent configuration (Requirement 2.1)
        self.user_agent_preset = user_agent_preset
        self.user_agent = USER_AGENT_PRESETS.get(user_agent_preset, USER_AGENT_PRESETS["MAG250"])
        
        # Cloudscraper configuration (Requirement 3.1)
        self.use_cloudscraper = use_cloudscraper and CLOUDSCRAPER_AVAILABLE
        self._cloudscraper_detected = False
        
        # Retry configuration (Requirement 7.1, 45.1)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        
        # Timeout configuration (Requirement 45.1)
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        
        # Endpoint tracking (Requirement 11.1)
        self.endpoints = DEFAULT_ENDPOINTS.copy()
        self.successful_endpoint: Optional[str] = None
        
        # Token and Keep-Alive management (Requirements 41.x, 43.x)
        self._token_manager: Optional[TokenManager] = None
        self._keep_alive_manager: Optional[KeepAliveManager] = None
        self._keep_alive_interval: int = 300  # 5 minutes default
        self._account_id: Optional[int] = None
        
        # Load settings from database if available
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from database."""
        try:
            from .mac_portal_models import MACPortalGlobalSettings, FailoverSettings
            
            global_settings = MACPortalGlobalSettings.get_settings()
            failover_settings = FailoverSettings.get_settings()
            
            self.max_retries = global_settings.max_retries
            self.retry_delay = global_settings.retry_delay
            self.exponential_backoff = global_settings.exponential_backoff
            self.connection_timeout = global_settings.connection_timeout
            self.read_timeout = global_settings.read_timeout
            self.use_cloudscraper = global_settings.cloudscraper_enabled and CLOUDSCRAPER_AVAILABLE
            
            if failover_settings.endpoint_priority:
                self.endpoints = failover_settings.endpoint_priority
                
        except Exception as e:
            logger.debug(f"Could not load settings from database: {e}")
    
    def _default_headers(self, with_auth: bool = False, enhanced: bool = False) -> dict:
        """Get default headers with configurable User-Agent."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        if enhanced:
            # Extract model from user agent for X-User-Agent header
            model = self.user_agent_preset
            headers.update({
                "X-User-Agent": f"Model: {model}; Link: WiFi",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            })
            
            if self.portal_url:
                parsed = urlparse(self.portal_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                headers["Referer"] = base_url + "/"
        
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        return headers


    def _get_timeout(self) -> Tuple[int, int]:
        """Get timeout tuple (connection, read)."""
        return (self.connection_timeout, self.read_timeout)
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with optional exponential backoff.
        
        Requirements: 7.2, 7.3
        """
        if self.exponential_backoff:
            # Exponential backoff: delay * 2^attempt
            return self.retry_delay * (2 ** attempt)
        return self.retry_delay
    
    def _should_use_cloudscraper(self, response: Optional[requests.Response] = None) -> bool:
        """
        Detect if cloudscraper should be used based on response.
        
        Requirements: 3.2, 3.3
        """
        if not CLOUDSCRAPER_AVAILABLE:
            return False
        
        if self._cloudscraper_detected:
            return True
        
        if response is not None:
            # Check for Cloudflare indicators
            if response.status_code == 403:
                content = response.text.lower()
                if 'cloudflare' in content or 'cf-ray' in response.headers.get('cf-ray', ''):
                    self._cloudscraper_detected = True
                    logger.info("Cloudflare protection detected, switching to cloudscraper")
                    return True
            
            # Check for Cloudflare headers
            if 'cf-ray' in response.headers:
                self._cloudscraper_detected = True
                return True
        
        return self.use_cloudscraper
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cookies: Optional[Dict] = None,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and exponential backoff.
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        last_error = None
        use_cloudscraper = self._should_use_cloudscraper()
        
        for attempt in range(self.max_retries):
            try:
                session = _get_session(use_cloudscraper=use_cloudscraper)
                proxies = self._get_proxies()
                timeout = self._get_timeout()
                
                if method.upper() == "GET":
                    response = session.get(
                        url,
                        params=params,
                        headers=headers,
                        cookies=cookies,
                        proxies=proxies,
                        timeout=timeout,
                    )
                else:
                    response = session.post(
                        url,
                        data=data or params,
                        headers=headers,
                        cookies=cookies,
                        proxies=proxies,
                        timeout=timeout,
                    )
                
                # Check if we need to switch to cloudscraper
                if not use_cloudscraper and self._should_use_cloudscraper(response):
                    use_cloudscraper = True
                    clear_session()
                    continue
                
                # Check for retryable status codes
                if response.status_code in [500, 502, 503, 504]:
                    raise requests.RequestException(f"Server error: {response.status_code}")
                
                return response
                
            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                delay = self._calculate_retry_delay(attempt)
                logger.debug(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}, retrying in {delay}s")
                time.sleep(delay)
                
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.debug(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}, retrying in {delay}s")
                    time.sleep(delay)
        
        raise MacPortalError(f"Request failed after {self.max_retries} attempts: {last_error}")
    
    def resolve_portal_url_multi_endpoint(self) -> str:
        """
        Resolve portal URL trying multiple endpoints.
        
        Requirements: 11.1, 11.2, 11.3, 11.4
        """
        # Check cache first
        from django.core.cache import cache
        cache_key = f"portal_url:{self.original_base_url}"
        cached_url = cache.get(cache_key)
        if cached_url:
            self.portal_url = cached_url
            return self.portal_url
        
        # If we have a successful endpoint cached, try it first
        if self.successful_endpoint:
            parsed = urlparse(self.original_base_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            url = base + self.successful_endpoint
            
            try:
                response = self._request_with_retry(
                    "GET",
                    url,
                    headers=self._default_headers(),
                    cookies=self._cookies(),
                )
                if response.status_code < 400:
                    self.portal_url = url
                    cache.set(cache_key, self.portal_url, 3600)
                    return self.portal_url
            except Exception:
                pass
        
        # Try xpcom discovery first
        discovered_url = self._discover_portal_via_xpcom()
        if discovered_url:
            self.portal_url = discovered_url
            cache.set(cache_key, self.portal_url, 3600)
            return self.portal_url
        
        # Try all endpoints
        parsed = urlparse(self.original_base_url)
        if not parsed.scheme:
            self.original_base_url = "http://" + self.original_base_url
            parsed = urlparse(self.original_base_url)
        
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        for endpoint in self.endpoints:
            url = base + endpoint
            try:
                response = self._request_with_retry(
                    "GET",
                    url,
                    headers=self._default_headers(),
                    cookies=self._cookies(),
                )
                if response.status_code < 400:
                    self.portal_url = url
                    self.successful_endpoint = endpoint
                    cache.set(cache_key, self.portal_url, 3600)
                    logger.info(f"Portal URL resolved via endpoint {endpoint}: {url}")
                    return self.portal_url
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
        
        # Fallback to base URL
        self.portal_url = self.original_base_url
        cache.set(cache_key, self.portal_url, 3600)
        return self.portal_url
    
    def resolve_portal_url(self) -> str:
        """Override to use multi-endpoint support."""
        return self.resolve_portal_url_multi_endpoint()


    def handshake_with_retry(self) -> str:
        """
        Get authentication token with retry logic.
        
        Requirements: 7.1, 41.1
        """
        from django.core.cache import cache
        cache_key = f"mac_token:{self.mac}:{self.original_base_url}"
        cached_token = cache.get(cache_key)
        if cached_token:
            self.token = cached_token
            return self.token
        
        portal = self.resolve_portal_url()
        parsed = urlparse(portal)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = self._default_headers(enhanced=True)
        
        # Try different endpoint variations
        endpoints = [
            "?type=stb&action=handshake&JsHttpRequest=1-xml",
            "/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml",
            "/server/load.php?type=stb&action=handshake&JsHttpRequest=1-xml",
        ]
        
        for endpoint in endpoints:
            full_url = base_url + endpoint
            
            try:
                response = self._request_with_retry(
                    "GET",
                    full_url,
                    headers=headers,
                    cookies=self._cookies(),
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "js" in data and "token" in data["js"]:
                            token = data["js"]["token"]
                            if token:
                                self.token = token
                                cache.set(cache_key, token, 1800)
                                logger.info(f"Token obtained for MAC {self.mac[:8]}...")
                                return token
                    except Exception as e:
                        logger.debug(f"Failed to parse token response: {e}")
            except Exception as e:
                logger.debug(f"Handshake endpoint {endpoint} failed: {e}")
        
        raise MacPortalError(f"Failed to get token for MAC {self.mac}")
    
    def handshake(self) -> str:
        """Override to use retry logic."""
        return self.handshake_with_retry()
    
    # ============== FFmpeg Stream URL Extraction (5.5) ==============
    
    @staticmethod
    def extract_stream_url_ffmpeg(cmd: str) -> Optional[str]:
        """
        Extract actual stream URL from ffmpeg command.
        
        Requirements: 27.1, 27.2, 27.3, 27.4
        """
        if not cmd:
            return None
        
        # Pattern 1: Direct URL in command
        url_pattern = r'(https?://[^\s"\']+)'
        matches = re.findall(url_pattern, cmd)
        if matches:
            # Return the last URL (usually the actual stream)
            return matches[-1]
        
        # Pattern 2: ffmpeg -i "URL" format
        ffmpeg_pattern = r'ffmpeg.*?-i\s+["\']?([^\s"\']+)["\']?'
        match = re.search(ffmpeg_pattern, cmd, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 3: ffrt URL format
        ffrt_pattern = r'ffrt\s+([^\s]+)'
        match = re.search(ffrt_pattern, cmd)
        if match:
            return match.group(1)
        
        # Pattern 4: Just the URL part after any command prefix
        parts = cmd.split()
        for part in reversed(parts):
            if part.startswith("http://") or part.startswith("https://"):
                return part
        
        return None
    
    @staticmethod
    def extract_stream_url_from_cmd(cmd: str, base_url: str = "") -> Optional[str]:
        """
        Extract stream URL from various cmd formats.
        
        Requirements: 27.1, 27.2
        """
        if not cmd:
            return None
        
        # Try ffmpeg extraction first
        url = ExtendedMacPortalClient.extract_stream_url_ffmpeg(cmd)
        if url:
            return url
        
        # Handle relative URLs
        parts = cmd.split()
        for part in parts:
            if part.startswith("/ch/") or part.startswith("ch/"):
                if base_url:
                    parsed = urlparse(base_url)
                    base = f"{parsed.scheme}://{parsed.netloc}"
                    return f"{base}/{part.lstrip('/')}"
        
        return None
    
    # ============== Stream Link Validation (5.6) ==============
    
    def validate_stream_url(
        self, 
        url: str, 
        timeout: int = 5,
        check_content_type: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate stream URL with HEAD request before playback.
        
        Requirements: 26.1, 26.2, 26.3, 26.4
        
        Returns:
            Tuple of (is_valid, status_message, details)
        """
        details = {
            "url": url,
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "response_time_ms": None,
            "error": None,
        }
        
        if not url:
            return False, "Empty URL", details
        
        if not url.startswith(("http://", "https://")):
            return False, "Invalid URL scheme", details
        
        start_time = time.time()
        
        try:
            session = _get_session(use_cloudscraper=self.use_cloudscraper)
            
            # Try HEAD request first
            response = session.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": self.user_agent},
            )
            
            details["status_code"] = response.status_code
            details["content_type"] = response.headers.get("Content-Type", "")
            details["content_length"] = response.headers.get("Content-Length")
            details["response_time_ms"] = int((time.time() - start_time) * 1000)
            
            # Check status code
            if response.status_code == 200:
                # Validate content type if requested
                if check_content_type:
                    content_type = details["content_type"].lower()
                    valid_types = [
                        "video/", "audio/", "application/octet-stream",
                        "application/x-mpegurl", "application/vnd.apple.mpegurl",
                        "application/dash+xml", "text/plain"
                    ]
                    if not any(vt in content_type for vt in valid_types):
                        return False, f"Invalid content type: {content_type}", details
                
                return True, "Stream is valid", details
            
            elif response.status_code in [301, 302, 303, 307, 308]:
                return True, "Stream redirects (valid)", details
            
            elif response.status_code == 403:
                return False, "Access forbidden (403)", details
            
            elif response.status_code == 404:
                return False, "Stream not found (404)", details
            
            elif response.status_code == 451:
                return False, "GEO-blocked (451)", details
            
            elif response.status_code >= 500:
                return False, f"Server error ({response.status_code})", details
            
            else:
                return False, f"Unexpected status: {response.status_code}", details
                
        except requests.Timeout:
            details["error"] = "Timeout"
            details["response_time_ms"] = int((time.time() - start_time) * 1000)
            return False, "Connection timeout", details
            
        except requests.ConnectionError as e:
            details["error"] = str(e)
            return False, "Connection error", details
            
        except Exception as e:
            details["error"] = str(e)
            return False, f"Validation error: {e}", details
    
    def validate_stream_url_with_get(
        self,
        url: str,
        timeout: int = 5,
        read_bytes: int = 1024
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate stream URL with GET request (reads first bytes).
        
        Requirements: 26.2
        """
        details = {
            "url": url,
            "status_code": None,
            "content_type": None,
            "bytes_read": 0,
            "response_time_ms": None,
            "error": None,
        }
        
        if not url or not url.startswith(("http://", "https://")):
            return False, "Invalid URL", details
        
        start_time = time.time()
        
        try:
            session = _get_session(use_cloudscraper=self.use_cloudscraper)
            
            response = session.get(
                url,
                timeout=timeout,
                stream=True,
                headers={"User-Agent": self.user_agent},
            )
            
            details["status_code"] = response.status_code
            details["content_type"] = response.headers.get("Content-Type", "")
            
            if response.status_code == 200:
                # Read first bytes to verify stream
                chunk = response.raw.read(read_bytes)
                details["bytes_read"] = len(chunk)
                details["response_time_ms"] = int((time.time() - start_time) * 1000)
                
                if len(chunk) > 0:
                    return True, "Stream is broadcasting", details
                else:
                    return False, "Empty stream", details
            
            details["response_time_ms"] = int((time.time() - start_time) * 1000)
            return False, f"Status: {response.status_code}", details
            
        except Exception as e:
            details["error"] = str(e)
            details["response_time_ms"] = int((time.time() - start_time) * 1000)
            return False, f"Error: {e}", details
        finally:
            try:
                response.close()
            except Exception:
                pass


    # ============== Enhanced create_link with validation ==============
    
    def create_link_validated(
        self, 
        cmd: str, 
        validate: bool = True,
        validation_timeout: int = 5
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Create stream link with optional validation.
        
        Requirements: 26.1, 26.3
        
        Returns:
            Tuple of (stream_url, is_valid, validation_details)
        """
        # Get the stream URL
        stream_url = self.create_link(cmd)
        
        if not validate:
            return stream_url, True, {}
        
        # Validate the stream
        is_valid, message, details = self.validate_stream_url(
            stream_url, 
            timeout=validation_timeout
        )
        
        if not is_valid:
            logger.warning(f"Stream validation failed for {stream_url[:50]}...: {message}")
        
        return stream_url, is_valid, details
    
    def create_link(self, cmd: str) -> str:
        """
        Override create_link with retry logic.
        
        Requirements: 7.1
        """
        if not cmd:
            raise MacPortalError("Missing cmd for create_link")
        
        if not self.token:
            self.handshake()
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
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
            response = self._request_with_retry(
                "GET",
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                data = response.json()
                link = data["js"]["cmd"].split()[-1]
                if link and link.startswith(("http://", "https://")):
                    return link
        except Exception as e:
            logger.debug(f"GET create_link failed: {e}")
        
        # Try POST as fallback
        try:
            response = self._request_with_retry(
                "POST",
                portal,
                data=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                data = response.json()
                link = data["js"]["cmd"].split()[-1]
                if link and link.startswith(("http://", "https://")):
                    return link
        except Exception as e:
            logger.debug(f"POST create_link failed: {e}")
        
        # Try FFmpeg extraction as last resort
        extracted = self.extract_stream_url_ffmpeg(cmd)
        if extracted:
            return extracted
        
        raise MacPortalError(f"Could not create link for cmd: {cmd}")
    
    # ============== User-Agent Management ==============
    
    def set_user_agent(self, preset: str) -> None:
        """
        Set User-Agent from preset.
        
        Requirements: 2.1, 2.2
        """
        if preset in USER_AGENT_PRESETS:
            self.user_agent_preset = preset
            self.user_agent = USER_AGENT_PRESETS[preset]
            logger.debug(f"User-Agent set to {preset}")
        else:
            logger.warning(f"Unknown User-Agent preset: {preset}")
    
    def set_custom_user_agent(self, user_agent: str) -> None:
        """
        Set custom User-Agent string.
        
        Requirements: 2.3
        """
        self.user_agent_preset = "custom"
        self.user_agent = user_agent
        logger.debug("Custom User-Agent set")
    
    @staticmethod
    def get_available_user_agents() -> Dict[str, str]:
        """Get all available User-Agent presets."""
        return USER_AGENT_PRESETS.copy()
    
    # ============== Keep-Alive Management (Requirements 43.1-43.4) ==============
    
    def set_account_id(self, account_id: int) -> None:
        """Set the account ID for token management."""
        self._account_id = account_id
    
    def _get_token_manager(self) -> TokenManager:
        """
        Get or create TokenManager for this client.
        
        Requirements: 41.1, 43.1
        """
        if self._token_manager is None:
            account_id = self._account_id or 0
            self._token_manager = TokenManagerRegistry.get_or_create(account_id, self.mac)
            self._token_manager.set_handshake_function(self._do_handshake)
        return self._token_manager
    
    def _do_handshake(self) -> bool:
        """Internal handshake function for token refresh."""
        try:
            token = self.handshake_with_retry()
            if token:
                self._get_token_manager().set_token(token)
                return True
        except Exception as e:
            logger.error(f"Handshake failed: {e}")
        return False
    
    def _send_keep_alive_request(self) -> None:
        """
        Send keep-alive request to portal.
        
        Requirements: 43.2, 43.3
        """
        if not self.token:
            return
        
        portal = self.resolve_portal_url()
        headers = self._default_headers(with_auth=True)
        
        # Use watchdog action for keep-alive
        params = {
            "type": "stb",
            "action": "watchdog",
            "JsHttpRequest": "1-xml",
        }
        
        try:
            response = self._request_with_retry(
                "GET",
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
            )
            
            if response.status_code == 200:
                logger.debug(f"Keep-alive sent for MAC {self.mac[:8]}...")
            elif response.status_code == 401:
                # Token expired, refresh it
                logger.info(f"Keep-alive got 401, refreshing token for MAC {self.mac[:8]}...")
                self._get_token_manager()._refresh_token()
        except Exception as e:
            logger.warning(f"Keep-alive failed for MAC {self.mac[:8]}...: {e}")
    
    def start_keep_alive(self, interval: int = None) -> None:
        """
        Start sending periodic keep-alive requests.
        
        Requirements: 43.1
        
        Args:
            interval: Keep-alive interval in seconds (default: 300 = 5 minutes)
        """
        if interval:
            self._keep_alive_interval = interval
        
        if self._keep_alive_manager is None:
            self._keep_alive_manager = KeepAliveManager(
                self._get_token_manager(),
                interval=self._keep_alive_interval
            )
            self._keep_alive_manager.set_keep_alive_function(self._send_keep_alive_request)
        
        self._keep_alive_manager.start()
        logger.info(f"Keep-alive started for MAC {self.mac[:8]}... (interval: {self._keep_alive_interval}s)")
    
    def stop_keep_alive(self) -> None:
        """
        Stop sending keep-alive requests.
        
        Requirements: 43.4
        """
        if self._keep_alive_manager:
            self._keep_alive_manager.stop()
            logger.info(f"Keep-alive stopped for MAC {self.mac[:8]}...")
    
    def is_keep_alive_active(self) -> bool:
        """Check if keep-alive is currently active."""
        return self._keep_alive_manager is not None and self._keep_alive_manager._active
    
    def get_keep_alive_interval(self) -> int:
        """Get current keep-alive interval in seconds."""
        return self._keep_alive_interval
    
    def set_keep_alive_interval(self, interval: int) -> None:
        """
        Set keep-alive interval.
        
        Args:
            interval: Interval in seconds (minimum 60)
        """
        self._keep_alive_interval = max(60, interval)
        if self._keep_alive_manager:
            self._keep_alive_manager.interval = self._keep_alive_interval


# ============== Utility Functions ==============

def calculate_exponential_backoff(
    attempt: int,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay.
    
    Requirements: 7.2, 7.3
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter to prevent thundering herd
    
    Returns:
        Delay in seconds
    """
    import random
    
    delay = base_delay * (2 ** attempt)
    delay = min(delay, max_delay)
    
    if jitter:
        # Add up to 25% jitter
        jitter_amount = delay * 0.25 * random.random()
        delay += jitter_amount
    
    return delay


def extract_ffmpeg_url(cmd: str) -> Optional[str]:
    """
    Extract URL from ffmpeg command string.
    
    Requirements: 27.1, 27.2, 27.3, 27.4
    """
    return ExtendedMacPortalClient.extract_stream_url_ffmpeg(cmd)


def validate_stream(
    url: str,
    timeout: int = 5,
    user_agent: str = None
) -> Tuple[bool, str]:
    """
    Quick stream validation utility.
    
    Requirements: 26.1
    """
    if not url:
        return False, "Empty URL"
    
    try:
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=headers,
        )
        
        if response.status_code in [200, 301, 302]:
            return True, "Valid"
        else:
            return False, f"Status: {response.status_code}"
            
    except Exception as e:
        return False, str(e)
