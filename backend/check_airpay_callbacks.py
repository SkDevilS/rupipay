#!/usr/bin/env python3
"""
Check recent Airpay callbacks from server logs and database
"""
import os
import sys
from datetime import datetime, timedelta
from database import get_db_connection

def check_recent_callbacks():
    """Check recent Airpay callbacks"""
    print("=" * 80)
    print("AIRPAY CALLBACK CHECKER")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check recent Airpay transactions
            print("\n1. Recent Airpay Transactions (Last 24 hours):")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    callback_url,
                    created_at,
                    updated_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                AND created_at >= NOW() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            if transactions:
                for txn in transactions:
                    print(f"\nTransaction ID: {txn['txn_id']}")
                    print(f"  Order ID: {txn['order_id']}")
                    print(f"  Merchant ID: {txn['merchant_id']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Status: {txn['status']}")
                    print(f"  PG Txn ID: {txn['pg_txn_id']}")
                    print(f"  Bank Ref: {txn['bank_ref_no']}")
                    print(f"  Callback URL: {txn['callback_url']}")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Updated: {txn['updated_at']}")
            else:
                print("No Airpay transactions found in last 24 hours")
            
            # Check callback logs if table exists
            print("\n2. Recent Callback Logs (Last 24 hours):")
            print("-" * 80)
            try:
                cursor.execute("""
                    SELECT 
                        txn_id,
                        callback_url,
                        callback_data,
                        response_status,
                        response_data,
                        created_at
                    FROM callback_logs
                    WHERE created_at >= NOW() - INTERVAL 24 HOUR
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                logs = cursor.fetchall()
                if logs:
                    for log in logs:
                        print(f"\nCallback Log:")
                        print(f"  Txn ID: {log['txn_id']}")
                        print(f"  URL: {log['callback_url']}")
                        print(f"  Data: {log['callback_data'][:200]}...")
                        print(f"  Response Status: {log['response_status']}")
                        print(f"  Response: {log['response_data'][:200] if log['response_data'] else 'None'}...")
                        print(f"  Time: {log['created_at']}")
                else:
                    print("No callback logs found")
            except Exception as e:
                print(f"Callback logs table may not exist: {e}")
            
    finally:
        conn.close()
    
    # Check server logs
    print("\n3. Checking Server Logs for Airpay Callbacks:")
    print("-" * 80)
    print("\nRun this command to see recent Airpay callback logs:")
    print("sudo journalctl -u moneyone-backend -n 500 | grep -i 'airpay.*callback'")
    print("\nOr for more detailed logs:")
    print("sudo journalctl -u moneyone-backend --since '1 hour ago' | grep -A 20 'Airpay V4 Payin Callback'")

if __name__ == '__main__':
    check_recent_callbacks()
