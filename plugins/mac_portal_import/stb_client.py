"""
STB/Stalker Portal Client für MAC Portal Import.

Basiert auf der MacReplay-Logik für Portal-Kommunikation.
"""

import logging
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


class STBClient:
    """
    Client für STB/Stalker Portal API-Kommunikation.
    
    Unterstützt:
    - Automatische Portal-URL-Erkennung
    - Token-Abruf und -Verwaltung
    - Kanal- und Genre-Abruf
    - Stream-Link-Generierung
    """
    
    # Standard User-Agent für MAG250
    DEFAULT_USER_AGENT = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
    
    # Session-Konfiguration
    SESSION_MAX_AGE = 300  # 5 Minuten
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Args:
            user_agent: Optional custom User-Agent
        """
        self._session: Optional[requests.Session] = None
        self._session_created: float = 0
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
    
    def _get_session(self) -> requests.Session:
        """
        Holt oder erstellt eine Requests-Session mit automatischer Erneuerung.
        
        Returns:
            Requests-Session
        """
        current_time = time.time()
        
        if self._session is None or (current_time - self._session_created) > self.SESSION_MAX_AGE:
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass
            
            self._session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504]
            )
            self._session.mount("http://", HTTPAdapter(max_retries=retries))
            self._session.mount("https://", HTTPAdapter(max_retries=retries))
            self._session_created = current_time
            logger.debug("Neue Requests-Session erstellt")
        
        return self._session
    
    def get_portal_url(self, url: str, proxy: Optional[str] = None) -> Optional[str]:
        """
        Ermittelt die Portal-URL aus der Basis-URL.
        
        Versucht xpcom.common.js zu parsen um den korrekten API-Endpoint zu finden.
        
        Args:
            url: Basis-URL des Portals
            proxy: Optional HTTP-Proxy
            
        Returns:
            Portal-URL oder None
        """
        def parse_response(url: str, data: requests.Response) -> str:
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

        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Mögliche Pfade für xpcom.common.js
        paths = [
            "/c/xpcom.common.js",
            "/client/xpcom.common.js",
            "/c_/xpcom.common.js",
            "/stalker_portal/c/xpcom.common.js",
            "/stalker_portal/c_/xpcom.common.js",
        ]

        proxies = {"http": proxy, "https": proxy} if proxy else None
        headers = {"User-Agent": self.user_agent}

        try:
            session = self._get_session()
            for path in paths:
                try:
                    response = session.get(
                        base_url + path,
                        headers=headers,
                        proxies=proxies,
                        timeout=10
                    )
                    if response.ok:
                        return parse_response(base_url + path, response)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Fehler bei Portal-URL-Erkennung: {e}")
        
        # Fallback: Standard-Endpoints probieren
        fallback_endpoints = [
            "/server/load.php",
            "/portal.php",
            "/stalker_portal/server/load.php",
            "/c/server/load.php",
        ]
        
        for endpoint in fallback_endpoints:
            test_url = base_url + endpoint
            try:
                response = self._get_session().get(
                    test_url + "?type=stb&action=handshake&JsHttpRequest=1-xml",
                    headers=headers,
                    proxies=proxies,
                    timeout=10
                )
                if response.ok and 'token' in response.text:
                    return test_url
            except Exception:
                continue
        
        return None
    
    def get_token(
        self, 
        url: str, 
        mac: str, 
        proxy: Optional[str] = None
    ) -> Optional[str]:
        """
        Holt ein Authentifizierungs-Token für eine MAC-Adresse.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            proxy: Optional HTTP-Proxy
            
        Returns:
            Token oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": self.user_agent}
        
        try:
            logger.debug(f"Token für MAC {mac} wird abgerufen von {url}")
            response = self._get_session().get(
                url + "?type=stb&action=handshake&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=20,
            )
            logger.debug(f"Token-Request Status: {response.status_code}")
            
            data = response.json()
            token = data.get("js", {}).get("token")
            
            if token:
                logger.info(f"Token erfolgreich für MAC {mac} erhalten")
                return token
                
        except Exception as e:
            logger.error(f"Fehler beim Token-Abruf für MAC {mac}: {e}")
        
        return None
    
    def get_profile(
        self, 
        url: str, 
        mac: str, 
        token: str, 
        proxy: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Holt das Profil für eine MAC-Adresse.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            proxy: Optional HTTP-Proxy
            
        Returns:
            Profil-Daten oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}",
        }
        
        try:
            response = self._get_session().get(
                url + "?type=stb&action=get_profile&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            return response.json().get("js")
        except Exception as e:
            logger.error(f"Fehler beim Profil-Abruf für MAC {mac}: {e}")
            return None
    
    def get_expires(
        self, 
        url: str, 
        mac: str, 
        token: str, 
        proxy: Optional[str] = None
    ) -> Optional[str]:
        """
        Holt das Ablaufdatum für eine MAC-Adresse.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            proxy: Optional HTTP-Proxy
            
        Returns:
            Ablaufdatum als String oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}",
        }
        
        try:
            logger.debug(f"Ablaufdatum für MAC {mac} wird abgerufen")
            response = self._get_session().get(
                url + "?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=15,
            )
            logger.debug(f"Ablaufdatum-Request Status: {response.status_code}")
            
            data = response.json()
            # Verschiedene Felder für Ablaufdatum probieren
            js = data.get("js", {})
            expires = (
                js.get("phone") or 
                js.get("expire_billing_date") or 
                js.get("exp_date") or
                js.get("date")
            )
            
            if expires:
                logger.info(f"Ablaufdatum für MAC {mac}: {expires}")
                return str(expires)
                
        except Exception as e:
            logger.error(f"Fehler beim Ablaufdatum-Abruf für MAC {mac}: {e}")
        
        return None
    
    def get_all_channels(
        self, 
        url: str, 
        mac: str, 
        token: str, 
        proxy: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Holt alle Kanäle für eine MAC-Adresse.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            proxy: Optional HTTP-Proxy
            
        Returns:
            Liste von Kanal-Daten oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}",
        }
        
        try:
            logger.debug(f"Alle Kanäle für MAC {mac} werden abgerufen")
            response = self._get_session().get(
                url + "?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=30,
            )
            logger.debug(f"Kanäle-Request Status: {response.status_code}")
            
            data = response.json()
            channels = data.get("js", {}).get("data", [])
            
            if channels:
                logger.info(f"{len(channels)} Kanäle für MAC {mac} erhalten")
                return channels
                
        except Exception as e:
            logger.error(f"Fehler beim Kanal-Abruf für MAC {mac}: {e}")
        
        return None
    
    def get_genre_names(
        self, 
        url: str, 
        mac: str, 
        token: str, 
        proxy: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Holt Genre-Namen für eine MAC-Adresse.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            proxy: Optional HTTP-Proxy
            
        Returns:
            Dict mit genre_id → genre_name oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}",
        }
        
        try:
            response = self._get_session().get(
                url + "?action=get_genres&type=itv&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            
            data = response.json()
            genre_data = data.get("js", [])
            
            if genre_data:
                genres = {}
                for item in genre_data:
                    gid = str(item.get("id", ""))
                    name = item.get("title", "")
                    if gid and name:
                        genres[gid] = name
                return genres
                
        except Exception as e:
            logger.error(f"Fehler beim Genre-Abruf für MAC {mac}: {e}")
        
        return None
    
    def get_link(
        self, 
        url: str, 
        mac: str, 
        token: str, 
        cmd: str, 
        proxy: Optional[str] = None
    ) -> Optional[str]:
        """
        Holt den Stream-Link für einen Kanal.
        
        Args:
            url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            cmd: Kanal-Befehl
            proxy: Optional HTTP-Proxy
            
        Returns:
            Stream-URL oder None
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}",
        }
        
        try:
            response = self._get_session().get(
                url + f"?type=itv&action=create_link&cmd={cmd}"
                "&series=0&forced_storage=false&disable_ad=false"
                "&download=false&force_ch_link_check=false&JsHttpRequest=1-xml",
                cookies=cookies,
                headers=headers,
                proxies=proxies,
                timeout=10,
            )
            
            data = response.json()
            cmd_result = data.get("js", {}).get("cmd", "")
            
            if cmd_result:
                # Extrahiere URL aus cmd (nach "ffmpeg " oder direkt)
                link = cmd_result.split()[-1]
                return link
                
        except Exception as e:
            logger.error(f"Fehler beim Link-Abruf: {e}")
        
        return None
    
    def close(self):
        """Schließt die Session."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
