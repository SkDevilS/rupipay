#!/usr/bin/env python3
"""
Check a specific payin transaction and see if callback was received
"""

import pymysql
from database import get_db_connection

def check_specific_payin(txn_id):
    """Check specific payin and callback logs"""
    
    print("=" * 80)
    print(f"Checking PayIn: {txn_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get payin details
            cursor.execute("""
                SELECT * FROM payin_transactions WHERE txn_id = %s
            """, (txn_id,))
            
            payin = cursor.fetchone()
            
            if not payin:
                print(f"❌ PayIn {txn_id} not found")
                return
            
            print(f"\nPayIn Details:")
            print(f"  Order ID: {payin['order_id']}")
            print(f"  Merchant: {payin['merchant_id']}")
            print(f"  Status: {payin['status']}")
            print(f"  Amount: ₹{payin['amount']}")
            print(f"  Charge: ₹{payin['charge_amount']}")
            print(f"  Net: ₹{payin['net_amount']}")
            print(f"  Gateway: {payin.get('pg_partner', 'PayU')}")
            print(f"  PG TXN ID: {payin.get('pg_txn_id', 'N/A')}")
            print(f"  UTR: {payin.get('bank_ref_no', 'N/A')}")
            print(f"  Created: {payin['created_at']}")
            print(f"  Completed: {payin.get('completed_at', 'Not completed')}")
            
            # Check callback logs
            print(f"\n" + "=" * 80)
            print("Checking Callback Logs...")
            print("=" * 80)
            
            cursor.execute("""
                SELECT * FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
            """, (txn_id,))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print(f"\nFound {len(callback_logs)} callback log entries:")
                for log in callback_logs:
                    print(f"\n  Callback URL: {log['callback_url']}")
                    print(f"  Response Code: {log['response_code']}")
                    print(f"  Request Data: {log.get('request_data', 'N/A')[:200]}")
                    print(f"  Response Data: {log.get('response_data', 'N/A')[:200]}")
                    print(f"  Created: {log['created_at']}")
            else:
                print("\n⚠️  NO callback logs found!")
                print("   This means either:")
                print("   1. Mudrape callback was never received")
                print("   2. Callback processing failed before logging")
                print("   3. Status was updated via status check, not callback")
            
            # Check if wallet was credited
            print(f"\n" + "=" * 80)
            print("Checking Wallet Credits...")
            print("=" * 80)
            
            cursor.execute("""
                SELECT * FROM merchant_wallet_transactions
                WHERE reference_id = %s
            """, (txn_id,))
            
            merchant_txns = cursor.fetchall()
            
            if merchant_txns:
                print(f"\n✓ Found merchant wallet transaction:")
                for txn in merchant_txns:
                    print(f"  Type: {txn['txn_type']}, Amount: ₹{txn['amount']}")
            else:
                print(f"\n❌ NO merchant wallet transaction found!")
                print(f"   Merchant wallet was NOT credited for this payin")
            
            cursor.execute("""
                SELECT * FROM admin_wallet_transactions
                WHERE reference_id = %s
            """, (txn_id,))
            
            admin_txns = cursor.fetchall()
            
            if admin_txns:
                print(f"\n✓ Found admin wallet transaction:")
                for txn in admin_txns:
                    print(f"  Type: {txn['txn_type']}, Amount: ₹{txn['amount']}")
            else:
                print(f"\n❌ NO admin wallet transaction found!")
                print(f"   Admin wallet was NOT credited for this payin")
            
            # SOLUTION
            print(f"\n" + "=" * 80)
            print("SOLUTION")
            print("=" * 80)
            
            if payin['status'] == 'SUCCESS' and not merchant_txns:
                print(f"\nThis payin is marked SUCCESS but wallet was NOT credited.")
                print(f"This can happen if:")
                print(f"  1. Callback was never received from Mudrape")
                print(f"  2. Status was checked but wallet credit failed")
                print(f"  3. Code was not deployed when this payin happened")
                print(f"\nTo fix this specific transaction, you can:")
                print(f"  1. Use admin manual complete to credit the wallet")
                print(f"  2. Or create a script to backfill this transaction")
                print(f"\nFor FUTURE transactions:")
                print(f"  1. Ensure the fix is deployed")
                print(f"  2. Restart backend: sudo systemctl restart moneyone-backend")
                print(f"  3. Test with a NEW payin transaction")
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        check_specific_payin(sys.argv[1])
    else:
        # Use the latest payin
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT txn_id FROM payin_transactions ORDER BY created_at DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                check_specific_payin(result['txn_id'])
        conn.close()
