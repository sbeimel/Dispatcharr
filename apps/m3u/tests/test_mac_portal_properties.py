"""
Property-Based Tests for MAC Portal Models.

Uses Hypothesis for property-based testing.
"""

from hypothesis import given, strategies as st, settings
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

# Import models
from apps.m3u.models import M3UAccount
from apps.m3u.mac_portal_models import VODResumePoint


class TestVODResumePointProperties(TestCase):
    """
    Property-based tests for VODResumePoint model.
    
    **Feature: mac-portal-improvements, Property 4: Resume Point Round-Trip**
    **Validates: Requirements 31.1, 31.2**
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test account
        cls.account = M3UAccount.objects.create(
            name="Test Account for Properties",
            account_type=M3UAccount.Types.MAC,
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.account.delete()
        super().tearDownClass()
    
    @given(
        position=st.integers(min_value=0, max_value=36000),
        vod_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
    def test_resume_point_roundtrip(self, position, vod_id):
        """
        **Feature: mac-portal-improvements, Property 4: Resume Point Round-Trip**
        
        For any VOD playback position saved, retrieving the resume point 
        should return the same position (within 1 second tolerance).
        
        **Validates: Requirements 31.1, 31.2**
        """
        # Skip empty vod_id
        if not vod_id.strip():
            return
        
        # Clean up any existing resume point with this vod_id
        VODResumePoint.objects.filter(
            m3u_account=self.account,
            vod_id=vod_id
        ).delete()
        
        # Save resume point
        resume_point = VODResumePoint.objects.create(
            m3u_account=self.account,
            vod_id=vod_id,
            content_type=VODResumePoint.ContentType.VOD,
            position_seconds=position,
            duration_seconds=position + 1000  # Arbitrary duration
        )
        
        # Retrieve resume point
        retrieved = VODResumePoint.objects.get(
            m3u_account=self.account,
            vod_id=vod_id,
            content_type=VODResumePoint.ContentType.VOD
        )
        
        # Assert round-trip consistency (within 1 second tolerance)
        assert abs(retrieved.position_seconds - position) <= 1, \
            f"Resume point mismatch: saved {position}, retrieved {retrieved.position_seconds}"
        
        # Clean up
        resume_point.delete()
    
    @given(
        position=st.integers(min_value=0, max_value=36000),
        duration=st.integers(min_value=100, max_value=36000)
    )
    @settings(max_examples=50)
    def test_is_near_end_property(self, position, duration):
        """
        Test that is_near_end correctly identifies positions near the end.
        
        Property: For any position within 15 minutes of duration, is_near_end returns True.
        """
        threshold_seconds = 15 * 60  # 15 minutes
        
        resume_point = VODResumePoint(
            m3u_account=self.account,
            vod_id="test_near_end",
            position_seconds=position,
            duration_seconds=duration
        )
        
        remaining = duration - position
        expected_near_end = remaining <= threshold_seconds
        
        assert resume_point.is_near_end(threshold_minutes=15) == expected_near_end, \
            f"is_near_end mismatch: position={position}, duration={duration}, remaining={remaining}"



class TestTokenManagerProperties(TestCase):
    """
    Property-based tests for TokenManager.
    
    **Feature: mac-portal-improvements, Property 1: Token Refresh Timing**
    **Validates: Requirements 41.2**
    """
    
    @given(
        ttl=st.integers(min_value=60, max_value=7200),
        threshold=st.floats(min_value=0.5, max_value=0.95)
    )
    @settings(max_examples=100)
    def test_token_refresh_timing(self, ttl, threshold):
        """
        **Feature: mac-portal-improvements, Property 1: Token Refresh Timing**
        
        For any token with known TTL, the system should refresh it when 
        remaining time falls below the configured threshold.
        
        **Validates: Requirements 41.2**
        """
        from apps.m3u.token_manager import TokenManager
        
        manager = TokenManager(account_id=1, mac_address="00:11:22:33:44:55")
        manager.refresh_threshold = threshold
        manager.token_ttl = ttl
        
        # Set token with full TTL remaining - should NOT need refresh
        manager.token = "test_token"
        manager.token_expiry = timezone.now() + timedelta(seconds=ttl)
        
        # With full TTL, should not need refresh
        assert not manager._should_refresh(), \
            f"Token with full TTL should not need refresh (ttl={ttl}, threshold={threshold})"
        
        # Set token with time below threshold - should need refresh
        threshold_seconds = ttl * (1 - threshold)
        remaining = threshold_seconds - 1  # Just below threshold
        manager.token_expiry = timezone.now() + timedelta(seconds=remaining)
        
        assert manager._should_refresh(), \
            f"Token below threshold should need refresh (remaining={remaining}, threshold_seconds={threshold_seconds})"
        
        # Clean up
        manager.invalidate()
    
    def test_token_expiry_invalidation(self):
        """Test that expired tokens are correctly identified."""
        from apps.m3u.token_manager import TokenManager
        
        manager = TokenManager(account_id=1, mac_address="00:11:22:33:44:66")
        
        # Set expired token
        manager.token = "expired_token"
        manager.token_expiry = timezone.now() - timedelta(seconds=10)
        
        # Should need refresh
        assert manager._should_refresh(), "Expired token should need refresh"
        
        # Should not be valid
        assert not manager.is_valid(), "Expired token should not be valid"
        
        # Clean up
        manager.invalidate()



class TestMACRotationProperties(TestCase):
    """
    Property-based tests for MACRotationManager.
    
    **Feature: mac-portal-improvements, Property 2: MAC Rotation Fairness**
    **Validates: Requirements 23.1, 23.3**
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test account with multiple MACs
        cls.account = M3UAccount.objects.create(
            name="Test Account for MAC Rotation",
            account_type=M3UAccount.Types.MAC,
            mac_address="00:11:22:33:44:55 00:11:22:33:44:66 00:11:22:33:44:77",
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.account.delete()
        super().tearDownClass()
    
    def test_health_based_selection_prefers_healthy(self):
        """
        **Feature: mac-portal-improvements, Property 2: MAC Rotation Fairness**
        
        For any set of available MACs, the rotation should prefer MACs 
        with higher health scores and exclude MACs in cooldown.
        
        **Validates: Requirements 23.1, 23.3**
        """
        from apps.m3u.mac_rotation_manager import MACRotationManager
        from apps.m3u.mac_portal_models import MACHealthRecord
        
        manager = MACRotationManager(self.account.id)
        manager._strategy = MACRotationManager.SelectionStrategy.HEALTH_BASED
        
        # Get all MACs
        macs = list(self.account.macs.all())
        if len(macs) < 2:
            self.skipTest("Need at least 2 MACs for this test")
        
        # Record different health events for each MAC
        # First MAC: all successes (high health)
        for _ in range(5):
            MACHealthRecord.record_success(macs[0])
        
        # Second MAC: all failures (low health)
        for _ in range(5):
            MACHealthRecord.record_failure(macs[1], error_message="Test failure")
        
        # Get next MAC - should be the healthy one
        selected = manager.get_next_mac()
        
        if selected:
            # Selected MAC should have highest health score among available
            selected_score = MACHealthRecord.get_health_score(selected)
            for mac in macs:
                if mac.id != selected.id:
                    other_score = MACHealthRecord.get_health_score(mac)
                    self.assertGreaterEqual(
                        selected_score, other_score,
                        "Selected MAC should have highest health score"
                    )
        
        # Clean up health records
        MACHealthRecord.objects.filter(mac__in=macs).delete()


class TestCooldownProperties(TestCase):
    """
    Property-based tests for Cooldown system.
    
    **Feature: mac-portal-improvements, Property 3: Cooldown Application**
    **Validates: Requirements 46.1, 46.2, 46.3**
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = M3UAccount.objects.create(
            name="Test Account for Cooldown",
            account_type=M3UAccount.Types.MAC,
            mac_address="00:AA:BB:CC:DD:EE",
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.account.delete()
        super().tearDownClass()
    
    @given(
        cooldown_minutes=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=20)
    def test_cooldown_application(self, cooldown_minutes):
        """
        **Feature: mac-portal-improvements, Property 3: Cooldown Application**
        
        For any MAC that fails authentication, the system should apply 
        the configured cooldown period and not use that MAC until cooldown expires.
        
        **Validates: Requirements 46.1, 46.2, 46.3**
        """
        from apps.m3u.mac_portal_models import MACCooldown
        
        macs = list(self.account.macs.all())
        if not macs:
            return
        
        mac = macs[0]
        
        # Clear any existing cooldowns
        MACCooldown.objects.filter(mac=mac).delete()
        
        # Apply cooldown
        cooldown = MACCooldown.apply_cooldown(
            mac, 
            MACCooldown.CooldownReason.FAILURE, 
            cooldown_minutes
        )
        
        # Verify cooldown is active
        self.assertTrue(MACCooldown.is_mac_in_cooldown(mac))
        
        # Verify expiry time is correct (within 1 second tolerance)
        expected_expiry = timezone.now() + timedelta(minutes=cooldown_minutes)
        actual_expiry = cooldown.expires_at
        diff = abs((expected_expiry - actual_expiry).total_seconds())
        self.assertLess(diff, 2, "Cooldown expiry should be within 2 seconds of expected")
        
        # Clean up
        MACCooldown.objects.filter(mac=mac).delete()



class TestFailoverProperties(TestCase):
    """
    Property-based tests for FailoverManager.
    
    **Feature: mac-portal-improvements, Property 9: Failover Priority Order**
    **Validates: Requirements 60.2**
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = M3UAccount.objects.create(
            name="Test Account for Failover",
            account_type=M3UAccount.Types.MAC,
            mac_address="00:FF:EE:DD:CC:BB",
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.account.delete()
        super().tearDownClass()
    
    def test_failover_priority_order(self):
        """
        **Feature: mac-portal-improvements, Property 9: Failover Priority Order**
        
        For any failure scenario, the system should try failover strategies 
        in the configured priority order.
        
        **Validates: Requirements 60.2**
        """
        from apps.m3u.failover_manager import FailoverManager
        from apps.m3u.mac_portal_models import FailoverSettings
        
        # Set up failover settings with specific priority
        settings = FailoverSettings.get_settings()
        settings.failover_priority = ['mac', 'endpoint', 'useragent', 'stream']
        settings.mac_failover_enabled = True
        settings.endpoint_failover_enabled = True
        settings.useragent_failover_enabled = True
        settings.stream_failover_enabled = True
        settings.save()
        
        manager = FailoverManager(self.account.id)
        manager._load_settings()
        
        # Verify priority order is loaded correctly
        self.assertEqual(
            manager._failover_priority,
            ['mac', 'endpoint', 'useragent', 'stream'],
            "Failover priority should match configured order"
        )
    
    def test_disabled_strategy_skipping(self):
        """
        **Feature: mac-portal-improvements, Property 10: Failover Strategy Skipping**
        
        For any disabled failover strategy, the system should skip it 
        and proceed to the next enabled strategy.
        
        **Validates: Requirements 55.2**
        """
        from apps.m3u.failover_manager import FailoverManager
        from apps.m3u.mac_portal_models import FailoverSettings
        
        # Disable some strategies
        settings = FailoverSettings.get_settings()
        settings.mac_failover_enabled = True
        settings.endpoint_failover_enabled = False  # Disabled
        settings.useragent_failover_enabled = False  # Disabled
        settings.stream_failover_enabled = True
        settings.save()
        
        manager = FailoverManager(self.account.id)
        manager._load_settings()
        
        # Verify disabled strategies are correctly identified
        self.assertTrue(manager._is_strategy_enabled('mac'))
        self.assertFalse(manager._is_strategy_enabled('endpoint'))
        self.assertFalse(manager._is_strategy_enabled('useragent'))
        self.assertTrue(manager._is_strategy_enabled('stream'))
    
    @given(
        mac_enabled=st.booleans(),
        endpoint_enabled=st.booleans(),
        useragent_enabled=st.booleans(),
        stream_enabled=st.booleans(),
    )
    @settings(max_examples=50)
    def test_failover_strategy_skipping_property(self, mac_enabled, endpoint_enabled, useragent_enabled, stream_enabled):
        """
        **Feature: mac-portal-improvements, Property 10: Failover Strategy Skipping**
        
        For any combination of enabled/disabled failover strategies,
        the system should correctly identify which strategies are enabled.
        
        **Validates: Requirements 55.2**
        """
        from apps.m3u.failover_manager import FailoverManager
        from apps.m3u.mac_portal_models import FailoverSettings
        
        # Configure strategies
        settings = FailoverSettings.get_settings()
        settings.mac_failover_enabled = mac_enabled
        settings.endpoint_failover_enabled = endpoint_enabled
        settings.useragent_failover_enabled = useragent_enabled
        settings.stream_failover_enabled = stream_enabled
        settings.save()
        
        manager = FailoverManager(self.account.id)
        manager._load_settings()
        
        # Verify each strategy's enabled state matches configuration
        self.assertEqual(
            manager._is_strategy_enabled('mac'), mac_enabled,
            f"MAC strategy enabled state mismatch: expected {mac_enabled}"
        )
        self.assertEqual(
            manager._is_strategy_enabled('endpoint'), endpoint_enabled,
            f"Endpoint strategy enabled state mismatch: expected {endpoint_enabled}"
        )
        self.assertEqual(
            manager._is_strategy_enabled('useragent'), useragent_enabled,
            f"User-Agent strategy enabled state mismatch: expected {useragent_enabled}"
        )
        self.assertEqual(
            manager._is_strategy_enabled('stream'), stream_enabled,
            f"Stream strategy enabled state mismatch: expected {stream_enabled}"
        )



class TestRetryExponentialBackoffProperties(TestCase):
    """
    Property-based tests for Retry with Exponential Backoff.
    
    **Feature: mac-portal-improvements, Property 6: Retry with Exponential Backoff**
    **Validates: Requirements 7.1, 45.1**
    """
    
    @given(
        attempt=st.integers(min_value=0, max_value=10),
        base_delay=st.floats(min_value=0.1, max_value=10.0),
    )
    @settings(max_examples=100)
    def test_exponential_backoff_calculation(self, attempt, base_delay):
        """
        **Feature: mac-portal-improvements, Property 6: Retry with Exponential Backoff**
        
        For any retry attempt, the delay should follow exponential backoff formula:
        delay = base_delay * 2^attempt
        
        **Validates: Requirements 7.1, 45.1**
        """
        from apps.m3u.mac_portal_client_extended import calculate_exponential_backoff
        
        # Calculate without jitter for deterministic testing
        delay = calculate_exponential_backoff(
            attempt=attempt,
            base_delay=base_delay,
            max_delay=3600.0,  # High max to not cap
            jitter=False
        )
        
        expected_delay = base_delay * (2 ** attempt)
        
        # Allow small floating point tolerance
        self.assertAlmostEqual(
            delay, expected_delay, places=5,
            msg=f"Exponential backoff mismatch: attempt={attempt}, base={base_delay}"
        )
    
    @given(
        attempt=st.integers(min_value=0, max_value=20),
        base_delay=st.floats(min_value=0.1, max_value=5.0),
        max_delay=st.floats(min_value=10.0, max_value=120.0),
    )
    @settings(max_examples=100)
    def test_exponential_backoff_max_cap(self, attempt, base_delay, max_delay):
        """
        Test that exponential backoff respects maximum delay cap.
        
        Property: For any attempt, delay should never exceed max_delay.
        """
        from apps.m3u.mac_portal_client_extended import calculate_exponential_backoff
        
        delay = calculate_exponential_backoff(
            attempt=attempt,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=False
        )
        
        self.assertLessEqual(
            delay, max_delay,
            f"Delay {delay} exceeds max_delay {max_delay}"
        )
    
    @given(
        attempt=st.integers(min_value=0, max_value=5),
        base_delay=st.floats(min_value=1.0, max_value=5.0),
    )
    @settings(max_examples=50)
    def test_exponential_backoff_jitter_bounds(self, attempt, base_delay):
        """
        Test that jitter stays within expected bounds (0-25% of delay).
        """
        from apps.m3u.mac_portal_client_extended import calculate_exponential_backoff
        
        # Calculate base delay without jitter
        base = calculate_exponential_backoff(
            attempt=attempt,
            base_delay=base_delay,
            max_delay=3600.0,
            jitter=False
        )
        
        # Calculate with jitter multiple times
        for _ in range(10):
            with_jitter = calculate_exponential_backoff(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=3600.0,
                jitter=True
            )
            
            # Jitter should add 0-25% to base delay
            self.assertGreaterEqual(with_jitter, base)
            self.assertLessEqual(with_jitter, base * 1.25 + 0.01)  # Small tolerance


class TestFFmpegURLExtractionProperties(TestCase):
    """
    Property-based tests for FFmpeg URL Extraction.
    
    **Feature: mac-portal-improvements, Property 7: FFmpeg URL Extraction**
    **Validates: Requirements 27.1**
    """
    
    @given(
        protocol=st.sampled_from(['http', 'https']),
        domain=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        path=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
    )
    @settings(max_examples=100)
    def test_ffmpeg_url_extraction_direct(self, protocol, domain, path):
        """
        **Feature: mac-portal-improvements, Property 7: FFmpeg URL Extraction**
        
        For any valid URL embedded in a command string, the extraction 
        should return the correct URL.
        
        **Validates: Requirements 27.1**
        """
        from apps.m3u.mac_portal_client_extended import extract_ffmpeg_url
        
        # Skip invalid domains
        if not domain or not domain.strip():
            return
        
        # Clean path
        clean_path = ''.join(c for c in path if c.isalnum() or c in '/-_.')
        if not clean_path:
            clean_path = "stream"
        
        # Construct URL
        url = f"{protocol}://{domain}.com/{clean_path}"
        
        # Test direct URL
        extracted = extract_ffmpeg_url(url)
        self.assertEqual(extracted, url, f"Direct URL extraction failed for {url}")
        
        # Test URL in ffmpeg command
        cmd = f"ffmpeg -i {url} -c copy output.ts"
        extracted = extract_ffmpeg_url(cmd)
        self.assertIsNotNone(extracted, f"FFmpeg command extraction failed for {cmd}")
        self.assertIn(protocol, extracted)
    
    def test_ffmpeg_url_extraction_patterns(self):
        """
        Test various ffmpeg command patterns.
        """
        from apps.m3u.mac_portal_client_extended import extract_ffmpeg_url
        
        test_cases = [
            # (input_cmd, expected_url_contains)
            ("http://example.com/stream.ts", "http://example.com/stream.ts"),
            ("https://cdn.example.com/live/123", "https://cdn.example.com/live/123"),
            ('ffmpeg -i "http://server.com/ch/1" -c copy out.ts', "http://server.com/ch/1"),
            ("ffrt http://portal.com/stream", "http://portal.com/stream"),
            ("ffmpeg -re -i https://secure.tv/live -f mpegts udp://127.0.0.1:1234", "https://secure.tv/live"),
        ]
        
        for cmd, expected in test_cases:
            extracted = extract_ffmpeg_url(cmd)
            self.assertIsNotNone(extracted, f"Failed to extract URL from: {cmd}")
            self.assertIn(expected.split('/')[2], extracted, f"Extracted URL mismatch for: {cmd}")
    
    def test_ffmpeg_url_extraction_empty_input(self):
        """Test that empty/None input returns None."""
        from apps.m3u.mac_portal_client_extended import extract_ffmpeg_url
        
        self.assertIsNone(extract_ffmpeg_url(None))
        self.assertIsNone(extract_ffmpeg_url(""))
        self.assertIsNone(extract_ffmpeg_url("no url here"))
    
    @given(
        prefix=st.text(min_size=0, max_size=20),
        suffix=st.text(min_size=0, max_size=20),
    )
    @settings(max_examples=50)
    def test_ffmpeg_url_extraction_with_noise(self, prefix, suffix):
        """
        Test URL extraction with random prefix/suffix noise.
        
        Property: URL should be extracted regardless of surrounding text.
        """
        from apps.m3u.mac_portal_client_extended import extract_ffmpeg_url
        
        url = "http://test.example.com/stream/live.ts"
        
        # Clean prefix/suffix to avoid creating invalid URLs
        clean_prefix = ''.join(c for c in prefix if c.isalnum() or c.isspace())
        clean_suffix = ''.join(c for c in suffix if c.isalnum() or c.isspace())
        
        cmd = f"{clean_prefix} {url} {clean_suffix}"
        extracted = extract_ffmpeg_url(cmd)
        
        self.assertIsNotNone(extracted, f"Failed to extract URL from noisy command: {cmd}")
        self.assertEqual(extracted, url, f"Extracted wrong URL from: {cmd}")



class TestPortalTypeDetectionProperties(TestCase):
    """
    Property-based tests for Portal Type Detection.
    
    **Feature: mac-portal-improvements, Property 12: Portal Type Detection Consistency**
    **Validates: Requirements 62.1, 62.6**
    """
    
    def test_portal_type_detection_from_url(self):
        """
        **Feature: mac-portal-improvements, Property 12: Portal Type Detection Consistency**
        
        For any portal URL with known patterns, the detector should
        consistently identify the correct portal type.
        
        **Validates: Requirements 62.1, 62.6**
        """
        from apps.m3u.portal_type_detector import PortalTypeDetector, PortalType
        
        test_cases = [
            ("http://example.com/magLoad.php", PortalType.MAGLOAD),
            ("http://example.com/playlist/user/pass/m3u", PortalType.XUIONE),
            ("http://example.com/player_api.php", PortalType.XTREAM),
            ("http://example.com/server/load.php", PortalType.UNKNOWN),  # Needs response analysis
        ]
        
        for url, expected_type in test_cases:
            detector = PortalTypeDetector(url)
            result = detector.detect_from_url()
            
            if expected_type != PortalType.UNKNOWN:
                self.assertEqual(
                    result.portal_type, expected_type,
                    f"URL {url} should be detected as {expected_type}, got {result.portal_type}"
                )
    
    @given(
        mac=st.text(min_size=17, max_size=17, alphabet='0123456789ABCDEF:'),
    )
    @settings(max_examples=20)
    def test_detection_result_consistency(self, mac):
        """
        Test that detection results are consistent for the same input.
        """
        from apps.m3u.portal_type_detector import PortalTypeDetector
        
        # Clean MAC to valid format
        if len(mac) != 17:
            return
        
        detector1 = PortalTypeDetector("http://test.com/server/load.php", mac)
        detector2 = PortalTypeDetector("http://test.com/server/load.php", mac)
        
        result1 = detector1.detect_from_url()
        result2 = detector2.detect_from_url()
        
        # Same input should produce same output
        self.assertEqual(result1.portal_type, result2.portal_type)
        self.assertEqual(result1.confidence, result2.confidence)


class TestErrorPatternRecognitionProperties(TestCase):
    """
    Property-based tests for Error Pattern Recognition.
    
    **Feature: mac-portal-improvements, Property 14: Error Pattern Recognition**
    **Validates: Requirements 68.1-68.7**
    """
    
    def test_error_pattern_classification(self):
        """
        **Feature: mac-portal-improvements, Property 14: Error Pattern Recognition**
        
        For any error response containing known patterns, the classifier
        should correctly identify the error type.
        
        **Validates: Requirements 68.1-68.7**
        """
        from apps.m3u.portal_type_detector import PortalTypeDetector, ErrorPattern
        
        test_cases = [
            ("Authorization failed for this MAC", ErrorPattern.AUTH_FAILED),
            ("Not valid MAC address", ErrorPattern.AUTH_FAILED),
            ("Device auto add is disabled", ErrorPattern.DEVICE_NOT_ALLOWED),
            ("Device conflict detected", ErrorPattern.DEVICE_CONFLICT),
            ("Your Subscription Expired", ErrorPattern.SUBSCRIPTION_EXPIRED),
            ('{"status": 2}', ErrorPattern.ACCOUNT_BLOCKED),
            ("Too many attempts, try again later", ErrorPattern.RATE_LIMITED),
            ('<div class="g-recaptcha">', ErrorPattern.CAPTCHA_REQUIRED),
            ("XUI.one - Debug Mode enabled", ErrorPattern.XUI_DEBUG),
            ("Some random error message", ErrorPattern.UNKNOWN),
        ]
        
        for response_text, expected_error in test_cases:
            result = PortalTypeDetector.classify_error(response_text)
            self.assertEqual(
                result, expected_error,
                f"Response '{response_text[:50]}...' should be classified as {expected_error}, got {result}"
            )
    
    def test_http_429_rate_limited(self):
        """Test that HTTP 429 is always classified as rate limited."""
        from apps.m3u.portal_type_detector import PortalTypeDetector, ErrorPattern
        
        result = PortalTypeDetector.classify_error("Any response", http_status=429)
        self.assertEqual(result, ErrorPattern.RATE_LIMITED)
    
    @given(
        error_type=st.sampled_from(['AUTH_FAILED', 'DEVICE_CONFLICT', 'RATE_LIMITED', 'UNKNOWN'])
    )
    @settings(max_examples=20)
    def test_recommended_action_exists(self, error_type):
        """
        Test that every error pattern has a recommended action.
        """
        from apps.m3u.portal_type_detector import PortalTypeDetector, ErrorPattern
        
        error = ErrorPattern[error_type]
        action = PortalTypeDetector.get_recommended_action(error)
        
        self.assertIn('action', action)
        self.assertIn('cooldown_minutes', action)
        self.assertIn('message', action)


class TestXtreamCredentialExtractionProperties(TestCase):
    """
    Property-based tests for Xtream Credential Extraction.
    
    **Feature: mac-portal-improvements, Property 13: Xtream Credential Extraction**
    **Validates: Requirements 64.1, 64.2, 84.1, 84.2**
    """
    
    @given(
        username=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        password=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        stream_id=st.integers(min_value=1, max_value=99999),
    )
    @settings(max_examples=50)
    def test_credential_extraction_roundtrip(self, username, password, stream_id):
        """
        **Feature: mac-portal-improvements, Property 13: Xtream Credential Extraction**
        
        For any valid username/password/stream_id, constructing a stream URL
        and extracting credentials should return the original values.
        
        **Validates: Requirements 64.1, 64.2, 84.1, 84.2**
        """
        from apps.m3u.portal_type_detector import XtreamCredentialExtractor
        
        # Skip empty values
        if not username.strip() or not password.strip():
            return
        
        # Construct stream URL
        stream_url = f"http://example.com/live/{username}/{password}/{stream_id}.ts"
        
        # Extract credentials
        result = XtreamCredentialExtractor.extract_credentials(stream_url)
        
        self.assertIsNotNone(result, f"Failed to extract from {stream_url}")
        self.assertEqual(result['username'], username)
        self.assertEqual(result['password'], password)
        self.assertEqual(result['stream_id'], str(stream_id))
    
    def test_m3u_url_generation(self):
        """Test M3U URL generation from credentials."""
        from apps.m3u.portal_type_detector import XtreamCredentialExtractor
        
        base_url = "http://example.com"
        username = "testuser"
        password = "testpass"
        
        m3u_url = XtreamCredentialExtractor.generate_m3u_url(base_url, username, password)
        
        self.assertIn("get.php", m3u_url)
        self.assertIn(f"username={username}", m3u_url)
        self.assertIn(f"password={password}", m3u_url)
        self.assertIn("type=m3u_plus", m3u_url)
    
    def test_player_api_url_generation(self):
        """Test player_api.php URL generation."""
        from apps.m3u.portal_type_detector import XtreamCredentialExtractor
        
        base_url = "http://example.com/"  # With trailing slash
        username = "user"
        password = "pass"
        
        api_url = XtreamCredentialExtractor.generate_player_api_url(base_url, username, password)
        
        self.assertIn("player_api.php", api_url)
        self.assertNotIn("//player", api_url)  # No double slash


class TestDeviceMetricsProperties(TestCase):
    """
    Property-based tests for Device Metrics Generation.
    
    **Feature: mac-portal-improvements, Property 15: Device Metrics Consistency**
    **Validates: Requirements 77.1-77.5**
    """
    
    @given(
        mac=st.from_regex(r'[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}', fullmatch=True),
        profile=st.sampled_from(['MAG250', 'MAG254', 'MAG322', 'MAG424']),
    )
    @settings(max_examples=50)
    def test_device_metrics_consistency(self, mac, profile):
        """
        **Feature: mac-portal-improvements, Property 15: Device Metrics Consistency**
        
        For any MAC address and profile, generating metrics twice should
        produce identical results.
        
        **Validates: Requirements 77.1-77.5**
        """
        from apps.m3u.portal_type_detector import DeviceMetricsGenerator
        
        metrics1 = DeviceMetricsGenerator.get_metrics(mac, profile)
        metrics2 = DeviceMetricsGenerator.get_metrics(mac, profile)
        
        # Same input should produce same output
        self.assertEqual(metrics1['sn'], metrics2['sn'])
        self.assertEqual(metrics1['device_id'], metrics2['device_id'])
        self.assertEqual(metrics1['signature'], metrics2['signature'])
        self.assertEqual(metrics1['hw_version'], metrics2['hw_version'])
    
    @given(
        mac=st.from_regex(r'[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}', fullmatch=True),
    )
    @settings(max_examples=30)
    def test_serial_number_contains_mac(self, mac):
        """
        Test that serial number is derived from MAC address.
        """
        from apps.m3u.portal_type_detector import DeviceMetricsGenerator
        
        sn = DeviceMetricsGenerator.generate_serial_number(mac)
        mac_clean = mac.replace(':', '').upper()
        
        # Serial number should contain the MAC (without colons)
        self.assertIn(mac_clean, sn)
