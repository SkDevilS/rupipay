#!/usr/bin/env python3
"""
Check Rang callback status - simple version
"""

from database import get_db_connection
import json
from datetime import datetime

def check_callback_logs():
    """Check callback logs for Rang transactions"""
    
    print("RANG CALLBACK LOGS CHECK")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check callback_logs for today
    cursor.execute("""
        SELECT cl.merchant_id, cl.txn_id, cl.callback_url, cl.response_code, 
               cl.request_data, cl.response_data, cl.created_at,
               pt.order_id, pt.pg_partner, pt.amount
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
            print(f"\nTXN: {log[1]}")  # txn_id
            print(f"Order: {log[7]}")  # order_id
            print(f"Amount: ₹{log[9]}")  # amount
            print(f"Callback URL: {log[2]}")  # callback_url
            print(f"Response Code: {log[3]}")  # response_code
            print(f"Time: {log[6]}")  # created_at
            
            # Show request data (what we sent to merchant)
            try:
                request_data = json.loads(log[4])  # request_data
                print("Data sent to merchant:")
                for key, value in request_data.items():
                    print(f"  {key}: {value}")
            except:
                print(f"Raw request data: {log[4][:100] if log[4] else 'None'}...")
    else:
        print("❌ No Rang callback logs found today")
    
    cursor.close()
    conn.close()

def check_transaction_updates():
    """Check which transactions got updated (indicating callback received)"""
    
    print(f"\n\nTRANSACTION UPDATE CHECK")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
            print(f"\nTXN: {txn[0]}")  # txn_id
            print(f"Order: {txn[1]}")  # order_id
            print(f"Status: {txn[2]}")  # status
            print(f"Amount: ₹{txn[3]}")  # amount
            print(f"PG TXN ID: {txn[4]}")  # pg_txn_id
            print(f"Created: {txn[5]}")  # created_at
            print(f"Updated: {txn[6]}")  # updated_at
            print(f"Update delay: {txn[7]} seconds")  # update_delay
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
            print(f"  TXN: {txn[0]} - Order: {txn[1]} - Status: {txn[2]} - PG: {txn[4]}")
    
    cursor.close()
    conn.close()

def check_merchant_callback_config():
    """Check merchant callback configuration"""
    
    print(f"\n\nMERCHANT CALLBACK CONFIG")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT merchant_id, payin_callback_url, payout_callback_url
        FROM merchant_callbacks
        WHERE merchant_id = '7679022140'
    """)
    
    config = cursor.fetchone()
    
    if config:
        print(f"Merchant ID: {config[0]}")
        print(f"Payin Callback URL: {config[1]}")
        print(f"Payout Callback URL: {config[2]}")
    else:
        print("❌ No callback configuration found for merchant 7679022140")
    
    cursor.close()
    conn.close()

def check_server_logs():
    """Check what we should look for in server logs"""
    
    print(f"\n\nSERVER LOG ANALYSIS")
    print("=" * 50)
    
    print("""
To check if Rang is sending callbacks to your server:

1. Check Nginx access logs:
   sudo tail -f /var/log/nginx/access.log | grep rang

2. Check for POST requests to callback endpoint:
   sudo grep "POST.*rang-payin-callback" /var/log/nginx/access.log

3. Check application logs:
   sudo journalctl -u moneyone-backend -f | grep -i rang

4. Look for specific patterns:
   - "RANG PAYIN CALLBACK RECEIVED" (from your callback handler)
   - POST requests to /rang-payin-callback
   - Any 200/400/500 responses from callback endpoint

If you see NO entries, then Rang is not sending callbacks to your server.
If you see entries but no database updates, then there's an issue with callback processing.
    """)

if __name__ == "__main__":
    check_callback_logs()
    check_transaction_updates()
    check_merchant_callback_config()
    check_server_logs()