#!/usr/bin/env python3
"""
Check Admin Transaction Details
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_transactions():
    """Check the specific transactions"""
    
    transactions = ['TXN55B24F6EE079', 'TXNFE9EDCDDBD58']
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            for txn_id in transactions:
                cursor.execute("""
                    SELECT txn_id, merchant_id, admin_id, status, pg_partner, 
                           amount, net_amount, charge_amount
                    FROM payout_transactions 
                    WHERE txn_id = %s
                """, (txn_id,))
                
                row = cursor.fetchone()
                if row:
                    print(f"TXN: {row['txn_id']}")
                    print(f"  Merchant ID: {row['merchant_id']}")
                    print(f"  Admin ID: {row['admin_id']}")
                    print(f"  Status: {row['status']}")
                    print(f"  PG Partner: {row['pg_partner']}")
                    print(f"  Amount: {row['amount']}")
                    print(f"  Net: {row['net_amount']}")
                    print(f"  Charges: {row['charge_amount']}")
                    print()
                else:
                    print(f"Transaction {txn_id} not found")
                    print()
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_transactions()