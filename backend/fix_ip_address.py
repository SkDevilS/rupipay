#!/usr/bin/env python3
"""Script to replace all request.remote_addr with get_real_ip() in app.py"""

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences
content = content.replace('ip_address = request.remote_addr', 'ip_address = get_real_ip()')

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Successfully replaced all occurrences of 'request.remote_addr' with 'get_real_ip()'")
