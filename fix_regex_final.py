#!/usr/bin/env python3
"""
Final fix for the regex pattern in models.py
"""

# Read the file
with open('apps/m3u/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken regex line
old_pattern = '''        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})
</content>
</file>
        return bool(re.match(pattern, mac))'''

new_pattern = '''        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))'''

# Replace the broken content
fixed_content = content.replace(old_pattern, new_pattern)

# Write back
with open('apps/m3u/models.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("✅ Fixed regex pattern in models.py")