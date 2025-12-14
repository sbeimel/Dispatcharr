"""
Property-Based Tests für MAC Portal Import Utilities.

Verwendet Hypothesis für Property-Based Testing.
"""

import pytest
from hypothesis import given, strategies as st
import re

from ..utils import MACNormalizer, StreamLinkGenerator


# Strategie für gültige MAC-Adressen
def mac_address_strategy():
    """Generiert gültige MAC-Adressen."""
    return st.from_regex(
        r'[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}',
        fullmatch=True
    )


class TestMACNormalizer:
    """Tests für MACNormalizer."""
    
    @given(macs=st.lists(mac_address_strategy(), min_size=1, max_size=5, unique=True))
    def test_normalization_with_spaces(self, macs):
        """
        **Feature: mac-portal-import, Property 1: MAC Normalization Consistency**
        
        Test: Leerzeichen-getrennte MACs werden korrekt normalisiert.
        """
        input_str = ' '.join(macs)
        result = MACNormalizer.normalize(input_str)
        
        # Alle MACs sollten gefunden werden
        assert len(result) == len(macs)
        
        # Alle MACs sollten uppercase sein
        for mac in result:
            assert mac == mac.upper()
        
        # Alle Original-MACs sollten enthalten sein
        for mac in macs:
            assert mac.upper() in result
    
    @given(macs=st.lists(mac_address_strategy(), min_size=1, max_size=5, unique=True))
    def test_normalization_with_commas(self, macs):
        """
        **Feature: mac-portal-import, Property 1: MAC Normalization Consistency**
        
        Test: Komma-getrennte MACs werden korrekt normalisiert.
        """
        input_str = ','.join(macs)
        result = MACNormalizer.normalize(input_str)
        
        assert len(result) == len(macs)
        for mac in macs:
            assert mac.upper() in result
    
    @given(macs=st.lists(mac_address_strategy(), min_size=1, max_size=5, unique=True))
    def test_normalization_with_comma_space(self, macs):
        """
        **Feature: mac-portal-import, Property 1: MAC Normalization Consistency**
        
        Test: Komma+Leerzeichen-getrennte MACs werden korrekt normalisiert.
        """
        input_str = ', '.join(macs)
        result = MACNormalizer.normalize(input_str)
        
        assert len(result) == len(macs)
        for mac in macs:
            assert mac.upper() in result
    
    @given(macs=st.lists(mac_address_strategy(), min_size=2, max_size=5, unique=True))
    def test_normalization_mixed_separators(self, macs):
        """
        **Feature: mac-portal-import, Property 1: MAC Normalization Consistency**
        
        Test: Gemischte Separatoren werden korrekt verarbeitet.
        """
        # Normalisiere MACs zu uppercase für korrekten Vergleich
        # (Strategie generiert case-sensitive unique, aber Normalizer ist case-insensitive)
        unique_upper_macs = list(dict.fromkeys(m.upper() for m in macs))
        
        # Mische verschiedene Separatoren
        separators = [' ', ',', ', ', '\n']
        parts = []
        for i, mac in enumerate(macs):
            parts.append(mac)
            if i < len(macs) - 1:
                parts.append(separators[i % len(separators)])
        
        input_str = ''.join(parts)
        result = MACNormalizer.normalize(input_str)
        
        # Ergebnis sollte alle unique uppercase MACs enthalten
        assert len(result) == len(unique_upper_macs)
        for mac in unique_upper_macs:
            assert mac in result
    
    @given(macs=st.lists(mac_address_strategy(), min_size=1, max_size=5))
    def test_normalization_removes_duplicates(self, macs):
        """
        **Feature: mac-portal-import, Property 1: MAC Normalization Consistency**
        
        Test: Duplikate werden entfernt.
        """
        # Füge Duplikate hinzu
        input_str = ' '.join(macs + macs)
        result = MACNormalizer.normalize(input_str)
        
        # Ergebnis sollte nur unique MACs enthalten
        unique_macs = list(set(m.upper() for m in macs))
        assert len(result) == len(unique_macs)
    
    @given(mac=st.text(min_size=17, max_size=17))
    def test_format_validation(self, mac):
        """
        **Feature: mac-portal-import, Property 2: MAC Format Validation**
        
        Test: Nur gültige MAC-Formate werden akzeptiert.
        """
        is_valid = MACNormalizer.validate_format(mac)
        
        if is_valid:
            # Muss dem Format entsprechen
            assert re.match(r'^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$', mac)
    
    def test_validate_format_valid_macs(self):
        """Test: Gültige MAC-Formate werden erkannt."""
        valid_macs = [
            '00:1A:79:19:1F:A9',
            '00:1a:79:19:1f:a9',
            'AA:BB:CC:DD:EE:FF',
            '00-1A-79-19-1F-A9',
        ]
        for mac in valid_macs:
            assert MACNormalizer.validate_format(mac), f"{mac} sollte gültig sein"
    
    def test_validate_format_invalid_macs(self):
        """Test: Ungültige MAC-Formate werden abgelehnt."""
        invalid_macs = [
            '00:1A:79:19:1F',      # Zu kurz
            '00:1A:79:19:1F:A9:00', # Zu lang
            '00:1A:79:19:1F:GG',   # Ungültige Zeichen
            '001A79191FA9',        # Keine Separatoren
            '',                    # Leer
        ]
        for mac in invalid_macs:
            assert not MACNormalizer.validate_format(mac), f"{mac} sollte ungültig sein"


class TestStreamLinkGenerator:
    """Tests für StreamLinkGenerator."""
    
    @given(
        stream_id=st.integers(min_value=1, max_value=999999),
        mac=mac_address_strategy()
    )
    def test_stream_link_format(self, stream_id, mac):
        """
        **Feature: mac-portal-import, Property 5: Stream Link Format**
        
        Test: Stream-Links haben das korrekte Format.
        """
        portal_url = "http://example.com/server/load.php"
        channel = {'id': stream_id, 'cmd': ''}
        
        link = StreamLinkGenerator.generate_link(portal_url, mac.upper(), channel)
        
        assert link is not None
        assert f"mac={mac.upper()}" in link
        assert f"stream={stream_id}" in link
        assert "extension=ts" in link
    
    @given(url=st.from_regex(r'http://[a-z]+\.[a-z]+/[a-z]+', fullmatch=True))
    def test_ffmpeg_url_extraction(self, url):
        """
        **Feature: mac-portal-import, Property 6: FFmpeg URL Extraction**
        
        Test: URLs werden korrekt aus FFmpeg-Befehlen extrahiert.
        """
        cmd = f"ffmpeg {url}"
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        
        assert result == url
    
    def test_extract_direct_url(self):
        """Test: Direkte URLs werden erkannt."""
        url = "http://example.com/stream/123.ts"
        result = StreamLinkGenerator.extract_url_from_cmd(url)
        assert result == url
    
    def test_extract_ffmpeg_url(self):
        """Test: FFmpeg-URLs werden extrahiert."""
        url = "http://example.com/play/live.php?mac=00:1A:79:19:1F:A9&stream=123"
        cmd = f"ffmpeg {url}"
        result = StreamLinkGenerator.extract_url_from_cmd(cmd)
        assert result == url
    
    def test_extract_empty_cmd(self):
        """Test: Leere cmd gibt None zurück."""
        assert StreamLinkGenerator.extract_url_from_cmd('') is None
        assert StreamLinkGenerator.extract_url_from_cmd(None) is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
