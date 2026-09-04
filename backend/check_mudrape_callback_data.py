#!/usr/bin/env python3
"""
Check what callback data Mudrape is sending
Searches backend logs for callback data by PG transaction ID
"""

import sys
import pymysql
import json
import re
from config import Config
from datetime import datetime

def get_db_connection():
    """Get database connection"""
    try:
        return pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def find_transaction_by_pg_txn_id(pg_txn_id):
    """Find transaction by PG transaction ID"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    callback_url,
                    created_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_txn_id = %s OR order_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (pg_txn_id, pg_txn_id))
            
            return cursor.fetchone()
    finally:
        conn.close()

def search_callback_in_logs(identifier):
    """Search for callback data in backend logs"""
    print(f"\n{'='*80}")
    print(f"Searching Backend Logs for Callback Data")
    print(f"{'='*80}\n")
    
    try:
        with open('../backend.log', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ backend.log not found")
        return None
    
    # Search for callback containing the identifier
    callback_data = None
    in_callback = False
    callback_lines = []
    
    for i, line in enumerate(lines):
        # Check if this is a callback start
        if 'Mudrape Payin Callback Received' in line:
            in_callback = True
            callback_lines = [line]
            continue
        
        # Collect callback lines
        if in_callback:
            callback_lines.append(line)
            
            # Check if this callback contains our identifier
            if identifier in line:
                # Found it! Extract the JSON data
                for j in range(len(callback_lines)):
                    if 'Callback Data:' in callback_lines[j]:
                        # Next lines contain JSON
                        json_lines = []
                        for k in range(j+1, min(j+50, len(callback_lines))):
                            if callback_lines[k].strip().startswith('Ref ID:') or callback_lines[k].strip().startswith('TXN ID:'):
                                break
                            json_lines.append(callback_lines[k])
                        
                        # Try to parse JSON
                        json_str = ''.join(json_lines).strip()
                        try:
                            callback_data = json.loads(json_str)
                            return callback_data
                        except:
                            # Try to extract JSON from the line
                            match = re.search(r'\{.*\}', json_str, re.DOTALL)
                            if match:
                                try:
                                    callback_data = json.loads(match.group(0))
                                    return callback_data
                                except:
                                    pass
            
            # End of callback section
            if '='*80 in line and len(callback_lines) > 5:
                in_callback = False
                callback_lines = []
    
    return None

def check_callback_logs_table(txn_id):
    """Check callback_logs table for this transaction"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (txn_id,))
            
            return cursor.fetchone()
    finally:
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_mudrape_callback_data.py <pg_txn_id_or_ref_id>")
        print("\nExamples:")
        print("  python check_mudrape_callback_data.py MPAY70861522689")
        print("  python check_mudrape_callback_data.py 20241234567890123456")
        sys.exit(1)
    
    identifier = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"Mudrape Callback Data Checker")
    print(f"{'='*80}\n")
    print(f"Searching for: {identifier}\n")
    
    # Step 1: Find transaction in database
    print(f"{'='*80}")
    print(f"Step 1: Finding Transaction in Database")
    print(f"{'='*80}\n")
    
    txn = find_transaction_by_pg_txn_id(identifier)
    
    if not txn:
        print(f"❌ Transaction not found for: {identifier}")
        print(f"\nTrying to search logs anyway...\n")
    else:
        print(f"✅ Transaction Found:")
        print(f"  TXN ID: {txn['txn_id']}")
        print(f"  Order ID (refId): {txn['order_id']}")
        print(f"  PG TXN ID: {txn['pg_txn_id']}")
        print(f"  Amount: ₹{txn['amount']}")
        print(f"  Status: {txn['status']}")
        print(f"  UTR: {txn['bank_ref_no'] or 'Not set'}")
        print(f"  Callback URL: {txn['callback_url']}")
        print(f"  Created: {txn['created_at']}")
        print(f"  Completed: {txn['completed_at'] or 'Not completed'}")
        print()
    
    # Step 2: Check callback_logs table
    if txn:
        print(f"{'='*80}")
        print(f"Step 2: Checking Callback Logs Table")
        print(f"{'='*80}\n")
        
        callback_log = check_callback_logs_table(txn['txn_id'])
        
        if callback_log:
            print(f"✅ Callback Log Found:")
            print(f"  Log ID: {callback_log['id']}")
            print(f"  Callback URL: {callback_log['callback_url']}")
            print(f"  Response Code: {callback_log['response_code']}")
            print(f"  Created: {callback_log['created_at']}")
            print(f"\n  Request Data (what we sent to merchant):")
            try:
                request_data = json.loads(callback_log['request_data'])
                print(json.dumps(request_data, indent=4))
            except:
                print(f"  {callback_log['request_data']}")
            print()
        else:
            print(f"⚠️  No callback log found in database")
            print(f"   This means either:")
            print(f"   1. Callback not received yet")
            print(f"   2. No merchant callback configured")
            print()
    
    # Step 3: Search backend logs for callback data
    print(f"{'='*80}")
    print(f"Step 3: Searching Backend Logs for Callback Data")
    print(f"{'='*80}\n")
    
    # Search using all possible identifiers
    search_terms = [identifier]
    if txn:
        search_terms.extend([txn['order_id'], txn['pg_txn_id'], txn['txn_id']])
    
    callback_data = None
    for term in search_terms:
        if term:
            callback_data = search_callback_in_logs(term)
            if callback_data:
                break
    
    if callback_data:
        print(f"✅ Callback Data Found in Logs!")
        print(f"\n{'='*80}")
        print(f"CALLBACK DATA FROM MUDRAPE:")
        print(f"{'='*80}\n")
        print(json.dumps(callback_data, indent=4))
        print()
        
        # Analyze the callback data
        print(f"{'='*80}")
        print(f"Callback Data Analysis:")
        print(f"{'='*80}\n")
        
        # Check for refId
        ref_id = callback_data.get('refId') or callback_data.get('ref_id') or callback_data.get('RefID')
        print(f"  refId: {ref_id or '❌ NOT FOUND'}")
        
        # Check for txnId
        txn_id_cb = callback_data.get('txnId') or callback_data.get('txn_id')
        print(f"  txnId: {txn_id_cb or '❌ NOT FOUND'}")
        
        # Check for status
        status = callback_data.get('status')
        print(f"  status: {status or '❌ NOT FOUND'}")
        
        # Check for amount
        amount = callback_data.get('amount')
        print(f"  amount: {amount or '❌ NOT FOUND'}")
        
        # Check for UTR
        utr = (callback_data.get('utr') or 
               callback_data.get('UTR') or 
               callback_data.get('bankRefNo') or 
               callback_data.get('bank_ref_no'))
        print(f"  utr: {utr or '❌ NOT FOUND'}")
        
        # Check for timestamp
        timestamp = callback_data.get('timestamp') or callback_data.get('createdAt')
        print(f"  timestamp: {timestamp or '❌ NOT FOUND'}")
        
        print()
        
        # Verify against database
        if txn and ref_id:
            print(f"{'='*80}")
            print(f"Verification:")
            print(f"{'='*80}\n")
            
            if ref_id == txn['order_id']:
                print(f"  ✅ refId matches database order_id")
            else:
                print(f"  ❌ refId MISMATCH!")
                print(f"     Callback: {ref_id}")
                print(f"     Database: {txn['order_id']}")
            
            if txn_id_cb and txn_id_cb == txn['pg_txn_id']:
                print(f"  ✅ txnId matches database pg_txn_id")
            elif txn_id_cb:
                print(f"  ⚠️  txnId different:")
                print(f"     Callback: {txn_id_cb}")
                print(f"     Database: {txn['pg_txn_id']}")
            
            if amount and float(amount) == float(txn['amount']):
                print(f"  ✅ amount matches database")
            elif amount:
                print(f"  ❌ amount MISMATCH!")
                print(f"     Callback: {amount}")
                print(f"     Database: {txn['amount']}")
            
            print()
    else:
        print(f"❌ No callback data found in backend logs")
        print(f"\nPossible reasons:")
        print(f"  1. Callback not received yet")
        print(f"  2. Callback URL not configured in Mudrape")
        print(f"  3. Backend not accessible from internet")
        print(f"  4. Logs rotated/cleared")
        print()
        print(f"To monitor callbacks in real-time:")
        print(f"  tail -f backend.log | grep -A 30 'Mudrape Payin Callback'")
        print()
    
    # Step 4: Recommendations
    print(f"{'='*80}")
    print(f"Recommendations:")
    print(f"{'='*80}\n")
    
    if not callback_data:
        print(f"To receive callbacks from Mudrape:")
        print(f"  1. Configure callback URL in Mudrape dashboard:")
        print(f"     https://admin.moneyone.co.in/api/callback/mudrape/payin")
        print(f"  2. Ensure backend is accessible from internet")
        print(f"  3. Check firewall allows HTTPS (port 443)")
        print(f"  4. Monitor logs: tail -f backend.log | grep 'Callback'")
    else:
        print(f"✅ Callback data successfully captured!")
        print(f"\nCallback format from Mudrape:")
        print(f"  - Uses: {list(callback_data.keys())}")
        print(f"  - refId format: {'camelCase' if 'refId' in callback_data else 'snake_case' if 'ref_id' in callback_data else 'unknown'}")
        print(f"  - txnId format: {'camelCase' if 'txnId' in callback_data else 'snake_case' if 'txn_id' in callback_data else 'unknown'}")
    
    print()

if __name__ == '__main__':
    main()
