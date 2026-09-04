#!/usr/bin/env python3
"""
Check Airpay callback processing issue
"""

import pymysql
import json
from datetime import datetime
from config import DB_CONFIG

def check_latest_airpay_transaction():
    """Check the latest Airpay transaction and its callback status"""
    
    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    
    try:
        with conn.cursor() as cursor:
            print("=" * 100)
            print("CHECKING LATEST AIRPAY TRANSACTION AND CALLBACK")
            print("=" * 100)
            
            # Get latest Airpay transaction
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    net_amount,
                    charge_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    created_at,
                    completed_at,
                    updated_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("⚠️  NO AIRPAY TRANSACTIONS FOUND")
                return
            
            print("\n📋 LATEST AIRPAY TRANSACTION:")
            print("-" * 100)
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
            
            # Check wallet credits for this transaction
            print("\n💰 WALLET CREDITS FOR THIS TRANSACTION:")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    amount,
                    txn_type,
                    description,
                    reference_id,
                    created_at
                FROM merchant_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                for wt in wallet_txns:
                    print(f"  ID: {wt['id']}")
                    print(f"  Merchant ID: {wt['merchant_id']}")
                    print(f"  Amount: ₹{wt['amount']}")
                    print(f"  Type: {wt['txn_type']}")
                    print(f"  Description: {wt['description']}")
                    print(f"  Created: {wt['created_at']}")
                    print()
            else:
                print("⚠️  NO WALLET CREDITS FOUND")
            
            # Check callback logs for this transaction
            print("\n📞 CALLBACK LOGS FOR THIS TRANSACTION:")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    txn_id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                for log in callback_logs:
                    print(f"  ID: {log['id']}")
                    print(f"  Callback URL: {log['callback_url']}")
                    print(f"  Response Code: {log['response_code']}")
                    print(f"  Request Data: {log['request_data'][:200]}...")
                    print(f"  Response Data: {log['response_data'][:200] if log['response_data'] else 'None'}...")
                    print(f"  Created: {log['created_at']}")
                    print()
            else:
                print("⚠️  NO CALLBACK LOGS FOUND")
            
            # Check merchant callback configuration
            print("\n⚙️  MERCHANT CALLBACK CONFIGURATION:")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    merchant_id,
                    payin_callback_url,
                    payout_callback_url,
                    created_at,
                    updated_at
                FROM merchant_callbacks
                WHERE merchant_id = %s
            """, (txn['merchant_id'],))
            
            callback_config = cursor.fetchone()
            
            if callback_config:
                print(f"  Merchant ID: {callback_config['merchant_id']}")
                print(f"  Payin Callback URL: {callback_config['payin_callback_url']}")
                print(f"  Payout Callback URL: {callback_config['payout_callback_url']}")
                print(f"  Created: {callback_config['created_at']}")
                print(f"  Updated: {callback_config['updated_at']}")
            else:
                print("⚠️  NO CALLBACK CONFIGURATION FOUND FOR THIS MERCHANT")
            
            print("\n" + "=" * 100)
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_latest_airpay_transaction()
