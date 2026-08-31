#!/usr/bin/env python3
"""
Complete Feature Parity Check: v0.27.0 → v0.30.0
Verifies ALL features from patches are present in v0.30.0
"""

import os
import re

# Critical features to check (from all patches)
FEATURES_TO_CHECK = {
    # M3U Proxy Features
    "apps/m3u/models.py": [
        "proxy = models.CharField",
        "proxy_for_api = models.BooleanField",
        "def get_proxy_for_api",
        "def get_proxy_for_streaming",
    ],
    "apps/m3u/serializers.py": [
        '"proxy"',
        '"proxy_for_api"',
    ],
    "apps/m3u/tasks.py": [
        "account.get_proxy_for_api()",
        "proxies = {",
    ],
    
    # Cooldown System
    "apps/proxy/live_proxy/url_utils.py": [
        "cooldown_skip_profiles",
        "profile:*:cooldown",
        "len(parts) >= 8",
    ],
    "apps/channels/models.py": [
        "cooldown_skip_profiles=None",
        "if profile.id in cooldown_skip_profiles:",
    ],
    "apps/proxy/live_proxy/server.py": [
        "if key_str.endswith(':cooldown'):",
        "cooldown_keys.append",
    ],
    "apps/proxy/live_proxy/input/manager.py": [
        "profile:*:cooldown",
    ],
    
    # VOD Proxy
    "apps/vod/tasks.py": [
        "account.get_proxy_for_api()",
    ],
    
    # XC Client Proxy
    "core/xtream_codes.py": [
        "self.session.proxies",
        "proxy=",
    ],
    
    # EPG Proxy
    "apps/epg/tasks.py": [
        "custom_properties.get('http_proxy')",
        "proxies =",
    ],
    
    # Frontend
    "frontend/src/components/forms/M3U.jsx": [
        "proxy:",
        "proxy_for_api:",
    ],
    "frontend/src/components/forms/EPG.jsx": [
        "http_proxy:",
    ],
}

def check_file(filepath, patterns):
    """Check if all patterns exist in file"""
    if not os.path.exists(filepath):
        return {"exists": False, "patterns": {}}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        results = {}
        for pattern in patterns:
            # Escape regex special chars but allow wildcards
            escaped = pattern.replace('*', '.*').replace('(', r'\(').replace(')', r'\)')
            found = bool(re.search(escaped, content))
            results[pattern] = found
        
        return {"exists": True, "patterns": results}
    except Exception as e:
        return {"exists": True, "error": str(e), "patterns": {}}

def main():
    print("=" * 100)
    print("COMPLETE FEATURE PARITY CHECK: v0.27.0 → v0.30.0")
    print("=" * 100)
    print()
    
    v027_root = "Dispatcharr - 27.0"
    v030_root = "."
    
    all_ok = True
    missing_features = []
    
    for file_path, patterns in FEATURES_TO_CHECK.items():
        print(f"\n📁 {file_path}")
        print("-" * 100)
        
        # Check v0.27.0
        v027_path = os.path.join(v027_root, file_path)
        v027_results = check_file(v027_path, patterns)
        
        # Check v0.30.0
        v030_path = os.path.join(v030_root, file_path)
        v030_results = check_file(v030_path, patterns)
        
        if not v027_results["exists"]:
            print(f"  ⚠️  File not found in v0.27.0")
            continue
        
        if not v030_results["exists"]:
            print(f"  ❌ File not found in v0.30.0!")
            all_ok = False
            continue
        
        # Compare patterns
        for pattern in patterns:
            v027_has = v027_results["patterns"].get(pattern, False)
            v030_has = v030_results["patterns"].get(pattern, False)
            
            if v027_has and not v030_has:
                status = "❌ MISSING"
                all_ok = False
                missing_features.append({
                    "file": file_path,
                    "pattern": pattern
                })
            elif not v027_has and not v030_has:
                status = "⚪ Not in v0.27.0"
            elif v027_has and v030_has:
                status = "✅ Present"
            else:
                status = "✨ New in v0.30.0"
            
            print(f"  {status:20s} {pattern}")
    
    print("\n")
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    if all_ok:
        print("✅ ALL FEATURES FROM v0.27.0 ARE PRESENT IN v0.30.0!")
    else:
        print(f"❌ FOUND {len(missing_features)} MISSING FEATURES:")
        print()
        for item in missing_features:
            print(f"  ❌ {item['file']}")
            print(f"     Pattern: {item['pattern']}")
            print()
    
    print("=" * 100)
    return 0 if all_ok else 1

if __name__ == '__main__':
    exit(main())
