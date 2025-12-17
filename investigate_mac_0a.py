#!/usr/bin/env python
"""
Investigation script to check why MAC :0A is not being tried during failover.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.m3u.models import M3UAccount, M3UAccountMac
from django.utils import timezone
from core.utils import RedisClient

def investigate_mac_0a():
    """Check MAC :0A status and availability."""
    
    print("=" * 80)
    print("MAC :0A Investigation")
    print("=" * 80)
    print()
    
    # Find MAC :0A
    macs = M3UAccountMac.objects.filter(address__icontains=':0A')
    
    if not macs.exists():
        print("❌ MAC :0A not found in database!")
        return
    
    for mac in macs:
        print(f"Found MAC: {mac.address}")
        print(f"  ID: {mac.id}")
        print(f"  Status: {mac.status}")
        print(f"  Priority: {mac.priority}")
        print(f"  Expires At: {mac.expires_at}")
        print(f"  Last Checked: {mac.last_checked}")
        print(f"  Last Error: {mac.last_error}")
        print()
        
        # Check M3U Account
        account = mac.m3u_account
        print(f"M3U Account:")
        print(f"  ID: {account.id}")
        print(f"  Name: {account.name}")
        print(f"  Type: {account.account_type}")
        print(f"  Active: {account.is_active}")
        print()
        
        # Check if expired
        now = timezone.now()
        if mac.expires_at and mac.expires_at <= now:
            print(f"⚠️  MAC is EXPIRED (expires_at: {mac.expires_at} <= now: {now})")
        else:
            print(f"✅ MAC expiry is OK (expires_at: {mac.expires_at})")
        print()
        
        # Check status
        if mac.status == M3UAccountMac.Status.EXPIRED:
            print("⚠️  MAC status is EXPIRED")
        elif mac.status == M3UAccountMac.Status.ERROR:
            print("⚠️  MAC status is ERROR")
        elif mac.status == M3UAccountMac.Status.VALID:
            print("✅ MAC status is VALID")
        else:
            print(f"⚠️  MAC status is {mac.status}")
        print()
        
        # Check Redis BUSY status
        try:
            redis_client = RedisClient.get_client()
            if redis_client:
                busy_key = f"mac_busy:{mac.id}"
                is_busy = redis_client.exists(busy_key)
                if is_busy:
                    ttl = redis_client.ttl(busy_key)
                    print(f"⚠️  MAC is BUSY in Redis (TTL: {ttl} seconds)")
                else:
                    print("✅ MAC is NOT busy in Redis")
            else:
                print("⚠️  Redis not available")
        except Exception as e:
            print(f"⚠️  Error checking Redis: {e}")
        print()
        
        # Check all MACs in same account
        print(f"All MACs in account {account.name}:")
        all_macs = account.macs.order_by('priority', 'id')
        for m in all_macs:
            status_icon = "✅" if m.status == M3UAccountMac.Status.VALID else "⚠️"
            busy_icon = ""
            try:
                if redis_client and redis_client.exists(f"mac_busy:{m.id}"):
                    busy_icon = " [BUSY]"
            except:
                pass
            print(f"  {status_icon} {m.address} (priority: {m.priority}, status: {m.status}){busy_icon}")
        print()
        
        # Check candidate MACs
        print("Candidate MACs for streaming:")
        candidates = account.get_candidate_macs_for_streaming()
        if candidates:
            for c in candidates:
                print(f"  ✅ {c.address} (priority: {c.priority})")
        else:
            print("  ❌ No candidate MACs available!")
        print()
        
        # Check if MAC :0A is in candidates
        mac_in_candidates = any(c.id == mac.id for c in candidates)
        if mac_in_candidates:
            print(f"✅ MAC :0A IS in candidate list (will be tried)")
        else:
            print(f"❌ MAC :0A is NOT in candidate list (will be skipped)")
            print()
            print("Reasons why MAC might be skipped:")
            if mac.status == M3UAccountMac.Status.EXPIRED:
                print("  - Status is EXPIRED")
            if mac.status == M3UAccountMac.Status.ERROR:
                print("  - Status is ERROR")
            if mac.expires_at and mac.expires_at <= now:
                print(f"  - Expiry date is in the past ({mac.expires_at})")
        print()
    
    print("=" * 80)
    print("Investigation Complete")
    print("=" * 80)

if __name__ == '__main__':
    investigate_mac_0a()
