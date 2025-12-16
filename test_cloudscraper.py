#!/usr/bin/env python3
"""
Test script to verify cloudscraper installation and functionality
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cloudscraper_import():
    """Test if cloudscraper can be imported"""
    try:
        import cloudscraper
        print("✅ cloudscraper imported successfully")
        return True
    except ImportError as e:
        print(f"❌ cloudscraper import failed: {e}")
        return False

def test_cloudscraper_session():
    """Test if cloudscraper session can be created"""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'linux',
                'desktop': True
            }
        )
        print("✅ cloudscraper session created successfully")
        return True
    except Exception as e:
        print(f"❌ cloudscraper session creation failed: {e}")
        return False

def test_mac_portal_client():
    """Test if MAC portal client can be imported with cloudscraper"""
    try:
        from apps.m3u.mac_portal_client import MacPortalClient, CLOUDSCRAPER_AVAILABLE
        print(f"✅ MAC portal client imported successfully")
        print(f"   CLOUDSCRAPER_AVAILABLE: {CLOUDSCRAPER_AVAILABLE}")
        return True
    except Exception as e:
        print(f"❌ MAC portal client import failed: {e}")
        return False

def main():
    print("Testing cloudscraper installation and integration...")
    print("=" * 50)
    
    success = True
    success &= test_cloudscraper_import()
    success &= test_cloudscraper_session()
    success &= test_mac_portal_client()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! Cloudscraper is ready for use.")
    else:
        print("❌ Some tests failed. Please install cloudscraper:")
        print("   pip install cloudscraper")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())