"""
MAC Portal Client for Stalker/STB portal communication.

This module provides a client for communicating with MAC-based IPTV portals
(Stalker portals, STB portals). It handles:
- Portal URL resolution
- Handshake authentication and token management
- Channel list retrieval
- Stream URL resolution via create_link API
- Proxy support for network routing
"""

import logging
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


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
      - stream URL resolution (create_link)
    """

    def __init__(
        self,
        base_url: str,
        mac: str,
        proxy: Optional[str] = None,
        timezone: str = "Europe/Berlin",
    ) -> None:
        """
        Initialize the MAC portal client.
        
        Args:
            base_url: Portal base URL (e.g., http://portal.example.com)
            mac: MAC address for authentication (e.g., 00:1A:79:12:34:56)
            proxy: Optional HTTP proxy URL
            timezone: Timezone for portal requests
        """
        if not base_url:
            raise ValueError("base_url is required")
        if not mac:
            raise ValueError("mac is required")
            
        self.original_base_url = base_url.rstrip("/")
        self.mac = mac
        self.timezone = timezone
        self.proxy = proxy

        # Set up session with retry logic
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        self.portal_url: Optional[str] = None
        self.token: Optional[str] = None
        # Cache for genre/category mapping
        self.genres_by_id: Dict[str, str] = {}

    # ------------- helpers -------------

    def _get_proxies(self) -> Optional[dict]:
        """Get proxy configuration for requests."""
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def _default_headers(self, with_auth: bool = False) -> dict:
        """Get default headers for portal requests."""
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
        }
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _cookies(self) -> dict:
        """Get cookies for portal requests."""
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
        
        Returns:
            The resolved portal URL
        """
        if self.portal_url:
            return self.portal_url

        if self.original_base_url.endswith("load.php"):
            self.portal_url = self.original_base_url
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
                r = self.session.get(
                    url,
                    headers=headers,
                    cookies=self._cookies(),
                    proxies=proxies,
                    timeout=5,
                )
                if r.status_code < 400:
                    self.portal_url = url
                    logger.info("MAC portal load.php detected: %s", url)
                    return self.portal_url
            except Exception as e:
                logger.debug("Portal candidate %s failed: %s", url, e)

        self.portal_url = self.original_base_url
        logger.warning(
            "Could not positively identify load.php, using base URL: %s",
            self.portal_url,
        )
        return self.portal_url

    # ------------- step 2: handshake / token -------------

    def handshake(self) -> str:
        """
        Perform handshake with portal to obtain session token.
        
        Returns:
            Session token string
            
        Raises:
            MacPortalError: If handshake fails
        """
        portal = self.resolve_portal_url()
        params = {
            "type": "stb",
            "action": "handshake",
            "JsHttpRequest": "1-xml",
        }
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=False)

        try:
            r = self.session.get(
                portal,
                params=params,
                headers=headers,
                cookies=self._cookies(),
                proxies=proxies,
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise MacPortalError(f"Handshake request failed: {exc}")

        try:
            data = r.json()
            token = data["js"]["token"]
        except (KeyError, ValueError) as exc:
            raise MacPortalError(f"Handshake response invalid - no token: {exc}")
            
        self.token = token
        logger.debug("MAC portal token acquired")
        return token

    # ------------- step 3: expiry / account info -------------

    def get_expires(self) -> Optional[str]:
        """
        Fetch expiry-like info from account_info/get_main_info.
        
        STB-Proxy uses 'phone' field for that.
        
        Returns:
            Expiry information string or None
        """
        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        try:
            r = self.session.get(
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
            return data.get("phone")  # May contain expiry-like info
        except Exception as e:
            logger.warning("Failed to get expiry info: %s", e)
            return None

    # ------------- step 4: genres / categories -------------

    def get_genres_map(self) -> Dict[str, str]:
        """
        Load mapping of genre/category id -> title from portal, if available.
        
        Returns:
            Dictionary mapping genre IDs to titles
        """
        if self.genres_by_id:
            return self.genres_by_id

        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        for action in ("get_genres", "get_genres_short"):
            try:
                r = self.session.get(
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

    def get_all_channels_raw(self) -> List[Dict[str, Any]]:
        """
        Get raw channel list from portal.
        
        Returns:
            List of raw channel dictionaries from portal
        """
        if not self.token:
            self.handshake()
        portal = self.resolve_portal_url()
        proxies = self._get_proxies()
        headers = self._default_headers(with_auth=True)

        try:
            r = self.session.get(
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
        except requests.RequestException as exc:
            raise MacPortalError(f"Failed to get channels: {exc}")

        try:
            js = r.json().get("js") or {}
            data = js.get("data") or []
        except (ValueError, KeyError) as exc:
            raise MacPortalError(f"Invalid channel response: {exc}")

        # Log a few sample entries to inspect keys
        for idx, ch in enumerate(data[:5]):
            try:
                keys = list(ch.keys())
            except Exception:
                keys = []
            logger.debug("MAC raw channel %s keys: %s", idx, keys)

        return data

    def create_link(self, cmd: str) -> str:
        """
        Resolve a portal channel command into a final stream URL using itv/create_link.
        
        Args:
            cmd: Channel command string from portal
            
        Returns:
            Resolved stream URL
            
        Raises:
            MacPortalError: If link creation fails
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
            r = self.session.get(
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

        url = self._extract_stream_url(cmd_value)
        if not url:
            raise MacPortalError("Could not extract stream URL from create_link response")

        return url

    def _extract_stream_url(self, cmd: str) -> Optional[str]:
        """Extract HTTP/HTTPS URL from command string."""
        if not cmd:
            return None
        parts = cmd.split()
        for p in reversed(parts):
            if p.startswith("http://") or p.startswith("https://"):
                return p
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

    def get_channels(self) -> List[Dict[str, Any]]:
        """
        Return normalized channels list.

        We try to map provider categories/groups onto our 'group' field.
        Different portals use different keys for the group/category, so we
        check several common ones in order.
        
        Returns:
            List of normalized channel dictionaries with keys:
            - id: Channel ID
            - name: Channel name
            - group: Group/category title
            - url: Stream URL (extracted from cmd)
            - raw: Original channel data
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
                # Skip channels without extractable URL
                continue

            normalized.append({
                "id": ch_id,
                "name": name,
                "group": group_title,
                "url": url,
                "cmd": cmd,  # Keep original cmd for create_link
                "raw": ch,
            })
            
        logger.info("Normalized %s MAC channels into groups", len(normalized))
        return normalized
