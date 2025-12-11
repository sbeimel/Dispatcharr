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
from typing import Optional, Dict, Any, List
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
        timezone: str = "Europe/Berlin",
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

    # ------------- helpers -------------

    def _get_proxies(self) -> Optional[dict]:
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def _default_headers(self, with_auth: bool = False) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
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
        Try to detect the portal load.php URL.
        If original_base_url already ends with load.php, use it as-is.
        Otherwise probe common paths.
        """
        cache_key = f"portal_url:{self.original_base_url}"
        cached_url = cache.get(cache_key)
        if cached_url:
            self.portal_url = cached_url
            return self.portal_url

        if self.portal_url:
            return self.portal_url

        if self.original_base_url.endswith("load.php"):
            self.portal_url = self.original_base_url
            cache.set(cache_key, self.portal_url, 3600)  # Cache for 1 hour
            return self.portal_url

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

    # ------------- step 2: handshake / token -------------

    def handshake(self) -> str:
        """Get authentication token from portal."""
        cache_key = f"mac_token:{self.mac}:{self.original_base_url}"
        cached_token = cache.get(cache_key)
        if cached_token:
            self.token = cached_token
            return self.token

        portal = self.resolve_portal_url()
        params = {
            "type": "stb",
            "action": "handshake",
            "JsHttpRequest": "1-xml",
        }
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=False)

        r = _get_session().get(
            portal,
            params=params,
            headers=headers,
            cookies=self._cookies(),
            proxies=proxies,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        try:
            token = data["js"]["token"]
        except Exception as exc:
            raise MacPortalError(f"Handshake without token: {exc}")
        
        self.token = token
        cache.set(cache_key, token, 1800)  # Cache for 30 minutes
        logger.debug("MAC portal token acquired for MAC %s", self.mac)
        return token

    # ------------- step 3: expiry / account info -------------

    def get_expires(self) -> Optional[str]:
        """
        Fetch expiry-like info from account_info/get_main_info.
        STB-Proxy uses 'phone' field for that.
        """
        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        r = _get_session().get(
            portal,
            params={
                "type": "account_info",
                "action": "get_main_info",
                "JsHttpRequest": "1-xml",
            },
            headers=headers,
            cookies=self._cookies(),
            proxies=proxies,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("js") or {}
        return data.get("phone")  # may contain expiry-like info

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
        """Get raw channel data from portal."""
        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        r = _get_session().get(
            portal,
            params={
                "type": "itv",
                "action": "get_all_channels",
                "JsHttpRequest": "1-xml",
            },
            headers=headers,
            cookies=self._cookies(),
            proxies=proxies,
            timeout=20,
        )
        r.raise_for_status()
        js = r.json().get("js") or {}
        data = js.get("data") or []

        # Log a few sample entries to inspect keys
        for idx, ch in enumerate(data[:10]):
            try:
                keys = list(ch.keys())
            except Exception:
                keys = []
            logger.debug("MAC raw channel %s keys: %s", idx, keys)

        return data

    def create_link(self, cmd: str) -> str:
        """
        Resolve a portal channel command into a final stream URL using itv/create_link.
        """
        if not cmd:
            raise MacPortalError("Missing cmd for create_link")

        if not self.token:
            self.handshake()

        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
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

        try:
            r = _get_session().get(
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
                proxies=proxies,
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise MacPortalError(f"create_link request failed: {exc}")

        try:
            js = r.json().get("js") or {}
        except Exception as exc:
            raise MacPortalError(f"create_link invalid JSON: {exc}")

        cmd_value = js.get("cmd")
        if not cmd_value or not isinstance(cmd_value, str):
            raise MacPortalError("create_link response without cmd field")

        url = None
        parts = cmd_value.split()
        for part in reversed(parts):
            if part.startswith("http://") or part.startswith("https://"):
                url = part
                break

        if not url:
            raise MacPortalError("Could not extract stream URL from create_link response")

        return url

    def _extract_stream_url(self, cmd: str) -> Optional[str]:
        """Extract stream URL from command string."""
        if not cmd:
            return None
        
        parts = cmd.split()
        
        # First, look for absolute URLs
        for p in parts:
            if p.startswith("http://") or p.startswith("https://"):
                return p
        
        # If no absolute URL found, look for relative paths and convert them
        for p in parts:
            if p.startswith("/ch/") or p.startswith("ch/"):
                # Convert relative path to absolute URL using portal base URL
                base_url = self.base_url.rstrip('/')
                if p.startswith("/"):
                    return f"{base_url}{p}"
                else:
                    return f"{base_url}/{p}"
        
        # Look for other common relative patterns
        for p in parts:
            if "/" in p and not p.startswith("ffmpeg"):
                # Likely a relative URL path
                base_url = self.base_url.rstrip('/')
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
        """
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

            normalized.append(
                {
                    "id": ch_id,
                    "name": name,
                    "group": group_title,
                    "url": url,
                    "cmd": cmd,
                    "raw": ch,
                }
            )
        logger.info("Normalized %s MAC channels into groups", len(normalized))
        return normalized

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