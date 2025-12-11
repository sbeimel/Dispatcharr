#!/usr/bin/env python3
"""
Test script to verify MAC failover functionality.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from apps.m3u.models import M3UAccount, M3UAccountMac
from apps.proxy.ts_proxy.failover_utils import FailoverManager
from apps.proxy.ts_proxy.url_utils import _resolve_mac_stream_with_failover
from apps.channels.models import Channel, Stream
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mac_failover():
    """Test MAC failover functionality."""
    
    print("=== MAC Failover Test ===")
    
    # Find MAC accounts
    mac_accounts = M3UAccount.objects.filter(account_type=M3UAccount.Types.MAC)
    
    if not mac_accounts.exists():
        print("❌ No MAC accounts found")
        return False
    
    print(f"✅ Found {mac_accounts.count()} MAC account(s)")
    
    for account in mac_accounts:
        print(f"\n--- Testing Account: {account.name} ---")
        print(f"Server URL: {account.server_url}")
        print(f"MAC Address Field: {account.mac_address}")
        
        # Test get_candidate_macs_for_streaming method
        try:
            candidates = account.get_candidate_macs_for_streaming()
            print(f"✅ get_candidate_macs_for_streaming() returned {len(candidates)} candidates")
            
            for i, mac in enumerate(candidates):
                print(f"  {i+1}. {mac.address} (status: {mac.status}, priority: {mac.priority})")
                
        except Exception as e:
            print(f"❌ get_candidate_macs_for_streaming() failed: {e}")
            continue
        
        # Test with a sample stream if available
        streams = Stream.objects.filter(m3u_account=account)[:1]
        if streams.exists():
            stream = streams.first()
            print(f"\n--- Testing Stream Resolution: {stream.name} ---")
            
            try:
                stream_url, mac_used, error = _resolve_mac_stream_with_failover(account, stream)
                if stream_url:
                    print(f"✅ Stream resolved successfully")
                    print(f"   URL: {stream_url[:80]}...")
                    print(f"   MAC used: {mac_used.address if mac_used else 'None'}")
                else:
                    print(f"❌ Stream resolution failed: {error}")
            except Exception as e:
                print(f"❌ Stream resolution error: {e}")
        else:
            print("⚠️  No streams found for this account")
    
    return True

def test_failover_manager():
    """Test FailoverManager functionality."""
    
    print("\n=== FailoverManager Test ===")
    
    # Find a channel with MAC streams
    channels = Channel.objects.filter(streams__m3u_account__account_type=M3UAccount.Types.MAC)[:1]
    
    if not channels.exists():
        print("❌ No channels with MAC streams found")
        return False
    
    channel = channels.first()
    print(f"✅ Testing with channel: {channel.name}")
    
    try:
        manager = FailoverManager(str(channel.uuid))
        stream_url, profile_id, error = manager.get_stream_with_failover()
        
        if stream_url:
            print(f"✅ FailoverManager resolved stream successfully")
            print(f"   URL: {stream_url[:80]}...")
            print(f"   Profile ID: {profile_id}")
        else:
            print(f"❌ FailoverManager failed: {error}")
            
    except Exception as e:
        print(f"❌ FailoverManager error: {e}")
        import traceback
        traceback.print_exc()
    
    return True

if __name__ == "__main__":
    print("Starting MAC failover tests...\n")
    
    success = True
    success &= test_mac_failover()
    success &= test_failover_manager()
    
    print(f"\n=== Test Results ===")
    if success:
        print("✅ All tests completed (check individual results above)")
    else:
        print("❌ Some tests failed")
    
    print("\nDone.")