#!/usr/bin/env python3
"""
View the actual Rang callback response data
"""

from database import get_db_connection
import json
from datetime import datetime

def view_recent_rang_callbacks():
    """View recent Rang callback responses"""
    
    print("RECENT RANG CALLBACK RESPONSES")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get recent Rang transactions that were updated (indicating callback received)
    cursor.execute("""
        SELECT txn_id, order_id, status, amount, pg_txn_id, bank_ref_no,
               created_at, updated_at, callback_url
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND updated_at > created_at
        ORDER BY updated_at DESC
        LIMIT 10
    """)
    
    transactions = cursor.fetchall()
    
    if transactions:
        print(f"Found {len(transactions)} Rang transactions with callbacks:")
        
        for i, txn in enumerate(transactions, 1):
            print(f"\n--- Transaction {i} ---")
            print(f"TXN ID: {txn[0]}")
            print(f"Order ID: {txn[1]}")
            print(f"Status: {txn[2]}")
            print(f"Amount: ₹{txn[3]}")
            print(f"PG TXN ID: {txn[4]}")
            print(f"Bank Ref No (UTR): {txn[5]}")
            print(f"Created: {txn[6]}")
            print(f"Updated: {txn[7]}")
            print(f"Callback URL: {txn[8]}")
            
            # Check if there are any callback logs for this transaction
            cursor.execute("""
                SELECT request_data, response_data, response_code, created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (txn[0],))
            
            callback_log = cursor.fetchone()
            
            if callback_log:
                print(f"\n📞 CALLBACK LOG FOUND:")
                print(f"Response Code: {callback_log[2]}")
                print(f"Callback Time: {callback_log[3]}")
                
                # Parse and display request data (what we sent to merchant)
                try:
                    request_data = json.loads(callback_log[0])
                    print(f"\n📤 DATA SENT TO MERCHANT:")
                    for key, value in request_data.items():
                        print(f"  {key}: {value}")
                except:
                    print(f"Raw request data: {callback_log[0]}")
                
                print(f"\n📥 MERCHANT RESPONSE:")
                print(f"  {callback_log[1][:200]}...")
            else:
                print(f"\n❌ No callback log found (callback not forwarded to merchant)")
    else:
        print("❌ No Rang transactions with callbacks found")
    
    cursor.close()
    conn.close()

def check_application_logs():
    """Check what Rang sent us by looking at application logs"""
    
    print(f"\n\nAPPLICATION LOG ANALYSIS")
    print("=" * 60)
    
    print("""
To see what Rang actually sent to your callback endpoint, check:

1. Application logs for callback data:
   sudo journalctl -u moneyone-backend --since today | grep -A 10 -B 5 "RANG PAYIN CALLBACK"

2. Check for raw callback data:
   sudo journalctl -u moneyone-backend --since today | grep -A 20 "Callback Data"

3. Check server access logs:
   sudo grep "POST.*rang-payin-callback" /var/log/nginx/access.log | tail -5

4. Check for any errors:
   sudo journalctl -u moneyone-backend --since today | grep -i "error.*rang"

The callback handler logs the raw data Rang sends, so you should see:
- Headers received
- Content-Type
- Raw callback data
- Parsed parameters
    """)

if __name__ == "__main__":
    view_recent_rang_callbacks()
    check_application_logs()