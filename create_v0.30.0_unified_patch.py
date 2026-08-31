#!/usr/bin/env python3
"""
Create unified patch file for v0.30.0 implementation
Uses direct file comparison
"""

import os
import sys
from pathlib import Path
import difflib
from datetime import datetime

def create_unified_diff(original_file, modified_file, label):
    """Create unified diff between two files"""
    try:
        if not os.path.exists(original_file):
            # New file
            with open(modified_file, 'r', encoding='utf-8') as f:
                modified_lines = f.readlines()
            
            diff_lines = [
                f"--- /dev/null\n",
                f"+++ {label}\n",
                f"@@ -0,0 +1,{len(modified_lines)} @@\n"
            ]
            for line in modified_lines:
                diff_lines.append(f"+{line}")
            return ''.join(diff_lines)
        
        # Existing file - compare
        with open(original_file, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        with open(modified_file, 'r', encoding='utf-8') as f:
            modified_lines = f.readlines()
        
        if original_lines == modified_lines:
            return ""  # No changes
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
            lineterm=''
        )
        
        return '\n'.join(diff) + '\n'
        
    except Exception as e:
        print(f"Error creating diff for {label}: {e}")
        return ""

def main():
    """Create comprehensive patch"""
    
    # Files to include (modified_path, original_path_relative, label)
    files = [
        # Core
        ("Dispatcharr-0.30.0/core/utils.py", "core/utils.py", "core/utils.py"),
        ("Dispatcharr-0.30.0/core/models.py", "core/models.py", "core/models.py"),
        ("Dispatcharr-0.30.0/core/xtream_codes.py", "core/xtream_codes.py", "core/xtream_codes.py"),
        
        # M3U
        ("Dispatcharr-0.30.0/apps/m3u/models.py", "apps/m3u/models.py", "apps/m3u/models.py"),
        ("Dispatcharr-0.30.0/apps/m3u/serializers.py", "apps/m3u/serializers.py", "apps/m3u/serializers.py"),
        ("Dispatcharr-0.30.0/apps/m3u/tasks.py", "apps/m3u/tasks.py", "apps/m3u/tasks.py"),
        ("Dispatcharr-0.30.0/apps/m3u/migrations/0020_m3uaccount_proxy.py", "", "apps/m3u/migrations/0020_m3uaccount_proxy.py"),
        ("Dispatcharr-0.30.0/apps/m3u/migrations/0021_m3uaccount_proxy_for_api.py", "", "apps/m3u/migrations/0021_m3uaccount_proxy_for_api.py"),
        
        # VOD
        ("Dispatcharr-0.30.0/apps/vod/tasks.py", "apps/vod/tasks.py", "apps/vod/tasks.py"),
        
        # Proxy
        ("Dispatcharr-0.30.0/apps/proxy/config.py", "apps/proxy/config.py", "apps/proxy/config.py"),
        ("Dispatcharr-0.30.0/apps/proxy/live_proxy/config_helper.py", "apps/proxy/live_proxy/config_helper.py", "apps/proxy/live_proxy/config_helper.py"),
        ("Dispatcharr-0.30.0/apps/proxy/live_proxy/redis_keys.py", "apps/proxy/live_proxy/redis_keys.py", "apps/proxy/live_proxy/redis_keys.py"),
        ("Dispatcharr-0.30.0/apps/proxy/live_proxy/url_utils.py", "apps/proxy/live_proxy/url_utils.py", "apps/proxy/live_proxy/url_utils.py"),
        ("Dispatcharr-0.30.0/apps/proxy/live_proxy/input/http_streamer.py", "apps/proxy/live_proxy/input/http_streamer.py", "apps/proxy/live_proxy/input/http_streamer.py"),
        ("Dispatcharr-0.30.0/apps/proxy/live_proxy/input/manager.py", "apps/proxy/live_proxy/input/manager.py", "apps/proxy/live_proxy/input/manager.py"),
        ("Dispatcharr-0.30.0/apps/proxy/vod_proxy/multi_worker_connection_manager.py", "apps/proxy/vod_proxy/multi_worker_connection_manager.py", "apps/proxy/vod_proxy/multi_worker_connection_manager.py"),
        
        # Frontend
        ("Dispatcharr-0.30.0/frontend/src/constants.js", "frontend/src/constants.js", "frontend/src/constants.js"),
        ("Dispatcharr-0.30.0/frontend/src/components/forms/M3U.jsx", "frontend/src/components/forms/M3U.jsx", "frontend/src/components/forms/M3U.jsx"),
        ("Dispatcharr-0.30.0/frontend/src/components/forms/settings/ProxySettingsForm.jsx", "frontend/src/components/forms/settings/ProxySettingsForm.jsx", "frontend/src/components/forms/settings/ProxySettingsForm.jsx"),
        ("Dispatcharr-0.30.0/frontend/src/utils/forms/settings/ProxySettingsFormUtils.js", "frontend/src/utils/forms/settings/ProxySettingsFormUtils.js", "frontend/src/utils/forms/settings/ProxySettingsFormUtils.js"),
    ]
    
    print("Creating comprehensive v0.30.0 patch file...")
    print(f"Processing {len(files)} files...")
    
    patch_lines = []
    patch_lines.append("# Dispatcharr v0.30.0 - Complete Implementation Patch\n")
    patch_lines.append("#\n")
    patch_lines.append("# Features Implemented:\n")
    patch_lines.append("#   ✓ HTTP Proxy for Live TV Streaming\n")
    patch_lines.append("#   ✓ HTTP Proxy for VOD Streaming (NEW)\n")
    patch_lines.append("#   ✓ HTTP Proxy for XC API Calls\n")
    patch_lines.append("#   ✓ Stream Cooldown System (Redis-based)\n")
    patch_lines.append("#   ✓ Extended Timeouts (13 settings, DB-backed)\n")
    patch_lines.append("#   ✓ Extended Timeouts Frontend UI (NEW)\n")
    patch_lines.append("#   ✓ UUID Validation in system logging\n")
    patch_lines.append("#   ✓ Adaptive Health Monitor\n")
    patch_lines.append("#   ✓ Stream Preview Failover (NEW)\n")
    patch_lines.append("#\n")
    patch_lines.append(f"# Files Modified: {len(files)}\n")
    patch_lines.append("#   - Backend: 16 files (14 modified + 2 new migrations)\n")
    patch_lines.append("#   - Frontend: 4 files (3 modified + 1 new)\n")
    patch_lines.append("#\n")
    patch_lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    patch_lines.append("#\n")
    patch_lines.append("# Apply with:\n")
    patch_lines.append("#   cd /path/to/Dispatcharr\n")
    patch_lines.append("#   patch -p1 < dispatcharr_v0.30.0_complete_implementation.patch\n")
    patch_lines.append("#\n")
    patch_lines.append("# Or with git:\n")
    patch_lines.append("#   git apply dispatcharr_v0.30.0_complete_implementation.patch\n")
    patch_lines.append("#\n")
    patch_lines.append("\n")
    
    files_with_changes = 0
    
    for modified_path, original_path, label in files:
        if not os.path.exists(modified_path):
            print(f"  SKIP: {modified_path} (not found)")
            continue
            
        print(f"  Processing: {label}")
        
        # Get diff
        if original_path:
            diff = create_unified_diff(original_path, modified_path, label)
        else:
            # New file (migrations)
            diff = create_unified_diff("", modified_path, label)
        
        if diff:
            patch_lines.append(diff)
            if not diff.endswith('\n'):
                patch_lines.append('\n')
            files_with_changes += 1
        else:
            print(f"    (no changes)")
    
    # Write patch
    patch_file = Path("dispatcharr_v0.30.0_complete_implementation.patch")
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(''.join(patch_lines))
    
    print(f"\n✓ Patch file created: {patch_file}")
    print(f"  Size: {patch_file.stat().st_size / 1024:.1f} KB")
    print(f"  Files with changes: {files_with_changes}/{len(files)}")
    
    with open(patch_file, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())
    print(f"  Total lines: {lines}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
