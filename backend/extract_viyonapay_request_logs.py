#!/usr/bin/env python3
"""
Extract ViyonaPay API request logs from systemd journal showing the actual unencrypted payload
that was sent to ViyonaPay, along with request_id and response status
"""

import subprocess
import re
import json
from datetime import datetime

def extract_viyonapay_logs():
    """Extract ViyonaPay request logs from systemd journal"""
    
    print("\n" + "="*100)
    print("VIYONAPAY API REQUEST LOGS - UNENCRYPTED PAYLOADS")
    print("="*100 + "\n")
    
    try:
        print(f"📦 Service: moneyone-api (systemctl)\n")
        print("🔍 Searching for ViyonaPay API requests...\n")
        
        # Get logs from systemd journal for moneyone-api service
        # Get last 5000 lines to capture more history
        log_result = subprocess.run(
            ['journalctl', '-u', 'moneyone-api', '-n', '5000', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if log_result.returncode != 0:
            print(f"❌ Failed to get logs: {log_result.stderr}")
            print("\n💡 Try running with sudo:")
            print("   sudo python3 backend/extract_viyonapay_request_logs.py")
            return
        
        logs = log_result.stdout
        lines = logs.split('\n')
        
        # Parse logs for ViyonaPay requests
        requests = []
        current_request = None
        
        for line in lines:
            # Look for payment intent creation start
            if '📤 Creating payment intent' in line and 'viyonapay' in line.lower():
                if current_request:
                    requests.append(current_request)
                
                current_request = {
                    'timestamp': extract_timestamp(line),
                    'url': None,
                    'order_id': None,
                    'amount': None,
                    'response_status': None,
                    'error': None,
                    'intent_id': None,
                    'payment_url': None,
                    'logs': [line]
                }
                
                # Extract URL
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    current_request['url'] = url_match.group(0)
            
            elif current_request:
                # Collect related log lines
                if any(marker in line for marker in [
                    '📦 Order ID:', '💰 Amount:', '📥 Response status:',
                    '✅ Payment intent', '❌', 'Intent ID:', 'Payment URL:',
                    'ViyonaPay Error', 'Creating payin order'
                ]):
                    current_request['logs'].append(line)
                    
                    # Extract order ID
                    if '📦 Order ID:' in line:
                        current_request['order_id'] = line.split('Order ID:')[1].strip()
                    
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
                    if '❌ ViyonaPay Error' in line:
                        error_match = re.search(r'Error[:\s]+(.+)', line)
                        if error_match:
                            current_request['error'] = error_match.group(1).strip()
                    
                    # Extract intent ID
                    if 'Intent ID:' in line:
                        current_request['intent_id'] = line.split('Intent ID:')[1].strip()
                    
                    # Extract payment URL
                    if 'Payment URL:' in line:
                        url_match = re.search(r'https?://[^\s]+', line)
                        if url_match:
                            current_request['payment_url'] = url_match.group(0)
                    
                    # Mark as complete if we see success or error
                    if ('✅ Payment intent created successfully' in line or 
                        '❌ ViyonaPay Error' in line or
                        'Payment intent creation failed' in line):
                        requests.append(current_request)
                        current_request = None
        
        # Add last request if exists
        if current_request:
            requests.append(current_request)
        
        if not requests:
            print("❌ No ViyonaPay requests found in logs")
            return
        
        print(f"✅ Found {len(requests)} ViyonaPay API requests\n")
        
        # Display results
        results = []
        for idx, req in enumerate(requests, 1):
            print(f"{'─'*100}")
            print(f"[{idx}] VIYONAPAY API REQUEST")
            print(f"{'─'*100}")
            print(f"Timestamp:        {req['timestamp']}")
            print(f"URL:              {req['url'] or 'N/A'}")
            print(f"Order ID:         {req['order_id'] or 'N/A'}")
            print(f"Amount:           ₹{req['amount'] or 'N/A'}")
            print(f"Response Status:  {req['response_status'] or 'N/A'}")
            
            if req['error']:
                print(f"\n❌ ERROR: {req['error']}")
            
            if req['intent_id']:
                print(f"\n✅ Intent ID:     {req['intent_id']}")
            
            if req['payment_url']:
                print(f"Payment URL:      {req['payment_url']}")
            
            print(f"\n📋 FULL LOG TRACE:")
            for log_line in req['logs']:
                print(f"  {log_line}")
            
            print()
            
            results.append(req)
        
        # Save to JSON
        output_file = f"viyonapay_request_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n{'='*100}")
        print(f"✅ Logs exported to: {output_file}")
        print(f"{'='*100}\n")
        
        # Summary
        success_count = sum(1 for r in requests if r.get('intent_id'))
        error_count = sum(1 for r in requests if r.get('error'))
        status_401 = sum(1 for r in requests if r.get('response_status') == '401')
        
        print(f"📊 SUMMARY:")
        print(f"{'─'*100}")
        print(f"Total Requests:       {len(requests)}")
        print(f"Successful:           {success_count}")
        print(f"Failed:               {error_count}")
        print(f"401 Errors:           {status_401}")
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
