#!/usr/bin/env python3
"""
Diagnostic script to check RMS_JSS transaction data structure
and verify column names in payin_transactions table
"""

import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database import get_db_connection
import json

def diagnose_rmsjss_data():
    """Check RMS_JSS transaction data structure"""
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Could not connect to database")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("RMS_JSS TRANSACTION DATA DIAGNOSIS")
            print("=" * 80)
            print()
            
            # Get the latest RMS_JSS transaction
            cursor.execute("""
                SELECT *
                FROM payin_transactions
                WHERE pg_partner = 'RMS_JSS'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("No RMS_JSS transactions found in database")
                return
            
            print("LATEST RMS_JSS TRANSACTION:")
            print("-" * 80)
            print(f"Transaction ID: {txn.get('txn_id', 'N/A')}")
            print(f"Order ID: {txn.get('order_id', 'N/A')}")
            print(f"Merchant ID: {txn.get('merchant_id', 'N/A')}")
            print(f"Status: {txn.get('status', 'N/A')}")
            print()
            
            print("AMOUNT FIELDS:")
            print("-" * 80)
            print(f"amount: {txn.get('amount', 'KEY NOT FOUND')}")
            print(f"net_amount: {txn.get('net_amount', 'KEY NOT FOUND')}")
            print(f"charge_amount: {txn.get('charge_amount', 'KEY NOT FOUND')}")
            print()
            
            print("CALLBACK FIELDS:")
            print("-" * 80)
            print(f"callback_url: {txn.get('callback_url', 'KEY NOT FOUND')}")
            print(f"pg_txn_id: {txn.get('pg_txn_id', 'KEY NOT FOUND')}")
            print(f"bank_ref_no: {txn.get('bank_ref_no', 'KEY NOT FOUND')}")
            print()
            
            print("ALL AVAILABLE KEYS IN TRANSACTION RECORD:")
            print("-" * 80)
            if isinstance(txn, dict):
                for key in sorted(txn.keys()):
                    value = txn[key]
                    if value is not None:
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: NULL")
            else:
                print(f"ERROR: Transaction is not a dictionary, it's a {type(txn)}")
                print(f"Value: {txn}")
            print()
            
            # Test the exact query used in callback route
            print("=" * 80)
            print("TESTING CALLBACK ROUTE QUERY")
            print("=" * 80)
            print()
            
            order_id = txn.get('order_id')
            if order_id:
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount, net_amount, charge_amount, callback_url
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'RMS_JSS'
                """, (order_id,))
                
                test_txn = cursor.fetchone()
                
                print(f"Query for order_id: {order_id}")
                print("-" * 80)
                
                if test_txn:
                    print("Result type:", type(test_txn))
                    print()
                    
                    if isinstance(test_txn, dict):
                        print("✓ Result is a dictionary")
                        print()
                        print("Keys available:")
                        for key in test_txn.keys():
                            print(f"  - {key}: {test_txn[key]}")
                        print()
                        
                        # Test accessing amount field
                        try:
                            amount = test_txn['amount']
                            print(f"✓ Successfully accessed amount: {amount}")
                        except KeyError as e:
                            print(f"✗ KeyError when accessing amount: {e}")
                            print(f"  Available keys: {list(test_txn.keys())}")
                    else:
                        print(f"✗ Result is NOT a dictionary, it's {type(test_txn)}")
                        print(f"  Value: {test_txn}")
                else:
                    print("✗ No result returned from query")
            
            print()
            print("=" * 80)
            print("DIAGNOSIS COMPLETE")
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_rmsjss_data()
