#!/usr/bin/env python3
"""
Check Flask application logs for ViyonaPay callback data
The callback might be logged in the application logs
"""

import os
import re
from datetime import datetime, timedelta

def check_flask_logs():
    """Check Flask logs for ViyonaPay callback data"""
    
    print("\n" + "="*80)
    print("  CHECKING FLASK APPLICATION LOGS")
    print("="*80)
    
    # Common log file locations
    log_locations = [
        '/var/log/moneyone/backend.log',
        '/var/log/moneyone/app.log',
        '/var/www/moneyone/moneyone/backend/app.log',
        '/var/www/moneyone/moneyone/logs/backend.log',
        'app.log',
        'backend.log',
        '../logs/backend.log',
        '/tmp/moneyone.log'
    ]
    
    print("\nSearching for log files...")
    
    found_logs = []
    for log_path in log_locations:
        if os.path.exists(log_path):
            found_logs.append(log_path)
            print(f"  ✓ Found: {log_path}")
    
    if not found_logs:
        print("\n❌ No log files found in common locations")
        print("\nTry checking Docker logs:")
        print("  docker logs moneyone-backend-1 --tail 200 | grep -i viyona")
        print("\nOr check systemd logs:")
        print("  journalctl -u moneyone-backend --since '1 hour ago' | grep -i viyona")
        return
    
    print(f"\n{'='*80}")
    print("  SEARCHING FOR VIYONAPAY CALLBACK DATA")
    print("="*80)
    
    # Search patterns
    patterns = [
        r'viyona',
        r'VIYONA',
        r'ViyonaPay',
        r'encryptedData',
        r'/api/callback/viyonapay',
        r'webhook.*callback',
        r'payin.*callback'
    ]
    
    for log_file in found_logs:
        print(f"\n{'-'*80}")
        print(f"  Checking: {log_file}")
        print(f"{'-'*80}")
        
        try:
            # Get file size
            size = os.path.getsize(log_file)
            print(f"File size: {size:,} bytes")
            
            # Read last 1000 lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                total_lines = len(lines)
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                print(f"Total lines: {total_lines:,}")
                print(f"Checking last {len(recent_lines)} lines...")
                
                matches = []
                for i, line in enumerate(recent_lines):
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            matches.append((i, line))
                            break
                
                if matches:
                    print(f"\n✅ Found {len(matches)} matching line(s):\n")
                    for idx, line in matches[-20:]:  # Show last 20 matches
                        print(f"  Line {idx}: {line.strip()[:200]}")
                else:
                    print("\n⚠️  No ViyonaPay-related entries found")
                    
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
    
    print("\n" + "="*80)
    print("  DOCKER LOGS COMMAND")
    print("="*80)
    print("\nIf using Docker, run this command to see recent logs:")
    print("\n  docker logs moneyone-backend-1 --tail 500 --since 1h | grep -i viyona")
    print("\nOr to see all recent backend logs:")
    print("\n  docker logs moneyone-backend-1 --tail 200")
    
    print("\n" + "="*80)
    print("  CHECKING CALLBACK ENDPOINT")
    print("="*80)
    print("\nViyonaPay callback endpoint should be:")
    print("  POST https://your-domain.com/api/callback/viyonapay/payin")
    print("\nCheck if this endpoint is registered in app.py")

if __name__ == "__main__":
    check_flask_logs()
    print("\n" + "="*80)
