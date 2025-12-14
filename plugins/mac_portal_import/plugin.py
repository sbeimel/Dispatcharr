"""
MAC Portal Import Plugin für Dispatcharr.

Ermöglicht das schnelle Importieren von Stalker/STB Portal-Daten mit automatischer
Profil-Erstellung für MAC-Failover.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .stb_client import STBClient
from .utils import (
    MACNormalizer,
    MACValidator,
    StreamLinkGenerator,
    ChannelFetcher,
)

logger = logging.getLogger(__name__)


class M3UGenerator:
    """Generiert M3U-Playlists aus Portal-Daten."""
    
    @staticmethod
    def generate(
        channels: List[Dict[str, Any]],
        genres: Dict[str, str],
        mac: str,
        portal_name: str
    ) -> str:
        """
        Generiert M3U-Content aus Kanal-Daten.
        
        Args:
            channels: Liste von Kanal-Daten
            genres: Dict mit genre_id → genre_name
            mac: MAC-Adresse für Stream-URLs
            portal_name: Name des Portals für tvg-id
            
        Returns:
            M3U-Content als String
        """
        safe_portal_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_' 
            for c in portal_name
        ).strip()
        
        m3u_lines = ["#EXTM3U"]
        
        for channel in channels:
            channel_id = str(channel.get("id", ""))
            channel_name = str(channel.get("name", ""))
            channel_number = str(channel.get("number", ""))
            genre_id = str(channel.get("tv_genre_id", ""))
            genre_name = genres.get(genre_id, "Uncategorized")
            logo = str(channel.get("logo", ""))
            cmd = str(channel.get("cmd", ""))
            
            # Erstelle EXTINF-Zeile
            extinf_parts = ['#EXTINF:-1']
            
            if channel_number:
                extinf_parts.append(f'tvg-chno="{channel_number}"')
            
            tvg_id = f"{safe_portal_name.lower().replace(' ', '_')}_{channel_id}"
            extinf_parts.append(f'tvg-id="{tvg_id}"')
            
            if channel_name:
                extinf_parts.append(f'tvg-name="{channel_name}"')
            
            if logo:
                extinf_parts.append(f'tvg-logo="{logo}"')
            
            if genre_name:
                extinf_parts.append(f'group-title="{genre_name}"')
            
            extinf_line = ' '.join(extinf_parts) + f',{channel_name}'
            
            # Extrahiere Stream-URL
            stream_url = StreamLinkGenerator.extract_url_from_cmd(cmd)
            
            if stream_url:
                m3u_lines.append(extinf_line)
                m3u_lines.append(stream_url)
            else:
                logger.debug(f"Überspringe Kanal {channel_id} ohne gültige Stream-URL")
        
        return '\n'.join(m3u_lines)


class Plugin:
    """
    MAC Portal Import Plugin für Dispatcharr.
    
    Ermöglicht:
    - MAC-Adressen-Normalisierung und -Validierung
    - Kanal-Abruf von Stalker/STB Portalen
    - M3U-Generierung mit automatischer Profil-Erstellung
    """
    
    name = "MAC Portal Import"
    version = "1.0.0"
    description = "Importiert Stalker/STB Portal-Daten mit automatischer Profil-Erstellung für MAC-Failover"
    
    fields = [
        {
            "id": "portal_name",
            "label": "Portal Name",
            "type": "string",
            "default": "",
            "help_text": "Name des IPTV-Portals (wird für M3U-Account verwendet)"
        },
        {
            "id": "portal_url",
            "label": "Portal URL",
            "type": "string",
            "default": "",
            "help_text": "URL des STB/Stalker-Portals (z.B. http://example.com/stalker_portal/)"
        },
        {
            "id": "mac_addresses",
            "label": "MAC-Adressen",
            "type": "string",
            "default": "",
            "help_text": "MAC-Adressen (Leerzeichen, Komma oder Zeilenumbruch getrennt)"
        },
        {
            "id": "proxy",
            "label": "Proxy (optional)",
            "type": "string",
            "default": "",
            "help_text": "HTTP-Proxy für Requests (z.B. http://proxy:8080)"
        },
    ]
    
    actions = [
        {
            "id": "normalize_macs",
            "label": "MACs normalisieren",
            "description": "Normalisiert MAC-Adressen zu einer pro Zeile",
        },
        {
            "id": "validate_macs",
            "label": "MACs validieren",
            "description": "Prüft alle MAC-Adressen gegen das Portal",
        },
        {
            "id": "fetch_channels",
            "label": "Kanäle abrufen",
            "description": "Ruft alle verfügbaren Kanäle vom Portal ab",
        },
        {
            "id": "import_portal",
            "label": "Portal importieren",
            "description": "Importiert Portal-Daten und erstellt M3U-Account mit Profilen",
        },
    ]
    
    def __init__(self):
        self.stb_client = STBClient()
    
    def run(self, action: str, params: dict, context: dict) -> Dict[str, Any]:
        """
        Führt eine Plugin-Aktion aus.
        
        Args:
            action: Aktions-ID
            params: Aktions-Parameter
            context: Kontext mit settings und logger
            
        Returns:
            Ergebnis-Dict
        """
        settings = context.get("settings", {})
        logger_ctx = context.get("logger", logger)
        
        portal_name = settings.get("portal_name", "").strip()
        portal_url = settings.get("portal_url", "").strip()
        mac_addresses = settings.get("mac_addresses", "").strip()
        proxy = settings.get("proxy", "").strip() or None
        
        # Aktionen ausführen
        if action == "normalize_macs":
            return self._normalize_macs(mac_addresses, logger_ctx)
        
        elif action == "validate_macs":
            return self._validate_macs(portal_url, mac_addresses, proxy, logger_ctx)
        
        elif action == "fetch_channels":
            return self._fetch_channels(portal_url, mac_addresses, proxy, logger_ctx)
        
        elif action == "import_portal":
            return self._import_portal(
                portal_name, portal_url, mac_addresses, proxy, logger_ctx
            )
        
        return {"status": "error", "message": f"Unbekannte Aktion: {action}"}
    
    def _normalize_macs(
        self, 
        mac_addresses: str, 
        logger_ctx: logging.Logger
    ) -> Dict[str, Any]:
        """Normalisiert MAC-Adressen."""
        logger_ctx.info("Normalisiere MAC-Adressen")
        
        macs = MACNormalizer.normalize(mac_addresses)
        
        if not macs:
            return {
                "status": "error",
                "message": "Keine gültigen MAC-Adressen gefunden"
            }
        
        return {
            "status": "success",
            "message": f"{len(macs)} MAC-Adressen normalisiert",
            "macs": macs,
            "normalized": MACNormalizer.format_for_display(macs)
        }
    
    def _validate_macs(
        self,
        portal_url: str,
        mac_addresses: str,
        proxy: Optional[str],
        logger_ctx: logging.Logger
    ) -> Dict[str, Any]:
        """Validiert MAC-Adressen gegen das Portal."""
        if not portal_url:
            return {"status": "error", "message": "Portal URL ist erforderlich"}
        
        macs = MACNormalizer.normalize(mac_addresses)
        if not macs:
            return {"status": "error", "message": "Keine gültigen MAC-Adressen gefunden"}
        
        logger_ctx.info(f"Validiere {len(macs)} MAC-Adressen gegen {portal_url}")
        
        # Portal-URL ermitteln wenn nötig
        if not portal_url.endswith(".php"):
            detected_url = self.stb_client.get_portal_url(portal_url, proxy)
            if detected_url:
                portal_url = detected_url
                logger_ctx.info(f"Portal-URL erkannt: {portal_url}")
            else:
                return {"status": "error", "message": "Konnte Portal-URL nicht ermitteln"}
        
        # MACs validieren
        validator = MACValidator(self.stb_client)
        results = validator.validate_all(portal_url, macs, proxy)
        
        valid_macs = validator.get_valid_macs(results)
        invalid_count = len(macs) - len(valid_macs)
        
        return {
            "status": "success" if valid_macs else "error",
            "message": f"{len(valid_macs)}/{len(macs)} MAC-Adressen gültig",
            "valid_count": len(valid_macs),
            "invalid_count": invalid_count,
            "valid_macs": valid_macs,
            "results": [
                {
                    "mac": r.mac,
                    "valid": r.valid,
                    "expired": r.expired,
                    "expiry": r.expiry_date,
                    "error": r.error
                }
                for r in results
            ]
        }
    
    def _fetch_channels(
        self,
        portal_url: str,
        mac_addresses: str,
        proxy: Optional[str],
        logger_ctx: logging.Logger
    ) -> Dict[str, Any]:
        """Ruft Kanäle vom Portal ab."""
        if not portal_url:
            return {"status": "error", "message": "Portal URL ist erforderlich"}
        
        macs = MACNormalizer.normalize(mac_addresses)
        if not macs:
            return {"status": "error", "message": "Keine gültigen MAC-Adressen gefunden"}
        
        logger_ctx.info(f"Rufe Kanäle ab von {portal_url}")
        
        # Portal-URL ermitteln
        if not portal_url.endswith(".php"):
            detected_url = self.stb_client.get_portal_url(portal_url, proxy)
            if detected_url:
                portal_url = detected_url
            else:
                return {"status": "error", "message": "Konnte Portal-URL nicht ermitteln"}
        
        # Mit erster funktionierender MAC versuchen
        for mac in macs:
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                continue
            
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            fetcher = ChannelFetcher(self.stb_client)
            data = fetcher.fetch_all(portal_url, mac, token, proxy)
            
            channels = data.get('channels', [])
            genres = data.get('genres', {})
            
            if channels:
                stats = fetcher.get_genre_statistics(channels, genres)
                
                return {
                    "status": "success",
                    "message": f"{len(channels)} Kanäle in {len(stats)} Gruppen gefunden",
                    "channel_count": len(channels),
                    "genre_count": len(stats),
                    "genres": stats,
                    "mac_used": mac
                }
        
        return {"status": "error", "message": "Konnte Kanäle mit keiner MAC abrufen"}
    
    def _import_portal(
        self,
        portal_name: str,
        portal_url: str,
        mac_addresses: str,
        proxy: Optional[str],
        logger_ctx: logging.Logger
    ) -> Dict[str, Any]:
        """Importiert Portal-Daten und erstellt M3U-Account mit Profilen."""
        if not portal_name:
            return {"status": "error", "message": "Portal Name ist erforderlich"}
        if not portal_url:
            return {"status": "error", "message": "Portal URL ist erforderlich"}
        
        macs = MACNormalizer.normalize(mac_addresses)
        if not macs:
            return {"status": "error", "message": "Keine gültigen MAC-Adressen gefunden"}
        
        logger_ctx.info(f"Importiere Portal: {portal_name}")
        
        # Portal-URL ermitteln
        if not portal_url.endswith(".php"):
            detected_url = self.stb_client.get_portal_url(portal_url, proxy)
            if detected_url:
                portal_url = detected_url
            else:
                return {"status": "error", "message": "Konnte Portal-URL nicht ermitteln"}
        
        # MACs validieren
        validator = MACValidator(self.stb_client)
        results = validator.validate_all(portal_url, macs, proxy)
        valid_macs = validator.get_valid_macs(results)
        
        if not valid_macs:
            return {
                "status": "error",
                "message": "Keine gültigen MAC-Adressen gefunden",
                "results": [
                    {"mac": r.mac, "valid": r.valid, "error": r.error}
                    for r in results
                ]
            }
        
        logger_ctx.info(f"{len(valid_macs)} gültige MACs gefunden")
        
        # Kanäle abrufen mit erster gültiger MAC
        first_mac = valid_macs[0]
        token = self.stb_client.get_token(portal_url, first_mac, proxy)
        if not token:
            return {"status": "error", "message": "Konnte Token nicht abrufen"}
        
        self.stb_client.get_profile(portal_url, first_mac, token, proxy)
        
        fetcher = ChannelFetcher(self.stb_client)
        data = fetcher.fetch_all(portal_url, first_mac, token, proxy)
        
        channels = data.get('channels', [])
        genres = data.get('genres', {})
        
        if not channels:
            return {"status": "error", "message": "Keine Kanäle gefunden"}
        
        logger_ctx.info(f"{len(channels)} Kanäle gefunden")
        
        # M3U generieren
        m3u_content = M3UGenerator.generate(channels, genres, first_mac, portal_name)
        
        # M3U-Datei speichern
        safe_name = portal_name.replace(' ', '_').replace('/', '_')
        output_dir = os.environ.get("DISPATCHARR_DATA_DIR", "/data")
        m3u_dir = os.path.join(output_dir, "m3u_imports")
        os.makedirs(m3u_dir, exist_ok=True)
        
        m3u_file = os.path.join(m3u_dir, f"{safe_name}_mac_import.m3u")
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        logger_ctx.info(f"M3U gespeichert: {m3u_file}")
        
        # Versuche M3U-Account und Profile zu erstellen
        account_id = None
        profiles_created = 0
        
        try:
            account_id, profiles_created = self._create_account_and_profiles(
                portal_name, portal_url, first_mac, valid_macs, m3u_file, logger_ctx
            )
        except Exception as e:
            logger_ctx.warning(f"Konnte Account/Profile nicht erstellen: {e}")
        
        # Genre-Statistiken
        stats = fetcher.get_genre_statistics(channels, genres)
        
        return {
            "status": "success",
            "message": f"Portal importiert: {len(channels)} Kanäle, {profiles_created} Profile",
            "account_id": account_id,
            "account_name": f"{portal_name} (MAC Import)",
            "m3u_file": m3u_file,
            "channel_count": len(channels),
            "genre_count": len(stats),
            "genres": stats,
            "valid_macs": valid_macs,
            "invalid_macs": [r.mac for r in results if not r.valid],
            "profiles_created": profiles_created,
            "validation_results": [
                {"mac": r.mac, "valid": r.valid, "expiry": r.expiry_date, "error": r.error}
                for r in results
            ]
        }
    
    def _create_account_and_profiles(
        self,
        portal_name: str,
        portal_url: str,
        first_mac: str,
        valid_macs: List[str],
        m3u_file: str,
        logger_ctx: logging.Logger
    ) -> tuple:
        """
        Erstellt M3U-Account und Profile in Dispatcharr.
        
        Returns:
            Tuple (account_id, profiles_created)
        """
        try:
            from apps.m3u.models import M3UAccount, M3UAccountProfile
        except ImportError:
            logger_ctx.warning("Django Models nicht verfügbar")
            return None, 0
        
        account_name = f"{portal_name} (MAC Import)"
        
        # Account erstellen oder aktualisieren
        account, created = M3UAccount.objects.get_or_create(
            name=account_name,
            defaults={
                'account_type': 'mac',
            }
        )
        
        # Felder setzen
        if hasattr(account, 'url'):
            account.url = f"file://{m3u_file}"
        if hasattr(account, 'portal_url'):
            account.portal_url = portal_url
        if hasattr(account, 'primary_mac'):
            account.primary_mac = first_mac
        
        account.save()
        logger_ctx.info(f"M3U-Account {'erstellt' if created else 'aktualisiert'}: {account_name}")
        
        # Bestehende Profile löschen
        M3UAccountProfile.objects.filter(m3u_account=account).delete()
        
        # Profile für jede gültige MAC erstellen
        profiles_created = 0
        for i, mac in enumerate(valid_macs):
            profile_name = f"{portal_name} MAC {i + 1}"
            
            M3UAccountProfile.objects.create(
                m3u_account=account,
                name=profile_name,
                max_connections=1,
                search_pattern=first_mac,
                replace_pattern=mac,
                enabled=True
            )
            profiles_created += 1
            logger_ctx.info(f"Profil erstellt: {profile_name}")
        
        # Refresh triggern
        try:
            from apps.m3u.tasks import refresh_m3u_account
            refresh_m3u_account.delay(account.id)
            logger_ctx.info(f"Refresh-Task gestartet für Account {account.id}")
        except Exception as e:
            logger_ctx.debug(f"Konnte Refresh nicht starten: {e}")
        
        return account.id, profiles_created
