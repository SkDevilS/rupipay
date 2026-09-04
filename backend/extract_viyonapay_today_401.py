#!/usr/bin/env python3
"""
Extract ViyonaPay 401 Errors from TODAY ONLY
Shows complete payload details for failed transactions
"""

import subprocess
import re
import json
from datetime import datetime
from collections import defaultdict

def extract_today_401_errors():
    """Extract ViyonaPay 401 error transactions from today"""
    
    print("\n" + "="*100)
    print("VIYONAPAY 401 ERRORS - TODAY ONLY")
    print("="*100 + "\n")
    
    try:
        print("📦 Service: moneyone-api (systemctl)")
        print("📅 Date: TODAY")
        print("🔍 Searching for 401 errors...\n")
        
        # Get logs from TODAY only using --since today
        log_result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'moneyone-api', '--since', 'today', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if log_result.returncode != 0:
            print(f"❌ Failed to get logs: {log_result.stderr}")
            return
        
        logs = log_result.stdout
        lines = logs.split('\n')
        
        print(f"📄 Total log lines from today: {len(lines)}\n")
        
        # First, let's find ALL ViyonaPay-related lines
        viyona_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['viyona', 'viyonapay']):
                viyona_lines.append(line)
        
        print(f"📊 ViyonaPay-related lines found: {len(viyona_lines)}\n")
        
        # Parse for 401 errors
        error_transactions = []
        current_transaction = None
        
        for i, line in enumerate(lines):
            # Start tracking when we see ViyonaPay activity
            if ('Creating payin order' in line and 'VIYONAPAY' in line) or \
               ('📤 Creating payment intent' in line and 'viyona' in line.lower()):
                
                if current_transaction and current_transaction.get('has_401_error'):
                    error_transactions.append(current_transaction)
                
                current_transaction = {
                    'timestamp': extract_timestamp(line),
                    'logs': [line],
                    'has_401_error': False,
                    'order_id': None,
                    'amount': None,
                    'url': None,
                    'error_message': None,
                    'request_id': None
                }
            
            # Collect related logs
            elif current_transaction:
                if any(marker in line for marker in [
                    'viyona', 'VIYONAPAY', '📤', '📦', '💰', '📥', '❌', '✓',
                    'payment intent', 'Order ID', 'Amount', 'Response status',
                    'request_id', 'Request-ID'
                ]):
                    current_transaction['logs'].append(line)
                    
                    # Extract URL
                    if 'Creating payment intent' in line or 'https://core.viyonapay.com' in line:
                        url_match = re.search(r'https?://[^\s]+', line)
                        if url_match:
                            current_transaction['url'] = url_match.group(0)
                    
                    # Extract Order ID
                    if 'Order ID' in line:
                        order_match = re.search(r'Order ID[:\s]+(\S+)', line, re.IGNORECASE)
                        if order_match:
                            current_transaction['order_id'] = order_match.group(1)
                    
                    # Extract Amount
                    if 'Amount' in line:
                        amount_match = re.search(r'₹([\d,.]+)', line)
                        if amount_match:
                            current_transaction['amount'] = amount_match.group(1)
                    
                    # Extract Request ID
                    if 'request' in line.lower() and 'id' in line.lower():
                        req_id_match = re.search(r'request[_\s-]*id[:\s]+([a-f0-9-]+)', line, re.IGNORECASE)
                        if req_id_match:
                            current_transaction['request_id'] = req_id_match.group(1)
                    
                    # Check for 401 error
                    if 'Response status: 401' in line or 'status: 401' in line:
                        current_transaction['has_401_error'] = True
                    
                    # Extract error message
                    if ('ViyonaPay Error' in line or 'Payment intent creation failed' in line or 
                        'intent creation failed' in line.lower()):
                        current_transaction['has_401_error'] = True
                        error_match = re.search(r'(?:Error[:\s]+|failed[:\s]+)(.+)', line, re.IGNORECASE)
                        if error_match:
                            current_transaction['error_message'] = error_match.group(1).strip()
                        elif not current_transaction['error_message']:
                            current_transaction['error_message'] = 'Payment intent creation failed'
        
        # Add last transaction if it has 401 error
        if current_transaction and current_transaction.get('has_401_error'):
            error_transactions.append(current_transaction)
        
        if not error_transactions:
            print("❌ No 401 error transactions found TODAY")
            print("\n💡 Showing all ViyonaPay activity from today:\n")
            
            if viyona_lines:
                print(f"Found {len(viyona_lines)} ViyonaPay-related log lines:")
                print("="*100)
                for idx, line in enumerate(viyona_lines[-50:], 1):  # Show last 50
                    print(f"[{idx}] {line}")
                print("="*100)
            else:
                print("No ViyonaPay activity found today")
            
            return
        
        print(f"✅ Found {len(error_transactions)} transactions with 401 errors TODAY\n")
        print("="*100)
        print("401 ERROR TRANSACTIONS - TODAY")
        print("="*100 + "\n")
        
        # Display each error transaction
        for idx, txn in enumerate(error_transactions, 1):
            print(f"{'─'*100}")
            print(f"[{idx}] TRANSACTION #{idx} - 401 ERROR")
            print(f"{'─'*100}")
            print(f"⏰ Timestamp:       {txn['timestamp']}")
            print(f"📦 Order ID:        {txn['order_id'] or 'N/A'}")
            print(f"💰 Amount:          ₹{txn['amount'] or 'N/A'}")
            print(f"🔑 Request ID:      {txn['request_id'] or 'N/A'}")
            print(f"🌐 API URL:         {txn['url'] or 'N/A'}")
            print(f"❌ Error:           {txn['error_message'] or 'Payment intent creation failed'}")
            
            print(f"\n📋 COMPLETE LOG TRACE:")
            print(f"{'─'*100}")
            for log_line in txn['logs']:
                print(f"  {log_line}")
            print()
        
        # Save to files
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_json = f"viyonapay_401_today_{timestamp_str}.json"
        output_txt = f"viyonapay_401_today_{timestamp_str}.txt"
        
        with open(output_json, 'w') as f:
            json.dump(error_transactions, f, indent=2, default=str)
        
        with open(output_txt, 'w') as f:
            f.write(f"VIYONAPAY 401 ERRORS - TODAY ({datetime.now().strftime('%Y-%m-%d')})\n")
            f.write("="*100 + "\n\n")
            
            for idx, txn in enumerate(error_transactions, 1):
                f.write(f"{'─'*100}\n")
                f.write(f"[{idx}] TRANSACTION #{idx} - 401 ERROR\n")
                f.write(f"{'─'*100}\n")
                f.write(f"Timestamp:       {txn['timestamp']}\n")
                f.write(f"Order ID:        {txn['order_id'] or 'N/A'}\n")
                f.write(f"Amount:          ₹{txn['amount'] or 'N/A'}\n")
                f.write(f"Request ID:      {txn['request_id'] or 'N/A'}\n")
                f.write(f"API URL:         {txn['url'] or 'N/A'}\n")
                f.write(f"Error:           {txn['error_message'] or 'Payment intent creation failed'}\n")
                f.write(f"\nCOMPLETE LOG TRACE:\n")
                f.write(f"{'─'*100}\n")
                for log_line in txn['logs']:
                    f.write(f"{log_line}\n")
                f.write("\n\n")
        
        print(f"\n{'='*100}")
        print(f"✅ Results saved to:")
        print(f"   - {output_json} (JSON format)")
        print(f"   - {output_txt} (Text format)")
        print(f"{'='*100}\n")
        
        # Summary
        print(f"📊 SUMMARY:")
        print(f"{'─'*100}")
        print(f"Date:                       {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Total 401 Errors:           {len(error_transactions)}")
        print(f"Transactions with Order ID: {sum(1 for t in error_transactions if t['order_id'])}")
        print(f"Transactions with Amount:   {sum(1 for t in error_transactions if t['amount'])}")
        print(f"Transactions with Req ID:   {sum(1 for t in error_transactions if t['request_id'])}")
        
        # Group by error message
        error_types = defaultdict(int)
        for txn in error_transactions:
            error_types[txn['error_message'] or 'Unknown'] += 1
        
        print(f"\nError Types:")
        for error_msg, count in error_types.items():
            print(f"  - {error_msg}: {count}")
        
        print(f"\n{'='*100}\n")
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout while fetching logs")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def extract_timestamp(line):
    """Extract timestamp from log line"""
    patterns = [
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',  # Mar 29 12:30:26
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})',  # 2026-03-29 12:30:26
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    extract_today_401_errors()
