#!/usr/bin/env python3
"""
Extract transaction API logs from Flask application logs
This script searches through log files to find API requests/responses for a specific transaction
"""
import re
import json
import sys
from datetime import datetime

def extract_logs_for_transaction(txn_id, log_file='/var/log/flask.log'):
    """
    Extract all log entries related to a specific transaction ID
    """
    print(f"Searching for transaction: {txn_id}")
    print(f"Log file: {log_file}")
    print("=" * 80)
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        print("\nTrying alternative log locations...")
        alternative_logs = [
            '/var/log/app.log',
            'app.log',
            'flask.log',
            '/tmp/flask.log'
        ]
        for alt_log in alternative_logs:
            try:
                with open(alt_log, 'r') as f:
                    lines = f.readlines()
                    log_file = alt_log
                    print(f"Found logs at: {alt_log}")
                    break
            except:
                continue
        else:
            print("Could not find any log files!")
            return None
    
    # Find all lines containing the transaction ID
    relevant_lines = []
    for i, line in enumerate(lines):
        if txn_id in line:
            # Get context (5 lines before and after)
            start = max(0, i - 5)
            end = min(len(lines), i + 6)
            relevant_lines.extend(lines[start:end])
    
    if not relevant_lines:
        print(f"No log entries found for transaction: {txn_id}")
        return None
    
    print(f"\nFound {len(relevant_lines)} relevant log lines")
    print("\n" + "=" * 80)
    print("LOG ENTRIES:")
    print("=" * 80)
    
    # Parse and categorize logs
    merchant_request = None
    gateway_request = None
    gateway_response = None
    callback_data = None
    
    for line in relevant_lines:
        print(line.strip())
        
        # Try to extract JSON data
        if 'merchant_request' in line.lower() or 'request payload' in line.lower():
            try:
                json_match = re.search(r'\{.*\}', line)
                if json_match:
                    merchant_request = json.loads(json_match.group())
            except:
                pass
        
        if 'gateway_request' in line.lower() or 'sending to gateway' in line.lower():
            try:
                json_match = re.search(r'\{.*\}', line)
                if json_match:
                    gateway_request = json.loads(json_match.group())
            except:
                pass
        
        if 'gateway_response' in line.lower() or 'response from gateway' in line.lower():
            try:
                json_match = re.search(r'\{.*\}', line)
                if json_match:
                    gateway_response = json.loads(json_match.group())
            except:
                pass
        
        if 'callback' in line.lower() and 'received' in line.lower():
            try:
                json_match = re.search(r'\{.*\}', line)
                if json_match:
                    callback_data = json.loads(json_match.group())
            except:
                pass
    
    print("\n" + "=" * 80)
    print("EXTRACTED DATA:")
    print("=" * 80)
    
    result = {
        'merchant_request': merchant_request,
        'gateway_request': gateway_request,
        'gateway_response': gateway_response,
        'callback_data': callback_data
    }
    
    for key, value in result.items():
        print(f"\n{key.upper()}:")
        if value:
            print(json.dumps(value, indent=2))
        else:
            print("  Not found in logs")
    
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_transaction_logs.py <transaction_id> [log_file]")
        print("\nExample:")
        print("  python extract_transaction_logs.py AIRPAY_9000000001_TRD341068C3A671BA_20260405150541")
        print("  python extract_transaction_logs.py AIRPAY_9000000001_TRD341068C3A671BA_20260405150541 /var/log/flask.log")
        sys.exit(1)
    
    txn_id = sys.argv[1]
    log_file = sys.argv[2] if len(sys.argv) > 2 else '/var/log/flask.log'
    
    extract_logs_for_transaction(txn_id, log_file)
