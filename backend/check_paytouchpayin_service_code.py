#!/usr/bin/env python3
"""
Check the actual code deployed in paytouchpayin_service.py
"""

import os

service_file = '/var/www/moneyone/moneyone/backend/paytouchpayin_service.py'

print("=" * 80)
print("CHECKING DEPLOYED PAYTOUCHPAYIN SERVICE CODE")
print("=" * 80)

if not os.path.exists(service_file):
    print(f"❌ File not found: {service_file}")
    exit(1)

with open(service_file, 'r') as f:
    lines = f.readlines()

print(f"\n📄 File: {service_file}")
print(f"📊 Total lines: {len(lines)}")

# Find the problematic query around line 176
print("\n" + "=" * 80)
print("LINES 170-185 (WHERE THE ERROR OCCURS)")
print("=" * 80)

for i in range(169, min(185, len(lines))):
    line_num = i + 1
    line = lines[i].rstrip()
    if 'SELECT' in line or 'FROM merchants' in line or 'WHERE merchant_id' in line:
        print(f">>> Line {line_num}: {line}")
    else:
        print(f"    Line {line_num}: {line}")

# Search for all SELECT queries from merchants table
print("\n" + "=" * 80)
print("ALL SELECT QUERIES FROM MERCHANTS TABLE")
print("=" * 80)

in_query = False
query_lines = []
query_start_line = 0

for i, line in enumerate(lines):
    line_num = i + 1
    if 'SELECT' in line and not line.strip().startswith('#'):
        in_query = True
        query_start_line = line_num
        query_lines = [line.rstrip()]
    elif in_query:
        query_lines.append(line.rstrip())
        if 'FROM merchants' in line or ('FROM' in line and 'merchants' in line):
            # Print this query
            print(f"\n📍 Query starting at line {query_start_line}:")
            for ql in query_lines:
                print(f"  {ql}")
            in_query = False
            query_lines = []
        elif ')' in line and 'execute' not in line.lower():
            in_query = False
            query_lines = []

print("\n" + "=" * 80)
print("CHECKING FOR 'name' COLUMN REFERENCES")
print("=" * 80)

for i, line in enumerate(lines):
    line_num = i + 1
    if 'name' in line.lower() and 'SELECT' in lines[max(0, i-5):i+1].__str__():
        print(f"Line {line_num}: {line.rstrip()}")

print("\n✅ Check complete!")
