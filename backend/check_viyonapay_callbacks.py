#!/usr/bin/env python3
"""
Check ViyonaPay callback data from merchant_callbacks table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime

def check_viyonapay_callbacks():
    """Check recent ViyonaPay callbacks"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Check callback_logs table for ViyonaPay callbacks
            # Note: callback_logs may not have txn_id column, so we check request_data instead
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE request_data LIKE '%VIYONAPAY%'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            callbacks = cursor.fetchall()
            
            if not callbacks:
                print("\n❌ No ViyonaPay callbacks found in callback_logs table")
                print("\n📋 Checking payin_transactions for ViyonaPay orders...")
                
                # Check payin_transactions
                cursor.execute("""
                    SELECT 
                        txn_id,
                        order_id,
                        merchant_id,
                        amount,
                        status,
                        pg_partner,
                        pg_txn_id,
                        bank_ref_no,
                        created_at,
                        updated_at
                    FROM payin_transactions
                    WHERE pg_partner = 'VIYONAPAY'
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                transactions = cursor.fetchall()
                
                if transactions:
                    print(f"\n✅ Found {len(transactions)} ViyonaPay transaction(s):\n")
                    for txn in transactions:
                        print(f"{'='*80}")
                        print(f"Transaction ID: {txn['txn_id']}")
                        print(f"Order ID: {txn['order_id']}")
                        print(f"Merchant ID: {txn['merchant_id']}")
                        print(f"Amount: ₹{txn['amount']}")
                        print(f"Status: {txn['status']}")
                        print(f"PG TXN ID: {txn['pg_txn_id']}")
                        print(f"Bank Ref No: {txn['bank_ref_no']}")
                        print(f"Created: {txn['created_at']}")
                        print(f"Updated: {txn['updated_at']}")
                        print()
                else:
                    print("❌ No ViyonaPay transactions found")
                
                return
            
            print(f"\n✅ Found {len(callbacks)} ViyonaPay callback(s):\n")
            
            for callback in callbacks:
                print(f"{'='*80}")
                print(f"Callback ID: {callback['id']}")
                print(f"Merchant ID: {callback['merchant_id']}")
                print(f"Callback URL: {callback['callback_url']}")
                print(f"Response Code: {callback['response_code']}")
                print(f"Created: {callback['created_at']}")
                print(f"\n📥 Request Data:")
                
                try:
                    request_data = json.loads(callback['request_data']) if callback['request_data'] else {}
                    print(json.dumps(request_data, indent=2))
                    
                    # Extract transaction ID from request data
                    txn_id = request_data.get('txn_id', 'N/A')
                    order_id = request_data.get('order_id', 'N/A')
                    print(f"\n  Transaction ID: {txn_id}")
                    print(f"  Order ID: {order_id}")
                except:
                    print(callback['request_data'])
                
                if callback['response_data']:
                    print(f"\n📤 Response Data:")
                    print(callback['response_data'][:500])  # First 500 chars
                
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ViyonaPay Callback Data Check")
    print("="*80)
    check_viyonapay_callbacks()
