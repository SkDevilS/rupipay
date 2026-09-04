#!/usr/bin/env python3
"""
Extract Last 200 ViyonaPay 401 Error Transactions with Full Payload Details
Focuses on "Payment intent creation failed" errors with complete request information including Request ID
"""

import subprocess
import re
import json
from datetime import datetime
from collections import defaultdict

def extract_401_errors():
    """Extract ViyonaPay 401 error transactions with full payload"""
    
    print("\n" + "="*100)
    print("LAST 200 VIYONAPAY 401 ERROR TRANSACTIONS - PAYMENT INTENT CREATION FAILED")
    print("="*100 + "\n")
    
    try:
        print("📦 Service: moneyone-api (systemctl)")
        print("🔍 Searching for 401 errors with full payload...\n")
        
        # Get logs from systemd journal - last 50000 lines to get more history
        log_result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'moneyone-api', '-n', '50000', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if log_result.returncode != 0:
            print(f"❌ Failed to get logs: {log_result.stderr}")
            return
        
        logs = log_result.stdout
        lines = logs.split('\n')
        
        print(f"📄 Total log lines retrieved: {len(lines)}\n")
        
        # Parse logs to find 401 error transactions
        error_transactions = []
        current_transaction = None
        in_viyona_request = False
        
        for i, line in enumerate(lines):
            # Start of a ViyonaPay request
            if '📤 Creating payment intent' in line and 'viyonapay.com' in line:
                if current_transaction and current_transaction.get('has_401_error'):
                    error_transactions.append(current_transaction)
                
                current_transaction = {
                    'timestamp': extract_timestamp(line),
                    'logs': [line],
                    'has_401_error': False,
                    'order_id': None,
                    'amount': None,
                    'customer_name': None,
                    'customer_email': None,
                    'customer_phone': None,
                    'request_id': None,
                    'url': None,
                    'error_message': None
                }
                in_viyona_request = True
                
                # Extract URL from this line
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    current_transaction['url'] = url_match.group(0)
            
            # Collect logs for current transaction
            elif in_viyona_request and current_transaction:
                # Check if this line is related to ViyonaPay
                if any(marker in line for marker in [
                    'viyona', 'VIYONAPAY', '📤', '📦', '💰', '📥', '❌', '✓', '🔑', '👤',
                    'payment intent', 'Order ID:', 'Amount:', 'Response status:', 'Request ID:', 'Customer:'
                ]):
                    current_transaction['logs'].append(line)
                    
                    # Extract Request ID (UUID format)
                    if '🔑 Request ID:' in line:
                        # Look for UUID pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                        request_id_match = re.search(r'Request ID:\s*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', line, re.IGNORECASE)
                        if request_id_match:
                            current_transaction['request_id'] = request_id_match.group(1)
                    
                    # Extract Order ID
                    if '📦 Order ID:' in line:
                        order_match = re.search(r'Order ID:\s*(\S+)', line)
                        if order_match:
                            current_transaction['order_id'] = order_match.group(1)
                    
                    # Extract Amount
                    if '💰 Amount:' in line:
                        amount_match = re.search(r'₹([\d,.]+)', line)
                        if amount_match:
                            current_transaction['amount'] = amount_match.group(1)
                    
                    # Extract Customer details from new logging format
                    if '👤 Customer:' in line:
                        # Format: 👤 Customer: Name (email, phone)
                        customer_match = re.search(r'Customer:\s*([^(]+)\(([^,]+),\s*([^)]+)\)', line)
                        if customer_match:
                            current_transaction['customer_name'] = customer_match.group(1).strip()
                            current_transaction['customer_email'] = customer_match.group(2).strip()
                            current_transaction['customer_phone'] = customer_match.group(3).strip()
                    
                    # Check for 401 error
                    if '📥 Response status: 401' in line:
                        current_transaction['has_401_error'] = True
                    
                    # Extract error message
                    if '❌ ViyonaPay Error' in line or 'Payment intent creation failed' in line:
                        error_match = re.search(r'(?:Error[:\s]+|failed[:\s]+)(.+)', line)
                        if error_match:
                            current_transaction['error_message'] = error_match.group(1).strip()
                        else:
                            current_transaction['error_message'] = 'Payment intent creation failed'
                
                # End of transaction (next transaction starts)
                if '📤 Creating payment intent' in line and i > 0:
                    if current_transaction.get('has_401_error'):
                        error_transactions.append(current_transaction)
                    current_transaction = None
                    in_viyona_request = False
        
        # Add last transaction if it has 401 error
        if current_transaction and current_transaction.get('has_401_error'):
            error_transactions.append(current_transaction)
        
        # Limit to last 200 transactions
        if len(error_transactions) > 200:
            error_transactions = error_transactions[-200:]
        
        if not error_transactions:
            print("❌ No 401 error transactions found")
            print("\n💡 This could mean:")
            print("   1. No 401 errors have occurred recently")
            print("   2. Logs have been rotated")
            print("   3. All recent transactions were successful")
            return
        
        print(f"✅ Found {len(error_transactions)} transactions with 401 errors\n")
        print("="*100)
        print("401 ERROR TRANSACTIONS WITH FULL DETAILS")
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
            
            if txn['customer_name']:
                print(f"👤 Customer Name:   {txn['customer_name']}")
            if txn['customer_email']:
                print(f"📧 Customer Email:  {txn['customer_email']}")
            if txn['customer_phone']:
                print(f"📱 Customer Phone:  {txn['customer_phone']}")
            
            print(f"\n📋 COMPLETE LOG TRACE:")
            print(f"{'─'*100}")
            for log_line in txn['logs']:
                print(f"  {log_line}")
            print()
        
        # Save to JSON file
        output_json = f"viyonapay_401_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_json, 'w') as f:
            json.dump(error_transactions, f, indent=2, default=str)
        
        # Save to readable text file
        output_txt = f"viyonapay_401_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_txt, 'w') as f:
            f.write("VIYONAPAY 401 ERROR TRANSACTIONS\n")
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
                
                if txn['customer_name']:
                    f.write(f"Customer Name:   {txn['customer_name']}\n")
                if txn['customer_email']:
                    f.write(f"Customer Email:  {txn['customer_email']}\n")
                if txn['customer_phone']:
                    f.write(f"Customer Phone:  {txn['customer_phone']}\n")
                
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
        print(f"Total 401 Errors:           {len(error_transactions)}")
        print(f"Transactions with Order ID: {sum(1 for t in error_transactions if t['order_id'])}")
        print(f"Transactions with Amount:   {sum(1 for t in error_transactions if t['amount'])}")
        print(f"Transactions with Request ID: {sum(1 for t in error_transactions if t['request_id'])}")
        
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
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',  # Mar 28 12:30:26
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})',  # 2024-03-28 12:30:26
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    extract_401_errors()
