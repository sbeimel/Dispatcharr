#!/usr/bin/env python3
"""
Test MAC address validation and processing.
"""

import re

def normalize_mac_address(mac):
    """Normalize MAC address to standard format (XX:XX:XX:XX:XX:XX)."""
    if not mac:
        return mac
    
    # Remove all separators and convert to uppercase
    clean_mac = re.sub(r'[:-]', '', mac.strip().upper())
    
    # Validate length
    if len(clean_mac) != 12:
        return mac  # Return original if invalid length
    
    # Add colons every 2 characters
    return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))

def is_valid_mac_format(mac):
    """Validate MAC address format."""
    if not mac:
        return False
    
    # Check standard format XX:XX:XX:XX:XX:XX
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac))

def test_mac_processing():
    """Test MAC address processing with the user's MAC addresses."""
    test_macs = "00:1A:79:19:1F:00 00:1A:79:19:1F:A7 00:1A:79:19:1F:A9"
    
    print(f"Testing MAC addresses: {test_macs}")
    
    # Parse MAC addresses from the field (space, comma, or newline separated)
    mac_addresses = []
    
    # Split by various separators and clean up
    raw_macs = re.split(r'[,\s\n\r]+', test_macs.strip())
    
    for mac in raw_macs:
        mac = mac.strip()
        if mac:
            print(f"  Processing MAC: '{mac}'")
            # Normalize MAC address format
            normalized_mac = normalize_mac_address(mac)
            print(f"    Normalized: '{normalized_mac}'")
            if is_valid_mac_format(normalized_mac):
                print(f"    ✅ Valid")
                mac_addresses.append(normalized_mac)
            else:
                print(f"    ❌ Invalid")
    
    print(f"\nFinal MAC addresses: {mac_addresses}")
    return mac_addresses

if __name__ == "__main__":
    test_mac_processing()