#!/usr/bin/env python
"""
Fix all references to account.proxy_url to use account.get_proxy() instead.
"""

import os
import re

files_to_fix = [
    'apps/m3u/api/mac_portal_api.py',
    'apps/m3u/vod_series_client.py',
]

def fix_file(filepath):
    """Replace proxy_url with get_proxy() in a file."""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count occurrences before
    before_count = content.count('proxy=account.proxy_url')
    
    if before_count == 0:
        print(f"✓ {filepath} - No changes needed")
        return True
    
    # Replace all occurrences
    new_content = content.replace('proxy=account.proxy_url', 'proxy=account.get_proxy()')
    
    # Count occurrences after
    after_count = new_content.count('proxy=account.proxy_url')
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ {filepath} - Replaced {before_count} occurrence(s)")
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Fixing proxy_url references")
    print("=" * 60)
    print()
    
    success_count = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            success_count += 1
    
    print()
    print("=" * 60)
    print(f"✓ Fixed {success_count}/{len(files_to_fix)} files")
    print("=" * 60)
    print()
    print("Changes made:")
    print("  proxy=account.proxy_url  →  proxy=account.get_proxy()")
    print()
    print("This ensures that:")
    print("  - MAC accounts use the 'proxy' field")
    print("  - STD/XC accounts use the 'proxy_std_xc' field")
    print("  - Empty proxies are handled correctly (return None)")
