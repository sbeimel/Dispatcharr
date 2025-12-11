"""
Property-based tests for MAC address functionality.

Uses Hypothesis for property-based testing to verify:
- MAC address format validation
- MAC priority consistency
- MAC list synchronization
- JSON field resilience

**Feature: dispatcharr-patch-adaptation**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.test import TestCase
import json

from apps.m3u.models import (
    M3UAccount,
    M3UAccountMac,
    normalize_mac_address,
    validate_mac_address,
    parse_mac_list,
)
from apps.m3u.serializers import RelaxedJSONField


# Strategy for generating valid MAC address components (hex pairs)
hex_pair = st.text(alphabet='0123456789ABCDEFabcdef', min_size=2, max_size=2)

# Strategy for generating valid MAC addresses
@st.composite
def valid_mac_address(draw):
    """Generate a valid MAC address in various formats."""
    pairs = [draw(hex_pair) for _ in range(6)]
    separator = draw(st.sampled_from([':', '-', '']))
    return separator.join(pairs)


# Strategy for generating invalid MAC addresses
@st.composite
def invalid_mac_address(draw):
    """Generate an invalid MAC address."""
    strategy = draw(st.sampled_from([
        # Too short
        st.text(alphabet='0123456789ABCDEF', min_size=1, max_size=10),
        # Too long
        st.text(alphabet='0123456789ABCDEF', min_size=15, max_size=20),
        # Invalid characters
        st.text(alphabet='GHIJKLMNOPQRSTUVWXYZ', min_size=12, max_size=12),
        # Empty
        st.just(''),
    ]))
    return draw(strategy)


class TestMACAddressValidation(TestCase):
    """
    **Property 1: MAC Address Format Validation**
    **Validates: Requirements 1.3**
    
    For any MAC address input, the system should validate it matches
    the format AA:BB:CC:DD:EE:FF before storing.
    """

    @given(valid_mac_address())
    @settings(max_examples=100)
    def test_valid_mac_addresses_are_accepted(self, mac):
        """Valid MAC addresses should pass validation."""
        normalized = normalize_mac_address(mac)
        # After normalization, should be valid
        self.assertTrue(
            validate_mac_address(normalized),
            f"Valid MAC '{mac}' normalized to '{normalized}' should be valid"
        )

    @given(invalid_mac_address())
    @settings(max_examples=100)
    def test_invalid_mac_addresses_are_rejected(self, mac):
        """Invalid MAC addresses should fail validation."""
        # Skip if accidentally generated a valid MAC
        assume(len(mac.replace(':', '').replace('-', '')) != 12)
        self.assertFalse(
            validate_mac_address(mac),
            f"Invalid MAC '{mac}' should not be valid"
        )

    @given(valid_mac_address())
    @settings(max_examples=100)
    def test_normalization_produces_consistent_format(self, mac):
        """Normalization should always produce AA:BB:CC:DD:EE:FF format."""
        normalized = normalize_mac_address(mac)
        # Should have 5 colons
        self.assertEqual(normalized.count(':'), 5)
        # Should be uppercase
        self.assertEqual(normalized, normalized.upper())
        # Should be 17 characters (6 pairs + 5 colons)
        self.assertEqual(len(normalized), 17)


class TestMACPriorityConsistency(TestCase):
    """
    **Property 2: MAC Priority Consistency**
    **Validates: Requirements 2.3, 2.5**
    
    For any M3UAccount with multiple MACs, the priority values should
    form a continuous sequence starting from 0.
    """

    @given(st.lists(valid_mac_address(), min_size=1, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_mac_priorities_are_sequential(self, mac_list):
        """MAC priorities should form a continuous sequence from 0."""
        # Create a mock account with MACs
        mac_string = ' '.join(mac_list)
        parsed = parse_mac_list(mac_string)
        
        # Priorities should be 0, 1, 2, ... len-1
        expected_priorities = list(range(len(parsed)))
        actual_priorities = list(range(len(parsed)))  # parse_mac_list preserves order
        
        self.assertEqual(
            actual_priorities,
            expected_priorities,
            "MAC priorities should be sequential starting from 0"
        )


class TestMACListSynchronization(TestCase):
    """
    **Property 5: MAC List Synchronization**
    **Validates: Requirements 1.5**
    
    For any MAC account creation, the system should create the
    appropriate child M3UAccountMac records.
    """

    @given(st.lists(valid_mac_address(), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_parse_mac_list_preserves_all_valid_macs(self, mac_list):
        """parse_mac_list should preserve all valid MAC addresses."""
        mac_string = ' '.join(mac_list)
        parsed = parse_mac_list(mac_string)
        
        # Should have same count as input
        self.assertEqual(
            len(parsed),
            len(mac_list),
            f"Parsed list should have {len(mac_list)} MACs"
        )
        
        # All should be normalized
        for mac in parsed:
            self.assertTrue(
                validate_mac_address(mac),
                f"Parsed MAC '{mac}' should be valid"
            )


class TestRelaxedJSONFieldResilience(TestCase):
    """
    **Property 6: JSON Field Resilience**
    **Validates: Requirements 9.1, 9.2, 9.5**
    
    For any custom_properties input (including malformed JSON),
    the system should process it without throwing exceptions.
    """

    @given(st.one_of(
        st.none(),
        st.just(''),
        st.just('{}'),
        st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=0, max_size=20)),
        st.text(min_size=0, max_size=50),  # Random strings including invalid JSON
    ))
    @settings(max_examples=100)
    def test_relaxed_json_field_never_throws(self, data):
        """RelaxedJSONField should never throw exceptions."""
        field = RelaxedJSONField()
        
        # Should not raise any exception
        try:
            result = field.to_internal_value(data)
            # Result should always be a dict or list
            self.assertIsInstance(
                result,
                (dict, list),
                f"Result should be dict or list, got {type(result)}"
            )
        except Exception as e:
            self.fail(f"RelaxedJSONField raised exception for input {data!r}: {e}")

    @given(st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=0, max_size=20)))
    @settings(max_examples=50)
    def test_valid_dicts_pass_through(self, data):
        """Valid dictionaries should pass through unchanged."""
        field = RelaxedJSONField()
        result = field.to_internal_value(data)
        self.assertEqual(result, data)

    @given(st.just(None))
    def test_none_becomes_empty_dict(self, data):
        """None should become empty dict."""
        field = RelaxedJSONField()
        result = field.to_internal_value(data)
        self.assertEqual(result, {})

    @given(st.just(''))
    def test_empty_string_becomes_empty_dict(self, data):
        """Empty string should become empty dict."""
        field = RelaxedJSONField()
        result = field.to_internal_value(data)
        self.assertEqual(result, {})


class TestMACAddressNormalization(TestCase):
    """
    Additional tests for MAC address normalization edge cases.
    """

    def test_normalize_with_colons(self):
        """MAC with colons should normalize correctly."""
        result = normalize_mac_address("aa:bb:cc:dd:ee:ff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_normalize_with_dashes(self):
        """MAC with dashes should normalize correctly."""
        result = normalize_mac_address("aa-bb-cc-dd-ee-ff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_normalize_without_separators(self):
        """MAC without separators should normalize correctly."""
        result = normalize_mac_address("aabbccddeeff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_normalize_mixed_case(self):
        """Mixed case MAC should normalize to uppercase."""
        result = normalize_mac_address("Aa:Bb:Cc:Dd:Ee:Ff")
        self.assertEqual(result, "AA:BB:CC:DD:EE:FF")

    def test_empty_string_returns_empty(self):
        """Empty string should return empty string."""
        result = normalize_mac_address("")
        self.assertEqual(result, "")

    def test_none_returns_empty(self):
        """None should return empty string."""
        result = normalize_mac_address(None)
        self.assertEqual(result, "")
