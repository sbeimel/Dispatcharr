"""
STB Profil V1 - Dispatcharr Plugin

Live TV Integration für STB/Stalker-basierte IPTV-Portale.

Features:
- Live TV Import mit MAC-Rotation
- Multi-Stream Failover via Profile
- XMLTV/EPG Import
- Genre-Filter
- Kanalnamen-Bereinigung
- MAC-Status Prüfung
- Profile-Management

by StiniStinson
"""

import logging
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse
import re
import time

logger = logging.getLogger(__name__)


class STBClient:
    """Client für STB/Stalker Portal API-Kommunikation."""
    
    def __init__(self):
        self._session = None
        self._session_created = 0
        self._SESSION_MAX_AGE = 300
    
    def _get_session(self):
        current_time = time.time()
        if self._session is None or (current_time - self._session_created) > self._SESSION_MAX_AGE:
            if self._session is not None:
                try:
                    self._session.close()
                except:
                    pass
            self._session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
            self._session.mount("http://", HTTPAdapter(max_retries=retries))
            self._session.mount("https://", HTTPAdapter(max_retries=retries))
            self._session_created = current_time
        return self._session
    
    def get_portal_url(self, url, proxy=None):
        """Ermittelt die Portal-URL aus der Basis-URL."""
        def parse_response(url, data):
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

        url = urlparse(url).scheme + "://" + urlparse(url).netloc
        urls = [
            "/c/xpcom.common.js",
            "/client/xpcom.common.js",
            "/c_/xpcom.common.js",
            "/stalker_portal/c/xpcom.common.js",
            "/stalker_portal/c_/xpcom.common.js",
        ]

        proxies = {"http": proxy, "https": proxy} if proxy else None
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)"}

        try:
            session = self._get_session()
            for path in urls:
                try:
                    response = session.get(url + path, headers=headers, proxies=proxies, timeout=10)
                    if response.ok:
                        return parse_response(url + path, response)
                except:
                    continue
        except:
            pass
        return None
    
    def get_token(self, url, mac, proxy=None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)"}
        try:
            response = self._get_session().get(
                url + "?type=stb&action=handshake&JsHttpRequest=1-xml",
                cookies=cookies, headers=headers, proxies=proxies, timeout=20,
            )
            token = response.json()["js"]["token"]
            if token:
                logger.info(f"Token erfolgreich für MAC {mac} erhalten")
                return token
        except Exception as e:
            logger.error(f"Fehler beim Token-Abruf für MAC {mac}: {e}")
        return None
    
    def get_profile(self, url, mac, token, proxy=None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)", "Authorization": "Bearer " + token}
        try:
            response = self._get_session().get(
                url + "?type=stb&action=get_profile&JsHttpRequest=1-xml",
                cookies=cookies, headers=headers, proxies=proxies, timeout=10,
            )
            return response.json()["js"]
        except:
            return None
    
    def get_expires(self, url, mac, token, proxy=None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)", "Authorization": "Bearer " + token}
        try:
            response = self._get_session().get(
                url + "?type=account_info&action=get_main_info&JsHttpRequest=1-xml",
                cookies=cookies, headers=headers, proxies=proxies, timeout=15,
            )
            expires = response.json()["js"]["phone"]
            if expires:
                logger.info(f"Ablaufdatum für MAC {mac}: {expires}")
                return expires
        except Exception as e:
            logger.error(f"Fehler beim Ablaufdatum-Abruf für MAC {mac}: {e}")
        return None
    
    def get_all_channels(self, url, mac, token, proxy=None):
        """Holt alle Live TV Kanäle."""
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)", "Authorization": "Bearer " + token}
        try:
            response = self._get_session().get(
                url + "?type=itv&action=get_all_channels&force_ch_link_check=&JsHttpRequest=1-xml",
                cookies=cookies, headers=headers, proxies=proxies, timeout=30,
            )
            channels = response.json()["js"]["data"]
            if channels:
                logger.info(f"{len(channels)} Kanäle für MAC {mac} erhalten")
                return channels
        except Exception as e:
            logger.error(f"Fehler beim Kanal-Abruf für MAC {mac}: {e}")
        return None
    
    def get_genre_names(self, url, mac, token, proxy=None):
        """Holt Genre-Namen für Live TV."""
        proxies = {"http": proxy, "https": proxy} if proxy else None
        cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
        headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)", "Authorization": "Bearer " + token}
        try:
            response = self._get_session().get(
                url + "?action=get_genres&type=itv&JsHttpRequest=1-xml",
                cookies=cookies, headers=headers, proxies=proxies, timeout=10,
            )
            genre_data = response.json()["js"]
            if genre_data:
                genres = {}
                for item in genre_data:
                    genres[item["id"]] = item["title"]
                return genres
        except:
            pass
        return None


class Plugin:
    """STB Profil V1 - Live TV Integration für Dispatcharr"""
    
    name = "STB Profil V1"
    version = "v1.0.0"
    description = "STB/Stalker IPTV - Live TV mit MAC-Rotation und Profile-Management - by StiniStinson"
    
    fields = [
        {
            "id": "portal_name",
            "label": "Portal Name",
            "type": "string",
            "default": "",
            "help_text": "Name des IPTV-Portals"
        },
        {
            "id": "portal_url",
            "label": "Portal URL",
            "type": "string",
            "default": "",
            "help_text": "URL des STB/Stalker-Portals"
        },
        {
            "id": "mac_addresses",
            "label": "MAC-Adressen",
            "type": "string",
            "default": "",
            "help_text": "MAC-Adressen getrennt durch Komma oder Leerzeichen (z.B. '00:1A:79:XX:XX:XX, 00:1A:79:YY:YY:YY' oder '00:1A:79:XX:XX:XX 00:1A:79:YY:YY:YY')"
        },
        {
            "id": "proxy",
            "label": "Proxy (optional)",
            "type": "string",
            "default": "",
            "help_text": "HTTP-Proxy für API-Requests UND M3U Account (MOD: wird als proxy_std_xc gesetzt). Format: http://proxy:8080"
        },
        {
            "id": "genre_filter",
            "label": "Genre-Filter (optional)",
            "type": "string",
            "default": "",
            "help_text": "Filtert Live TV nach Genre-Stichworten (z.B. 'DE, SPORT, NEWS, GERMAN'). Nur Kanäle deren Genre einen dieser Begriffe enthält werden importiert. Leer = Alle Genres. Komma-getrennt, case-insensitive."
        },
        {
            "id": "auto_create_channels",
            "label": "Live TV: Channels automatisch erstellen",
            "type": "boolean",
            "default": False,
            "help_text": "Erstellt automatisch Channels aus Streams (Standard: nur Streams importieren). ⚠️ Wird ignoriert wenn 'Plugin-URL MAC-Rotation' aktiviert ist."
        },
        {
            "id": "streams_per_mac",
            "label": "  ↳ Streams pro MAC",
            "type": "number",
            "default": 1,
            "help_text": "⚠️ Nur relevant wenn 'Channels automatisch erstellen' aktiviert! Anzahl der MACs die pro Channel verwendet werden (Standard: 1). WICHTIG: Bei Wert 1 werden automatisch Failover-Profile für alle weiteren MACs erstellt (empfohlen). Bei Wert >1 werden mehrere Streams direkt in die M3U geschrieben (KEINE Profile!)."
        },
        {
            "id": "channel_profile",
            "label": "  ↳ Channel-Profil Name",
            "type": "string",
            "default": "All",
            "help_text": "⚠️ Nur relevant wenn 'Channels automatisch erstellen' aktiviert! Name des Channel-Profils (z.B. 'MAC Portal Channels'). Wird automatisch erstellt falls nicht vorhanden."
        },
        {
            "id": "clean_channel_names",
            "label": "Live TV: Kanalnamen bereinigen",
            "type": "boolean",
            "default": False,
            "help_text": "Entfernt Prefixes (┃DE┃, [UK], DE ✨) UND Sonderzeichen (Emojis ✨🔥⭐, Symbole, Umlaute→ae/oe/ue, Akzente, Kyrillisch, Arabisch, Chinesisch). Standard: Nur Display-Name, tvg-name bleibt Original."
        },
        {
            "id": "clean_tvg_name",
            "label": "Live TV: Auch tvg-name bereinigen",
            "type": "boolean",
            "default": False,
            "help_text": "Bereinigt auch tvg-name (nicht nur Display-Name). ⚠️ WARNUNG: Kann EPG-Matching beeinträchtigen! Nur aktivieren wenn EPG auch bereinigte Namen verwendet."
        },
    ]
    
    actions = [
        {
            "id": "test_portal",
            "label": "Portal testen",
            "description": "Testet die Verbindung zum Portal und alle MAC-Adressen",
        },
        {
            "id": "check_mac_status",
            "label": "MAC-Status prüfen",
            "description": "Prüft den Status, Ablaufdatum und Kanal-Prefixes aller MAC-Adressen",
        },
        {
            "id": "add_profiles",
            "label": "➕ Profile hinzufügen",
            "description": "Fügt MAC-Adressen als Profile zu bestehendem M3U Account hinzu (Portal Name muss exakt übereinstimmen)",
        },
        {
            "id": "show_account_info",
            "label": "ℹ️ Account-Info anzeigen",
            "description": "Zeigt Basis-MAC und alle Profile des M3U Accounts an (Portal Name muss exakt übereinstimmen)",
        },
        {
            "id": "remove_profiles",
            "label": "�️ Profile löschen",
            "description": "Löscht ALLE Profile (außer Default) vom M3U Account (Portal Name muss exakt übereinstimmen)",
        },
        {
            "id": "import_live_tv",
            "label": "📺 Live TV importieren",
            "description": "Importiert Live TV Streams - SCHNELL! (~1 Min für 500 Channels)",
        },
        {
            "id": "import_xmltv",
            "label": "📡 XMLTV/EPG importieren",
            "description": "Lädt die XMLTV-EPG-Datei vom Portal herunter und registriert EPG-Quelle",
        },
    ]
    
    def __init__(self):
        self.stb_client = STBClient()
        self._patch_get_stream_url()
    
    def _detect_dispatcharr_type(self):
        """
        Erkennt ob Dispatcharr-MOD oder Standard installiert ist.
        
        Returns:
            tuple: (account_type, is_mod)
            - account_type: 'MAC' für MOD, 'STD' für Standard
            - is_mod: True wenn MOD, False wenn Standard
        """
        try:
            from apps.m3u.models import M3UAccount
            if hasattr(M3UAccount.Types, 'MAC'):
                logger.info("✅ Dispatcharr-MOD erkannt (MAC Type verfügbar)")
                return ('MAC', True)
            else:
                logger.info("ℹ️ Standard Dispatcharr erkannt (nur STD/XC Types)")
                return ('STD', False)
        except:
            logger.warning("⚠️ Konnte Dispatcharr Type nicht erkennen, nutze STD")
            return ('STD', False)
    
    def _patch_get_stream_url(self):
        """Monkey Patch für get_stream_url() - KEINE Dispatcharr-Anpassung nötig!"""
        try:
            from apps.vod.models import M3UMovieRelation, M3UEpisodeRelation
            
            original_movie_get_stream_url = M3UMovieRelation.get_stream_url
            original_episode_get_stream_url = M3UEpisodeRelation.get_stream_url
            
            def patched_movie_get_stream_url(self):
                if self.custom_properties and 'mac_portal_stream_url' in self.custom_properties:
                    logger.debug(f"[MACBridge] Using MAC Portal stream URL from custom_properties")
                    return self.custom_properties['mac_portal_stream_url']
                return original_movie_get_stream_url(self)
            
            def patched_episode_get_stream_url(self):
                if self.custom_properties and 'mac_portal_stream_url' in self.custom_properties:
                    logger.debug(f"[MACBridge] Using MAC Portal stream URL from custom_properties")
                    return self.custom_properties['mac_portal_stream_url']
                return original_episode_get_stream_url(self)
            
            M3UMovieRelation.get_stream_url = patched_movie_get_stream_url
            M3UEpisodeRelation.get_stream_url = patched_episode_get_stream_url
            
            logger.info("✅ [MACBridge v3 ENHANCED] get_stream_url() erfolgreich gepatcht (Monkey Patch)")
            logger.info("✅ [MACBridge v3 ENHANCED] Streaming funktioniert jetzt für MAC Portal!")
            
        except Exception as e:
            logger.error(f"❌ [MACBridge v3 ENHANCED] Fehler beim Monkey Patching: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run(self, action: str, params: dict, context: dict):
        """Führt eine Plugin-Aktion aus."""
        settings = context.get("settings", {})
        logger_ctx = context.get("logger", logger)
        
        portal_url = settings.get("portal_url", "").strip()
        mac_addresses = settings.get("mac_addresses", "").strip()
        
        if not portal_url or not mac_addresses:
            return {"status": "error", "message": "Portal URL und MAC-Adressen sind erforderlich"}
        
        # Parse MACs: Unterstützt Komma UND Leerzeichen als Trenner
        macs = [mac.strip() for mac in re.split(r'[,\s]+', mac_addresses) if mac.strip()]
        proxy = settings.get("proxy", "").strip() or None
        
        if not portal_url.endswith(".php"):
            portal_url = self.stb_client.get_portal_url(portal_url, proxy)
            if not portal_url:
                return {"status": "error", "message": "Konnte Portal-URL nicht ermitteln"}
        
        if action == "test_portal":
            return self._test_portal(portal_url, macs, proxy, logger_ctx)
        
        elif action == "check_mac_status":
            return self._check_mac_status(portal_url, macs, proxy, logger_ctx)
        
        elif action == "add_profiles":
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            return self._add_profiles_to_account(portal_url, macs, proxy, portal_name, logger_ctx)
        
        elif action == "show_account_info":
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            return self._show_account_info(portal_name, logger_ctx)
        
        elif action == "remove_profiles":
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            return self._remove_profiles(portal_name, logger_ctx)
        
        elif action == "import_live_tv":
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            genre_filter = settings.get("genre_filter", "").strip()
            auto_create_channels = settings.get("auto_create_channels", False)
            channel_profile = settings.get("channel_profile", "All").strip()
            return self._import_live_tv(portal_url, macs, proxy, portal_name, genre_filter, auto_create_channels, channel_profile, settings, logger_ctx)
        
        elif action == "import_xmltv":
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            return self._import_xmltv(portal_url, macs, proxy, portal_name, logger_ctx)
        
        elif action == "import_vod":
            # Nutze Settings für Import-Methode
            import_method = settings.get("import_method", "direct")
            portal_name = settings.get("portal_name", "MAC Portal").strip()
            country_filter = settings.get("country_filter", "").strip()
            
            if import_method == "m3u":
                return self._import_vod_m3u(portal_url, macs[0], proxy, portal_name, country_filter, settings, logger_ctx)
            else:
                return self._import_vod_direct(portal_url, macs[0], proxy, portal_name, country_filter, settings, logger_ctx)
        
        return {"status": "error", "message": f"Unbekannte Aktion: {action}"}
    
    def _test_portal(self, portal_url, macs, proxy, logger_ctx):
        """Testet die Portal-Verbindung."""
        logger_ctx.info(f"Teste Portal: {portal_url}")
        results = []
        for mac in macs:
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if token:
                expires = self.stb_client.get_expires(portal_url, mac, token, proxy)
                results.append({"mac": mac, "status": "success", "expires": expires})
            else:
                results.append({"mac": mac, "status": "error"})
        success_count = sum(1 for r in results if r["status"] == "success")
        return {
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}/{len(macs)} MAC-Adressen erfolgreich getestet",
            "results": results
        }
    
    def _list_vod_categories(self, portal_url, mac, proxy, logger_ctx):
        """Zeigt alle verfügbaren VOD-Kategorien."""
        logger_ctx.info(f"📁 Hole VOD-Kategorien vom Portal...")
        
        try:
            # Hole Token
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return {"status": "error", "message": "Konnte Token nicht abrufen"}
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            proxies = {"http": proxy, "https": proxy} if proxy else None
            cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                "Authorization": f"Bearer {token}",
            }
            
            # Hole VOD-Kategorien
            vod_cat_url = f"{portal_url}?type=vod&action=get_categories&JsHttpRequest=1-xml"
            response = requests.get(vod_cat_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "error", "message": "Fehler beim Abrufen der VOD-Kategorien"}
            
            vod_categories = response.json()["js"]
            
            # Filtere "*" Kategorie raus
            vod_categories = [cat for cat in vod_categories if cat['id'] != "*"]
            
            # Sortiere alphabetisch
            vod_categories.sort(key=lambda x: x['title'])
            
            # Erstelle Liste
            category_names = [cat['title'] for cat in vod_categories]
            
            logger_ctx.info(f"✅ {len(category_names)} Kategorien gefunden")
            
            # Erstelle formatierte Ausgabe
            message_lines = [
                f"📁 {len(category_names)} VOD-Kategorien gefunden:",
                "",
                "Kopiere die gewünschten Kategorien in die Settings:",
                ""
            ]
            
            for i, name in enumerate(category_names, 1):
                message_lines.append(f"{i}. {name}")
            
            message_lines.extend([
                "",
                "💡 Beispiel für Settings:",
                f"  vod_category_include: \"{category_names[0]}, {category_names[1] if len(category_names) > 1 else ''}\"",
                "",
                "Oder alle außer bestimmte:",
                "  vod_category_exclude: \"XXX, Adult, Erotik\""
            ])
            
            return {
                "status": "success",
                "message": "\n".join(message_lines),
                "categories": category_names,
                "total": len(category_names)
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _import_vod_direct(self, portal_url, mac, proxy, portal_name, country_filter, settings, logger_ctx):
        """
        Importiert VOD DIREKT in die Datenbank.
        Nutzt account_type='MAC' auf MOD, 'STD' auf Standard (Monkey Patch übernimmt Streaming).
        """
        logger_ctx.info(f"🎬 VOD Direkt-Import vom Portal: {portal_name}")
        
        # Erkenne Dispatcharr Type
        account_type, is_mod = self._detect_dispatcharr_type()
        logger_ctx.info(f"Nutze account_type='{account_type}' für VOD")
        
        # Pagination ist immer aktiviert (macht am meisten Sinn)
        use_pagination = True
        max_items = settings.get("max_items_per_category", 0)
        skip_existing = settings.get("skip_existing", True)
        
        logger_ctx.info(f"⚙️ Max Items: {max_items or 'Alle'}, Skip Existing: {skip_existing}")
        
        try:
            from apps.vod.models import VODCategory, Movie, M3UMovieRelation
            from apps.m3u.models import M3UAccount
            
            # Hole Token
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return {"status": "error", "message": "Konnte Token nicht abrufen"}
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            proxies = {"http": proxy, "https": proxy} if proxy else None
            cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                "Authorization": f"Bearer {token}",
            }
            
            # Hole VOD-Kategorien
            vod_cat_url = f"{portal_url}?type=vod&action=get_categories&JsHttpRequest=1-xml"
            response = requests.get(vod_cat_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "error", "message": "Fehler beim Abrufen der VOD-Kategorien"}
            
            vod_categories = response.json()["js"]
            
            # Filtere nach Ländercode
            if country_filter:
                allowed_countries = [c.strip().upper() for c in country_filter.split(",") if c.strip()]
                vod_categories = [cat for cat in vod_categories 
                                if cat['id'] != "*" and self._matches_country_filter(cat['title'], allowed_countries)]
            
            logger_ctx.info(f"📁 {len(vod_categories)} Kategorien gefunden")
            
            # Erstelle M3U Account
            account_name = f"MAC Portal VOD - {portal_name}"
            account_defaults = {
                'account_type': account_type,  # MAC auf MOD, STD auf Standard
                'server_url': portal_url,
                'username': mac,
            }
            
            # MOD-Support: Setze proxy in BEIDEN Feldern
            if proxy:
                if hasattr(M3UAccount, 'proxy'):
                    account_defaults['proxy'] = proxy
                if hasattr(M3UAccount, 'proxy_std_xc'):
                    account_defaults['proxy_std_xc'] = proxy
                logger_ctx.info(f"✅ Proxy für M3U Account gesetzt: {proxy}")
            
            m3u_account, created = M3UAccount.objects.get_or_create(
                name=account_name,
                defaults=account_defaults
            )
            
            # Update proxy bei existierendem Account (BEIDE Felder)
            if not created and proxy:
                if hasattr(m3u_account, 'proxy'):
                    m3u_account.proxy = proxy
                if hasattr(m3u_account, 'proxy_std_xc'):
                    m3u_account.proxy_std_xc = proxy
                m3u_account.save()
                logger_ctx.info(f"✅ Proxy für M3U Account aktualisiert: {proxy}")
            
            logger_ctx.info(f"✅ M3U Account: {account_name}")
            
            total_movies = 0
            total_skipped = 0
            
            # Importiere Filme pro Kategorie
            for cat_idx, category in enumerate(vod_categories, 1):
                if category['id'] == "*":
                    continue
                
                logger_ctx.info(f"📁 [{cat_idx}/{len(vod_categories)}] {category['title']}")
                
                vod_category, _ = VODCategory.objects.get_or_create(
                    name=category['title'],
                    defaults={'category_type': 'movie'}
                )
                
                # Hole Filme mit Pagination
                page = 1
                category_movies = 0
                
                while True:
                    if max_items > 0 and category_movies >= max_items:
                        logger_ctx.info(f"  ⏹️ Limit erreicht ({max_items} Filme)")
                        break
                    
                    # Hole Seite
                    vod_url = f"{portal_url}?type=vod&action=get_ordered_list&category={category['id']}&sortby=added&p={page}&JsHttpRequest=1-xml"
                    
                    try:
                        response = requests.get(vod_url, headers=headers, cookies=cookies, proxies=proxies, timeout=60)
                    except Exception as e:
                        logger_ctx.warning(f"  ⚠️ Timeout Seite {page}: {e}")
                        break
                    
                    if response.status_code != 200:
                        break
                    
                    vod_items = response.json()["js"]["data"]
                    
                    if not vod_items:
                        break
                    
                    logger_ctx.info(f"  📄 Seite {page}: {len(vod_items)} Filme")
                    
                    # Batch-Import
                    for item in vod_items:
                        if max_items > 0 and category_movies >= max_items:
                            break
                        
                        try:
                            movie_name = item.get('name', '')
                            
                            # Name-Filter auf Item-Ebene (nur für VOD/Serien)
                            name_filter = settings.get("name_filter", "").strip()
                            if name_filter:
                                search_terms = [term.strip() for term in name_filter.split(",") if term.strip()]
                                if search_terms and not self._matches_name_filter(movie_name, search_terms):
                                    continue
                            
                            # Prüfe ob existiert
                            if skip_existing and Movie.objects.filter(name=movie_name).exists():
                                total_skipped += 1
                                continue
                            
                            cmd = item.get('cmd', '')
                            if not cmd:
                                continue
                            
                            # Hole Stream-URL
                            stream_url_response = requests.get(
                                f"{portal_url}?type=vod&action=create_link&cmd={cmd}&JsHttpRequest=1-xml",
                                headers=headers, cookies=cookies, proxies=proxies, timeout=10
                            )
                            
                            if stream_url_response.status_code != 200:
                                continue
                            
                            stream_url = stream_url_response.json()["js"].get("cmd", "").split()[-1]
                            
                            if not stream_url or not stream_url.startswith("http"):
                                continue
                            
                            # Erstelle oder hole Logo
                            from apps.vod.models import VODLogo
                            logo = None
                            logo_url = item.get('screenshot_uri', '')
                            if logo_url:
                                logo, _ = VODLogo.objects.get_or_create(
                                    url=logo_url,
                                    defaults={'name': item.get('name', 'Unknown')}
                                )
                            
                            # Erstelle Movie mit Metadaten
                            movie, _ = Movie.objects.get_or_create(
                                name=item.get('name', 'Unknown'),
                                defaults={
                                    'logo': logo,
                                    'description': item.get('description', ''),
                                    'year': self._extract_year(item.get('year')),
                                    'rating': self._clean_rating(item.get('rating_imdb')),
                                    'genre': item.get('genre_title', ''),
                                    'custom_properties': {
                                        'mac_portal_stream_url': stream_url,  # Für Monkey Patch
                                        'cmd': stream_url,  # Für Dispatcharr-MOD native
                                        'mac_portal_id': item.get('id'),
                                        'mac_portal_name': portal_name,
                                    }
                                }
                            )
                            
                            # Erstelle Relation
                            M3UMovieRelation.objects.update_or_create(
                                m3u_account=m3u_account,
                                stream_id=item.get('id', ''),
                                defaults={
                                    'movie': movie,
                                    'category': vod_category,
                                    'container_extension': 'mp4',
                                    'custom_properties': {
                                        'mac_portal_stream_url': stream_url,  # Für Monkey Patch
                                        'cmd': stream_url,  # Für Dispatcharr-MOD native
                                    }
                                }
                            )
                            
                            total_movies += 1
                            category_movies += 1
                            
                        except Exception as e:
                            logger_ctx.debug(f"Fehler: {e}")
                            continue
                    
                    if not use_pagination:
                        break
                    
                    page += 1
                
                logger_ctx.info(f"  ✅ {category_movies} Filme importiert")
            
            logger_ctx.info(f"🎉 Import abgeschlossen: {total_movies} Filme, {total_skipped} übersprungen")
            
            return {
                "status": "success",
                "message": f"✅ {total_movies} Filme importiert, {total_skipped} übersprungen",
                "total_movies": total_movies,
                "total_skipped": total_skipped,
                "method": "direct",
                "pagination_used": use_pagination
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _import_vod_m3u(self, portal_url, mac, proxy, portal_name, country_filter, settings, logger_ctx):
        """
        Generiert M3U-Datei für VOD und erstellt M3U-Account in Dispatcharr.
        
        ⚠️ WARNUNG: M3U-Import ist SEHR LANGSAM!
        - Muss für jeden Film Stream-URL vorab holen
        - 500 Filme = ~25 Minuten
        - 5000 Filme = ~3 Stunden
        
        💡 EMPFEHLUNG: Nutze Direkt-Import (viel schneller!)
        """
        logger_ctx.info(f"🎬 VOD M3U-Import vom Portal: {portal_name}")
        logger_ctx.warning("⚠️ M3U-Import ist SEHR LANGSAM! Direkt-Import ist 10x schneller!")
        
        # Pagination ist immer aktiviert (macht am meisten Sinn)
        use_pagination = True
        max_items = settings.get("max_items_per_category", 0)
        
        logger_ctx.info(f"⚙️ Max Items: {max_items or 'Alle'}")
        
        try:
            import os
            from apps.m3u.models import M3UAccount
            
            # Hole Token
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return {"status": "error", "message": "Konnte Token nicht abrufen"}
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            proxies = {"http": proxy, "https": proxy} if proxy else None
            cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                "Authorization": f"Bearer {token}",
            }
            
            # Hole VOD-Kategorien
            vod_cat_url = f"{portal_url}?type=vod&action=get_categories&JsHttpRequest=1-xml"
            response = requests.get(vod_cat_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "error", "message": "Fehler beim Abrufen der VOD-Kategorien"}
            
            vod_categories = response.json()["js"]
            
            # Filtere nach Ländercode
            if country_filter:
                allowed_countries = [c.strip().upper() for c in country_filter.split(",") if c.strip()]
                vod_categories = [cat for cat in vod_categories 
                                if cat['id'] != "*" and self._matches_country_filter(cat['title'], allowed_countries)]
            
            logger_ctx.info(f"📁 {len(vod_categories)} Kategorien gefunden")
            
            # Generiere M3U-Content
            m3u_lines = ['#EXTM3U']
            total_movies = 0
            
            safe_portal_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in portal_name)
            
            # Sammle Filme pro Kategorie
            for cat_idx, category in enumerate(vod_categories, 1):
                if category['id'] == "*":
                    continue
                
                logger_ctx.info(f"📁 [{cat_idx}/{len(vod_categories)}] {category['title']}")
                
                category_movies = 0
                page = 1
                
                while True:
                    if max_items > 0 and category_movies >= max_items:
                        logger_ctx.info(f"  ⏹️ Limit erreicht ({max_items} Filme)")
                        break
                    
                    # Hole Seite
                    vod_url = f"{portal_url}?type=vod&action=get_ordered_list&category={category['id']}&sortby=added&p={page}&JsHttpRequest=1-xml"
                    
                    try:
                        response = requests.get(vod_url, headers=headers, cookies=cookies, proxies=proxies, timeout=60)
                    except Exception as e:
                        logger_ctx.warning(f"  ⚠️ Timeout Seite {page}: {e}")
                        break
                    
                    if response.status_code != 200:
                        break
                    
                    vod_items = response.json()["js"]["data"]
                    
                    if not vod_items:
                        break
                    
                    logger_ctx.info(f"  📄 Seite {page}: {len(vod_items)} Filme")
                    logger_ctx.info(f"  ⏳ Hole Stream-URLs (kann lange dauern)...")
                    
                    # Verarbeite Filme
                    for item in vod_items:
                        if max_items > 0 and category_movies >= max_items:
                            break
                        
                        try:
                            movie_name = item.get('name', '')
                            
                            # Name-Filter auf Item-Ebene (nur für VOD/Serien)
                            name_filter = settings.get("name_filter", "").strip()
                            if name_filter:
                                search_terms = [term.strip() for term in name_filter.split(",") if term.strip()]
                                if search_terms and not self._matches_name_filter(movie_name, search_terms):
                                    continue
                            
                            cmd = item.get('cmd', '')
                            if not cmd:
                                continue
                            
                            # Hole Stream-URL (LANGSAM!)
                            stream_url_response = requests.get(
                                f"{portal_url}?type=vod&action=create_link&cmd={cmd}&JsHttpRequest=1-xml",
                                headers=headers, cookies=cookies, proxies=proxies, timeout=10
                            )
                            
                            if stream_url_response.status_code != 200:
                                continue
                            
                            stream_url = stream_url_response.json()["js"].get("cmd", "").split()[-1]
                            
                            if not stream_url or not stream_url.startswith("http"):
                                continue
                            
                            # Erstelle EXTINF-Zeile
                            movie_name = item.get('name', 'Unknown')
                            movie_id = item.get('id', '')
                            logo = item.get('screenshot_uri', '')
                            year = item.get('year', '')
                            
                            extinf_parts = ['#EXTINF:-1']
                            
                            # Metadaten
                            extinf_parts.append(f'tvg-id="{safe_portal_name.lower().replace(" ", "_")}_{movie_id}"')
                            extinf_parts.append(f'tvg-name="{movie_name}"')
                            
                            if logo:
                                extinf_parts.append(f'tvg-logo="{logo}"')
                            
                            extinf_parts.append(f'group-title="{category["title"]}"')
                            
                            if year:
                                extinf_parts.append(f'tvg-year="{year}"')
                            
                            # Custom Properties für Monkey Patch
                            extinf_parts.append(f'mac-portal-id="{movie_id}"')
                            extinf_parts.append(f'mac-portal-name="{portal_name}"')
                            
                            extinf_line = ' '.join(extinf_parts) + f',{movie_name}'
                            m3u_lines.append(extinf_line)
                            m3u_lines.append(stream_url)
                            
                            total_movies += 1
                            category_movies += 1
                            
                        except Exception as e:
                            logger_ctx.debug(f"Fehler: {e}")
                            continue
                    
                    if not use_pagination:
                        break
                    
                    page += 1
                
                logger_ctx.info(f"  ✅ {category_movies} Filme hinzugefügt")
            
            m3u_content = '\n'.join(m3u_lines)
            
            # Speichere M3U-Datei
            output_dir = "/app/sources"
            if not os.path.exists(output_dir):
                output_dir = os.path.join(os.getcwd(), "sources")
                os.makedirs(output_dir, exist_ok=True)
            
            safe_filename = safe_portal_name.replace(' ', '_')
            output_file = os.path.join(output_dir, f"{safe_filename}_vod.m3u")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(m3u_content)
            
            logger_ctx.info(f"✅ M3U-Datei gespeichert: {output_file}")
            
            # Erstelle M3U-Account in Dispatcharr
            account_name = f"MAC Portal VOD - {portal_name}"
            
            existing_account = M3UAccount.objects.filter(name=account_name).first()
            
            if existing_account:
                logger_ctx.info(f"Account existiert bereits, aktualisiere: {account_name}")
                existing_account.url = f"file://{output_file}"
                
                # MOD-Support: Update proxy in BEIDEN Feldern
                if proxy:
                    if hasattr(existing_account, 'proxy'):
                        existing_account.proxy = proxy
                    if hasattr(existing_account, 'proxy_std_xc'):
                        existing_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account aktualisiert: {proxy}")
                
                existing_account.save()
                account_id = existing_account.id
            else:
                logger_ctx.info(f"Erstelle neuen M3U-Account: {account_name}")
                new_account = M3UAccount(name=account_name)
                
                # Setze Account-Type
                if hasattr(new_account, 'account_type'):
                    new_account.account_type = 'STD'
                
                # Setze URL/Path (verschiedene Dispatcharr-Versionen)
                if hasattr(new_account, 'url'):
                    new_account.url = f"file://{output_file}"
                elif hasattr(new_account, 'file_path'):
                    new_account.file_path = output_file
                elif hasattr(new_account, 'path'):
                    new_account.path = output_file
                
                # MOD-Support: Setze proxy in BEIDEN Feldern
                if proxy:
                    if hasattr(new_account, 'proxy'):
                        new_account.proxy = proxy
                    if hasattr(new_account, 'proxy_std_xc'):
                        new_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account gesetzt: {proxy}")
                
                new_account.save()
                account_id = new_account.id
            
            logger_ctx.info(f"✅ M3U-Account erstellt/aktualisiert: {account_name} (ID: {account_id})")
            
            # Trigger Refresh
            try:
                from apps.m3u.tasks import refresh_m3u_account
                refresh_m3u_account.delay(account_id)
                logger_ctx.info(f"✅ Refresh-Task gestartet für Account {account_id}")
            except Exception as refresh_error:
                logger_ctx.debug(f"Konnte Refresh-Task nicht starten: {refresh_error}")
            
            logger_ctx.info(f"🎉 M3U-Import abgeschlossen: {total_movies} Filme")
            
            return {
                "status": "success",
                "message": f"✅ M3U-Datei mit {total_movies} Filmen erstellt (⚠️ Nutze Direkt-Import für schnelleren Import!)",
                "total_movies": total_movies,
                "account_id": account_id,
                "account_name": account_name,
                "file_path": output_file,
                "method": "m3u",
                "pagination_used": use_pagination
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _cleanup_vod(self, logger_ctx):
        """Löscht ALLE MAC Portal VOD-Daten (Filme UND Serien)."""
        try:
            from apps.vod.models import Movie, Series, Episode, M3UMovieRelation, M3USeriesRelation, M3UEpisodeRelation
            from apps.m3u.models import M3UAccount
            
            logger_ctx.info("🗑️ Lösche MAC Portal VOD-Daten...")
            
            # Zähle vor dem Löschen
            movie_relations = M3UMovieRelation.objects.filter(m3u_account__name__contains='MAC Portal')
            movie_count = movie_relations.count()
            
            series_relations = M3USeriesRelation.objects.filter(m3u_account__name__contains='MAC Portal')
            series_count = series_relations.count()
            
            episode_relations = M3UEpisodeRelation.objects.filter(m3u_account__name__contains='MAC Portal')
            episode_count = episode_relations.count()
            
            # Lösche Relations
            logger_ctx.info(f"  🗑️ Lösche {movie_count} Film-Relations...")
            movie_relations.delete()
            
            logger_ctx.info(f"  🗑️ Lösche {episode_count} Episoden-Relations...")
            episode_relations.delete()
            
            logger_ctx.info(f"  🗑️ Lösche {series_count} Serien-Relations...")
            series_relations.delete()
            
            # Lösche verwaiste Filme
            orphaned_movies = Movie.objects.filter(m3u_relations__isnull=True)
            orphaned_movies_count = orphaned_movies.count()
            if orphaned_movies_count > 0:
                logger_ctx.info(f"  🗑️ Lösche {orphaned_movies_count} verwaiste Filme...")
                orphaned_movies.delete()
            
            # Finde verwaiste Serien (ohne Relations)
            orphaned_series = Series.objects.filter(m3u_relations__isnull=True)
            orphaned_series_count = orphaned_series.count()
            
            # Lösche ALLE Episoden dieser Serien (auch wenn sie noch Relations haben)
            if orphaned_series_count > 0:
                orphaned_episodes = Episode.objects.filter(series__in=orphaned_series)
                orphaned_episodes_count = orphaned_episodes.count()
                if orphaned_episodes_count > 0:
                    logger_ctx.info(f"  🗑️ Lösche {orphaned_episodes_count} verwaiste Episoden...")
                    orphaned_episodes.delete()
                
                # Jetzt können wir die Serien löschen
                logger_ctx.info(f"  🗑️ Lösche {orphaned_series_count} verwaiste Serien...")
                orphaned_series.delete()
            
            # Lösche verwaiste Episoden (ohne Series)
            remaining_orphaned_episodes = Episode.objects.filter(m3u_relations__isnull=True)
            remaining_count = remaining_orphaned_episodes.count()
            if remaining_count > 0:
                logger_ctx.info(f"  🗑️ Lösche {remaining_count} weitere verwaiste Episoden...")
                remaining_orphaned_episodes.delete()
            
            # Lösche M3U Accounts
            accounts = M3UAccount.objects.filter(name__contains='MAC Portal')
            account_count = accounts.count()
            if account_count > 0:
                logger_ctx.info(f"  🗑️ Lösche {account_count} M3U Account(s)...")
                accounts.delete()
            
            logger_ctx.info("✅ Cleanup abgeschlossen!")
            
            # Erstelle Zusammenfassung
            summary_parts = []
            if movie_count > 0:
                summary_parts.append(f"{movie_count} Filme")
            if series_count > 0:
                summary_parts.append(f"{series_count} Serien")
            if episode_count > 0:
                summary_parts.append(f"{episode_count} Episoden")
            
            summary = ", ".join(summary_parts) if summary_parts else "Keine Daten"
            
            return {
                "status": "success",
                "message": f"✅ Gelöscht: {summary}",
                "deleted": {
                    "movies": movie_count,
                    "series": series_count,
                    "episodes": episode_count,
                    "accounts": account_count
                }
            }
        except Exception as e:
            logger_ctx.error(f"❌ Fehler beim Cleanup: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _extract_year(self, year_value):
        """
        Extrahiert das Jahr aus verschiedenen Formaten.
        
        Args:
            year_value: Jahr als String, Int oder Datum (z.B. "2025", 2025, "2025-12-05")
        
        Returns:
            int oder None: Das Jahr als Integer oder None wenn nicht extrahierbar
        """
        if not year_value:
            return None
        try:
            match = re.search(r'(\d{4})', str(year_value))
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
        except:
            pass
        return None
    
    def _clean_rating(self, rating_value):
        """
        Bereinigt Rating-Werte (z.B. IMDB-Rating).
        
        Args:
            rating_value: Rating als String oder Float (z.B. "8.5", 8.5, "8.5/10")
        
        Returns:
            float oder None: Rating als Float (0.0-10.0) oder None
        """
        if not rating_value:
            return None
        try:
            # Extrahiere Zahl aus String (z.B. "8.5/10" -> "8.5")
            rating_str = str(rating_value).split('/')[0].strip()
            rating = float(rating_str)
            # Validiere Bereich
            if 0.0 <= rating <= 10.0:
                return rating
        except:
            pass
        return None
    
    def _matches_country_filter(self, name, allowed_countries):
        """
        Filter-Methode für Ländercodes (nur für Kategorien).
        
        Funktioniert für:
        - Ländercodes: "DE", "UK", "US" (2-3 Großbuchstaben, case-sensitive)
        
        Beispiele:
        - "┃DE┃ SPORT", ["DE"] → True
        - "UK Movies", ["UK"] → True
        - "FR Films", ["DE", "UK"] → False
        """
        if not name or not allowed_countries:
            return False
        
        # Prüfe ob EINER der Ländercodes zutrifft (ODER-Verknüpfung für Kategorien)
        for country_code in allowed_countries:
            country_code = country_code.strip().upper()
            
            # Ländercode-Matching (case-sensitive, mit Prefix-Erkennung)
            pattern = r'[┃|\[\(]?(' + re.escape(country_code) + r')[┃|\]\)]?[\s✨:|\-]'
            if re.search(pattern, name):
                return True
        
        return False
    
    def _matches_name_filter(self, name, search_terms):
        """
        Filter-Methode für Name-Suche (nur für einzelne Filme/Serien).
        
        Funktioniert für:
        - Suchbegriffe: "Breaking Bad", "Dark" (längere Texte, case-insensitive)
        
        Logik: EINER der Suchbegriffe muss zutreffen (ODER-Verknüpfung)
        
        Beispiele:
        - "Breaking Bad", ["Breaking Bad", "Dark"] → True
        - "Game of Thrones", ["thrones"] → True (Teil-Match)
        - "Better Call Saul", ["Breaking Bad", "Dark"] → False
        """
        if not name or not search_terms:
            return False
        
        name_lower = name.lower()
        
        # Prüfe ob EINER der Suchbegriffe zutrifft (ODER-Verknüpfung)
        for search_term in search_terms:
            search_term_stripped = search_term.strip().lower()
            if search_term_stripped in name_lower:
                return True
        
        return False

    
    def _import_live_tv(self, portal_url, macs, proxy, portal_name, genre_filter, auto_create_channels, channel_profile, settings, logger_ctx):
        """
        Importiert Live TV Channels als M3U mit Streams.
        
        Optional: Erstellt automatisch Channels (wenn auto_create_channels=True)
        Standard: Nur Streams (User erstellt Channels manuell)
        """
        logger_ctx.info(f"📺 Live TV Import vom Portal: {portal_name}")
        logger_ctx.info(f"⚙️ Auto-Create Channels: {auto_create_channels}")
        
        # Hole streams_per_mac aus Settings
        streams_per_mac = settings.get("streams_per_mac", 1)
        
        try:
            import os
            import re
            from apps.m3u.models import M3UAccount
            
            # Hole Kanäle und Genres
            channels = None
            genres = None
            
            for mac in macs:
                try:
                    token = self.stb_client.get_token(portal_url, mac, proxy)
                    if token:
                        self.stb_client.get_profile(portal_url, mac, token, proxy)
                        channels = self.stb_client.get_all_channels(portal_url, mac, token, proxy)
                        genres = self.stb_client.get_genre_names(portal_url, mac, token, proxy)
                        if channels and genres:
                            break
                except Exception as e:
                    logger_ctx.error(f"Fehler beim Kanal-Abruf mit MAC {mac}: {e}")
                    continue
            
            if not channels or not genres:
                return {"status": "error", "message": "Konnte Kanäle nicht abrufen"}
            
            # Generiere M3U-Content
            safe_portal_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in portal_name)
            safe_portal_name = safe_portal_name.strip()
            
            account_name = portal_name
            m3u_lines = ['#EXTM3U']
            imported_tvg_ids = set()
            
            # Extrahiere Base-URL
            base_url = portal_url.replace("/portal.php", "")
            
            # Parse genre_filter für Genre-Filterung
            genre_filters = []
            if genre_filter:
                genre_filters = [f.strip().upper() for f in genre_filter.split(",") if f.strip()]
                logger_ctx.info(f"🔍 Genre-Filter aktiv: {genre_filters}")
            
            filtered_count = 0
            
            for channel in channels:
                channel_id = str(channel["id"])
                channel_name = str(channel["name"])
                channel_number = str(channel.get("number", ""))
                genre_id = str(channel.get("tv_genre_id", ""))
                genre_name = genres.get(genre_id, "")
                logo = str(channel.get("logo", ""))
                cmd = str(channel.get("cmd", ""))
                
                # Genre-Filter: Überspringe Kanäle wenn Genre nicht matched
                if genre_filters and genre_name:
                    genre_upper = genre_name.upper()
                    if not any(filter_term in genre_upper for filter_term in genre_filters):
                        filtered_count += 1
                        logger_ctx.debug(f"⏭️ Überspringe Kanal '{channel_name}' (Genre: {genre_name})")
                        continue
                
                # Erstelle EXTINF-Zeile
                extinf_parts = ['#EXTINF:-1']
                
                if channel_number:
                    extinf_parts.append(f'tvg-chno="{channel_number}"')
                
                # Bereinige Kanalnamen wenn aktiviert
                clean_name = channel_name
                display_name = channel_name
                
                if settings.get("clean_channel_names", False):
                    # Schritt 1: Entferne Prefix
                    clean_name = self._remove_prefix(clean_name)
                    # Schritt 2: Entferne Sonderzeichen
                    clean_name = self._remove_special_chars(clean_name)
                    
                    if channel_name != clean_name:
                        logger_ctx.debug(f"Kanalname bereinigt: '{channel_name}' → '{clean_name}'")
                    
                    # Display-Name ist immer bereinigt
                    display_name = clean_name
                
                # tvg-name: Standard = Original, Optional = bereinigt
                tvg_name = channel_name  # Standard: Original für EPG-Matching
                if settings.get("clean_channel_names", False) and settings.get("clean_tvg_name", False):
                    tvg_name = clean_name  # Optional: Auch tvg-name bereinigen
                
                tvg_id = f"{safe_portal_name.lower().replace(' ', '_')}_{channel_id}"
                extinf_parts.append(f'tvg-id="{tvg_id}"')
                
                if tvg_name:
                    extinf_parts.append(f'tvg-name="{tvg_name}"')
                
                if logo:
                    extinf_parts.append(f'tvg-logo="{logo}"')
                
                if genre_name:
                    extinf_parts.append(f'group-title="{genre_name}"')
                
                # Extrahiere Channel-ID für URL
                ch_id = None
                if cmd:
                    cmd_clean = cmd.replace("ffmpeg ", "").strip()
                    if "localhost" in cmd_clean:
                        ch_id_match = re.search(r'/ch/(\d+)', cmd_clean)
                        if ch_id_match:
                            ch_id = ch_id_match.group(1)
                
                if not ch_id:
                    logger_ctx.debug(f"Überspringe Kanal {channel_id} ohne gültige Channel-ID")
                    continue
                
                # Standard Modus: Mehrere Streams (Multi-Stream oder Profile)
                macs_to_use = macs[:streams_per_mac]  # Nur die ersten X MACs verwenden
                for mac in macs_to_use:
                    # Für Multi-Stream: Gleiche tvg-id, aber unterschiedliche MAC in URL
                    extinf_line = ' '.join(extinf_parts) + f',{display_name}'
                    m3u_lines.append(extinf_line)
                    stream_url = f"{base_url}/play/live.php?mac={mac}&stream={ch_id}&extension=ts"
                    m3u_lines.append(stream_url)
                
                imported_tvg_ids.add(tvg_id)
            
            # Speichere M3U-Datei
            output_dir = "/app/sources"
            if not os.path.exists(output_dir):
                output_dir = os.path.join(os.getcwd(), "sources")
                os.makedirs(output_dir, exist_ok=True)
            
            safe_filename = safe_portal_name.replace(' ', '_')
            output_file = os.path.join(output_dir, f"{safe_filename}_live_tv.m3u")
            
            with open(output_file, 'wb') as f:
                for line in m3u_lines:
                    f.write((line + '\n').encode('utf-8'))
            
            logger_ctx.info(f"✅ M3U-Datei gespeichert: {output_file}")
            
            # Erstelle M3U-Account
            existing_account = M3UAccount.objects.filter(name=account_name).first()
            
            if existing_account:
                logger_ctx.info(f"Account existiert bereits, aktualisiere: {account_name}")
                # Setze file_path (KEIN file:// Prefix!)
                if hasattr(existing_account, 'file_path'):
                    existing_account.file_path = output_file
                if hasattr(existing_account, 'server_url'):
                    existing_account.server_url = None  # Leeren für file-based accounts
                
                # MOD-Support: Update proxy in BEIDEN Feldern
                if proxy:
                    if hasattr(existing_account, 'proxy'):
                        existing_account.proxy = proxy
                    if hasattr(existing_account, 'proxy_std_xc'):
                        existing_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account aktualisiert: {proxy}")
                
                existing_account.save()
                account_id = existing_account.id
            else:
                logger_ctx.info(f"Erstelle neuen M3U-Account: {account_name}")
                new_account = M3UAccount(name=account_name)
                
                # Setze Account-Type
                if hasattr(new_account, 'account_type'):
                    new_account.account_type = 'STD'
                
                # Setze file_path (KEIN file:// Prefix!)
                if hasattr(new_account, 'file_path'):
                    new_account.file_path = output_file
                # server_url bleibt None für file-based accounts
                
                # MOD-Support: Setze proxy in BEIDE Felder (proxy UND proxy_std_xc)
                if proxy:
                    # proxy - wird im WebUI angezeigt (Serializer)
                    if hasattr(new_account, 'proxy'):
                        new_account.proxy = proxy
                    # proxy_std_xc - wird beim Streaming verwendet (MOD)
                    if hasattr(new_account, 'proxy_std_xc'):
                        new_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account gesetzt: {proxy}")
                
                new_account.save()
                account_id = new_account.id
                
                # WICHTIG: Proxy nochmal setzen NACH dem Save (Serializer könnte überschreiben)
                if proxy:
                    update_fields = {}
                    if hasattr(new_account, 'proxy'):
                        update_fields['proxy'] = proxy
                        logger_ctx.info(f"🔍 DEBUG: Setze 'proxy' Feld auf: {proxy}")
                    if hasattr(new_account, 'proxy_std_xc'):
                        update_fields['proxy_std_xc'] = proxy
                        logger_ctx.info(f"🔍 DEBUG: Setze 'proxy_std_xc' Feld auf: {proxy}")
                    if update_fields:
                        M3UAccount.objects.filter(id=account_id).update(**update_fields)
                        logger_ctx.info(f"✅ Proxy nochmal gesetzt nach Save: {proxy}")
                        
                        # Verify: Lese Account nochmal aus DB
                        verify_account = M3UAccount.objects.get(id=account_id)
                        logger_ctx.info(f"🔍 VERIFY: proxy = {getattr(verify_account, 'proxy', 'NICHT VORHANDEN')}")
                        logger_ctx.info(f"🔍 VERIFY: proxy_std_xc = {getattr(verify_account, 'proxy_std_xc', 'NICHT VORHANDEN')}")
            
            logger_ctx.info(f"✅ M3U-Account erstellt/aktualisiert: {account_name} (ID: {account_id})")
            
            # Erstelle M3U Account Profiles für Failover (nur wenn streams_per_mac = 1)
            if len(macs) > 1 and streams_per_mac == 1:
                logger_ctx.info(f"⚙️ Erstelle {len(macs)-1} Failover-Profile für MAC-Rotation...")
                try:
                    from apps.m3u.models import M3UAccountProfile
                    
                    first_mac = macs[0]  # Erste MAC ist in allen URLs
                    
                    for i, mac in enumerate(macs[1:], start=2):  # Ab zweiter MAC
                        profile_name = str(i)
                        
                        # Prüfe ob Profil bereits existiert
                        profile, created = M3UAccountProfile.objects.get_or_create(
                            m3u_account_id=account_id,
                            name=profile_name,
                            defaults={
                                'is_default': False,
                                'max_streams': 1,
                                'is_active': True,
                                'search_pattern': first_mac,
                                'replace_pattern': mac
                            }
                        )
                        
                        if created:
                            logger_ctx.info(f"  ✅ Profil '{profile_name}' erstellt: {first_mac} → {mac}")
                        else:
                            # Update existing profile
                            profile.search_pattern = first_mac
                            profile.replace_pattern = mac
                            profile.max_streams = 1
                            profile.is_active = True
                            profile.save()
                            logger_ctx.info(f"  ✅ Profil '{profile_name}' aktualisiert: {first_mac} → {mac}")
                    
                    logger_ctx.info(f"✅ {len(macs)-1} Failover-Profile erstellt/aktualisiert")
                    
                except Exception as profile_error:
                    logger_ctx.warning(f"⚠️ Konnte Failover-Profile nicht erstellen: {profile_error}")
                    import traceback
                    logger_ctx.debug(traceback.format_exc())
            
            # Trigger Refresh (erstellt Streams)
            try:
                from apps.m3u.tasks import refresh_m3u_account
                refresh_m3u_account.delay(account_id)
                logger_ctx.info(f"✅ Refresh-Task gestartet für Account {account_id}")
            except Exception as refresh_error:
                logger_ctx.debug(f"Konnte Refresh-Task nicht starten: {refresh_error}")
            
            # Optional: Channels erstellen
            channels_created = 0
            if auto_create_channels:
                logger_ctx.info(f"⚙️ Erstelle Channels automatisch (Profil: {channel_profile})...")
                channel_result = self._create_multi_stream_channels(
                    account_id=account_id,
                    profile_name=channel_profile,
                    imported_tvg_ids=list(imported_tvg_ids),
                    macs=macs,
                    streams_per_mac=streams_per_mac,
                    logger_ctx=logger_ctx
                )
                if channel_result.get("status") == "success":
                    channels_created = channel_result.get("channels_created", 0)
                    logger_ctx.info(f"✅ {channels_created} Channels erstellt")
                else:
                    logger_ctx.warning(f"⚠️ Channel-Erstellung teilweise fehlgeschlagen: {channel_result.get('message', 'Unbekannter Fehler')}")
            
            logger_ctx.info(f"🎉 Live TV Import abgeschlossen: {len(imported_tvg_ids)} Streams")
            
            if filtered_count > 0:
                logger_ctx.info(f"🔍 {filtered_count} Kanäle durch Genre-Filter ausgeschlossen")
            
            result = {
                "status": "success",
                "message": f"✅ {len(imported_tvg_ids)} Live TV Streams importiert" + (f", {channels_created} Channels erstellt" if channels_created > 0 else ""),
                "account_id": account_id,
                "account_name": account_name,
                "file_path": output_file,
                "stream_count": len(imported_tvg_ids),
                "channels_auto_created": channels_created > 0,
                "channels_created": channels_created
            }
            
            if not auto_create_channels:
                result["info"] = "Streams wurden importiert. Channels können in Dispatcharr UI erstellt werden (Channel Groups → Auto-Channel-Sync)"
            
            return result
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _create_multi_stream_channels(self, account_id, profile_name, imported_tvg_ids, macs, streams_per_mac, logger_ctx):
        """
        Erstellt Channels mit mehreren Streams (Multi-Stream Failover).
        Jeder Channel bekommt mehrere Streams (1 pro MAC, bis zu streams_per_mac).
        
        Args:
            account_id: ID des M3U-Accounts
            profile_name: Name des Channel-Profils
            imported_tvg_ids: Liste der tvg-ids, die importiert wurden
            macs: Liste der MAC-Adressen
            streams_per_mac: Maximale Anzahl MACs pro Channel
            logger_ctx: Logger-Kontext
        """
        try:
            from apps.channels.models import ChannelProfile, Channel, ChannelStream, ChannelProfileMembership, Stream
            from apps.m3u.models import M3UAccount
            import time
            
            logger_ctx.info(f"🔄 Warte auf Source-Refresh...")
            
            # Trigger Source Refresh
            try:
                from apps.m3u.tasks import refresh_single_m3u_account
                task = refresh_single_m3u_account.delay(account_id)
                logger_ctx.info("  ⏳ Source-Refresh-Task gestartet...")
                
                # Warte auf Abschluss (max 60 Sekunden)
                timeout = 60
                for i in range(timeout):
                    if task.ready():
                        logger_ctx.info("  ✅ Source-Refresh abgeschlossen")
                        time.sleep(5)  # Warte auf DB-Commit
                        break
                    time.sleep(1)
                else:
                    logger_ctx.warning(f"  ⚠️ Source-Refresh dauert länger als {timeout}s")
                    time.sleep(5)
                    
            except Exception as refresh_error:
                logger_ctx.warning(f"  ⚠️ Source-Refresh fehlgeschlagen: {refresh_error}")
                time.sleep(5)
            
            # Hole oder erstelle Channel-Profil
            profile, created = ChannelProfile.objects.get_or_create(name=profile_name)
            if created:
                logger_ctx.info(f"✅ Channel-Profil erstellt: {profile_name}")
            else:
                logger_ctx.info(f"✅ Channel-Profil gefunden: {profile_name}")
            
            # Hole Account
            try:
                account = M3UAccount.objects.get(id=account_id)
            except M3UAccount.DoesNotExist:
                return {"status": "error", "message": "M3U-Account nicht gefunden"}
            
            # Hole alle Streams für diesen Account
            all_streams = Stream.objects.filter(m3u_account=account, tvg_id__in=imported_tvg_ids)
            stream_count = all_streams.count()
            
            logger_ctx.info(f"📊 Gefunden: {stream_count} Streams für {len(imported_tvg_ids)} tvg-ids")
            
            if stream_count == 0:
                logger_ctx.warning("⚠️ Keine Streams gefunden. Warte länger...")
                time.sleep(10)
                all_streams = Stream.objects.filter(m3u_account=account, tvg_id__in=imported_tvg_ids)
                stream_count = all_streams.count()
                
                if stream_count == 0:
                    return {"status": "error", "message": "Keine Streams gefunden nach Wartezeit"}
            
            # Gruppiere Streams nach tvg-id (jede tvg-id = 1 Channel mit mehreren Streams)
            from collections import defaultdict
            streams_by_tvg_id = defaultdict(list)
            
            for stream in all_streams:
                tvg_id = stream.tvg_id
                if tvg_id:
                    streams_by_tvg_id[tvg_id].append(stream)
            
            logger_ctx.info(f"📺 Erstelle Channels für {len(streams_by_tvg_id)} eindeutige tvg-ids...")
            
            channels_created = 0
            channels_skipped = 0
            total_stream_links = 0
            
            for tvg_id, streams in streams_by_tvg_id.items():
                try:
                    # Prüfe ob Channel bereits existiert
                    existing_channel = Channel.objects.filter(
                        tvg_id=tvg_id,
                        channelprofilemembership__channel_profile=profile
                    ).first()
                    
                    if existing_channel:
                        channels_skipped += 1
                        logger_ctx.debug(f"  ⏭️ Channel existiert bereits: {tvg_id}")
                        continue
                    
                    # Nimm ersten Stream für Channel-Infos
                    first_stream = streams[0]
                    
                    # Extrahiere Channel-Nummer
                    channel_number = 0.0
                    if first_stream.custom_properties and 'tvg-chno' in first_stream.custom_properties:
                        try:
                            channel_number = float(first_stream.custom_properties['tvg-chno'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Erstelle Channel
                    channel = Channel.objects.create(
                        name=first_stream.name,
                        channel_number=channel_number,
                        tvg_id=tvg_id,
                        channel_group=first_stream.channel_group
                    )
                    
                    # Verknüpfe mehrere Streams mit diesem Channel (bis zu streams_per_mac)
                    streams_to_link = streams[:streams_per_mac]
                    
                    for stream in streams_to_link:
                        ChannelStream.objects.create(
                            channel=channel,
                            stream=stream
                        )
                        total_stream_links += 1
                    
                    # Verknüpfe Channel mit Profil
                    ChannelProfileMembership.objects.create(
                        channel_profile=profile,
                        channel=channel,
                        enabled=True
                    )
                    
                    channels_created += 1
                    logger_ctx.debug(f"  ✅ Channel: {first_stream.name} ({len(streams_to_link)} Streams)")
                    
                except Exception as channel_error:
                    logger_ctx.warning(f"  ⚠️ Fehler bei Channel {tvg_id}: {channel_error}")
                    continue
            
            logger_ctx.info(f"🎉 {channels_created} Channels erstellt, {total_stream_links} Stream-Verknüpfungen, {channels_skipped} übersprungen")
            
            return {
                "status": "success",
                "profile_id": profile.id,
                "profile_name": profile_name,
                "channels_created": channels_created,
                "channels_skipped": channels_skipped,
                "stream_links": total_stream_links
            }
            
        except Exception as e:
            logger_ctx.error(f"❌ Fehler bei Channel-Erstellung: {e}")
            import traceback
            logger_ctx.debug(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _extract_country_code(self, name):
        """
        Extrahiert den Ländercode aus einem Kanalnamen.
        Unterstützt alle gängigen Prefix-Formate und extrahiert nur den 2-3 Buchstaben Code.
        
        Beispiele:
        - ┃DE┃ SERIEN → DE
        - |NL| SPORT → NL
        - DE ✨ RADIO → DE
        - [UK] News → UK
        - (US) Movies → US
        - FR: Channel → FR
        - DE - Regional → DE
        """
        if not name:
            return None
        
        # Erweiterte Muster für Ländercode-Extraktion
        patterns = [
            r'^┃([A-Z]{2,3})┃',                    # ┃DE┃
            r'^\|([A-Z]{2,3})\|',                  # |DE|
            r'^\[([A-Z]{2,3})\]',                  # [DE]
            r'^\(([A-Z]{2,3})\)',                  # (DE)
            r'^([A-Z]{2,3})\s*[✨🔥⭐🎬🎵🎮📺🌟💎🎯🔴⚡💥🌈🎪🎭🎨🎤🎧🎼🎹🎺🎻🥁🎸]+', # DE ✨
            r'^([A-Z]{2,3})\s*[:|\-]\s*',          # DE:, DE|, DE -, DE-
            r'^([A-Z]{2,3})\s+(?=[A-Z])',          # DE SERIEN
            r'^([A-Z]{2,3})\s*\*',                 # DE*
            r'^([A-Z]{2,3})\s*►',                  # DE►
            r'^([A-Z]{2,3})\s*»',                  # DE»
            r'^([A-Z]{2,3})\s*•',                  # DE•
            r'^([A-Z]{2,3})\s*→',                  # DE→
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name.strip())
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_prefix(self, channel_name):
        """
        Extrahiert Prefix aus Kanalnamen.
        Unterstützt Formate wie:
        - ┃DE┃ SERIEN 24/7
        - |DE| SERIEN 24/7
        - DE ✨ RADIO
        - [DE] Channel Name
        - (DE) Channel Name
        - DE: Channel Name
        - DE | Channel Name
        """
        if not channel_name:
            return None
        
        # Muster für verschiedene Prefix-Formate
        patterns = [
            r'^(┃[^┃]+┃)',           # ┃DE┃
            r'^(\|[^\|]+\|)',         # |DE|
            r'^\[([^\]]+)\]',         # [DE]
            r'^\(([^\)]+)\)',         # (DE)
            r'^([A-Z]{2,3}\s*[✨🔥⭐🎬🎵🎮📺🌟💎🎯🔴⚡💥🌈🎪🎭🎨🎬🎤🎧🎼🎹🎺🎻🥁🎸]+)', # DE ✨, DE 🔥, etc.
            r'^([A-Z]{2,3})\s*[:|\-]', # DE:, DE|, DE-
            r'^([A-Z]{2,3})\s+(?=[A-Z])', # DE SERIEN (DE gefolgt von Großbuchstaben)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, channel_name.strip())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _remove_prefix(self, channel_name):
        """
        Entfernt Prefix aus Kanalnamen.
        
        Beispiele:
        - ┃DE┃ SERIEN 24/7 → SERIEN 24/7
        - |NL| SPORT HD → SPORT HD
        - DE ✨ RADIO → RADIO
        - [UK] News → News
        - (US) Movies → Movies
        - FR: Channel → Channel
        """
        if not channel_name:
            return channel_name
        
        # Muster für verschiedene Prefix-Formate (mit Capture-Group für Rest)
        patterns = [
            r'^┃[^┃]+┃\s*(.+)',                    # ┃DE┃ Rest
            r'^\|[^\|]+\|\s*(.+)',                  # |DE| Rest
            r'^\[[^\]]+\]\s*(.+)',                  # [DE] Rest
            r'^\([^\)]+\)\s*(.+)',                  # (DE) Rest
            r'^[A-Z]{2,3}\s*[✨🔥⭐🎬🎵🎮📺🌟💎🎯🔴⚡💥🌈🎪🎭🎨🎤🎧🎼🎹🎺🎻🥁🎸]+\s*(.+)', # DE ✨ Rest
            r'^[A-Z]{2,3}\s*[:|\-]\s*(.+)',        # DE: Rest, DE| Rest, DE- Rest
            r'^[A-Z]{2,3}\s*\*\s*(.+)',            # DE* Rest
            r'^[A-Z]{2,3}\s*►\s*(.+)',             # DE► Rest
            r'^[A-Z]{2,3}\s*»\s*(.+)',             # DE» Rest
            r'^[A-Z]{2,3}\s*•\s*(.+)',             # DE• Rest
            r'^[A-Z]{2,3}\s*→\s*(.+)',             # DE→ Rest
            r'^[A-Z]{2,3}\s+([A-Z].+)',            # DE SERIEN (DE gefolgt von Großbuchstaben)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, channel_name.strip())
            if match:
                return match.group(1).strip()
        
        # Kein Prefix gefunden, gib Original zurück
        return channel_name
    
    def _remove_special_chars(self, text):
        """
        Entfernt Sonderzeichen, Emojis und nicht-ASCII Zeichen aus Text.
        
        Entfernt:
        - Emojis: ✨, 🔥, ⭐, 🎬, 📺, etc.
        - Symbole: ┃, |, →, ►, », •, etc.
        - Umlaute: ä, ö, ü, ß, etc.
        - Akzente: é, è, à, ñ, etc.
        - Kyrillisch: а, б, в, г, etc.
        - Arabisch: ا, ب, ت, etc.
        - Chinesisch: 中, 文, etc.
        
        Behält:
        - Buchstaben A-Z, a-z
        - Zahlen 0-9
        - Leerzeichen
        - Grundlegende Satzzeichen: . , - _ ( ) [ ]
        
        Beispiele:
        - "ARD HD ✨" → "ARD HD"
        - "┃DE┃ SPORT" → "DE SPORT"
        - "Österreich 🇦🇹" → "Osterreich"
        - "Спорт HD" → "HD"
        """
        if not text:
            return text
        
        # Ersetze Umlaute vor der Bereinigung (optional)
        umlaut_map = {
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
            'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'å': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
            'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u',
            'ñ': 'n', 'ç': 'c',
        }
        
        for umlaut, replacement in umlaut_map.items():
            text = text.replace(umlaut, replacement)
        
        # Entferne alle nicht-ASCII Zeichen (Emojis, Symbole, Kyrillisch, Arabisch, Chinesisch, etc.)
        # Behalte nur: A-Z, a-z, 0-9, Leerzeichen, . , - _ ( ) [ ]
        cleaned = ''.join(c for c in text if c.isascii() and (c.isalnum() or c in ' .,-_()[]'))
        
        # Entferne mehrfache Leerzeichen
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _check_mac_status(self, portal_url, macs, proxy, logger_ctx):
        """Prüft den Status, Ablaufdatum, Prefixes und Genres aller MAC-Adressen."""
        logger_ctx.info(f"Prüfe MAC-Status für {len(macs)} Adressen")
        
        results = []
        active_count = 0
        all_prefixes = set()
        all_genres = set()
        
        for mac in macs:
            try:
                token = self.stb_client.get_token(portal_url, mac, proxy)
                
                if token:
                    expires = self.stb_client.get_expires(portal_url, mac, token, proxy)
                    
                    if expires:
                        # Hole Kanäle und Genres
                        channels = None
                        genres = None
                        try:
                            self.stb_client.get_profile(portal_url, mac, token, proxy)
                            channels = self.stb_client.get_all_channels(portal_url, mac, token, proxy)
                            genres = self.stb_client.get_genre_names(portal_url, mac, token, proxy)
                        except Exception as e:
                            logger_ctx.debug(f"Konnte Kanäle für MAC {mac} nicht abrufen: {e}")
                        
                        # Extrahiere Prefixes aus Kanalnamen
                        prefixes = set()
                        channel_genres = set()
                        if channels and genres:
                            for channel in channels:
                                channel_name = channel.get("name", "")
                                prefix = self._extract_prefix(channel_name)
                                if prefix:
                                    prefixes.add(prefix)
                                    all_prefixes.add(prefix)
                                
                                # Sammle Genres
                                genre_id = str(channel.get("tv_genre_id", ""))
                                genre_name = genres.get(genre_id, "")
                                if genre_name:
                                    channel_genres.add(genre_name)
                                    all_genres.add(genre_name)
                        
                        results.append({
                            "mac": mac,
                            "status": "active",
                            "expires": expires,
                            "channel_count": len(channels) if channels else 0,
                            "prefixes": sorted(list(prefixes)),
                            "genres": sorted(list(channel_genres))
                        })
                        active_count += 1
                    else:
                        results.append({
                            "mac": mac,
                            "status": "inactive",
                            "message": "Kein Ablaufdatum verfügbar"
                        })
                else:
                    results.append({
                        "mac": mac,
                        "status": "inactive",
                        "message": "Kein Token erhalten"
                    })
            
            except Exception as e:
                results.append({
                    "mac": mac,
                    "status": "error",
                    "message": str(e)
                })
        
        # Ausgabe mit Genres
        logger_ctx.info("")
        logger_ctx.info("=" * 60)
        logger_ctx.info(f"Gefundene Genres ({len(all_genres)}):")
        logger_ctx.info("=" * 60)
        for genre in sorted(all_genres):
            logger_ctx.info(f"  • {genre}")
        logger_ctx.info("=" * 60)
        logger_ctx.info("")
        logger_ctx.info("💡 Tipp: Nutze diese Genre-Namen für den 'Ländercode-Filter'")
        logger_ctx.info("   Beispiel: 'DE, GER, GERMAN' filtert nur deutsche Genres")
        logger_ctx.info("")
        
        return {
            "status": "success",
            "message": f"{active_count}/{len(macs)} MAC-Adressen aktiv",
            "active_count": active_count,
            "total_count": len(macs),
            "all_prefixes": sorted(list(all_prefixes)),
            "all_genres": sorted(list(all_genres)),
            "results": results
        }
    
    def _add_profiles_to_account(self, portal_url, macs, proxy, portal_name, logger_ctx):
        """
        Fügt MAC-Adressen als Profile zu einem bestehenden M3U Account hinzu.
        
        Sucht nach einem M3U Account mit exakt dem gleichen Namen wie portal_name.
        Extrahiert automatisch die Basis-MAC aus dem Account (server_url oder username).
        Erstellt dann Profile für alle Plugin-MACs.
        
        Funktioniert ohne .patch - nutzt nur Django Models.
        """
        logger_ctx.info(f"➕ Profile hinzufügen zu Account: {portal_name}")
        
        try:
            from apps.m3u.models import M3UAccount, M3UAccountProfile
            import re
            
            # Suche M3U Account mit exakt dem gleichen Namen
            account = M3UAccount.objects.filter(name=portal_name).first()
            
            if not account:
                logger_ctx.error(f"❌ Kein M3U Account mit Name '{portal_name}' gefunden!")
                logger_ctx.info("💡 Tipp: Der Portal Name im Plugin muss exakt mit dem M3U Account Namen übereinstimmen.")
                logger_ctx.info("💡 Verfügbare M3U Accounts:")
                
                all_accounts = M3UAccount.objects.all()
                for acc in all_accounts:
                    logger_ctx.info(f"   - '{acc.name}' (Type: {getattr(acc, 'account_type', 'N/A')})")
                
                return {
                    "status": "error",
                    "message": f"Kein M3U Account mit Name '{portal_name}' gefunden. Portal Name muss exakt übereinstimmen!"
                }
            
            logger_ctx.info(f"✅ M3U Account gefunden: {account.name} (ID: {account.id})")
            logger_ctx.info(f"   Account Type: {getattr(account, 'account_type', 'N/A')}")
            
            # Prüfe ob wir mindestens 1 MAC haben
            if len(macs) < 1:
                logger_ctx.error("❌ Keine MAC-Adressen konfiguriert!")
                return {
                    "status": "error",
                    "message": "Mindestens 1 MAC-Adresse nötig."
                }
            
            # AUTO-DETECT: Extrahiere Basis-MAC aus dem Account
            base_mac = None
            
            # Methode 1: Aus username (bei MAC Account Type)
            if hasattr(account, 'username') and account.username:
                # MAC-Format: XX:XX:XX:XX:XX:XX oder XX-XX-XX-XX-XX-XX
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, account.username)
                if match:
                    base_mac = match.group(0)
                    logger_ctx.info(f"🔍 Basis-MAC aus username extrahiert: {base_mac}")
            
            # Methode 2: Aus server_url
            if not base_mac and hasattr(account, 'server_url') and account.server_url:
                mac_pattern = r'mac=([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, account.server_url)
                if match:
                    base_mac = match.group(0).replace('mac=', '')
                    logger_ctx.info(f"🔍 Basis-MAC aus server_url extrahiert: {base_mac}")
            
            # Methode 3: Aus file_path (M3U-Datei lesen)
            if not base_mac and hasattr(account, 'file_path') and account.file_path:
                try:
                    import os
                    if os.path.exists(account.file_path):
                        with open(account.file_path, 'r', encoding='utf-8') as f:
                            # Lese erste 50 Zeilen
                            for i, line in enumerate(f):
                                if i > 50:
                                    break
                                mac_pattern = r'mac=([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                                match = re.search(mac_pattern, line)
                                if match:
                                    base_mac = match.group(0).replace('mac=', '')
                                    logger_ctx.info(f"🔍 Basis-MAC aus M3U-Datei extrahiert: {base_mac}")
                                    break
                except Exception as e:
                    logger_ctx.debug(f"Konnte M3U-Datei nicht lesen: {e}")
            
            # Fallback: Nutze erste MAC aus Plugin
            if not base_mac:
                base_mac = macs[0]
                logger_ctx.warning(f"⚠️ Konnte Basis-MAC nicht aus Account extrahieren, nutze erste Plugin-MAC: {base_mac}")
                logger_ctx.warning(f"⚠️ WICHTIG: Diese MAC muss in den Stream-URLs des Accounts enthalten sein!")
            else:
                logger_ctx.info(f"✅ Basis-MAC (search_pattern): {base_mac}")
            
            # Normalisiere MAC-Format (mit Doppelpunkt)
            base_mac = base_mac.replace('-', ':').upper()
            
            # Hole existierende Profile
            existing_profiles = M3UAccountProfile.objects.filter(m3u_account=account)
            existing_profile_names = set(p.name for p in existing_profiles)
            logger_ctx.info(f"📋 Existierende Profile: {len(existing_profiles)}")
            
            # Finde nächste freie Profil-Nummer
            existing_numbers = []
            for name in existing_profile_names:
                try:
                    existing_numbers.append(int(name))
                except ValueError:
                    pass
            
            next_number = max(existing_numbers) + 1 if existing_numbers else 2
            
            profiles_created = 0
            profiles_updated = 0
            profiles_skipped = 0
            
            # Erstelle Profile für ALLE Plugin-MACs (die nicht schon die Basis-MAC sind)
            for mac in macs:
                # Normalisiere MAC-Format
                mac_normalized = mac.replace('-', ':').upper()
                
                # Skip wenn es die Basis-MAC ist
                if mac_normalized == base_mac:
                    logger_ctx.info(f"  ⏭️ Überspringe Basis-MAC: {mac}")
                    profiles_skipped += 1
                    continue
                
                # Prüfe ob ein Profil mit dieser MAC bereits existiert
                existing_with_mac = M3UAccountProfile.objects.filter(
                    m3u_account=account,
                    replace_pattern=mac_normalized
                ).first()
                
                if existing_with_mac:
                    logger_ctx.info(f"  ℹ️ Profil für MAC {mac} existiert bereits: '{existing_with_mac.name}'")
                    # Update search_pattern falls nötig
                    if existing_with_mac.search_pattern != base_mac:
                        existing_with_mac.search_pattern = base_mac
                        existing_with_mac.save()
                        logger_ctx.info(f"     ✅ search_pattern aktualisiert: {base_mac}")
                        profiles_updated += 1
                    else:
                        profiles_skipped += 1
                    continue
                
                # Erstelle neues Profil
                profile_name = str(next_number)
                profile = M3UAccountProfile.objects.create(
                    m3u_account=account,
                    name=profile_name,
                    is_default=False,
                    max_streams=1,
                    is_active=True,
                    search_pattern=base_mac,
                    replace_pattern=mac_normalized
                )
                
                logger_ctx.info(f"  ✅ Profil '{profile_name}' erstellt: {base_mac} → {mac_normalized}")
                profiles_created += 1
                next_number += 1
            
            # Zusammenfassung
            logger_ctx.info("")
            logger_ctx.info("=" * 50)
            logger_ctx.info(f"✅ Profile hinzugefügt zu Account: {account.name}")
            logger_ctx.info(f"   Neue Profile: {profiles_created}")
            logger_ctx.info(f"   Aktualisierte Profile: {profiles_updated}")
            logger_ctx.info(f"   Übersprungen: {profiles_skipped}")
            logger_ctx.info(f"   Basis-MAC: {base_mac}")
            logger_ctx.info("=" * 50)
            
            return {
                "status": "success",
                "message": f"{profiles_created} Profile erstellt, {profiles_updated} aktualisiert, {profiles_skipped} übersprungen für Account '{account.name}'",
                "account_id": account.id,
                "account_name": account.name,
                "profiles_created": profiles_created,
                "profiles_updated": profiles_updated,
                "profiles_skipped": profiles_skipped,
                "base_mac": base_mac
            }
            
        except ImportError as e:
            logger_ctx.error(f"❌ Import-Fehler: {e}")
            return {"status": "error", "message": f"Import-Fehler: {e}"}
        except Exception as e:
            logger_ctx.error(f"❌ Fehler beim Hinzufügen der Profile: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def _import_xmltv(self, portal_url, macs, proxy, portal_name, logger_ctx):
        """Lädt die XMLTV-EPG-Datei vom Portal herunter und speichert sie in /app/sources."""
        logger_ctx.info(f"📡 Lade XMLTV-EPG vom Portal: {portal_name}")
        
        try:
            import os
            
            # Extrahiere Base-URL (ohne /portal.php)
            base_url = portal_url.replace("/portal.php", "")
            
            # Verwende die erste MAC-Adresse
            mac = macs[0]
            
            # Lade XMLTV-Datei herunter
            proxies = {"http": proxy, "https": proxy} if proxy else None
            headers = {"User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)"}
            
            xmltv_content = None
            used_method = None
            epg_url = None  # Die URL die wir für die EPG-Quelle verwenden
            
            # Methode 1: API-Endpoint (get_epg_info) - Diese URL für EPG-Quelle verwenden
            api_url = f"{portal_url}?type=itv&action=get_epg_info&period=24&mac={mac}"
            logger_ctx.info(f"Versuche API-Methode: {api_url}")
            
            try:
                # Hole Token für API-Zugriff
                token = self.stb_client.get_token(portal_url, mac, proxy)
                if token:
                    cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
                    api_headers = {
                        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                        "Authorization": f"Bearer {token}",
                    }
                    response = requests.get(api_url, headers=api_headers, cookies=cookies, proxies=proxies, timeout=60)
                    
                    if response.status_code == 200 and len(response.content) > 100:
                        xmltv_content = response.content
                        used_method = "API (get_epg_info)"
                        epg_url = api_url
                        logger_ctx.info("✅ EPG via API-Methode erfolgreich geladen")
            except Exception as e:
                logger_ctx.warning(f"API-Methode fehlgeschlagen: {e}")
            
            # Methode 2: Fallback zu xmltv.php
            if not xmltv_content:
                xmltv_url = f"{base_url}/xmltv.php?username={mac}&password={mac}"
                logger_ctx.info(f"Versuche xmltv.php-Methode: {xmltv_url}")
                
                try:
                    response = requests.get(xmltv_url, headers=headers, proxies=proxies, timeout=60)
                    
                    if response.status_code == 200 and len(response.content) > 100:
                        xmltv_content = response.content
                        used_method = "xmltv.php"
                        epg_url = xmltv_url
                        logger_ctx.info("✅ EPG via xmltv.php erfolgreich geladen")
                except Exception as e:
                    logger_ctx.warning(f"xmltv.php-Methode fehlgeschlagen: {e}")
            
            # Prüfe ob EPG-Daten geladen wurden
            if not xmltv_content:
                return {
                    "status": "error",
                    "message": "Konnte XMLTV-Datei nicht laden (beide Methoden fehlgeschlagen)"
                }
            
            if len(xmltv_content) < 100:
                return {
                    "status": "error",
                    "message": "XMLTV-Datei ist zu klein oder leer"
                }
            
            # Speichere XMLTV-Datei
            output_dir = "/app/sources"
            if not os.path.exists(output_dir):
                output_dir = os.path.join(os.getcwd(), "sources")
                os.makedirs(output_dir, exist_ok=True)
            
            # Sanitize portal name für Dateinamen
            safe_portal_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in portal_name)
            safe_filename = safe_portal_name.replace(' ', '_').lower()
            output_file = os.path.join(output_dir, f"{safe_filename}_epg.xml")
            
            # Schreibe XMLTV-Datei
            with open(output_file, 'wb') as f:
                f.write(xmltv_content)
            
            file_size_mb = len(xmltv_content) / (1024 * 1024)
            logger_ctx.info(f"✅ XMLTV-Datei gespeichert: {output_file} ({file_size_mb:.2f} MB) via {used_method}")
            
            # Registriere EPG-Quelle über Dispatcharr API mit direkter URL
            epg_source_name = f"{portal_name} EPG"
            epg_source_id = None
            
            if epg_url:
                try:
                    from apps.epg.models import EPGSource
                    
                    logger_ctx.info(f"Registriere EPG-Quelle: {epg_source_name}")
                    logger_ctx.info(f"EPG-URL: {epg_url}")
                    
                    # Prüfe ob EPG-Quelle bereits existiert
                    epg_source, created = EPGSource.objects.get_or_create(
                        name=epg_source_name,
                        defaults={
                            'source_type': 'xmltv',
                            'url': epg_url,
                            'is_active': True,
                        }
                    )
                    
                    # Aktualisiere Felder falls bereits vorhanden
                    if not created:
                        epg_source.source_type = 'xmltv'
                        epg_source.url = epg_url
                        epg_source.is_active = True
                        epg_source.save()
                        logger_ctx.info(f"✅ EPG-Quelle aktualisiert: {epg_source_name} (ID: {epg_source.id})")
                    else:
                        logger_ctx.info(f"✅ EPG-Quelle erstellt: {epg_source_name} (ID: {epg_source.id})")
                    
                    epg_source_id = epg_source.id
                    
                except Exception as epg_error:
                    logger_ctx.warning(f"Konnte EPG-Quelle nicht registrieren: {epg_error}")
                    logger_ctx.warning("EPG-Datei wurde gespeichert, muss aber manuell in Dispatcharr hinzugefügt werden")
            else:
                logger_ctx.warning("Keine EPG-URL verfügbar, EPG-Quelle wird nicht registriert")
            
            result = {
                "status": "success",
                "message": f"✅ XMLTV-EPG erfolgreich importiert ({file_size_mb:.2f} MB) via {used_method}",
                "file_path": output_file,
                "file_size_bytes": len(xmltv_content),
                "method": used_method,
                "epg_url": epg_url
            }
            
            if epg_source_id:
                result["epg_source_id"] = epg_source_id
                result["epg_source_name"] = epg_source_name
            
            return result
            
        except Exception as e:
            logger_ctx.error(f"Fehler beim XMLTV-Import: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Fehler beim XMLTV-Import: {str(e)}"
            }
    
    def _show_auto_update_status(self, settings, logger_ctx):
        """Zeigt den Status des automatischen Updates."""
        try:
            auto_update_enabled = settings.get('auto_update_enabled', False)
            interval_hours = settings.get('auto_update_interval_hours', 6)
            
            logger_ctx.info("=" * 60)
            logger_ctx.info("MACBridge Auto-Update Status")
            logger_ctx.info("=" * 60)
            logger_ctx.info("")
            
            if auto_update_enabled:
                logger_ctx.info("✅ Auto-Update ist AKTIVIERT")
                logger_ctx.info(f"   Intervall: Alle {interval_hours} Stunden")
                logger_ctx.info("")
                logger_ctx.info("Geplante Tasks:")
                logger_ctx.info(f"  • VOD-Import: Alle {interval_hours} Stunden um :00")
                logger_ctx.info(f"  • Live TV-Import: Alle {interval_hours} Stunden um :30")
                logger_ctx.info("")
                logger_ctx.info("⚠️ HINWEIS: Auto-Update Tasks müssen in Celery Beat konfiguriert werden.")
                logger_ctx.info("Die Tasks werden automatisch von Celery Beat ausgeführt.")
                logger_ctx.info("Logs findest du in den Dispatcharr-Logs.")
                logger_ctx.info("")
                logger_ctx.info("💡 Zum Deaktivieren:")
                logger_ctx.info("   Setze 'Auto-Update aktivieren' auf 'false' in den Plugin-Einstellungen")
            else:
                logger_ctx.info("❌ Auto-Update ist DEAKTIVIERT")
                logger_ctx.info("")
                logger_ctx.info("💡 Zum Aktivieren:")
                logger_ctx.info("   1. Gehe zu den Plugin-Einstellungen")
                logger_ctx.info("   2. Setze 'Auto-Update aktivieren' auf 'true'")
                logger_ctx.info("   3. Optional: Passe 'Update-Intervall (Stunden)' an")
                logger_ctx.info("   4. Speichere die Einstellungen")
                logger_ctx.info("")
                logger_ctx.info("Nach der Aktivierung werden automatisch alle")
                logger_ctx.info(f"{interval_hours} Stunden neue VODs und Live TV importiert.")
                logger_ctx.info("")
                logger_ctx.info("⚠️ HINWEIS: Celery Beat muss separat konfiguriert werden!")
            
            logger_ctx.info("")
            logger_ctx.info("=" * 60)
            
            # Prüfe ob Celery Beat läuft
            try:
                from celery import current_app
                inspect = current_app.control.inspect()
                scheduled = inspect.scheduled()
                
                if scheduled:
                    logger_ctx.info("")
                    logger_ctx.info("📊 Celery Beat Status: Läuft")
                    
                    # Suche nach MACBridge Tasks
                    macbridge_tasks = []
                    for worker, tasks in scheduled.items():
                        for task in tasks:
                            if 'macbridge' in task.get('name', '').lower():
                                macbridge_tasks.append(task)
                    
                    if macbridge_tasks:
                        logger_ctx.info(f"   Gefundene MACBridge Tasks: {len(macbridge_tasks)}")
                else:
                    logger_ctx.info("")
                    logger_ctx.info("⚠️  Celery Beat Status: Nicht erreichbar")
                    logger_ctx.info("   Stelle sicher, dass Celery Beat läuft")
            except Exception as e:
                logger_ctx.info("")
                logger_ctx.info(f"⚠️  Celery Status konnte nicht geprüft werden: {e}")
            
            return {
                "status": "success",
                "message": f"Auto-Update ist {'aktiviert' if auto_update_enabled else 'deaktiviert'}",
                "auto_update_enabled": auto_update_enabled,
                "interval_hours": interval_hours
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler beim Prüfen des Auto-Update-Status: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Fehler beim Prüfen des Auto-Update-Status: {str(e)}"
            }

    def _import_series_direct(self, portal_url, mac, proxy, portal_name, country_filter, settings, logger_ctx):
        """
        Importiert Serien DIREKT in die Datenbank.
        Ähnlich wie VOD Direct-Import aber für Serien mit Episoden.
        """
        logger_ctx.info(f"📺 Serien Direkt-Import vom Portal: {portal_name}")
        
        # Pagination ist immer aktiviert
        use_pagination = True
        max_items = settings.get("max_items_per_category", 0)
        skip_existing = settings.get("skip_existing", True)
        
        logger_ctx.info(f"⚙️ Max Items: {max_items or 'Alle'}, Skip Existing: {skip_existing}")
        
        try:
            from apps.vod.models import VODCategory, Series, Episode, VODLogo, M3USeriesRelation, M3UEpisodeRelation
            from apps.m3u.models import M3UAccount
            
            # Hole Token
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return {"status": "error", "message": "Konnte Token nicht abrufen"}
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            proxies = {"http": proxy, "https": proxy} if proxy else None
            cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                "Authorization": f"Bearer {token}",
            }
            
            # Hole Serien-Kategorien
            series_cat_url = f"{portal_url}?type=series&action=get_categories&JsHttpRequest=1-xml"
            response = requests.get(series_cat_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "error", "message": "Fehler beim Abrufen der Serien-Kategorien"}
            
            series_categories = response.json()["js"]
            
            # Filtere nach Ländercode
            if country_filter:
                allowed_countries = [c.strip().upper() for c in country_filter.split(",") if c.strip()]
                series_categories = [cat for cat in series_categories 
                                    if cat['id'] != "*" and self._matches_country_filter(cat['title'], allowed_countries)]
            
            logger_ctx.info(f"📁 {len(series_categories)} Kategorien gefunden")
            
            # Erkenne Dispatcharr Type
            account_type, is_mod = self._detect_dispatcharr_type()
            logger_ctx.info(f"Nutze account_type='{account_type}' für Serien")
            
            # Erstelle M3U Account
            account_name = f"MAC Portal Serien - {portal_name}"
            account_defaults = {
                'account_type': account_type,  # MAC auf MOD, STD auf Standard
                'server_url': portal_url,
                'username': mac,
            }
            
            # MOD-Support: Setze proxy in BEIDEN Feldern
            if proxy:
                if hasattr(M3UAccount, 'proxy'):
                    account_defaults['proxy'] = proxy
                if hasattr(M3UAccount, 'proxy_std_xc'):
                    account_defaults['proxy_std_xc'] = proxy
                logger_ctx.info(f"✅ Proxy für M3U Account gesetzt: {proxy}")
            
            m3u_account, created = M3UAccount.objects.get_or_create(
                name=account_name,
                defaults=account_defaults
            )
            
            # Update proxy bei existierendem Account
            if not created and proxy:
                if hasattr(m3u_account, 'proxy'):
                    m3u_account.proxy = proxy
                if hasattr(m3u_account, 'proxy_std_xc'):
                    m3u_account.proxy_std_xc = proxy
                m3u_account.save()
                logger_ctx.info(f"✅ Proxy für M3U Account aktualisiert: {proxy}")
            
            logger_ctx.info(f"✅ M3U Account: {account_name}")
            
            total_series = 0
            total_episodes = 0
            total_skipped = 0
            
            # Importiere Serien pro Kategorie
            for cat_idx, category in enumerate(series_categories, 1):
                if category['id'] == "*":
                    continue
                
                logger_ctx.info(f"📁 [{cat_idx}/{len(series_categories)}] {category['title']}")
                
                vod_category, _ = VODCategory.objects.get_or_create(
                    name=category['title'],
                    defaults={'category_type': 'series'}
                )
                
                # Hole Serien mit Pagination
                page = 1
                category_series = 0
                
                while True:
                    if max_items > 0 and category_series >= max_items:
                        logger_ctx.info(f"  ⏹️ Limit erreicht ({max_items} Serien)")
                        break
                    
                    # Hole Seite
                    series_url = f"{portal_url}?type=series&action=get_ordered_list&movie_id=0&season_id=0&episode_id=0&row=0&JsHttpRequest=1-xml&category={category['id']}&sortby=added&p={page}"
                    
                    try:
                        response = requests.get(series_url, headers=headers, cookies=cookies, proxies=proxies, timeout=60)
                    except Exception as e:
                        logger_ctx.warning(f"  ⚠️ Timeout Seite {page}: {e}")
                        break
                    
                    if response.status_code != 200:
                        break
                    
                    series_items = response.json()["js"]["data"]
                    
                    if not series_items:
                        break
                    
                    logger_ctx.info(f"  📄 Seite {page}: {len(series_items)} Serien")
                    
                    # Batch-Import
                    for item in series_items:
                        if max_items > 0 and category_series >= max_items:
                            break
                        
                        try:
                            series_name = item.get('name', 'Unknown')
                            series_id = item.get('id', '').split(':')[0]
                            
                            # Name-Filter auf Item-Ebene (nur für VOD/Serien)
                            name_filter = settings.get("name_filter", "").strip()
                            if name_filter:
                                search_terms = [term.strip() for term in name_filter.split(",") if term.strip()]
                                if search_terms and not self._matches_name_filter(series_name, search_terms):
                                    continue
                            
                            # Prüfe ob existiert
                            if skip_existing and Series.objects.filter(name=series_name).exists():
                                total_skipped += 1
                                continue
                            
                            # Erstelle oder hole Logo
                            logo = None
                            logo_url = item.get('screenshot_uri', '')
                            if logo_url:
                                logo, _ = VODLogo.objects.get_or_create(
                                    url=logo_url,
                                    defaults={'name': series_name}
                                )
                            
                            # Erstelle Serie mit Metadaten
                            series, _ = Series.objects.get_or_create(
                                name=series_name,
                                defaults={
                                    'logo': logo,
                                    'description': item.get('description', ''),
                                    'year': self._extract_year(item.get('year')),
                                    'rating': self._clean_rating(item.get('rating_imdb')),
                                    'genre': item.get('genre_title', ''),
                                }
                            )
                            
                            # Erstelle Relation mit Flags um Xtream API Refresh zu verhindern
                            from django.utils import timezone
                            M3USeriesRelation.objects.update_or_create(
                                m3u_account=m3u_account,
                                external_series_id=str(series_id),
                                defaults={
                                    'series': series,
                                    'category': vod_category,
                                    'custom_properties': {
                                        'portal_url': portal_url,
                                        'mac': mac,
                                        'episodes_fetched': True,  # Verhindert Xtream API Refresh
                                        'detailed_fetched': True   # Verhindert Xtream API Refresh
                                    },
                                    'last_episode_refresh': timezone.now()  # Verhindert Xtream API Refresh
                                }
                            )
                            
                            total_series += 1
                            category_series += 1
                            
                            # Hole Episoden (nur erste Staffel für Performance)
                            series_episodes = 0
                            try:
                                seasons_url = f"{portal_url}?type=series&action=get_ordered_list&movie_id={series_id}&season_id=0&episode_id=0&row=0&JsHttpRequest=1-xml&category={category['id']}&sortby=added&p=1"
                                seasons_response = requests.get(seasons_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
                                
                                if seasons_response.status_code == 200:
                                    seasons_data = seasons_response.json()["js"]["data"]
                                    
                                    if seasons_data:
                                        logger_ctx.debug(f"    📺 {series_name}: {len(seasons_data)} Staffel(n) gefunden")
                                        
                                        # Alle Staffeln importieren
                                        for season in seasons_data:
                                            season_id_parts = season['id'].split(':')
                                            if len(season_id_parts) >= 2:
                                                season_num = int(season_id_parts[1])
                                            else:
                                                logger_ctx.debug(f"    ⚠️ Ungültige Season-ID: {season['id']}")
                                                continue
                                            
                                            # Episoden sind als Array von Nummern gespeichert
                                            episodes = season.get('series', [])
                                            
                                            if not episodes:
                                                logger_ctx.debug(f"    ⚠️ Keine Episoden in Staffel {season_num}")
                                                continue
                                            
                                            logger_ctx.debug(f"    📺 Staffel {season_num}: {len(episodes)} Episode(n)")
                                            
                                            # Alle Episoden importieren (kein Limit wie im Original)
                                            for episode_num in list(episodes):
                                                try:
                                                    # episode_num ist bereits die Episoden-Nummer (int)
                                                    episode_name = f"{series_name} S{season_num:02d}E{episode_num:02d}"
                                                    
                                                    # Schritt 1: Hole Episode-Details um den cmd zu bekommen
                                                    episode_details_url = f"{portal_url}?type=series&action=get_ordered_list&movie_id={series_id}&season_id={season_num}&episode_id={episode_num}&row=0&JsHttpRequest=1-xml&category={category['id']}&sortby=added&p=1"
                                                    
                                                    ep_response = requests.get(episode_details_url, headers=headers, cookies=cookies, proxies=proxies, timeout=15)
                                                    
                                                    if ep_response.status_code != 200:
                                                        logger_ctx.debug(f"    ⚠️ Fehler beim Abrufen der Episode-Details für {episode_name}: {ep_response.status_code}")
                                                        continue
                                                    
                                                    ep_data = ep_response.json()["js"]["data"]
                                                    if not ep_data or len(ep_data) == 0:
                                                        logger_ctx.debug(f"    ⚠️ Keine Episode-Daten für {episode_name}")
                                                        continue
                                                    
                                                    cmd = ep_data[0].get('cmd', '')
                                                    if not cmd:
                                                        logger_ctx.debug(f"    ⚠️ Kein cmd für {episode_name}")
                                                        continue
                                                    
                                                    # Schritt 2: Hole Stream-URL mit dem cmd
                                                    from urllib.parse import quote
                                                    create_link_url = f"{portal_url}?type=vod&action=create_link&cmd={quote(cmd)}&series={episode_num}"
                                                    
                                                    link_response = requests.get(create_link_url, headers=headers, cookies=cookies, proxies=proxies, timeout=10)
                                                    
                                                    if link_response.status_code != 200:
                                                        logger_ctx.debug(f"    ⚠️ Fehler beim Abrufen der Stream-URL für {episode_name}: {link_response.status_code}")
                                                        continue
                                                    
                                                    link_data = link_response.json()
                                                    stream_cmd = link_data.get('js', {}).get('cmd', '')
                                                    
                                                    if not stream_cmd:
                                                        logger_ctx.debug(f"    ⚠️ Kein stream_cmd für {episode_name}")
                                                        continue
                                                    
                                                    # Extrahiere URL aus cmd (kann "ffmpeg http://..." sein)
                                                    if stream_cmd.startswith('ffmpeg '):
                                                        stream_url = stream_cmd.split(' ', 1)[1]
                                                    else:
                                                        stream_url = stream_cmd
                                                    
                                                    if not stream_url or not stream_url.startswith("http"):
                                                        logger_ctx.debug(f"    ⚠️ Ungültige Stream-URL für {episode_name}: {stream_url}")
                                                        continue
                                                    
                                                    # Erstelle Episode
                                                    episode, _ = Episode.objects.get_or_create(
                                                        series=series,
                                                        season_number=season_num,
                                                        episode_number=episode_num,
                                                        defaults={'name': episode_name}
                                                    )
                                                    
                                                    # Erstelle Relation mit vollständiger Stream-URL
                                                    M3UEpisodeRelation.objects.get_or_create(
                                                        m3u_account=m3u_account,
                                                        episode=episode,
                                                        defaults={
                                                            'stream_id': stream_url,
                                                            'container_extension': '',
                                                            'custom_properties': {
                                                                'mac_portal_stream_url': stream_url,  # Für Monkey Patch
                                                                'cmd': stream_url,  # Für Dispatcharr-MOD native
                                                                'portal_url': portal_url,
                                                                'mac': mac,
                                                            }
                                                        }
                                                    )
                                                    
                                                    total_episodes += 1
                                                    series_episodes += 1
                                                
                                                except Exception as ep_error:
                                                    logger_ctx.debug(f"    ⚠️ Fehler bei Episode {episode_num}: {ep_error}")
                                                    continue
                                        
                                        if series_episodes > 0:
                                            logger_ctx.debug(f"    ✅ {series_episodes} Episode(n) importiert")
                                    else:
                                        logger_ctx.debug(f"    ⚠️ Keine Staffel-Daten für {series_name}")
                                        
                            except Exception as e:
                                logger_ctx.warning(f"    ⚠️ Fehler bei Episoden für {series_name}: {e}")
                                import traceback
                                logger_ctx.debug(traceback.format_exc())
                            
                        except Exception as e:
                            logger_ctx.debug(f"Fehler: {e}")
                            continue
                    
                    if not use_pagination:
                        break
                    
                    page += 1
                
                logger_ctx.info(f"  ✅ {category_series} Serien importiert")
            
            logger_ctx.info(f"🎉 Import abgeschlossen: {total_series} Serien, {total_episodes} Episoden, {total_skipped} übersprungen")
            
            return {
                "status": "success",
                "message": f"✅ {total_series} Serien, {total_episodes} Episoden importiert, {total_skipped} übersprungen",
                "total_series": total_series,
                "total_episodes": total_episodes,
                "total_skipped": total_skipped,
                "method": "direct",
                "pagination_used": use_pagination
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _import_series_m3u(self, portal_url, mac, proxy, portal_name, country_filter, settings, logger_ctx):
        """
        Generiert M3U-Datei für Serien und erstellt M3U-Account.
        
        ⚠️ WARNUNG: M3U-Import ist SEHR LANGSAM!
        - Muss für jede Episode Stream-URL vorab holen
        - 100 Serien mit je 10 Episoden = ~1000 API-Calls = ~30 Minuten
        
        💡 EMPFEHLUNG: Nutze Direkt-Import (viel schneller!)
        """
        logger_ctx.info(f"📺 Serien M3U-Import vom Portal: {portal_name}")
        logger_ctx.warning("⚠️ M3U-Import ist SEHR LANGSAM! Direkt-Import ist schneller!")
        
        # Pagination ist immer aktiviert
        use_pagination = True
        max_items = settings.get("max_items_per_category", 0)
        
        logger_ctx.info(f"⚙️ Max Items: {max_items or 'Alle'}")
        
        try:
            import os
            from apps.m3u.models import M3UAccount
            
            # Hole Token
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return {"status": "error", "message": "Konnte Token nicht abrufen"}
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            proxies = {"http": proxy, "https": proxy} if proxy else None
            cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
            headers = {
                "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
                "Authorization": f"Bearer {token}",
            }
            
            # Hole Serien-Kategorien
            series_cat_url = f"{portal_url}?type=series&action=get_categories&JsHttpRequest=1-xml"
            response = requests.get(series_cat_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "error", "message": "Fehler beim Abrufen der Serien-Kategorien"}
            
            series_categories = response.json()["js"]
            
            # Filtere nach Ländercode
            if country_filter:
                allowed_countries = [c.strip().upper() for c in country_filter.split(",") if c.strip()]
                series_categories = [cat for cat in series_categories 
                                    if cat['id'] != "*" and self._matches_country_filter(cat['title'], allowed_countries)]
            
            logger_ctx.info(f"📁 {len(series_categories)} Kategorien gefunden")
            
            # Generiere M3U-Content
            m3u_lines = ['#EXTM3U']
            total_series = 0
            total_episodes = 0
            
            safe_portal_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in portal_name)
            
            # Sammle Serien & Episoden pro Kategorie
            for cat_idx, category in enumerate(series_categories, 1):
                if category['id'] == "*":
                    continue
                
                logger_ctx.info(f"📁 [{cat_idx}/{len(series_categories)}] {category['title']}")
                
                category_series = 0
                page = 1
                
                while True:
                    if max_items > 0 and category_series >= max_items:
                        logger_ctx.info(f"  ⏹️ Limit erreicht ({max_items} Serien)")
                        break
                    
                    # Hole Seite
                    series_url = f"{portal_url}?type=series&action=get_ordered_list&movie_id=0&season_id=0&episode_id=0&row=0&JsHttpRequest=1-xml&category={category['id']}&sortby=added&p={page}"
                    
                    try:
                        response = requests.get(series_url, headers=headers, cookies=cookies, proxies=proxies, timeout=60)
                    except Exception as e:
                        logger_ctx.warning(f"  ⚠️ Timeout Seite {page}: {e}")
                        break
                    
                    if response.status_code != 200:
                        break
                    
                    series_items = response.json()["js"]["data"]
                    
                    if not series_items:
                        break
                    
                    logger_ctx.info(f"  📄 Seite {page}: {len(series_items)} Serien")
                    logger_ctx.info(f"  ⏳ Hole Episoden-URLs (kann lange dauern)...")
                    
                    # Verarbeite Serien
                    for item in series_items:
                        if max_items > 0 and category_series >= max_items:
                            break
                        
                        try:
                            series_name = item.get('name', 'Unknown')
                            series_id = item.get('id', '').split(':')[0]
                            logo = item.get('screenshot_uri', '')
                            
                            # Name-Filter auf Item-Ebene (nur für VOD/Serien)
                            name_filter = settings.get("name_filter", "").strip()
                            if name_filter:
                                search_terms = [term.strip() for term in name_filter.split(",") if term.strip()]
                                if search_terms and not self._matches_name_filter(series_name, search_terms):
                                    continue
                            
                            # Hole Episoden (nur erste Staffel)
                            seasons_url = f"{portal_url}?type=series&action=get_ordered_list&movie_id={series_id}&season_id=0&episode_id=0&row=0&JsHttpRequest=1-xml&category={category['id']}&sortby=added&p=1"
                            
                            try:
                                seasons_response = requests.get(seasons_url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
                                
                                if seasons_response.status_code == 200:
                                    seasons_data = seasons_response.json()["js"]["data"]
                                    
                                    if not seasons_data:
                                        continue
                                    
                                    # Alle Staffeln importieren
                                    for season in seasons_data:
                                        season_id_parts = season['id'].split(':')
                                        if len(season_id_parts) >= 2:
                                            season_num = int(season_id_parts[1])
                                        else:
                                            continue
                                        
                                        # Episoden sind als Array von Nummern gespeichert
                                        episodes = season.get('series', [])
                                        
                                        if not episodes:
                                            continue
                                        
                                        # Alle Episoden importieren (kein Limit wie im Original)
                                        for episode_num in list(episodes):
                                            try:
                                                episode_name = f"{series_name} S{season_num:02d}E{episode_num:02d}"
                                                episode_id = f"{series_id}:{season_num}:{episode_num}"
                                                
                                                # Hole Stream-URL (LANGSAM!)
                                                stream_url_response = requests.get(
                                                    f"{portal_url}?type=series&action=create_link&cmd={episode_id}&JsHttpRequest=1-xml",
                                                    headers=headers, cookies=cookies, proxies=proxies, timeout=10
                                                )
                                                
                                                if stream_url_response.status_code != 200:
                                                    continue
                                                
                                                stream_cmd = stream_url_response.json()["js"].get("cmd", "")
                                                if not stream_cmd:
                                                    continue
                                                
                                                # Extrahiere URL aus cmd
                                                stream_url = stream_cmd.split()[-1]
                                                
                                                if not stream_url or not stream_url.startswith("http"):
                                                    continue
                                            
                                            except Exception as ep_error:
                                                logger_ctx.debug(f"    ⚠️ Fehler bei Episode {episode_num}: {ep_error}")
                                                continue
                                            
                                            # Erstelle EXTINF-Zeile
                                            extinf_parts = ['#EXTINF:-1']
                                            
                                            # Metadaten
                                            extinf_parts.append(f'tvg-id="{safe_portal_name.lower().replace(" ", "_")}_{series_id}_{season_num}_{episode_num}"')
                                            extinf_parts.append(f'tvg-name="{episode_name}"')
                                            
                                            if logo:
                                                extinf_parts.append(f'tvg-logo="{logo}"')
                                            
                                            extinf_parts.append(f'group-title="{category["title"]}"')
                                            
                                            # Custom Properties
                                            extinf_parts.append(f'mac-portal-id="{episode_id}"')
                                            extinf_parts.append(f'mac-portal-name="{portal_name}"')
                                            
                                            extinf_line = ' '.join(extinf_parts) + f',{episode_name}'
                                            m3u_lines.append(extinf_line)
                                            m3u_lines.append(stream_url)
                                            
                                            total_episodes += 1
                                    
                                    total_series += 1
                                    category_series += 1
                                    
                            except Exception as e:
                                logger_ctx.debug(f"Fehler bei Episoden: {e}")
                                continue
                            
                        except Exception as e:
                            logger_ctx.debug(f"Fehler: {e}")
                            continue
                    
                    if not use_pagination:
                        break
                    
                    page += 1
                
                logger_ctx.info(f"  ✅ {category_series} Serien hinzugefügt")
            
            m3u_content = '\n'.join(m3u_lines)
            
            # Speichere M3U-Datei
            output_dir = "/app/sources"
            if not os.path.exists(output_dir):
                output_dir = os.path.join(os.getcwd(), "sources")
                os.makedirs(output_dir, exist_ok=True)
            
            safe_filename = safe_portal_name.replace(' ', '_')
            output_file = os.path.join(output_dir, f"{safe_filename}_series.m3u")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(m3u_content)
            
            logger_ctx.info(f"✅ M3U-Datei gespeichert: {output_file}")
            
            # Erstelle M3U-Account in Dispatcharr
            account_name = f"MAC Portal Serien - {portal_name}"
            
            existing_account = M3UAccount.objects.filter(name=account_name).first()
            
            if existing_account:
                logger_ctx.info(f"Account existiert bereits, aktualisiere: {account_name}")
                existing_account.url = f"file://{output_file}"
                
                # MOD-Support: Update proxy in BEIDEN Feldern
                if proxy:
                    if hasattr(existing_account, 'proxy'):
                        existing_account.proxy = proxy
                    if hasattr(existing_account, 'proxy_std_xc'):
                        existing_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account aktualisiert: {proxy}")
                
                existing_account.save()
                account_id = existing_account.id
            else:
                logger_ctx.info(f"Erstelle neuen M3U-Account: {account_name}")
                new_account = M3UAccount(name=account_name)
                
                # Setze Account-Type
                if hasattr(new_account, 'account_type'):
                    new_account.account_type = 'STD'
                
                # Setze URL/Path
                if hasattr(new_account, 'url'):
                    new_account.url = f"file://{output_file}"
                elif hasattr(new_account, 'file_path'):
                    new_account.file_path = output_file
                elif hasattr(new_account, 'path'):
                    new_account.path = output_file
                
                # MOD-Support: Setze proxy in BEIDEN Feldern
                if proxy:
                    if hasattr(new_account, 'proxy'):
                        new_account.proxy = proxy
                    if hasattr(new_account, 'proxy_std_xc'):
                        new_account.proxy_std_xc = proxy
                    logger_ctx.info(f"✅ Proxy für M3U Account gesetzt: {proxy}")
                
                new_account.save()
                account_id = new_account.id
            
            logger_ctx.info(f"✅ M3U-Account erstellt/aktualisiert: {account_name} (ID: {account_id})")
            
            # Trigger Refresh
            try:
                from apps.m3u.tasks import refresh_m3u_account
                refresh_m3u_account.delay(account_id)
                logger_ctx.info(f"✅ Refresh-Task gestartet für Account {account_id}")
            except Exception as refresh_error:
                logger_ctx.debug(f"Konnte Refresh-Task nicht starten: {refresh_error}")
            
            logger_ctx.info(f"🎉 M3U-Import abgeschlossen: {total_series} Serien, {total_episodes} Episoden")
            
            return {
                "status": "success",
                "message": f"✅ M3U-Datei mit {total_series} Serien, {total_episodes} Episoden erstellt (⚠️ Nutze Direkt-Import für schnelleren Import!)",
                "total_series": total_series,
                "total_episodes": total_episodes,
                "account_id": account_id,
                "account_name": account_name,
                "file_path": output_file,
                "method": "m3u",
                "pagination_used": use_pagination
            }
            
        except Exception as e:
            logger_ctx.error(f"Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def _show_account_info(self, portal_name, logger_ctx):
        """
        Zeigt Basis-MAC und alle Profile des M3U Accounts an.
        """
        logger_ctx.info(f"ℹ️ Account-Info für: {portal_name}")
        
        try:
            from apps.m3u.models import M3UAccount, M3UAccountProfile
            import re
            
            # Suche M3U Account mit exakt dem gleichen Namen
            account = M3UAccount.objects.filter(name=portal_name).first()
            
            if not account:
                logger_ctx.error(f"❌ Kein M3U Account mit Name '{portal_name}' gefunden!")
                logger_ctx.info("💡 Verfügbare M3U Accounts:")
                
                all_accounts = M3UAccount.objects.all()
                for acc in all_accounts:
                    logger_ctx.info(f"   - '{acc.name}'")
                
                return {
                    "status": "error",
                    "message": f"Kein M3U Account mit Name '{portal_name}' gefunden."
                }
            
            logger_ctx.info(f"✅ M3U Account gefunden: {account.name} (ID: {account.id})")
            
            # Extrahiere Basis-MAC
            base_mac = None
            detection_method = None
            
            # Methode 1: Aus username
            if hasattr(account, 'username') and account.username:
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, account.username)
                if match:
                    base_mac = match.group(0)
                    detection_method = "username"
            
            # Methode 2: Aus server_url
            if not base_mac and hasattr(account, 'server_url') and account.server_url:
                mac_pattern = r'mac=([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, account.server_url)
                if match:
                    base_mac = match.group(0).replace('mac=', '')
                    detection_method = "server_url"
            
            # Methode 3: Aus file_path (M3U-Datei lesen)
            if not base_mac and hasattr(account, 'file_path') and account.file_path:
                try:
                    import os
                    if os.path.exists(account.file_path):
                        with open(account.file_path, 'r', encoding='utf-8') as f:
                            for i, line in enumerate(f):
                                if i > 50:
                                    break
                                mac_pattern = r'mac=([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
                                match = re.search(mac_pattern, line)
                                if match:
                                    base_mac = match.group(0).replace('mac=', '')
                                    detection_method = "M3U-Datei"
                                    break
                except Exception as e:
                    logger_ctx.debug(f"Konnte M3U-Datei nicht lesen: {e}")
            
            # Hole alle Profile
            profiles = M3UAccountProfile.objects.filter(m3u_account=account).order_by('name')
            
            # Ausgabe
            logger_ctx.info("")
            logger_ctx.info("=" * 60)
            logger_ctx.info(f"Account: {account.name}")
            logger_ctx.info("=" * 60)
            
            if base_mac:
                logger_ctx.info(f"🔍 Basis-MAC (Default): {base_mac}")
                logger_ctx.info(f"   Erkannt aus: {detection_method}")
            else:
                logger_ctx.info("⚠️ Basis-MAC konnte nicht erkannt werden")
            
            logger_ctx.info("")
            logger_ctx.info(f"📋 Profile: {profiles.count()}")
            
            if profiles.count() > 0:
                logger_ctx.info("")
                for profile in profiles:
                    status = "✅ Aktiv" if profile.is_active else "❌ Inaktiv"
                    logger_ctx.info(f"  Profil '{profile.name}': {status}")
                    logger_ctx.info(f"    Search:  {profile.search_pattern}")
                    logger_ctx.info(f"    Replace: {profile.replace_pattern}")
                    logger_ctx.info(f"    Max Streams: {profile.max_streams}")
                    logger_ctx.info("")
            else:
                logger_ctx.info("  (Keine Profile vorhanden)")
            
            logger_ctx.info("=" * 60)
            
            return {
                "status": "success",
                "message": f"Account '{account.name}' hat {profiles.count()} Profile",
                "account_id": account.id,
                "account_name": account.name,
                "base_mac": base_mac,
                "detection_method": detection_method,
                "profile_count": profiles.count(),
                "profiles": [
                    {
                        "name": p.name,
                        "search_pattern": p.search_pattern,
                        "replace_pattern": p.replace_pattern,
                        "is_active": p.is_active,
                        "max_streams": p.max_streams
                    }
                    for p in profiles
                ]
            }
            
        except Exception as e:
            logger_ctx.error(f"❌ Fehler: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _remove_profiles(self, portal_name, logger_ctx):
        """
        Löscht ALLE Profile (außer Default) vom M3U Account.
        """
        logger_ctx.info(f"🗑️ Lösche Profile von Account: {portal_name}")
        
        try:
            from apps.m3u.models import M3UAccount, M3UAccountProfile
            
            # Suche M3U Account mit exakt dem gleichen Namen
            account = M3UAccount.objects.filter(name=portal_name).first()
            
            if not account:
                logger_ctx.error(f"❌ Kein M3U Account mit Name '{portal_name}' gefunden!")
                logger_ctx.info("💡 Verfügbare M3U Accounts:")
                
                all_accounts = M3UAccount.objects.all()
                for acc in all_accounts:
                    logger_ctx.info(f"   - '{acc.name}'")
                
                return {
                    "status": "error",
                    "message": f"Kein M3U Account mit Name '{portal_name}' gefunden."
                }
            
            logger_ctx.info(f"✅ M3U Account gefunden: {account.name} (ID: {account.id})")
            
            # Hole alle Profile
            profiles = M3UAccountProfile.objects.filter(m3u_account=account)
            profile_count = profiles.count()
            
            if profile_count == 0:
                logger_ctx.info("ℹ️ Keine Profile vorhanden zum Löschen")
                return {
                    "status": "success",
                    "message": "Keine Profile vorhanden",
                    "deleted_count": 0
                }
            
            logger_ctx.info(f"📋 Gefunden: {profile_count} Profile")
            logger_ctx.info("")
            
            # Liste Profile vor dem Löschen
            for profile in profiles:
                logger_ctx.info(f"  🗑️ Lösche Profil '{profile.name}': {profile.search_pattern} → {profile.replace_pattern}")
            
            # Lösche alle Profile
            deleted_count = profiles.delete()[0]
            
            logger_ctx.info("")
            logger_ctx.info("=" * 60)
            logger_ctx.info(f"✅ {deleted_count} Profile gelöscht von Account: {account.name}")
            logger_ctx.info("=" * 60)
            
            return {
                "status": "success",
                "message": f"✅ {deleted_count} Profile gelöscht von Account '{account.name}'",
                "account_id": account.id,
                "account_name": account.name,
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger_ctx.error(f"❌ Fehler beim Löschen der Profile: {e}")
            import traceback
            logger_ctx.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
