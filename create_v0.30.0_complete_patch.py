#!/usr/bin/env python3
"""
Create comprehensive patch file for v0.30.0 implementation
Includes: HTTP Proxy, Cooldown System, Extended Timeouts, UUID Validation, 
          Adaptive Health Monitor, VOD Proxy Support, Extended Timeouts Frontend
"""

import subprocess
import sys
from pathlib import Path

def run_git_diff(file_path, base_dir="Dispatcharr-0.30.0"):
    """Run git diff for a single file"""
    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "/dev/null", str(file_path)],
            capture_output=True,
            text=True,
            cwd="."
        )
        # For new files, git diff --no-index returns non-zero
        # Check if file exists in git
        check_result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(file_path)],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if check_result.returncode == 0:
            # File is tracked, get normal diff
            result = subprocess.run(
                ["git", "diff", "HEAD", str(file_path)],
                capture_output=True,
                text=True,
                cwd="."
            )
            return result.stdout
        else:
            # New file, create diff from /dev/null
            result = subprocess.run(
                ["git", "diff", "--no-index", "/dev/null", str(file_path)],
                capture_output=True,
                text=True,
                cwd="."
            )
            # Clean up the path in diff output
            diff_output = result.stdout
            diff_output = diff_output.replace("/dev/null", f"a/{file_path}")
            diff_output = diff_output.replace(f"b/{file_path}", f"b/{file_path}")
            return diff_output
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return ""

def create_comprehensive_patch():
    """Create comprehensive patch file"""
    
    # Define all modified files
    backend_files = [
        # Core
        "Dispatcharr-0.30.0/core/utils.py",
        "Dispatcharr-0.30.0/core/models.py",
        "Dispatcharr-0.30.0/core/xtream_codes.py",
        
        # M3U
        "Dispatcharr-0.30.0/apps/m3u/models.py",
        "Dispatcharr-0.30.0/apps/m3u/serializers.py",
        "Dispatcharr-0.30.0/apps/m3u/tasks.py",
        "Dispatcharr-0.30.0/apps/m3u/migrations/0020_m3uaccount_proxy.py",
        "Dispatcharr-0.30.0/apps/m3u/migrations/0021_m3uaccount_proxy_for_api.py",
        
        # VOD
        "Dispatcharr-0.30.0/apps/vod/tasks.py",
        
        # Proxy
        "Dispatcharr-0.30.0/apps/proxy/config.py",
        "Dispatcharr-0.30.0/apps/proxy/live_proxy/config_helper.py",
        "Dispatcharr-0.30.0/apps/proxy/live_proxy/redis_keys.py",
        "Dispatcharr-0.30.0/apps/proxy/live_proxy/input/http_streamer.py",
        "Dispatcharr-0.30.0/apps/proxy/live_proxy/input/manager.py",
        
        # VOD Proxy (NEW)
        "Dispatcharr-0.30.0/apps/proxy/vod_proxy/multi_worker_connection_manager.py",
    ]
    
    frontend_files = [
        "Dispatcharr-0.30.0/frontend/src/constants.js",
        "Dispatcharr-0.30.0/frontend/src/components/forms/M3U.jsx",
        "Dispatcharr-0.30.0/frontend/src/components/forms/settings/ProxySettingsForm.jsx",
        "Dispatcharr-0.30.0/frontend/src/utils/forms/settings/ProxySettingsFormUtils.js",
    ]
    
    all_files = backend_files + frontend_files
    
    print("Creating comprehensive patch file...")
    print(f"Processing {len(all_files)} files...")
    
    patch_content = []
    patch_content.append("# Dispatcharr v0.30.0 - Complete Implementation Patch\n")
    patch_content.append("# Features:\n")
    patch_content.append("#   - HTTP Proxy for Live TV + VOD Streaming\n")
    patch_content.append("#   - HTTP Proxy for XC API Calls\n")
    patch_content.append("#   - Stream Cooldown System (Redis-based)\n")
    patch_content.append("#   - Extended Timeouts (13 settings, DB-backed)\n")
    patch_content.append("#   - UUID Validation in system logging\n")
    patch_content.append("#   - Adaptive Health Monitor\n")
    patch_content.append("#   - VOD Proxy Support (NEW)\n")
    patch_content.append("#   - Extended Timeouts Frontend UI (NEW)\n")
    patch_content.append("#\n")
    patch_content.append(f"# Files modified: {len(all_files)}\n")
    patch_content.append("#   - Backend: 15 files (including 2 migrations)\n")
    patch_content.append("#   - Frontend: 4 files\n")
    patch_content.append("#\n")
    patch_content.append("# Apply with: git apply dispatcharr_v0.30.0_complete_implementation.patch\n")
    patch_content.append("# Or use: patch -p1 < dispatcharr_v0.30.0_complete_implementation.patch\n")
    patch_content.append("\n")
    
    for file_path in all_files:
        print(f"  Processing: {file_path}")
        diff = run_git_diff(file_path)
        if diff:
            patch_content.append(diff)
            if not diff.endswith("\n"):
                patch_content.append("\n")
    
    # Write patch file
    patch_file = Path("dispatcharr_v0.30.0_complete_implementation.patch")
    with open(patch_file, "w", encoding="utf-8") as f:
        f.write("".join(patch_content))
    
    print(f"\n✓ Patch file created: {patch_file}")
    print(f"  Size: {patch_file.stat().st_size / 1024:.1f} KB")
    print(f"  Files: {len(all_files)}")
    
    # Count lines
    with open(patch_file, "r", encoding="utf-8") as f:
        lines = len(f.readlines())
    print(f"  Lines: {lines}")
    
    return True

if __name__ == "__main__":
    try:
        success = create_comprehensive_patch()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
