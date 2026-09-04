#!/usr/bin/env python3
"""
Check the most recent 2 Airpay transactions and their callback data
"""
import os
import sys
from datetime import datetime
from database import get_db_connection
import json

def check_recent_transactions():
    """Check recent Airpay transactions and callback data"""
    print("=" * 100)
    print("AIRPAY RECENT TRANSACTIONS AND CALLBACK DATA")
    print("=" * 100)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get most recent 2 Airpay transactions
            print("\n📋 Fetching most recent 2 Airpay transactions...")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    payee_name,
                    payee_email,
                    payee_mobile,
                    callback_url,
                    created_at,
                    updated_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 2
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No Airpay transactions found")
                return
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{'='*100}")
                print(f"TRANSACTION #{idx}")
                print(f"{'='*100}")
                
                print(f"\n📌 Transaction Details:")
                print(f"  Transaction ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Merchant ID: {txn['merchant_id']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Charge: ₹{txn['charge_amount']}")
                print(f"  Net Amount: ₹{txn['net_amount']}")
                print(f"  Status: {txn['status']}")
                print(f"  PG Txn ID: {txn['pg_txn_id']}")
                print(f"  Bank Ref/UTR: {txn['bank_ref_no']}")
                print(f"  Payment Mode: {txn['payment_mode']}")
                print(f"  Payee: {txn['payee_name']}")
                print(f"  Email: {txn['payee_email']}")
                print(f"  Mobile: {txn['payee_mobile']}")
                print(f"  Callback URL: {txn['callback_url']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Updated: {txn['updated_at']}")
                print(f"  Completed: {txn['completed_at']}")
                
                # Check if callback was sent to merchant
                print(f"\n📤 Merchant Callback Logs:")
                print("-" * 100)
                
                try:
                    cursor.execute("""
                        SELECT 
                            callback_url,
                            callback_data,
                            response_status,
                            response_data,
                            created_at
                        FROM callback_logs
                        WHERE txn_id = %s
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (txn['txn_id'],))
                    
                    callback_logs = cursor.fetchall()
                    
                    if callback_logs:
                        for log_idx, log in enumerate(callback_logs, 1):
                            print(f"\n  Callback Attempt #{log_idx}:")
                            print(f"    URL: {log['callback_url']}")
                            print(f"    Time: {log['created_at']}")
                            print(f"    Response Status: {log['response_status']}")
                            
                            # Parse and display callback data
                            try:
                                callback_data = json.loads(log['callback_data'])
                                print(f"    Callback Data Sent to Merchant:")
                                for key, value in callback_data.items():
                                    print(f"      {key}: {value}")
                            except:
                                print(f"    Callback Data: {log['callback_data'][:200]}...")
                            
                            if log['response_data']:
                                print(f"    Merchant Response: {log['response_data'][:200]}...")
                    else:
                        print("  ⚠️  No callback logs found for this transaction")
                        print("  This means either:")
                        print("    1. Callback was not sent to merchant")
                        print("    2. Callback URL was not configured")
                        print("    3. Airpay hasn't sent callback yet")
                
                except Exception as e:
                    print(f"  ⚠️  Could not fetch callback logs: {e}")
                
                # Check wallet transactions
                print(f"\n💰 Wallet Transactions:")
                print("-" * 100)
                
                cursor.execute("""
                    SELECT 
                        wallet_txn_id,
                        merchant_id,
                        txn_type,
                        amount,
                        balance_after,
                        description,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    for wtxn in wallet_txns:
                        print(f"\n  Wallet Transaction:")
                        print(f"    ID: {wtxn['wallet_txn_id']}")
                        print(f"    Merchant: {wtxn['merchant_id']}")
                        print(f"    Type: {wtxn['txn_type']}")
                        print(f"    Amount: ₹{wtxn['amount']}")
                        print(f"    Balance After: ₹{wtxn['balance_after']}")
                        print(f"    Description: {wtxn['description']}")
                        print(f"    Time: {wtxn['created_at']}")
                else:
                    print("  ⚠️  No wallet transactions found")
                    print("  This means wallet was not credited (transaction may not be successful)")
            
            # Check server logs
            print(f"\n{'='*100}")
            print("📝 SERVER LOGS")
            print(f"{'='*100}")
            print("\nTo see what Airpay sent in callbacks, check server logs:")
            print("\n1. Recent Airpay callbacks:")
            print("   sudo journalctl -u moneyone-backend --since '2 hours ago' | grep -A 30 'Airpay V4 Payin Callback'")
            
            print("\n2. Check callback log file (if exists):")
            print("   cat /var/www/moneyone/moneyone/backend/logs/airpay_callbacks_*.log | tail -200")
            
            print("\n3. Search for specific order ID in logs:")
            if transactions:
                print(f"   sudo journalctl -u moneyone-backend | grep '{transactions[0]['order_id']}'")
            
    finally:
        conn.close()
    
    print(f"\n{'='*100}")
    print("SUMMARY")
    print(f"{'='*100}")
    print("\nTo debug callback forwarding issues:")
    print("1. Check if Airpay is sending callbacks (server logs)")
    print("2. Check if callback_url is stored in transaction")
    print("3. Check if callback was forwarded to merchant (callback_logs table)")
    print("4. Check merchant's callback endpoint is accessible")
    print("\nIf callbacks are not being forwarded:")
    print("- Verify callback_url is in customvar when creating order")
    print("- Check airpay_callback_routes.py is parsing customvar correctly")
    print("- Ensure merchant's callback endpoint is reachable")

if __name__ == '__main__':
    check_recent_transactions()
