#!/usr/bin/env python3
"""
Check if a Viyonapay order exists in the database
"""
import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database import get_db_connection

# Order ID from the callback
order_id = "ORD98787865452612432"

print(f"\n{'='*60}")
print(f"🔍 Checking Viyonapay Order in Database")
print(f"{'='*60}\n")

conn = get_db_connection()
if not conn:
    print(f"❌ Database connection failed")
    sys.exit(1)

try:
    with conn.cursor() as cursor:
        # Search for transaction
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, net_amount, charge_amount,
                status, pg_partner, pg_txn_id, bank_ref_no, payment_mode,
                created_at, updated_at, completed_at
            FROM payin_transactions
            WHERE order_id = %s
            ORDER BY created_at DESC
        """, (order_id,))
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print(f"❌ No transaction found for order_id: {order_id}")
            print(f"\nSearching for similar order IDs...")
            
            # Search for similar order IDs
            cursor.execute("""
                SELECT order_id, txn_id, status, pg_partner, created_at
                FROM payin_transactions
                WHERE order_id LIKE %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (f"%{order_id[:10]}%",))
            
            similar = cursor.fetchall()
            if similar:
                print(f"\n📋 Similar Order IDs:")
                for txn in similar:
                    print(f"  - {txn['order_id']} | {txn['txn_id']} | {txn['status']} | {txn['pg_partner']} | {txn['created_at']}")
            else:
                print(f"  No similar order IDs found")
            
            # Check recent VIYONAPAY transactions
            print(f"\n📋 Recent VIYONAPAY Transactions:")
            cursor.execute("""
                SELECT txn_id, order_id, status, amount, created_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            recent = cursor.fetchall()
            if recent:
                for txn in recent:
                    print(f"  - {txn['order_id']} | {txn['txn_id']} | {txn['status']} | ₹{txn['amount']} | {txn['created_at']}")
            else:
                print(f"  No VIYONAPAY transactions found")
        else:
            print(f"✅ Found {len(transactions)} transaction(s):\n")
            
            for txn in transactions:
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Amount: ₹{txn['amount']}")
                print(f"Net Amount: ₹{txn['net_amount']}")
                print(f"Charge: ₹{txn['charge_amount']}")
                print(f"Status: {txn['status']}")
                print(f"PG Partner: {txn['pg_partner']}")
                print(f"PG Txn ID: {txn['pg_txn_id'] or 'N/A'}")
                print(f"Bank Ref: {txn['bank_ref_no'] or 'N/A'}")
                print(f"Payment Mode: {txn['payment_mode'] or 'N/A'}")
                print(f"Created: {txn['created_at']}")
                print(f"Updated: {txn['updated_at']}")
                print(f"Completed: {txn['completed_at'] or 'N/A'}")
                print(f"\n{'-'*60}\n")
                
finally:
    conn.close()

print(f"{'='*60}\n")
