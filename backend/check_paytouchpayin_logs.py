#!/usr/bin/env python3
"""
Check Paytouchpayin service logs for errors
"""

import subprocess
import sys

print("=" * 60)
print("Checking Paytouchpayin Service Logs")
print("=" * 60)
print()

# Check last 100 lines of backend logs for Paytouchpayin
print("📋 Checking backend service logs for Paytouchpayin...")
print()

try:
    result = subprocess.run(
        ['sudo', 'journalctl', '-u', 'moneyone-backend', '-n', '100', '--no-pager'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    lines = result.stdout.split('\n')
    
    # Filter for Paytouchpayin related logs
    paytouchpayin_logs = []
    for line in lines:
        if any(keyword in line.lower() for keyword in ['paytouchpayin', 'ptpin', 'creating payin order']):
            paytouchpayin_logs.append(line)
    
    if paytouchpayin_logs:
        print("Found Paytouchpayin logs:")
        print("-" * 60)
        for log in paytouchpayin_logs[-20:]:  # Last 20 relevant logs
            print(log)
        print("-" * 60)
    else:
        print("⚠ No Paytouchpayin logs found in last 100 lines")
        print()
        print("Showing last 20 lines of backend logs:")
        print("-" * 60)
        for line in lines[-20:]:
            print(line)
        print("-" * 60)
    
except subprocess.TimeoutExpired:
    print("❌ Command timed out")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("To view real-time logs, run:")
print("  sudo journalctl -u moneyone-backend -f | grep -i paytouchpayin")
print("=" * 60)
