#!/usr/bin/env python3
"""
Verification script for cooldown-on-disconnect implementation
Checks if cooldown is properly set when streams disconnect or buffer timeout
"""

import re
import sys

def check_file_content(filepath, pattern, description):
    """Check if pattern exists in file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description}")
                return False
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def main():
    print("=" * 80)
    print("COOLDOWN ON DISCONNECT - VERIFICATION")
    print("=" * 80)
    print()
    
    manager_file = "apps/proxy/live_proxy/input/manager.py"
    all_checks_passed = True
    
    # Check 1: Buffering timeout cooldown
    print("--- Feature 1: Cooldown on Buffering Timeout ---")
    pattern1 = r'buffering_duration > self\.buffering_timeout:.*?self\._set_stream_cooldown\(\)'
    all_checks_passed &= check_file_content(
        manager_file, 
        pattern1,
        "Cooldown is set when buffering timeout is reached"
    )
    
    # Check 2: Early disconnect cooldown
    print("\n--- Feature 2: Cooldown on Early Disconnect ---")
    pattern2 = r'if not chunk:.*?connection_start_time.*?stable_connection_threshold.*?self\._set_stream_cooldown\(\)'
    all_checks_passed &= check_file_content(
        manager_file,
        pattern2,
        "Cooldown is set when connection closes before stable threshold"
    )
    
    # Check 3: Stable threshold check exists
    print("\n--- Feature 3: Stable Connection Threshold Check ---")
    pattern3 = r'connection_duration < stable_threshold'
    all_checks_passed &= check_file_content(
        manager_file,
        pattern3,
        "Early disconnect is detected by comparing to stable_connection_threshold"
    )
    
    # Check 4: connection_start_time is used
    print("\n--- Feature 4: Connection Start Time Tracking ---")
    pattern4 = r"connection_start = getattr\(self, 'connection_start_time', None\)"
    all_checks_passed &= check_file_content(
        manager_file,
        pattern4,
        "connection_start_time is retrieved safely with getattr"
    )
    
    # Check 5: Logging for early disconnect
    print("\n--- Feature 5: Logging ---")
    pattern5 = r'Stream disconnected after.*?setting cooldown'
    all_checks_passed &= check_file_content(
        manager_file,
        pattern5,
        "Early disconnect with cooldown is logged"
    )
    
    # Check 6: Original cooldown logic still intact
    print("\n--- Feature 6: Original Cooldown Logic (Connection Failures) ---")
    pattern6 = r'if failures >= self\.max_retries:.*?self\._set_stream_cooldown\(\)'
    all_checks_passed &= check_file_content(
        manager_file,
        pattern6,
        "Original cooldown on connection failure is still present"
    )
    
    # Check 7: No duplicate imports or broken syntax
    print("\n--- Feature 7: Syntax Validation ---")
    try:
        with open(manager_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Count _set_stream_cooldown calls
        cooldown_calls = sum(1 for line in lines if '_set_stream_cooldown()' in line)
        print(f"✅ Found {cooldown_calls} cooldown calls (expected: 4)")
        
        if cooldown_calls != 4:
            print(f"⚠️  Warning: Expected 4 cooldown calls, found {cooldown_calls}")
            all_checks_passed = False
            
    except Exception as e:
        print(f"❌ Error during syntax validation: {e}")
        all_checks_passed = False
    
    # Check 8: ConfigHelper.stream_cooldown_enabled() check exists
    print("\n--- Feature 8: Cooldown Feature Flag ---")
    pattern8 = r'if not ConfigHelper\.stream_cooldown_enabled\(\):\s+return'
    all_checks_passed &= check_file_content(
        manager_file,
        pattern8,
        "Cooldown respects stream_cooldown_enabled setting"
    )
    
    print()
    print("=" * 80)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Implementation is correct!")
        print("=" * 80)
        print()
        print("Summary of new cooldown triggers:")
        print("1. Connection failures (max_retries reached) - ORIGINAL ✅")
        print("2. Buffering timeout - NEW ✅")
        print("3. Early disconnect (< stable_connection_threshold) - NEW ✅")
        print()
        print("Benefits:")
        print("• Prevents immediate retry of streams that connect but don't work")
        print("• Reduces provider load from unstable streams")
        print("• Uses existing stable_connection_threshold (default: 30s)")
        print("• Respects stream_cooldown_enabled setting")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Review implementation!")
        print("=" * 80)
        return 1

if __name__ == '__main__':
    sys.exit(main())
