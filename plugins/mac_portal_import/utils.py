"""
Utility-Klassen für MAC Portal Import.

Enthält:
- MACNormalizer: Normalisiert MAC-Adressen aus verschiedenen Eingabeformaten
- MACValidator: Validiert MAC-Adressen gegen ein Portal
- StreamLinkGenerator: Generiert direkte Stream-Links
- ChannelFetcher: Ruft Kanäle und Gruppen vom Portal ab
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MACNormalizer:
    """
    Normalisiert MAC-Adressen aus verschiedenen Eingabeformaten.
    
    Unterstützte Eingabeformate:
    - "00:1a:79:19:1F:A9 00:1a:79:19:1F:B9" (Leerzeichen)
    - "00:1a:79:19:1F:A9,00:1a:79:19:1F:B9" (Komma)
    - "00:1a:79:19:1F:A9, 00:1a:79:19:1F:B9" (Komma + Leerzeichen)
    - Gemischte Formate
    - Mit Bindestrichen: "00-1a-79-19-1F-A9"
    """
    
    # Regex für MAC-Adressen (mit : oder - als Separator)
    MAC_PATTERN = re.compile(r'([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}')
    
    @classmethod
    def normalize(cls, input_text: str) -> List[str]:
        """
        Normalisiert MAC-Adressen aus verschiedenen Formaten.
        
        Args:
            input_text: Eingabetext mit MAC-Adressen
            
        Returns:
            Liste von normalisierten MACs (uppercase, mit Doppelpunkten)
        """
        if not input_text:
            return []
        
        result = []
        for match in cls.MAC_PATTERN.finditer(input_text):
            mac = match.group(0).upper().replace('-', ':')
            if mac not in result:  # Duplikate entfernen
                result.append(mac)
        
        return result
    
    @classmethod
    def validate_format(cls, mac: str) -> bool:
        """
        Validiert das Format einer einzelnen MAC-Adresse.
        
        Args:
            mac: MAC-Adresse zum Validieren
            
        Returns:
            True wenn Format gültig, sonst False
        """
        return bool(cls.MAC_PATTERN.fullmatch(mac))
    
    @classmethod
    def format_for_display(cls, macs: List[str]) -> str:
        """
        Formatiert MAC-Adressen für Anzeige (eine pro Zeile).
        
        Args:
            macs: Liste von MAC-Adressen
            
        Returns:
            String mit einer MAC pro Zeile
        """
        return '\n'.join(macs)


@dataclass
class MACValidationResult:
    """Ergebnis der MAC-Validierung."""
    mac: str
    valid: bool
    expired: bool = False
    expiry_date: Optional[str] = None
    error: Optional[str] = None


class MACValidator:
    """
    Validiert MAC-Adressen gegen ein Portal.
    
    Prüft:
    - Token-Abruf möglich
    - Ablaufdatum vorhanden und nicht abgelaufen
    """
    
    # Unterstützte Datumsformate für Expiry
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%d.%m.%Y',
        '%Y-%m-%d %H:%M:%S',
        '%d.%m.%Y %H:%M:%S',
        '%Y/%m/%d',
        '%d/%m/%Y',
    ]
    
    def __init__(self, stb_client: Any):
        """
        Args:
            stb_client: STBClient-Instanz für Portal-Kommunikation
        """
        self.stb_client = stb_client
    
    def validate_mac(
        self, 
        portal_url: str, 
        mac: str, 
        proxy: Optional[str] = None
    ) -> MACValidationResult:
        """
        Validiert eine einzelne MAC-Adresse.
        
        Args:
            portal_url: Portal-URL
            mac: MAC-Adresse
            proxy: Optional HTTP-Proxy
            
        Returns:
            MACValidationResult mit Validierungsergebnis
        """
        try:
            # Token abrufen
            token = self.stb_client.get_token(portal_url, mac, proxy)
            if not token:
                return MACValidationResult(
                    mac=mac,
                    valid=False,
                    error="Token konnte nicht abgerufen werden"
                )
            
            # Profil abrufen (für manche Portale erforderlich)
            self.stb_client.get_profile(portal_url, mac, token, proxy)
            
            # Ablaufdatum abrufen
            expiry = self.stb_client.get_expires(portal_url, mac, token, proxy)
            if not expiry:
                return MACValidationResult(
                    mac=mac,
                    valid=False,
                    error="Ablaufdatum nicht verfügbar"
                )
            
            # Prüfe ob abgelaufen
            is_expired = self._check_expired(expiry)
            
            return MACValidationResult(
                mac=mac,
                valid=not is_expired,
                expired=is_expired,
                expiry_date=expiry,
                error="MAC ist abgelaufen" if is_expired else None
            )
            
        except Exception as e:
            logger.error(f"Fehler bei MAC-Validierung {mac}: {e}")
            return MACValidationResult(
                mac=mac,
                valid=False,
                error=str(e)
            )
    
    def validate_all(
        self, 
        portal_url: str, 
        macs: List[str], 
        proxy: Optional[str] = None
    ) -> List[MACValidationResult]:
        """
        Validiert alle MAC-Adressen.
        
        Args:
            portal_url: Portal-URL
            macs: Liste von MAC-Adressen
            proxy: Optional HTTP-Proxy
            
        Returns:
            Liste von MACValidationResult
        """
        return [self.validate_mac(portal_url, mac, proxy) for mac in macs]
    
    def get_valid_macs(self, results: List[MACValidationResult]) -> List[str]:
        """
        Extrahiert gültige MACs aus Validierungsergebnissen.
        
        Args:
            results: Liste von MACValidationResult
            
        Returns:
            Liste von gültigen MAC-Adressen
        """
        return [r.mac for r in results if r.valid]
    
    def _check_expired(self, expiry_str: str) -> bool:
        """
        Prüft ob ein Ablaufdatum in der Vergangenheit liegt.
        
        Args:
            expiry_str: Ablaufdatum als String
            
        Returns:
            True wenn abgelaufen, sonst False
        """
        for fmt in self.DATE_FORMATS:
            try:
                expiry_date = datetime.strptime(expiry_str.strip(), fmt)
                return expiry_date < datetime.now()
            except ValueError:
                continue
        
        # Bei unbekanntem Format als nicht abgelaufen behandeln
        logger.warning(f"Unbekanntes Datumsformat: {expiry_str}")
        return False


class StreamLinkGenerator:
    """
    Generiert direkte Stream-Links aus Portal-Daten.
    """
    
    @staticmethod
    def generate_link(portal_url: str, mac: str, channel: Dict[str, Any]) -> Optional[str]:
        """
        Generiert einen direkten Stream-Link.
        
        Args:
            portal_url: Portal-URL
            mac: MAC-Adresse
            channel: Kanal-Daten vom Portal
            
        Returns:
            Stream-URL oder None
        """
        cmd = channel.get('cmd', '')
        
        # Wenn cmd bereits eine HTTP-URL enthält, extrahiere sie
        if cmd and 'http' in cmd:
            return StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        # Fallback: URL aus Portal-Basis und Channel-ID konstruieren
        stream_id = channel.get('id', '')
        if not stream_id:
            return None
        
        # Extrahiere Basis-URL aus Portal-URL
        from urllib.parse import urlparse
        parsed = urlparse(portal_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        return f"{base_url}/play/live.php?mac={mac}&stream={stream_id}&extension=ts"
    
    @staticmethod
    def extract_url_from_cmd(cmd: str) -> Optional[str]:
        """
        Extrahiert HTTP-URL aus cmd-String (z.B. FFmpeg-Befehl).
        
        Args:
            cmd: cmd-String vom Portal
            
        Returns:
            Extrahierte URL oder None
        """
        if not cmd:
            return None
        
        # FFmpeg-Prefix entfernen
        if 'ffmpeg' in cmd.lower():
            # Format: "ffmpeg http://..."
            parts = cmd.split('ffmpeg ')
            if len(parts) > 1:
                return parts[-1].strip()
        
        # Direkte URL
        if cmd.strip().startswith('http'):
            return cmd.strip()
        
        return None


class ChannelFetcher:
    """
    Ruft Kanäle und Gruppen vom Portal ab.
    """
    
    def __init__(self, stb_client: Any):
        """
        Args:
            stb_client: STBClient-Instanz für Portal-Kommunikation
        """
        self.stb_client = stb_client
    
    def fetch_all(
        self, 
        portal_url: str, 
        mac: str, 
        token: str, 
        proxy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ruft alle Kanäle und Gruppen ab.
        
        Args:
            portal_url: Portal-URL
            mac: MAC-Adresse
            token: Auth-Token
            proxy: Optional HTTP-Proxy
            
        Returns:
            Dict mit 'channels' und 'genres'
        """
        channels = self.stb_client.get_all_channels(portal_url, mac, token, proxy)
        genres = self.stb_client.get_genre_names(portal_url, mac, token, proxy)
        
        return {
            'channels': channels or [],
            'genres': genres or {}
        }
    
    def enrich_channels_with_groups(
        self, 
        channels: List[Dict[str, Any]], 
        genres: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Reichert Kanäle mit Gruppen-Namen an.
        
        Args:
            channels: Liste von Kanal-Daten
            genres: Dict mit genre_id → genre_name Mapping
            
        Returns:
            Kanäle mit hinzugefügtem 'group_title' Feld
        """
        for channel in channels:
            genre_id = str(channel.get('tv_genre_id', ''))
            channel['group_title'] = genres.get(genre_id, 'Uncategorized')
        return channels
    
    def get_genre_statistics(
        self, 
        channels: List[Dict[str, Any]], 
        genres: Dict[str, str]
    ) -> Dict[str, int]:
        """
        Berechnet Statistiken über Kanäle pro Genre.
        
        Args:
            channels: Liste von Kanal-Daten
            genres: Dict mit genre_id → genre_name Mapping
            
        Returns:
            Dict mit genre_name → channel_count
        """
        stats = {}
        for channel in channels:
            genre_id = str(channel.get('tv_genre_id', ''))
            genre_name = genres.get(genre_id, 'Uncategorized')
            stats[genre_name] = stats.get(genre_name, 0) + 1
        return stats
