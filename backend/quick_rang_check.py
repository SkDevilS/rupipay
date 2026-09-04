#!/usr/bin/env python3
"""
Quick check for Rang callback data
"""

from database import get_db_connection

def check_rang_callbacks():
    """Quick check for Rang callback data"""
    
    print("RANG CALLBACK DATA CHECK")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check recent Rang transactions that were updated
    print("1. Recent Rang transactions with updates:")
    cursor.execute("""
        SELECT txn_id, order_id, status, amount, pg_txn_id, bank_ref_no, created_at, updated_at
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND updated_at > created_at
        ORDER BY updated_at DESC
        LIMIT 5
    """)
    
    transactions = cursor.fetchall()
    
    if transactions:
        for txn in transactions:
            print(f"TXN: {txn[0]} | Order: {txn[1]} | Status: {txn[2]} | Amount: ₹{txn[3]}")
            print(f"PG TXN: {txn[4]} | UTR: {txn[5]} | Updated: {txn[7]}")
            print("-" * 50)
    else:
        print("No updated transactions found")
    
    # Check callback logs
    print("\n2. Callback logs for Rang:")
    cursor.execute("""
        SELECT cl.txn_id, cl.response_code, cl.created_at, cl.request_data
        FROM callback_logs cl
        JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
        WHERE pt.pg_partner = 'Rang'
        ORDER BY cl.created_at DESC
        LIMIT 3
    """)
    
    logs = cursor.fetchall()
    
    if logs:
        for log in logs:
            print(f"TXN: {log[0]} | Response: {log[1]} | Time: {log[2]}")
            print(f"Data: {log[3][:100]}...")
            print("-" * 50)
    else:
        print("No callback logs found")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_rang_callbacks()