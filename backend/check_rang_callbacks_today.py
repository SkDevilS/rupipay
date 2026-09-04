#!/usr/bin/env python3
"""
Check Rang callbacks for today's transactions
Shows if callbacks were received and what data was sent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json

def check_todays_rang_transactions():
    """Check all Rang transactions created today"""
    print("=" * 80)
    print("RANG TRANSACTIONS CREATED TODAY")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's Rang transactions
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, status, 
                bank_ref_no, pg_txn_id, callback_url,
                created_at, updated_at, completed_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
        """)
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("❌ No Rang transactions found for today")
            return
        
        print(f"✅ Found {len(transactions)} Rang transaction(s) today:")
        print()
        
        for i, txn in enumerate(transactions, 1):
            print(f"Transaction {i}:")
            print(f"  TXN ID: {txn['txn_id']}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Merchant: {txn['merchant_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Status: {txn['status']}")
            print(f"  UTR: {txn['bank_ref_no'] or 'Not received'}")
            print(f"  PG TXN ID: {txn['pg_txn_id'] or 'Not received'}")
            print(f"  Callback URL: {txn['callback_url'] or 'Not set'}")
            print(f"  Created: {txn['created_at']}")
            print(f"  Updated: {txn['updated_at']}")
            print(f"  Completed: {txn['completed_at'] or 'Not completed'}")
            print("-" * 60)
        
        cursor.close()
        conn.close()
        
        return transactions
        
    except Exception as e:
        print(f"❌ Error checking transactions: {str(e)}")
        return []

def check_rang_callback_logs():
    """Check callback logs for Rang transactions today"""
    print("\n" + "=" * 80)
    print("RANG CALLBACK LOGS FOR TODAY")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get callback logs for today's Rang transactions
        cursor.execute("""
            SELECT 
                cl.merchant_id, cl.txn_id, cl.callback_url,
                cl.request_data, cl.response_code, cl.response_data,
                cl.created_at,
                pt.order_id, pt.status as txn_status
            FROM callback_logs cl
            JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
            WHERE pt.pg_partner = 'Rang'
            AND DATE(cl.created_at) = CURDATE()
            ORDER BY cl.created_at DESC
        """)
        
        callback_logs = cursor.fetchall()
        
        if not callback_logs:
            print("❌ No callback logs found for Rang transactions today")
            print("   This means either:")
            print("   - No callbacks were received from Rang")
            print("   - No merchant callbacks were forwarded")
            return
        
        print(f"✅ Found {len(callback_logs)} callback log(s) for Rang today:")
        print()
        
        for i, log in enumerate(callback_logs, 1):
            print(f"Callback Log {i}:")
            print(f"  TXN ID: {log['txn_id']}")
            print(f"  Order ID: {log['order_id']}")
            print(f"  Merchant: {log['merchant_id']}")
            print(f"  Transaction Status: {log['txn_status']}")
            print(f"  Callback URL: {log['callback_url']}")
            print(f"  Response Code: {log['response_code']}")
            print(f"  Timestamp: {log['created_at']}")
            
            # Parse and display request data
            try:
                request_data = json.loads(log['request_data'])
                print(f"  Request Data:")
                for key, value in request_data.items():
                    print(f"    {key}: {value}")
            except:
                print(f"  Request Data: {log['request_data']}")
            
            # Show response data (truncated)
            response_data = log['response_data'] or 'No response'
            if len(response_data) > 100:
                response_data = response_data[:100] + "..."
            print(f"  Response: {response_data}")
            print("-" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking callback logs: {str(e)}")

def check_rang_callback_received():
    """Check if Rang sent any callbacks to our system today"""
    print("\n" + "=" * 80)
    print("CHECKING IF RANG CALLBACKS WERE RECEIVED")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for transactions that were updated today (indicating callback received)
        cursor.execute("""
            SELECT 
                txn_id, order_id, status, bank_ref_no, pg_txn_id,
                created_at, updated_at, completed_at,
                CASE 
                    WHEN updated_at > created_at THEN 'YES'
                    ELSE 'NO'
                END as callback_received
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
        """)
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("❌ No Rang transactions found for today")
            return
        
        print("Callback Status Analysis:")
        print()
        
        callbacks_received = 0
        callbacks_pending = 0
        
        for txn in transactions:
            callback_status = "✅ RECEIVED" if txn['callback_received'] == 'YES' else "❌ PENDING"
            
            if txn['callback_received'] == 'YES':
                callbacks_received += 1
            else:
                callbacks_pending += 1
            
            print(f"TXN: {txn['txn_id']}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Status: {txn['status']}")
            print(f"  Callback: {callback_status}")
            print(f"  Created: {txn['created_at']}")
            print(f"  Updated: {txn['updated_at']}")
            
            if txn['callback_received'] == 'YES':
                print(f"  UTR: {txn['bank_ref_no'] or 'Not provided'}")
                print(f"  PG TXN ID: {txn['pg_txn_id'] or 'Not provided'}")
                print(f"  Completed: {txn['completed_at'] or 'Not set'}")
            
            print()
        
        print("=" * 60)
        print(f"SUMMARY:")
        print(f"  Total Transactions: {len(transactions)}")
        print(f"  Callbacks Received: {callbacks_received}")
        print(f"  Callbacks Pending: {callbacks_pending}")
        
        if callbacks_pending > 0:
            print(f"\n⚠️  {callbacks_pending} transaction(s) haven't received callbacks yet")
            print("   Possible reasons:")
            print("   - Payment not completed by customer")
            print("   - Rang hasn't sent callback yet")
            print("   - Callback URL configuration issue")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking callback status: {str(e)}")

if __name__ == "__main__":
    print("RANG CALLBACK CHECKER - TODAY'S TRANSACTIONS")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check all today's transactions
    transactions = check_todays_rang_transactions()
    
    # Check callback logs
    check_rang_callback_logs()
    
    # Check callback received status
    check_rang_callback_received()
    
    print("\n" + "=" * 80)
    print("CALLBACK CHECKER COMPLETED")
    print("=" * 80)