#!/usr/bin/env python3
"""
Check the latest Airpay callback received and transaction status
"""

from database import get_db_connection
import json
from datetime import datetime

print("=" * 100)
print("CHECKING LATEST AIRPAY TRANSACTION AND CALLBACK")
print("=" * 100)
print()

conn = get_db_connection()
if not conn:
    print("❌ Database connection failed")
    exit(1)

try:
    with conn.cursor() as cursor:
        # Check latest Airpay transaction
        print("📋 LATEST AIRPAY TRANSACTION:")
        print("-" * 100)
        cursor.execute("""
            SELECT txn_id, order_id, merchant_id, amount, net_amount, charge_amount, 
                   status, pg_txn_id, bank_ref_no, payment_mode, 
                   created_at, completed_at, updated_at
            FROM payin_transactions
            WHERE pg_partner = 'Airpay'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        
        if txn:
            print(f"Transaction ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant ID: {txn['merchant_id']}")
            print(f"Amount: ₹{txn['amount']}")
            print(f"Net Amount: ₹{txn['net_amount']}")
            print(f"Charge: ₹{txn['charge_amount']}")
            print(f"Status: {txn['status']}")
            print(f"PG Txn ID: {txn['pg_txn_id']}")
            print(f"Bank Ref No (UTR): {txn['bank_ref_no']}")
            print(f"Payment Mode: {txn['payment_mode']}")
            print(f"Created: {txn['created_at']}")
            print(f"Completed: {txn['completed_at']}")
            print(f"Updated: {txn['updated_at']}")
            print()
            
            # Check wallet credits
            print("💰 WALLET CREDITS FOR THIS TRANSACTION:")
            print("-" * 100)
            cursor.execute("""
                SELECT merchant_id, txn_id, txn_type, amount, balance_before, balance_after, 
                       description, created_at
                FROM merchant_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                for wt in wallet_txns:
                    print(f"  Merchant: {wt['merchant_id']}")
                    print(f"  Type: {wt['txn_type']}")
                    print(f"  Amount: ₹{wt['amount']}")
                    print(f"  Balance: ₹{wt['balance_before']} → ₹{wt['balance_after']}")
                    print(f"  Description: {wt['description']}")
                    print(f"  Created: {wt['created_at']}")
                    print()
            else:
                print("  ⚠️  NO WALLET CREDITS FOUND")
                print()
            
            # Check callback logs
            print("📞 CALLBACK LOGS FOR THIS TRANSACTION:")
            print("-" * 100)
            cursor.execute("""
                SELECT merchant_id, txn_id, callback_url, request_data, response_code, 
                       response_data, created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                for log in callback_logs:
                    print(f"  Callback URL: {log['callback_url']}")
                    print(f"  Response Code: {log['response_code']}")
                    print(f"  Request Data: {log['request_data'][:200]}...")
                    print(f"  Response Data: {log['response_data'][:200]}...")
                    print(f"  Created: {log['created_at']}")
                    print()
            else:
                print("  ⚠️  NO CALLBACK LOGS FOUND")
                print()
            
            # Check merchant callback configuration
            print("⚙️  MERCHANT CALLBACK CONFIGURATION:")
            print("-" * 100)
            cursor.execute("""
                SELECT merchant_id, callback_url, is_active, created_at, updated_at
                FROM merchant_callbacks
                WHERE merchant_id = %s
            """, (txn['merchant_id'],))
            
            merchant_callback = cursor.fetchone()
            
            if merchant_callback:
                print(f"  Merchant ID: {merchant_callback['merchant_id']}")
                print(f"  Callback URL: {merchant_callback['callback_url']}")
                print(f"  Is Active: {merchant_callback['is_active']}")
                print(f"  Created: {merchant_callback['created_at']}")
                print(f"  Updated: {merchant_callback['updated_at']}")
            else:
                print("  ⚠️  NO MERCHANT CALLBACK CONFIGURATION FOUND")
            print()
            
        else:
            print("❌ No Airpay transactions found")
            print()
        
        # Check callback log file
        print("📄 CHECKING CALLBACK LOG FILE:")
        print("-" * 100)
        import os
        log_dir = '/var/www/moneyone/moneyone/backend/logs'
        today = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f'airpay_callbacks_{today}.log')
        
        if os.path.exists(log_file):
            print(f"Log file exists: {log_file}")
            print(f"Last 50 lines:")
            print()
            os.system(f"tail -50 {log_file}")
        else:
            print(f"⚠️  Log file not found: {log_file}")
        print()

finally:
    conn.close()

print("=" * 100)
print("DIAGNOSIS COMPLETE")
print("=" * 100)
print()
print("NEXT STEPS:")
print("1. If status is still INITIATED - callback was not received or not processed")
print("2. If wallet credits are missing - callback processing failed")
print("3. If callback logs are missing - callback forwarding failed")
print("4. Check backend logs: sudo journalctl -u moneyone-backend -n 100")
print()
