#!/usr/bin/env python3
"""
Verification script for v0.31.0 Cooldown on Disconnect patch
Checks if all changes were applied correctly
"""

import re
import sys

def check_file_changes(filepath, checks, file_desc):
    """Check if expected patterns exist in file"""
    print(f"\n--- {file_desc} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_pass = True
        for pattern, description in checks:
            if re.search(pattern, content, re.MULTILINE):
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - MISSING")
                all_pass = False
        
        return all_pass
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return False
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def main():
    print("=" * 80)
    print("DISPATCHARR v0.31.0 PATCH VERIFICATION")
    print("Cooldown on Disconnect & Buffering Enhancement")
    print("=" * 80)
    
    all_checks_passed = True
    
    # Backend Checks
    print("\n" + "=" * 80)
    print("BACKEND VERIFICATION")
    print("=" * 80)
    
    # 1. core/models.py
    backend1_checks = [
        (r'"stream_cooldown_on_buffering":\s*True', 
         'Setting: stream_cooldown_on_buffering'),
        (r'"stream_cooldown_on_disconnect":\s*True', 
         'Setting: stream_cooldown_on_disconnect'),
        (r'"stream_disconnect_stability_threshold":\s*30', 
         'Setting: stream_disconnect_stability_threshold'),
    ]
    all_checks_passed &= check_file_changes(
        'core/models.py',
        backend1_checks,
        'core/models.py (Settings Definitions)'
    )
    
    # 2. config_helper.py
    backend2_checks = [
        (r'def stream_cooldown_on_buffering\(', 
         'Method: stream_cooldown_on_buffering()'),
        (r'def stream_cooldown_on_disconnect\(', 
         'Method: stream_cooldown_on_disconnect()'),
        (r'def stream_disconnect_stability_threshold\(', 
         'Method: stream_disconnect_stability_threshold()'),
    ]
    all_checks_passed &= check_file_changes(
        'apps/proxy/live_proxy/config_helper.py',
        backend2_checks,
        'config_helper.py (Config Methods)'
    )
    
    # 3. manager.py
    backend3_checks = [
        (r'if ConfigHelper\.stream_cooldown_on_buffering\(\):', 
         'Buffering: Conditional cooldown check'),
        (r'if ConfigHelper\.stream_cooldown_on_disconnect\(\):', 
         'Disconnect: Conditional cooldown check'),
        (r'stability_threshold = ConfigHelper\.stream_disconnect_stability_threshold\(\)', 
         'Disconnect: Uses configurable threshold'),
        (r'stability_threshold == 0', 
         'Disconnect: Handles threshold=0 case'),
        (r'should_cooldown = \(stability_threshold == 0\) or \(connection_duration < stability_threshold\)', 
         'Disconnect: Correct logic for cooldown decision'),
    ]
    all_checks_passed &= check_file_changes(
        'apps/proxy/live_proxy/input/manager.py',
        backend3_checks,
        'manager.py (Cooldown Logic)'
    )
    
    # Frontend Checks
    print("\n" + "=" * 80)
    print("FRONTEND VERIFICATION")
    print("=" * 80)
    
    # 4. constants.js
    frontend1_checks = [
        (r'stream_cooldown_on_buffering:\s*{', 
         'Constant: stream_cooldown_on_buffering'),
        (r'stream_cooldown_on_disconnect:\s*{', 
         'Constant: stream_cooldown_on_disconnect'),
        (r'stream_disconnect_stability_threshold:\s*{', 
         'Constant: stream_disconnect_stability_threshold'),
    ]
    all_checks_passed &= check_file_changes(
        'frontend/src/constants.js',
        frontend1_checks,
        'constants.js (UI Labels)'
    )
    
    # 5. ProxySettingsFormUtils.js
    frontend2_checks = [
        (r'stream_cooldown_on_buffering:\s*true', 
         'Default: stream_cooldown_on_buffering = true'),
        (r'stream_cooldown_on_disconnect:\s*true', 
         'Default: stream_cooldown_on_disconnect = true'),
        (r'stream_disconnect_stability_threshold:\s*30', 
         'Default: stream_disconnect_stability_threshold = 30'),
    ]
    all_checks_passed &= check_file_changes(
        'frontend/src/utils/forms/settings/ProxySettingsFormUtils.js',
        frontend2_checks,
        'ProxySettingsFormUtils.js (Form Defaults)'
    )
    
    # 6. ProxySettingsForm.jsx
    frontend3_checks = [
        (r"'stream_cooldown_on_buffering'", 
         'Form field: stream_cooldown_on_buffering registered'),
        (r"'stream_cooldown_on_disconnect'", 
         'Form field: stream_cooldown_on_disconnect registered'),
        (r"'stream_disconnect_stability_threshold'", 
         'Form field: stream_disconnect_stability_threshold registered'),
        (r"\? 600", 
         'Max value: 600 seconds (10 minutes)'),
    ]
    all_checks_passed &= check_file_changes(
        'frontend/src/components/forms/settings/ProxySettingsForm.jsx',
        frontend3_checks,
        'ProxySettingsForm.jsx (Form Mapping)'
    )
    
    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if all_checks_passed:
        print("\n✅ ALL CHECKS PASSED - Patch v0.31.0 successfully applied!")
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Build frontend: cd frontend && npm run build")
        print("2. Restart service: docker-compose restart")
        print("3. Open WebUI: Settings → Proxy Settings")
        print("4. Verify new fields visible:")
        print("   - ☑️  Cooldown on Buffering Timeout")
        print("   - ☑️  Cooldown on Disconnect")
        print("   - 🔢 Disconnect Stability Threshold (0-600)")
        print("\n5. Test configuration:")
        print("   - Set Threshold to 0 for aggressive cooldown")
        print("   - Check logs: grep cooldown logs/dispatcharr.log")
        print("\n" + "=" * 80)
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED - Patch may not be fully applied")
        print("\nPossible issues:")
        print("1. Patch not applied: git apply dispatcharr_v0.31.0_cooldown_on_disconnect.patch")
        print("2. Wrong base version: Patch requires v0.30.0+")
        print("3. Manual changes: Some files may have been modified")
        print("\nRecommendation:")
        print("- Review failed checks above")
        print("- Apply patch again or make manual changes")
        print("- Refer to PATCH_v0.31.0_COOLDOWN_ON_DISCONNECT_GUIDE.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
