#!/usr/bin/env python3
"""
Install cloudscraper for Cloudflare bypass functionality
"""

import subprocess
import sys
import os

def install_cloudscraper():
    """Install cloudscraper using pip"""
    try:
        print("Installing cloudscraper...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "cloudscraper==1.2.71"
        ], capture_output=True, text=True, check=True)
        
        print("✅ cloudscraper installed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install cloudscraper: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error installing cloudscraper: {e}")
        return False

def verify_installation():
    """Verify that cloudscraper was installed correctly"""
    try:
        import cloudscraper
        print(f"✅ cloudscraper version: {cloudscraper.__version__}")
        
        # Test creating a scraper
        scraper = cloudscraper.create_scraper()
        print("✅ cloudscraper session creation test passed")
        return True
    except ImportError:
        print("❌ cloudscraper still not available after installation")
        return False
    except Exception as e:
        print(f"❌ cloudscraper verification failed: {e}")
        return False

def main():
    print("Cloudscraper Installation Script")
    print("=" * 40)
    
    # Check if already installed
    try:
        import cloudscraper
        print(f"✅ cloudscraper is already installed (version: {cloudscraper.__version__})")
        return 0
    except ImportError:
        print("cloudscraper not found, installing...")
    
    # Install cloudscraper
    if not install_cloudscraper():
        return 1
    
    # Verify installation
    if not verify_installation():
        return 1
    
    print("=" * 40)
    print("✅ Installation completed successfully!")
    print("You can now restart Dispatcharr to use Cloudflare bypass functionality.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())