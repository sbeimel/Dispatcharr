#!/usr/bin/env python3
"""
Fix the corrupted models.py file.
"""

# Read the current file
with open('apps/m3u/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the corrupted regex pattern
corrupted_pattern = '''        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})
</content>
</file>
        return bool(re.match(pattern, mac))'''

fixed_pattern = '''        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))'''

# Replace the corrupted content
fixed_content = content.replace(corrupted_pattern, fixed_pattern)

# Write the fixed content back
with open('apps/m3u/models.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("✅ Fixed corrupted models.py file")