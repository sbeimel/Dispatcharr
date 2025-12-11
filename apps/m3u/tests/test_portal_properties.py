"""
Property-based tests for MAC Portal Client functionality.

Uses Hypothesis for property-based testing to verify:
- Portal URL resolution
- Portal handshake
- Channel data normalization

**Feature: dispatcharr-patch-adaptation**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
import json

from apps.m3u.mac_portal_client import MacPortalClient, MacPortalError


# Strategy for generating valid portal URLs
@st.composite
def valid_portal_url(draw):
    """Generate a valid portal URL."""
    scheme = draw(st.sampled_from(['http', 'https']))
    domain = draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=3, max_size=15))
    tld = draw(st.sampled_from(['com', 'net', 'org', 'io']))
    path = draw(st.sampled_from(['', '/portal', '/stalker_portal', '/c']))
    return f"{scheme}://{domain}.{tld}{path}"


# Strategy for generating valid MAC addresses
@st.composite
def valid_mac_address(draw):
    """Generate a valid MAC address."""
    hex_pair = st.text(alphabet='0123456789ABCDEF', min_size=2, max_size=2)
    pairs = [draw(hex_pair) for _ in range(6)]
    return ':'.join(pairs)


class TestPortalURLResolution(TestCase):
    """
    **Property 3: Portal URL Resolution**
    **Validates: Requirements 5.3**
    
    For any portal URL provided, the system should auto-detect
    the correct load.php endpoint path.
    """

    @given(valid_portal_url(), valid_mac_address())
    @settings(max_examples=50)
    def test_portal_url_resolution_does_not_throw(self, url, mac):
        """Portal URL resolution should not throw exceptions."""
        client = MacPortalClient(base_url=url, mac=mac)
        
        # Mock the session to avoid actual network calls
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404  # Simulate not found
            mock_get.return_value = mock_response
            
            # Should not raise, should fall back to original URL
            try:
                result = client.resolve_portal_url()
                self.assertIsNotNone(result)
                self.assertIsInstance(result, str)
            except Exception as e:
                self.fail(f"resolve_portal_url raised exception: {e}")

    def test_url_ending_with_load_php_used_directly(self):
        """URL ending with load.php should be used directly."""
        url = "http://example.com/stalker_portal/server/load.php"
        client = MacPortalClient(base_url=url, mac="00:11:22:33:44:55")
        
        result = client.resolve_portal_url()
        self.assertEqual(result, url)

    def test_url_without_scheme_gets_http_added(self):
        """URL without scheme should get http:// added."""
        client = MacPortalClient(base_url="example.com/portal", mac="00:11:22:33:44:55")
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = client.resolve_portal_url()
            # Should have http:// prefix
            self.assertTrue(result.startswith('http://'))


class TestPortalHandshake(TestCase):
    """
    **Property 5: Portal Communication Round Trip**
    **Validates: Requirements 5.1**
    
    For any valid MAC portal handshake, the system should be able
    to authenticate and retrieve a session token.
    """

    @given(valid_mac_address())
    @settings(max_examples=50)
    def test_handshake_with_valid_response_extracts_token(self, mac):
        """Handshake with valid response should extract token."""
        client = MacPortalClient(base_url="http://example.com", mac=mac)
        
        with patch.object(client.session, 'get') as mock_get:
            # Mock successful handshake response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "js": {"token": "test_token_12345"}
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            token = client.handshake()
            self.assertEqual(token, "test_token_12345")
            self.assertEqual(client.token, "test_token_12345")

    def test_handshake_without_token_raises_error(self):
        """Handshake without token in response should raise MacPortalError."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"js": {}}  # No token
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            with self.assertRaises(MacPortalError):
                client.handshake()


class TestChannelParsing(TestCase):
    """
    **Property 2: Channel Data Normalization**
    **Validates: Requirements 5.2**
    
    For any valid portal response, the system should parse and
    normalize channel data correctly.
    """

    @given(st.lists(
        st.fixed_dictionaries({
            'id': st.integers(min_value=1, max_value=10000),
            'name': st.text(min_size=1, max_size=50),
            'cmd': st.just('ffmpeg http://stream.example.com/live/123'),
            'tv_genre_id': st.integers(min_value=1, max_value=100),
        }),
        min_size=0,
        max_size=10
    ))
    @settings(max_examples=50)
    def test_channel_normalization_preserves_data(self, channels):
        """Channel normalization should preserve essential data."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        client.token = "test_token"
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"js": {"data": channels}}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = client.get_channels()
            
            # Should have same count as input (all have valid URLs)
            self.assertEqual(len(result), len(channels))
            
            # Each result should have required fields
            for ch in result:
                self.assertIn('id', ch)
                self.assertIn('name', ch)
                self.assertIn('group', ch)
                self.assertIn('url', ch)

    def test_channels_without_url_are_skipped(self):
        """Channels without extractable URL should be skipped."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        client.token = "test_token"
        
        channels = [
            {'id': 1, 'name': 'Channel 1', 'cmd': ''},  # No URL
            {'id': 2, 'name': 'Channel 2', 'cmd': 'ffmpeg http://stream.example.com/live/2'},
        ]
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"js": {"data": channels}}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = client.get_channels()
            
            # Only channel with URL should be included
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['id'], 2)


class TestCreateLink(TestCase):
    """
    Tests for create_link functionality.
    """

    def test_create_link_extracts_url_from_response(self):
        """create_link should extract URL from portal response."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        client.token = "test_token"
        client.portal_url = "http://example.com/load.php"
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "js": {"cmd": "ffmpeg http://stream.example.com/live/123.ts"}
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = client.create_link("ffmpeg http://original.com/stream")
            self.assertEqual(result, "http://stream.example.com/live/123.ts")

    def test_create_link_without_cmd_raises_error(self):
        """create_link without cmd should raise MacPortalError."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        
        with self.assertRaises(MacPortalError):
            client.create_link("")

    def test_create_link_with_https_url(self):
        """create_link should handle HTTPS URLs."""
        client = MacPortalClient(base_url="http://example.com", mac="00:11:22:33:44:55")
        client.token = "test_token"
        client.portal_url = "http://example.com/load.php"
        
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "js": {"cmd": "ffmpeg https://secure.example.com/live/123.ts"}
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = client.create_link("ffmpeg http://original.com/stream")
            self.assertEqual(result, "https://secure.example.com/live/123.ts")
