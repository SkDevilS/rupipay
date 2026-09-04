#!/usr/bin/env python3
"""
Check if order_id ORD98787865452612432 exists in database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_order():
    order_id = "ORD98787865452612432"
    
    print(f"\n{'='*60}")
    print(f"🔍 Checking Order: {order_id}")
    print(f"{'='*60}\n")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check in payin_transactions
            print("📋 Searching in payin_transactions table...")
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    pg_partner,
                    status,
                    amount,
                    net_amount,
                    charge_amount,
                    pg_txn_id,
                    created_at,
                    updated_at
                FROM payin_transactions
                WHERE order_id = %s
                ORDER BY created_at DESC
            """, (order_id,))
            
            transactions = cursor.fetchall()
            
            if transactions:
                print(f"✅ Found {len(transactions)} transaction(s):\n")
                for txn in transactions:
                    print(f"  Transaction ID: {txn['txn_id']}")
                    print(f"  Merchant ID: {txn['merchant_id']}")
                    print(f"  Order ID: {txn['order_id']}")
                    print(f"  PG Partner: {txn['pg_partner']}")
                    print(f"  Status: {txn['status']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Net Amount: ₹{txn['net_amount']}")
                    print(f"  Charge: ₹{txn['charge_amount']}")
                    print(f"  PG Txn ID: {txn['pg_txn_id']}")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Updated: {txn['updated_at']}")
                    print()
            else:
                print(f"❌ No transaction found with order_id: {order_id}\n")
                
                # Search for similar order_ids
                print("🔍 Searching for similar order_ids...")
                cursor.execute("""
                    SELECT order_id, txn_id, merchant_id, pg_partner, status, created_at
                    FROM payin_transactions
                    WHERE order_id LIKE %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (f"%{order_id[-10:]}%",))
                
                similar = cursor.fetchall()
                if similar:
                    print(f"Found {len(similar)} similar order_ids:\n")
                    for txn in similar:
                        print(f"  Order ID: {txn['order_id']}")
                        print(f"  Txn ID: {txn['txn_id']}")
                        print(f"  PG: {txn['pg_partner']}")
                        print(f"  Status: {txn['status']}")
                        print(f"  Created: {txn['created_at']}")
                        print()
                else:
                    print("No similar order_ids found\n")
                
                # Check recent VIYONAPAY transactions
                print("📋 Recent VIYONAPAY transactions:")
                cursor.execute("""
                    SELECT 
                        txn_id,
                        merchant_id,
                        order_id,
                        status,
                        amount,
                        created_at
                    FROM payin_transactions
                    WHERE pg_partner = 'VIYONAPAY'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                recent = cursor.fetchall()
                if recent:
                    print(f"Found {len(recent)} recent VIYONAPAY transactions:\n")
                    for txn in recent:
                        print(f"  Order ID: {txn['order_id']}")
                        print(f"  Txn ID: {txn['txn_id']}")
                        print(f"  Status: {txn['status']}")
                        print(f"  Amount: ₹{txn['amount']}")
                        print(f"  Created: {txn['created_at']}")
                        print()
                else:
                    print("No VIYONAPAY transactions found\n")
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_order()
