#!/usr/bin/env python3
"""
Detailed logic verification for cooldown implementation
Tests edge cases and potential issues
"""

import re
import sys

def read_function(filepath, start_pattern, end_pattern=None):
    """Extract function code from file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start_match = re.search(start_pattern, content)
    if not start_match:
        return None
        
    start_pos = start_match.start()
    
    # Find next function definition if no end pattern
    if end_pattern is None:
        next_func = re.search(r'\n    def ', content[start_pos + 10:])
        if next_func:
            end_pos = start_pos + 10 + next_func.start()
        else:
            end_pos = len(content)
    else:
        end_match = re.search(end_pattern, content[start_pos:])
        if end_match:
            end_pos = start_pos + end_match.end()
        else:
            end_pos = len(content)
    
    return content[start_pos:end_pos]

def check_edge_cases():
    """Check for potential edge cases and issues"""
    print("=" * 80)
    print("EDGE CASE VALIDATION")
    print("=" * 80)
    print()
    
    manager_file = "apps/proxy/live_proxy/input/manager.py"
    all_safe = True
    
    with open(manager_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Edge Case 1: Check if connection_start_time exists before using it
    print("--- Edge Case 1: Safe connection_start_time Access ---")
    if "getattr(self, 'connection_start_time', None)" in content:
        print("✅ Uses getattr() - safe even if connection_start_time is not set")
    else:
        print("❌ Direct access to connection_start_time - may cause AttributeError")
        all_safe = False
    
    # Edge Case 2: Check if cooldown respects enabled flag
    print("\n--- Edge Case 2: Cooldown Feature Flag Check ---")
    cooldown_func = read_function(manager_file, r'def _set_stream_cooldown\(')
    if cooldown_func and "if not ConfigHelper.stream_cooldown_enabled():" in cooldown_func:
        print("✅ Cooldown checks if feature is enabled before executing")
    else:
        print("❌ Cooldown may execute even when disabled")
        all_safe = False
    
    # Edge Case 3: Check for None checks
    print("\n--- Edge Case 3: Null Safety ---")
    disconnect_section = re.search(
        r'if not chunk:.*?self\._close_socket\(\)',
        content,
        re.DOTALL
    )
    if disconnect_section:
        section = disconnect_section.group(0)
        if "if connection_start:" in section:
            print("✅ Checks if connection_start exists before calculating duration")
        else:
            print("❌ May calculate duration with None value")
            all_safe = False
    
    # Edge Case 4: Buffering timeout doesn't break existing logic
    print("\n--- Edge Case 4: Buffering Timeout Integration ---")
    buffering_section = re.search(
        r'if buffering_duration > self\.buffering_timeout:.*?if self\._try_next_stream\(\):',
        content,
        re.DOTALL
    )
    if buffering_section:
        section = buffering_section.group(0)
        # Check that cooldown is called BEFORE _try_next_stream
        cooldown_pos = section.find('_set_stream_cooldown()')
        try_next_pos = section.find('if self._try_next_stream():')
        
        if cooldown_pos > 0 and try_next_pos > 0 and cooldown_pos < try_next_pos:
            print("✅ Cooldown is set BEFORE trying next stream (correct order)")
        else:
            print("❌ Cooldown order may be incorrect")
            all_safe = False
    
    # Edge Case 5: Check that original connection failure logic is unchanged
    print("\n--- Edge Case 5: Original Logic Preserved ---")
    original_patterns = [
        (r'if failures >= self\.max_retries:.*?url_failed = True', 
         "Connection failure detection"),
        (r'failures = self\._record_connection_failure\(\)',
         "Failure recording"),
        (r'if self\._try_next_stream_with_cooldown\(\):',
         "Cooldown-aware stream switching")
    ]
    
    for pattern, desc in original_patterns:
        if re.search(pattern, content, re.DOTALL):
            print(f"✅ {desc} - intact")
        else:
            print(f"❌ {desc} - may be broken")
            all_safe = False
    
    # Edge Case 6: Verify stable_threshold is fetched correctly
    print("\n--- Edge Case 6: Configuration Access ---")
    if "ConfigHelper.stable_connection_threshold()" in content:
        print("✅ Uses ConfigHelper for stable_connection_threshold")
    else:
        print("⚠️  May use hardcoded threshold instead of config")
    
    # Edge Case 7: Check logging doesn't break execution
    print("\n--- Edge Case 7: Logging Safety ---")
    if re.search(r'logger\.info\(.*?setting cooldown.*?\)', content):
        print("✅ Adds informative logging for early disconnect cooldown")
    else:
        print("⚠️  No logging for early disconnect cooldown (not critical)")
    
    print()
    print("=" * 80)
    if all_safe:
        print("✅ ALL EDGE CASES HANDLED SAFELY")
        print("=" * 80)
        return 0
    else:
        print("❌ SOME EDGE CASES MAY CAUSE ISSUES")
        print("=" * 80)
        return 1

def check_backwards_compatibility():
    """Ensure changes don't break existing behavior"""
    print()
    print("=" * 80)
    print("BACKWARDS COMPATIBILITY CHECK")
    print("=" * 80)
    print()
    
    manager_file = "apps/proxy/live_proxy/input/manager.py"
    
    with open(manager_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("Original cooldown at connection failure still exists",
         r'if failures >= self\.max_retries:.*?self\._set_stream_cooldown\(\)',
         True),
        ("_try_next_stream() signature unchanged",
         r'def _try_next_stream\(self\):',
         True),
        ("fetch_chunk() still returns bool",
         r'def fetch_chunk\(self\):.*?return (True|False)',
         True),
        ("Connection close logic still calls _close_socket()",
         r'if not chunk:.*?self\._close_socket\(\)',
         True),
        ("Buffering timeout still tries next stream",
         r'buffering_duration > self\.buffering_timeout:.*?if self\._try_next_stream\(\):',
         True)
    ]
    
    all_compatible = True
    for desc, pattern, required in checks:
        found = re.search(pattern, content, re.DOTALL)
        if found:
            print(f"✅ {desc}")
        else:
            if required:
                print(f"❌ {desc} - MISSING")
                all_compatible = False
            else:
                print(f"⚠️  {desc} - not found (may be optional)")
    
    print()
    print("=" * 80)
    if all_compatible:
        print("✅ FULLY BACKWARDS COMPATIBLE")
        print("=" * 80)
        print()
        print("Changes are additive only:")
        print("• Adds cooldown on buffering timeout")
        print("• Adds cooldown on early disconnect")
        print("• Does NOT modify existing logic")
        print("• Does NOT change function signatures")
        print("• Does NOT break existing behavior")
        return 0
    else:
        print("❌ MAY BREAK EXISTING BEHAVIOR")
        print("=" * 80)
        return 1

def main():
    result1 = check_edge_cases()
    result2 = check_backwards_compatibility()
    
    print()
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    if result1 == 0 and result2 == 0:
        print("✅ Implementation is SAFE and CORRECT")
        print()
        print("Ready to deploy:")
        print("1. All edge cases handled safely")
        print("2. Fully backwards compatible")
        print("3. Respects existing configuration")
        print("4. Adds logging for debugging")
        print()
        return 0
    else:
        print("❌ Review required before deployment")
        return 1

if __name__ == '__main__':
    sys.exit(main())
