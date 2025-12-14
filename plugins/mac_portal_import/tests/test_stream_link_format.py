"""
Property-Based Test for Stream Link Format.

**Feature: mac-portal-import, Property 5: Stream Link Format**
**Validates: Requirements 3.3**

Tests that stream links follow the format:
http://portal/play/live.php?mac=MAC&stream=ID&extension=ts
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import given, strategies as st, settings
import re
from urllib.parse import urlparse, parse_qs

from utils import StreamLinkGenerator


# Strategie für gültige MAC-Adressen
def mac_address_strategy():
    """Generiert gültige MAC-Adressen."""
    return st.from_regex(
        r'[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}',
        fullmatch=True
    )


# Strategie für Portal-URLs
def portal_url_strategy():
    """Generiert gültige Portal-URLs."""
    return st.from_regex(
        r'https?://[a-z0-9]+\.[a-z]{2,6}(:[0-9]{1,5})?(/[a-z0-9_/]*)?',
        fullmatch=True
    )


class TestStreamLinkFormat:
    """
    Property-Based Tests für Stream Link Format.
    
    **Feature: mac-portal-import, Property 5: Stream Link Format**
    **Validates: Requirements 3.3**
    """
    
    @given(
        stream_id=st.integers(min_value=1, max_value=999999),
        mac=mac_address_strategy()
    )
    @settings(max_examples=100)
    def test_stream_link_contains_required_components(self, stream_id, mac):
        """
        **Feature: mac-portal-import, Property 5: Stream Link Format**
        **Validates: Requirements 3.3**
        
        Property: For any channel with ID and portal URL, the generated stream link
        should contain mac=MAC, stream=ID, and extension=ts.
        """
        portal_url = "http://example.com/server/load.php"
        channel = {'id': stream_id, 'cmd': ''}
        
        link = StreamLinkGenerator.generate_link(portal_url, mac.upper(), channel)
        
        # Link should not be None
        assert link is not None, "Stream link should not be None"
        
        # Link should contain the MAC address
        assert f"mac={mac.upper()}" in link, f"Link should contain mac={mac.upper()}"
        
        # Link should contain the stream ID
        assert f"stream={stream_id}" in link, f"Link should contain stream={stream_id}"
        
        # Link should contain extension=ts
        assert "extension=ts" in link, "Link should contain extension=ts"
    
    @given(
        stream_id=st.integers(min_value=1, max_value=999999),
        mac=mac_address_strategy()
    )
    @settings(max_examples=100)
    def test_stream_link_format_structure(self, stream_id, mac):
        """
        **Feature: mac-portal-import, Property 5: Stream Link Format**
        **Validates: Requirements 3.3**
        
        Property: Stream links should follow the format:
        http://portal/play/live.php?mac=MAC&stream=ID&extension=ts
        """
        portal_url = "http://example.com/stalker_portal/server/load.php"
        channel = {'id': stream_id, 'cmd': ''}
        
        link = StreamLinkGenerator.generate_link(portal_url, mac.upper(), channel)
        
        # Parse the URL
        parsed = urlparse(link)
        
        # Should be HTTP or HTTPS
        assert parsed.scheme in ['http', 'https'], "Link should use http or https"
        
        # Should have a netloc (host)
        assert parsed.netloc, "Link should have a host"
        
        # Path should contain play/live.php
        assert 'play/live.php' in parsed.path, "Link path should contain play/live.php"
        
        # Parse query parameters
        query_params = parse_qs(parsed.query)
        
        # Should have mac parameter
        assert 'mac' in query_params, "Link should have mac parameter"
        assert query_params['mac'][0] == mac.upper(), "MAC should match"
        
        # Should have stream parameter
        assert 'stream' in query_params, "Link should have stream parameter"
        assert query_params['stream'][0] == str(stream_id), "Stream ID should match"
        
        # Should have extension parameter
        assert 'extension' in query_params, "Link should have extension parameter"
        assert query_params['extension'][0] == 'ts', "Extension should be ts"
    
    @given(
        stream_id=st.integers(min_value=1, max_value=999999),
        mac=mac_address_strategy(),
        port=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=100)
    def test_stream_link_preserves_portal_host(self, stream_id, mac, port):
        """
        **Feature: mac-portal-import, Property 5: Stream Link Format**
        **Validates: Requirements 3.3**
        
        Property: The generated stream link should use the same host as the portal URL.
        """
        portal_url = f"http://testportal.com:{port}/stalker_portal/server/load.php"
        channel = {'id': stream_id, 'cmd': ''}
        
        link = StreamLinkGenerator.generate_link(portal_url, mac.upper(), channel)
        
        # Parse both URLs
        portal_parsed = urlparse(portal_url)
        link_parsed = urlparse(link)
        
        # Host should match
        assert link_parsed.netloc == portal_parsed.netloc, \
            f"Link host {link_parsed.netloc} should match portal host {portal_parsed.netloc}"
    
    def test_stream_link_with_empty_channel_id(self):
        """
        Edge case: Channel without ID should return None.
        """
        portal_url = "http://example.com/server/load.php"
        channel = {'cmd': ''}  # No 'id' field
        
        link = StreamLinkGenerator.generate_link(portal_url, "00:1A:79:19:1F:A9", channel)
        
        assert link is None, "Link should be None when channel has no ID"
    
    def test_stream_link_with_cmd_url(self):
        """
        Edge case: Channel with cmd containing URL should extract the URL.
        """
        portal_url = "http://example.com/server/load.php"
        expected_url = "http://stream.example.com/live/123.ts"
        channel = {'id': 123, 'cmd': expected_url}
        
        link = StreamLinkGenerator.generate_link(portal_url, "00:1A:79:19:1F:A9", channel)
        
        assert link == expected_url, "Link should be the URL from cmd"


def run_tests_manually():
    """Run tests manually without pytest to avoid Django interference."""
    from hypothesis import settings as hypothesis_settings
    
    test_instance = TestStreamLinkFormat()
    
    print("Running Property-Based Tests for Stream Link Format...")
    print("=" * 60)
    
    tests = [
        ('test_stream_link_contains_required_components', test_instance.test_stream_link_contains_required_components),
        ('test_stream_link_format_structure', test_instance.test_stream_link_format_structure),
        ('test_stream_link_preserves_portal_host', test_instance.test_stream_link_preserves_portal_host),
        ('test_stream_link_with_empty_channel_id', test_instance.test_stream_link_with_empty_channel_id),
        ('test_stream_link_with_cmd_url', test_instance.test_stream_link_with_cmd_url),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}...")
            test_func()
            print(f"  ✓ PASSED")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests_manually()
    exit(0 if success else 1)
