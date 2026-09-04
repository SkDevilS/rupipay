#!/usr/bin/env python3
"""
Check what data is actually stored in the database for these transactions
"""
import pymysql
from config import DB_CONFIG

def check_transactions():
    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    cursor = conn.cursor()
    
    # Check the two transactions mentioned
    txn_ids = [
        'airpay_9000000001_tr61cce10f7d6df72_20260312234216',  # Vibhu Bhasin
        'airpay_9000000001_tr2e09916780bde17_20260312235552'   # Smit Bedi (if exists)
    ]
    
    print("=" * 80)
    print("CHECKING TRANSACTION DATA IN DATABASE")
    print("=" * 80)
    
    for txn_id in txn_ids:
        cursor.execute("""
            SELECT 
                txn_id,
                order_id,
                amount,
                payee_name,
                payee_email,
                payee_mobile,
                bank_ref_no,
                pg_txn_id,
                status,
                created_at
            FROM payin_transactions
            WHERE txn_id = %s
        """, (txn_id,))
        
        txn = cursor.fetchone()
        
        if txn:
            print(f"\nTransaction ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Amount: {txn['amount']}")
            print(f"Customer Name: {txn['payee_name']}")
            print(f"Customer Email: {txn['payee_email']}")
            print(f"Customer Mobile: {txn['payee_mobile']}")
            print(f"Bank Ref: {txn['bank_ref_no']}")
            print(f"PG Txn ID: {txn['pg_txn_id']}")
            print(f"Status: {txn['status']}")
            print("-" * 80)
        else:
            print(f"\nTransaction {txn_id} NOT FOUND in database")
            print("-" * 80)
    
    # Also check recent SUCCESS transactions
    print("\n" + "=" * 80)
    print("RECENT SUCCESS TRANSACTIONS (Last 5)")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            txn_id,
            order_id,
            payee_name,
            payee_email,
            payee_mobile,
            status,
            created_at
        FROM payin_transactions
        WHERE status = 'SUCCESS'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    transactions = cursor.fetchall()
    
    for txn in transactions:
        print(f"\nTxn ID: {txn['txn_id']}")
        print(f"Order ID: {txn['order_id']}")
        print(f"Name: {txn['payee_name']}")
        print(f"Email: {txn['payee_email']}")
        print(f"Mobile: {txn['payee_mobile']}")
        print(f"Created: {txn['created_at']}")
        print("-" * 40)
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    check_transactions()
