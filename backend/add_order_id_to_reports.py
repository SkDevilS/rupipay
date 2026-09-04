#!/usr/bin/env python3
"""
Script to add order_id field to all payout report API endpoints
"""

import re

# Read the file
with open('payout_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Add order_id to SELECT statements after reference_id
# For queries with explicit column list
pattern1 = r'(pt\.reference_id,)\s*\n\s*(pt\.batch_id,)'
replacement1 = r'\1\n        pt.order_id,\n        \2'
content = re.sub(pattern1, replacement1, content)

# Pattern 2: Add order_id to formatted_payout dictionaries after reference_id
# For dictionaries with payout['reference_id']
pattern2 = r"('reference_id': payout\['reference_id'\],)\s*\n\s*('batch_id':)"
replacement2 = r"\1\n        'order_id': payout['order_id'],\n        \2"
content = re.sub(pattern2, replacement2, content)

# Pattern 3: For dictionaries with payout.get('reference_id')
pattern3 = r"('reference_id': payout\.get\('reference_id'\),)\s*\n\s*('batch_id':)"
replacement3 = r"\1\n        'order_id': payout.get('order_id'),\n        \2"
content = re.sub(pattern3, replacement3, content)

# Write the modified content back
with open('payout_routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Successfully added order_id to all payout report endpoints")
print("✓ Modified payout_routes.py")
