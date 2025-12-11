#!/usr/bin/env python3
"""
Fix MAC validation by replacing the entire function.
"""

import re

def fix_mac_validation():
    """Fix the MAC validation function in models.py"""
    
    # Read the entire file
    with open('apps/m3u/models.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the corrupted function
    # Look for the function start
    start_marker = '@staticmethod\n    def is_valid_mac_format(mac):'
    end_marker = 'def save(self, *args, **kwargs):'
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print("❌ Could not find function markers")
        return False
    
    # Create the new function
    new_function = '''@staticmethod
    def is_valid_mac_format(mac):
        """Validate MAC address format."""
        if not mac:
            return False
        
        # Check standard format XX:XX:XX:XX:XX:XX
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    '''
    
    # Replace the corrupted function
    new_content = content[:start_pos] + new_function + content[end_pos:]
    
    # Write back the fixed content
    with open('apps/m3u/models.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Fixed MAC validation function")
    return True

if __name__ == "__main__":
    fix_mac_validation()