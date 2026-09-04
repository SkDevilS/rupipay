#!/usr/bin/env python3
"""
Extract ViyonaPay API request logs from systemd journal
Shows unencrypted payloads sent to ViyonaPay with request details
"""

import subprocess
import re
import json
from datetime import datetime

def extract_viyonapay_logs():
    """Extract ViyonaPay request logs from systemd journal"""
    
    print("\n" + "="*100)
    print("VIYONAPAY API REQUEST LOGS - LAST 200 CALLS")
    print("="*100 + "\n")
    
    try:
        print("📦 Service: moneyone-api (systemctl)")
        print("🔍 Searching for ViyonaPay API requests...\n")
        
        # Get logs from systemd journal - last 10000 lines to capture more history
        log_result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'moneyone-api', '-n', '10000', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if log_result.returncode != 0:
            print(f"❌ Failed to get logs: {log_result.stderr}")
            return
        
        logs = log_result.stdout
        lines = logs.split('\n')
        
        print(f"📄 Total log lines retrieved: {len(lines)}\n")
        
        # Parse logs for ViyonaPay-related entries
        viyona_logs = []
        current_request = None
        
        for line in lines:
            # Look for any ViyonaPay-related log entries
            if 'viyona' in line.lower() or 'VIYONAPAY' in line:
                viyona_logs.append(line)
                
                # Try to identify request start
                if 'Creating payin order' in line and 'VIYONAPAY' in line:
                    if current_request:
                        # Save previous request
                        pass
                    current_request = {
                        'timestamp': extract_timestamp(line),
                        'logs': [line]
                    }
                
                # Look for payment intent creation
                elif '📤 Creating payment intent' in line:
                    if not current_request:
                        current_request = {
                            'timestamp': extract_timestamp(line),
                            'logs': []
                        }
                    current_request['logs'].append(line)
                    
                    # Extract URL
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match:
                        current_request['url'] = url_match.group(0)
                
                # Collect related information
                elif current_request:
                    current_request['logs'].append(line)
                    
                    # Extract order ID
                    if '📦 Order ID:' in line:
                        order_match = re.search(r'Order ID:\s*(\S+)', line)
                        if order_match:
                            current_request['order_id'] = order_match.group(1)
                    
                    # Extract amount
                    if '💰 Amount:' in line:
                        amount_match = re.search(r'₹([\d,.]+)', line)
                        if amount_match:
                            current_request['amount'] = amount_match.group(1)
                    
                    # Extract response status
                    if '📥 Response status:' in line:
                        status_match = re.search(r'status:\s*(\d+)', line)
                        if status_match:
                            current_request['response_status'] = status_match.group(1)
                    
                    # Extract error
                    if '❌' in line and ('ViyonaPay Error' in line or 'Payment intent creation failed' in line):
                        error_match = re.search(r'(?:Error[:\s]+|failed[:\s]+)(.+)', line)
                        if error_match:
                            current_request['error'] = error_match.group(1).strip()
        
        if not viyona_logs:
            print("❌ No ViyonaPay-related logs found")
            print("\n💡 This could mean:")
            print("   1. No ViyonaPay transactions have been made recently")
            print("   2. Logs have been rotated")
            print("   3. ViyonaPay service is not being used")
            return
        
        print(f"✅ Found {len(viyona_logs)} ViyonaPay-related log lines\n")
        print("="*100)
        print("VIYONAPAY LOG ENTRIES")
        print("="*100 + "\n")
        
        # Display all ViyonaPay-related logs
        for idx, log_line in enumerate(viyona_logs[-200:], 1):  # Last 200 entries
            print(f"[{idx}] {log_line}")
        
        # Save to file
        output_file = f"viyonapay_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_file, 'w') as f:
            f.write("VIYONAPAY API LOGS\n")
            f.write("="*100 + "\n\n")
            for log_line in viyona_logs:
                f.write(log_line + "\n")
        
        print(f"\n{'='*100}")
        print(f"✅ Logs saved to: {output_file}")
        print(f"{'='*100}\n")
        
        # Summary
        print(f"📊 SUMMARY:")
        print(f"{'─'*100}")
        print(f"Total ViyonaPay log entries: {len(viyona_logs)}")
        print(f"Displayed (last 200):        {min(200, len(viyona_logs))}")
        
        # Count specific patterns
        intent_creations = sum(1 for line in viyona_logs if '📤 Creating payment intent' in line)
        errors_401 = sum(1 for line in viyona_logs if '📥 Response status: 401' in line)
        errors = sum(1 for line in viyona_logs if '❌' in line and 'ViyonaPay' in line)
        
        print(f"Payment intent requests:     {intent_creations}")
        print(f"401 Errors:                  {errors_401}")
        print(f"Total Errors:                {errors}")
        print(f"\n{'='*100}\n")
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout while fetching logs")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def extract_timestamp(line):
    """Extract timestamp from log line"""
    # Try to find timestamp in various formats
    patterns = [
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',  # Mar 28 12:30:26
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})',  # 2024-03-28 12:30:26
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    extract_viyonapay_logs()
