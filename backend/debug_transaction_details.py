#!/usr/bin/env python3
"""
Debug transaction details to understand why status didn't update
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def debug_transaction():
    """Debug the transaction details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the transaction we just tested
        cursor.execute("""
            SELECT * FROM payin_transactions 
            WHERE order_id = 'ORD66565656352725263'
        """)
        
        txn = cursor.fetchone()
        
        if txn:
            print("Transaction Details:")
            for key, value in txn.items():
                print(f"  {key}: {value}")
        else:
            print("Transaction not found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_transaction()