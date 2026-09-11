#!/usr/bin/env python3
"""
Verification script for WebUI cooldown settings implementation
Checks backend and frontend integration
"""

import re
import sys
import json

def check_backend():
    """Verify backend implementation"""
    print("=" * 80)
    print("BACKEND VERIFICATION")
    print("=" * 80)
    print()
    
    all_pass = True
    
    # Check core/models.py
    print("--- core/models.py ---")
    with open("core/models.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('stream_cooldown_enabled', 'Base cooldown enable flag'),
        ('stream_cooldown_minutes', 'Cooldown duration'),
        ('stream_cooldown_on_buffering', 'Buffering timeout trigger'),
        ('stream_cooldown_on_disconnect', 'Disconnect trigger'),
        ('stream_disconnect_stability_threshold', 'Disconnect threshold'),
    ]
    
    for key, desc in checks:
        if f'"{key}"' in content:
            print(f"✅ {desc}: {key}")
        else:
            print(f"❌ {desc}: {key} - MISSING")
            all_pass = False
    
    # Check config_helper.py
    print("\n--- apps/proxy/live_proxy/config_helper.py ---")
    with open("apps/proxy/live_proxy/config_helper.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    helper_checks = [
        ('stream_cooldown_enabled', 'stream_cooldown_enabled()'),
        ('stream_cooldown_seconds', 'stream_cooldown_seconds()'),
        ('stream_cooldown_on_buffering', 'stream_cooldown_on_buffering()'),
        ('stream_cooldown_on_disconnect', 'stream_cooldown_on_disconnect()'),
        ('stream_disconnect_stability_threshold', 'stream_disconnect_stability_threshold()'),
    ]
    
    for key, desc in helper_checks:
        pattern = f'def {key}\\('
        if re.search(pattern, content):
            print(f"✅ ConfigHelper method: {desc}")
        else:
            print(f"❌ ConfigHelper method: {desc} - MISSING")
            all_pass = False
    
    # Check manager.py integration
    print("\n--- apps/proxy/live_proxy/input/manager.py ---")
    with open("apps/proxy/live_proxy/input/manager.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    logic_checks = [
        ('ConfigHelper.stream_cooldown_on_buffering()', 
         'Buffering timeout checks new setting'),
        ('ConfigHelper.stream_cooldown_on_disconnect()', 
         'Disconnect checks new setting'),
        ('ConfigHelper.stream_disconnect_stability_threshold()', 
         'Uses configurable threshold'),
        ('stability_threshold == 0', 
         'Handles 0 threshold (cooldown on ANY disconnect)'),
    ]
    
    for pattern, desc in logic_checks:
        if pattern in content:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - MISSING")
            all_pass = False
    
    return all_pass

def check_frontend():
    """Verify frontend implementation"""
    print("\n" + "=" * 80)
    print("FRONTEND VERIFICATION")
    print("=" * 80)
    print()
    
    all_pass = True
    
    # Check constants.js
    print("--- frontend/src/constants.js ---")
    with open("frontend/src/constants.js", 'r', encoding='utf-8') as f:
        content = f.read()
    
    const_checks = [
        ('stream_cooldown_enabled', 'Base enable flag'),
        ('stream_cooldown_minutes', 'Duration setting'),
        ('stream_cooldown_on_buffering', 'Buffering trigger toggle'),
        ('stream_cooldown_on_disconnect', 'Disconnect trigger toggle'),
        ('stream_disconnect_stability_threshold', 'Disconnect threshold'),
    ]
    
    for key, desc in const_checks:
        if f'{key}:' in content:
            print(f"✅ Constant defined: {desc} ({key})")
        else:
            print(f"❌ Constant defined: {desc} ({key}) - MISSING")
            all_pass = False
    
    # Check ProxySettingsFormUtils.js
    print("\n--- frontend/src/utils/forms/settings/ProxySettingsFormUtils.js ---")
    with open("frontend/src/utils/forms/settings/ProxySettingsFormUtils.js", 'r', encoding='utf-8') as f:
        content = f.read()
    
    default_checks = [
        ('stream_cooldown_enabled: false', 'Disabled by default'),
        ('stream_cooldown_minutes: 10', 'Default 10 minutes'),
        ('stream_cooldown_on_buffering: true', 'Buffering trigger enabled by default'),
        ('stream_cooldown_on_disconnect: true', 'Disconnect trigger enabled by default'),
        ('stream_disconnect_stability_threshold: 30', 'Default 30s threshold'),
    ]
    
    for pattern, desc in default_checks:
        if pattern in content:
            print(f"✅ Default value: {desc}")
        else:
            print(f"❌ Default value: {desc} - MISSING")
            all_pass = False
    
    # Check ProxySettingsForm.jsx
    print("\n--- frontend/src/components/forms/settings/ProxySettingsForm.jsx ---")
    with open("frontend/src/components/forms/settings/ProxySettingsForm.jsx", 'r', encoding='utf-8') as f:
        content = f.read()
    
    form_checks = [
        ("'stream_cooldown_on_buffering'", 'Buffering checkbox registered'),
        ("'stream_cooldown_on_disconnect'", 'Disconnect checkbox registered'),
        ("'stream_disconnect_stability_threshold'", 'Threshold number input registered'),
        ('? 600', 'Threshold max set to 600s (10min)'),
    ]
    
    for pattern, desc in form_checks:
        if pattern in content:
            print(f"✅ Form field: {desc}")
        else:
            print(f"❌ Form field: {desc} - MISSING")
            all_pass = False
    
    return all_pass

def check_logic_correctness():
    """Verify logic is correct"""
    print("\n" + "=" * 80)
    print("LOGIC CORRECTNESS")
    print("=" * 80)
    print()
    
    all_pass = True
    
    with open("apps/proxy/live_proxy/input/manager.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check buffering logic
    print("--- Buffering Timeout Logic ---")
    buffering_section = re.search(
        r'if buffering_duration > self\.buffering_timeout:.*?if self\._try_next_stream\(\):',
        content,
        re.DOTALL
    )
    
    if buffering_section:
        section = buffering_section.group(0)
        
        if 'ConfigHelper.stream_cooldown_on_buffering()' in section:
            print("✅ Checks stream_cooldown_on_buffering() setting")
        else:
            print("❌ Does NOT check stream_cooldown_on_buffering() - will always apply")
            all_pass = False
        
        if 'if ConfigHelper.stream_cooldown_on_buffering():' in section:
            print("✅ Conditional cooldown based on setting")
        else:
            print("❌ Cooldown not conditional")
            all_pass = False
    else:
        print("❌ Buffering section not found")
        all_pass = False
    
    # Check disconnect logic
    print("\n--- Disconnect Logic ---")
    disconnect_section = re.search(
        r'if not chunk:.*?self\._close_socket\(\)',
        content,
        re.DOTALL
    )
    
    if disconnect_section:
        section = disconnect_section.group(0)
        
        checks = [
            ('ConfigHelper.stream_cooldown_on_disconnect()', 
             'Checks on_disconnect setting'),
            ('ConfigHelper.stream_disconnect_stability_threshold()', 
             'Uses configurable threshold'),
            ('stability_threshold == 0', 
             'Handles 0 threshold case'),
            ('should_cooldown =', 
             'Calculates if cooldown should apply'),
            ('if should_cooldown:', 
             'Conditionally applies cooldown'),
        ]
        
        for pattern, desc in checks:
            if pattern in section:
                print(f"✅ {desc}")
            else:
                print(f"❌ {desc} - MISSING")
                all_pass = False
    else:
        print("❌ Disconnect section not found")
        all_pass = False
    
    # Check threshold == 0 logic
    print("\n--- Threshold = 0 Handling ---")
    if '(stability_threshold == 0) or (connection_duration < stability_threshold)' in content:
        print("✅ Correct logic: threshold==0 OR duration<threshold")
    elif 'stability_threshold == 0' in content:
        print("⚠️  threshold==0 check exists but logic may be incorrect")
    else:
        print("❌ Missing threshold==0 check - won't cooldown on ANY disconnect when threshold=0")
        all_pass = False
    
    return all_pass

def main():
    backend_ok = check_backend()
    frontend_ok = check_frontend()
    logic_ok = check_logic_correctness()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if backend_ok and frontend_ok and logic_ok:
        print("✅ ALL CHECKS PASSED")
        print()
        print("New WebUI Settings:")
        print("1. ☑️  Stream Cooldown on Buffering Timeout")
        print("2. ☑️  Stream Cooldown on Disconnect")
        print("3. 🔢 Disconnect Stability Threshold (0-600s)")
        print()
        print("Threshold = 0:")
        print("  → Cooldown applied on ANY provider disconnect")
        print()
        print("Threshold > 0 (e.g., 30s):")
        print("  → Cooldown only if stream disconnects before threshold")
        print("  → Streams running >= threshold are considered stable (no cooldown)")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        if not backend_ok:
            print("❌ Backend implementation incomplete")
        if not frontend_ok:
            print("❌ Frontend implementation incomplete")
        if not logic_ok:
            print("❌ Logic correctness issues")
        return 1

if __name__ == '__main__':
    sys.exit(main())
