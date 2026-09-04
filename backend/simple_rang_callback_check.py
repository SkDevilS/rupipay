#!/usr/bin/env python3
"""
Simple check for Rang callback issues
"""

from database import get_db_connection
import json
from datetime import datetime

def check_callback_logs():
    """Check callback logs for Rang transactions"""
    
    print("RANG CALLBACK LOGS CHECK")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check callback_logs for today
    cursor.execute("""
        SELECT cl.*, pt.order_id, pt.pg_partner, pt.amount
        FROM callback_logs cl
        JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
        WHERE pt.pg_partner = 'Rang'
        AND DATE(cl.created_at) = CURDATE()
        ORDER BY cl.created_at DESC
    """)
    
    logs = cursor.fetchall()
    
    if logs:
        print(f"Found {len(logs)} Rang callback logs today:")
        for log in logs:
            print(f"\nTXN: {log['txn_id']}")
            print(f"Order: {log['order_id']}")
            print(f"Amount: ₹{log['amount']}")
            print(f"Callback URL: {log['callback_url']}")
            print(f"Response Code: {log['response_code']}")
            print(f"Time: {log['created_at']}")
            
            # Show request data (what we sent to merchant)
            try:
                request_data = json.loads(log['request_data'])
                print("Data sent to merchant:")
                for key, value in request_data.items():
                    print(f"  {key}: {value}")
            except:
                print(f"Raw request data: {log['request_data'][:100]}...")
    else:
        print("❌ No Rang callback logs found today")
    
    cursor.close()
    conn.close()

def check_transaction_updates():
    """Check which transactions got updated (indicating callback received)"""
    
    print(f"\n\nTRANSACTION UPDATE CHECK")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check transactions that were updated after creation
    cursor.execute("""
        SELECT txn_id, order_id, status, amount, pg_txn_id,
               created_at, updated_at,
               TIMESTAMPDIFF(SECOND, created_at, updated_at) as update_delay
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND DATE(created_at) = CURDATE()
        AND updated_at > created_at
        ORDER BY created_at DESC
    """)
    
    updated_txns = cursor.fetchall()
    
    if updated_txns:
        print(f"Found {len(updated_txns)} transactions that were updated:")
        for txn in updated_txns:
            print(f"\nTXN: {txn['txn_id']}")
            print(f"Order: {txn['order_id']}")
            print(f"Status: {txn['status']}")
            print(f"Amount: ₹{txn['amount']}")
            print(f"PG TXN ID: {txn['pg_txn_id']}")
            print(f"Created: {txn['created_at']}")
            print(f"Updated: {txn['updated_at']}")
            print(f"Update delay: {txn['update_delay']} seconds")
            print("✅ This transaction received a callback")
    else:
        print("❌ No transactions were updated (no callbacks processed)")
    
    # Check transactions that haven't been updated
    cursor.execute("""
        SELECT txn_id, order_id, status, amount, pg_txn_id, created_at
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND DATE(created_at) = CURDATE()
        AND updated_at = created_at
        AND pg_txn_id IS NOT NULL
        ORDER BY created_at DESC
    """)
    
    stuck_txns = cursor.fetchall()
    
    if stuck_txns:
        print(f"\n❌ Found {len(stuck_txns)} transactions stuck (no callback):")
        for txn in stuck_txns:
            print(f"  TXN: {txn['txn_id']} - Order: {txn['order_id']} - Status: {txn['status']} - PG: {txn['pg_txn_id']}")
    
    cursor.close()
    conn.close()

def check_merchant_callback_config():
    """Check merchant callback configuration"""
    
    print(f"\n\nMERCHANT CALLBACK CONFIG")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT merchant_id, payin_callback_url, payout_callback_url
        FROM merchant_callbacks
        WHERE merchant_id = '7679022140'
    """)
    
    config = cursor.fetchone()
    
    if config:
        print(f"Merchant ID: {config['merchant_id']}")
        print(f"Payin Callback URL: {config['payin_callback_url']}")
        print(f"Payout Callback URL: {config['payout_callback_url']}")
    else:
        print("❌ No callback configuration found for merchant 7679022140")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_callback_logs()
    check_transaction_updates()
    check_merchant_callback_config()