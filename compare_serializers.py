#!/usr/bin/env python3
"""
Compare M3UAccountSerializer fields between v0.27.0 and v0.30.0
"""

import re

def extract_fields(filepath):
    """Extract fields list from serializer file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find M3UAccountSerializer class
    match = re.search(r'class M3UAccountSerializer.*?class Meta:.*?fields = \[(.*?)\]', content, re.DOTALL)
    if match:
        fields_str = match.group(1)
        # Extract field names (quoted strings), handle multiline
        fields = re.findall(r'"([^"]+)"', fields_str)
        return set(fields)
    return set()

def main():
    v027_path = r'Dispatcharr - 27.0\apps\m3u\serializers.py'
    v030_path = r'apps\m3u\serializers.py'
    
    v027_fields = extract_fields(v027_path)
    v030_fields = extract_fields(v030_path)
    
    print("=" * 80)
    print("M3UAccountSerializer Fields Comparison")
    print("=" * 80)
    print()
    
    print(f"v0.27.0 has {len(v027_fields)} fields")
    print(f"v0.30.0 has {len(v030_fields)} fields")
    print()
    
    missing_in_v030 = v027_fields - v030_fields
    new_in_v030 = v030_fields - v027_fields
    common = v027_fields & v030_fields
    
    if missing_in_v030:
        print("❌ MISSING IN v0.30.0 (were in v0.27.0):")
        for field in sorted(missing_in_v030):
            print(f"   - {field}")
        print()
    else:
        print("✅ No fields missing in v0.30.0")
        print()
    
    if new_in_v030:
        print("✨ NEW IN v0.30.0 (not in v0.27.0):")
        for field in sorted(new_in_v030):
            print(f"   + {field}")
        print()
    else:
        print("ℹ️  No new fields in v0.30.0")
        print()
    
    print(f"✅ {len(common)} common fields")
    print()
    
    # Check for critical fields
    critical_fields = ['proxy', 'proxy_for_api', 'username', 'password', 'enable_vod']
    print("🔍 Critical Fields Status:")
    for field in critical_fields:
        v027_has = field in v027_fields
        v030_has = field in v030_fields
        status = "✅" if (v027_has and v030_has) else ("⚠️" if v030_has else "❌")
        print(f"   {status} {field:20s} - v0.27.0: {v027_has}, v0.30.0: {v030_has}")
    print()
    
    print("=" * 80)

if __name__ == '__main__':
    main()
