#!/usr/bin/env python
"""
Test script to verify empty proxy field handling.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from apps.m3u.models import M3UAccount
from core.models import StreamProfile

def test_empty_proxy_handling():
    """Test that empty proxy fields are handled correctly."""
    print("Testing Empty Proxy Field Handling")
    print("=" * 40)
    
    # Test different empty values
    test_cases = [
        (None, "None value"),
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("http://proxy:8080", "Valid proxy"),
        ("  http://proxy:8080  ", "Valid proxy with whitespace"),
    ]
    
    for proxy_value, description in test_cases:
        print(f"\nTesting: {description} -> '{proxy_value}'")
        
        # Create a test account
        account = M3UAccount(
            name=f"test_account_{description.replace(' ', '_')}",
            account_type=M3UAccount.Types.MAC,
            proxy=proxy_value
        )
        
        # Test get_proxy method
        result = account.get_proxy()
        print(f"  get_proxy() result: '{result}'")
        
        # Expected behavior
        if proxy_value and proxy_value.strip():
            expected = proxy_value.strip()
            if result == expected:
                print(f"  ✅ Correct: Returns cleaned proxy '{expected}'")
            else:
                print(f"  ❌ Error: Expected '{expected}', got '{result}'")
        else:
            if result is None:
                print(f"  ✅ Correct: Returns None for empty/invalid proxy")
            else:
                print(f"  ❌ Error: Expected None, got '{result}'")

def test_proxy_in_stream_commands():
    """Test proxy handling in stream commands."""
    print("\n\nTesting Proxy in Stream Commands")
    print("=" * 35)
    
    # Get or create a stream profile
    try:
        profile = StreamProfile.objects.filter(name="ffmpeg").first()
        if not profile:
            print("❌ No ffmpeg profile found")
            return
            
        test_url = "http://example.com/stream.m3u8"
        test_user_agent = "Dispatcharr/1.0"
        
        # Test with different proxy values
        test_cases = [
            (None, "No proxy"),
            ("", "Empty proxy"),
            ("   ", "Whitespace proxy"),
            ("http://proxy:8080", "Valid proxy"),
        ]
        
        for proxy_value, description in test_cases:
            print(f"\nTesting: {description} -> '{proxy_value}'")
            
            # Create test account
            account = M3UAccount(
                name="test_account",
                account_type=M3UAccount.Types.MAC,
                proxy=proxy_value
            )
            
            # Get proxy using get_proxy method
            account_proxy = account.get_proxy()
            print(f"  Account proxy: '{account_proxy}'")
            
            # Build command
            cmd = profile.build_command(test_url, test_user_agent, account_proxy)
            cmd_str = " ".join(cmd)
            print(f"  Command: {cmd_str}")
            
            # Check if proxy is in command
            has_proxy_param = "-http_proxy" in cmd_str
            
            if account_proxy:
                if has_proxy_param and account_proxy in cmd_str:
                    print(f"  ✅ Correct: Proxy parameter included")
                else:
                    print(f"  ❌ Error: Proxy should be included but isn't")
            else:
                if not has_proxy_param:
                    print(f"  ✅ Correct: No proxy parameter (as expected)")
                else:
                    print(f"  ❌ Error: Proxy parameter included when it shouldn't be")
                    
    except Exception as e:
        print(f"❌ Error testing stream commands: {e}")

def test_mac_portal_client_proxy():
    """Test MAC portal client proxy handling."""
    print("\n\nTesting MAC Portal Client Proxy")
    print("=" * 35)
    
    try:
        from apps.m3u.mac_portal_client import MacPortalClient
        
        test_cases = [
            (None, "No proxy"),
            ("", "Empty proxy"),
            ("   ", "Whitespace proxy"),
            ("http://proxy:8080", "Valid proxy"),
        ]
        
        for proxy_value, description in test_cases:
            print(f"\nTesting: {description} -> '{proxy_value}'")
            
            # Create client with proxy
            client = MacPortalClient(
                base_url="http://example.com",
                mac="00:1A:79:19:1F:A9",
                proxy=proxy_value
            )
            
            # Test _get_proxies method
            proxies = client._get_proxies()
            print(f"  _get_proxies() result: {proxies}")
            
            # Expected behavior
            if proxy_value and proxy_value.strip():
                if proxies and proxies.get('http') == proxy_value:
                    print(f"  ✅ Correct: Proxy configuration returned")
                else:
                    print(f"  ❌ Error: Expected proxy config, got {proxies}")
            else:
                if proxies is None:
                    print(f"  ✅ Correct: No proxy configuration (as expected)")
                else:
                    print(f"  ❌ Error: Expected None, got {proxies}")
                    
    except Exception as e:
        print(f"❌ Error testing MAC portal client: {e}")

if __name__ == "__main__":
    print("Empty Proxy Handling Test")
    print("=" * 50)
    
    # Test get_proxy method
    test_empty_proxy_handling()
    
    # Test stream commands
    test_proxy_in_stream_commands()
    
    # Test MAC portal client
    test_mac_portal_client_proxy()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nExpected behavior:")
    print("✅ Empty/None proxy fields should return None")
    print("✅ Valid proxy fields should return cleaned proxy URL")
    print("✅ Stream commands should only include proxy when valid")
    print("✅ MAC portal client should only use proxy when valid")