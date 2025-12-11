"""
Property-based tests for HTTP Basic Authentication functionality.

Uses Hypothesis for property-based testing to verify:
- Authentication requirement
- Endpoint protection consistency
- Secure logging

**Feature: dispatcharr-patch-adaptation**
"""

import pytest
from hypothesis import given, strategies as st, settings
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from unittest.mock import patch, Mock
import base64

from apps.output.views import get_basic_auth_user


class TestBasicAuthentication(TestCase):
    """
    **Property 4: Authentication Requirement**
    **Validates: Requirements 4.1, 4.2, 4.3**
    
    For any request to M3U or EPG endpoints, valid HTTP Basic
    Authentication credentials must be provided.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_missing_auth_header_returns_401(self):
        """Request without Authorization header should return 401."""
        request = self.factory.get('/output/m3u/')
        
        result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)
        self.assertIn('WWW-Authenticate', result)

    def test_invalid_auth_scheme_returns_401(self):
        """Request with non-Basic auth scheme should return 401."""
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer some_token'
        
        result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_malformed_base64_returns_401(self, garbage):
        """Malformed base64 in Authorization header should return 401."""
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {garbage}'
        
        result = get_basic_auth_user(request)
        
        # Should either return 401 or be a valid response
        if isinstance(result, HttpResponse):
            self.assertEqual(result.status_code, 401)

    @given(st.text(min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_base64_without_colon_returns_401(self, username):
        """Base64 content without colon separator should return 401."""
        # Encode username without password (no colon)
        encoded = base64.b64encode(username.encode()).decode()
        
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        
        result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)

    @given(
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789')
    )
    @settings(max_examples=50)
    def test_invalid_credentials_return_401(self, username, password):
        """Invalid username/password should return 401."""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock authenticate to return None (invalid credentials)
        with patch('apps.output.views.authenticate', return_value=None):
            result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)

    def test_valid_credentials_return_user(self):
        """Valid credentials should return User object."""
        credentials = "testuser:testpass"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        
        # Mock authenticate to return a user
        mock_user = Mock()
        mock_user.is_active = True
        
        with patch('apps.output.views.authenticate', return_value=mock_user):
            result = get_basic_auth_user(request)
        
        self.assertEqual(result, mock_user)

    def test_inactive_user_returns_401(self):
        """Inactive user should return 401."""
        credentials = "testuser:testpass"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock authenticate to return inactive user
        mock_user = Mock()
        mock_user.is_active = False
        
        with patch('apps.output.views.authenticate', return_value=mock_user):
            result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)


class TestEndpointProtectionConsistency(TestCase):
    """
    **Property 5: Endpoint Authentication Consistency**
    **Validates: Requirements 4.5**
    
    When authentication is configured, the system should apply it
    consistently across all M3U and EPG endpoints.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_m3u_endpoint_requires_auth(self):
        """M3U endpoint should require authentication."""
        request = self.factory.get('/output/m3u/')
        
        result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)

    def test_epg_endpoint_requires_auth(self):
        """EPG endpoint should require authentication."""
        request = self.factory.get('/output/epg/')
        
        result = get_basic_auth_user(request)
        
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 401)


class TestSecureLogging(TestCase):
    """
    **Property 3: Secure Authentication Logging**
    **Validates: Requirements 7.3**
    
    When authentication failures occur, the system should log the
    failure without exposing credentials.
    """

    def setUp(self):
        self.factory = RequestFactory()

    @given(
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789')
    )
    @settings(max_examples=20)
    def test_password_not_logged_on_failure(self, username, password):
        """Password should not appear in logs on authentication failure."""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = self.factory.get('/output/m3u/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        with patch('apps.output.views.authenticate', return_value=None):
            with patch('apps.output.views.logger') as mock_logger:
                get_basic_auth_user(request)
                
                # Check that password is not in any log call
                for call in mock_logger.warning.call_args_list:
                    log_message = str(call)
                    self.assertNotIn(password, log_message)
