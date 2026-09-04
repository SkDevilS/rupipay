#!/usr/bin/env python3
"""
Test Airpay V4 Check Status API
Tests the verify/check status endpoint with existing transactions
"""

from airpay_service import airpay_service
from database import get_db_connection
import json

def test_check_status():
    """Test check status for recent Airpay transactions"""
    
    print("=" * 100)
    print("AIRPAY V4 CHECK STATUS TEST")
    print("=" * 100)
    
    # Get recent Airpay transactions
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    created_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 2
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No Airpay transactions found")
                return
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{'='*100}")
                print(f"TESTING TRANSACTION #{idx}")
                print(f"{'='*100}")
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Amount: ₹{txn['amount']}")
                print(f"Current Status: {txn['status']}")
                print(f"PG Txn ID: {txn['pg_txn_id']}")
                print(f"Bank Ref/UTR: {txn['bank_ref_no']}")
                print(f"Created: {txn['created_at']}")
                
                print(f"\n{'─'*100}")
                print(f"TEST 1: Check status by Order ID")
                print(f"{'─'*100}")
                
                result = airpay_service.verify_payment(order_id=txn['order_id'])
                
                print(f"\n📊 Result:")
                print(json.dumps(result, indent=2, default=str))
                
                if result.get('success'):
                    print(f"\n✅ Status check successful!")
                    print(f"  Status: {result.get('status')}")
                    print(f"  Transaction Status Code: {result.get('transaction_status')}")
                    print(f"  Message: {result.get('message')}")
                    print(f"  RRN/UTR: {result.get('rrn')}")
                    print(f"  Payment Channel: {result.get('chmod')}")
                    print(f"  Bank: {result.get('bank_name')}")
                    
                    # Check if status changed
                    if result.get('status') != txn['status']:
                        print(f"\n⚠️  STATUS CHANGED: {txn['status']} → {result.get('status')}")
                        print(f"   This transaction should be updated in the database!")
                else:
                    print(f"\n❌ Status check failed: {result.get('message')}")
                
                # Test 2: Check by Airpay Transaction ID if available
                if txn['pg_txn_id']:
                    print(f"\n{'─'*100}")
                    print(f"TEST 2: Check status by Airpay Transaction ID")
                    print(f"{'─'*100}")
                    
                    result2 = airpay_service.verify_payment(ap_transactionid=txn['pg_txn_id'])
                    
                    print(f"\n📊 Result:")
                    print(json.dumps(result2, indent=2, default=str))
                    
                    if result2.get('success'):
                        print(f"\n✅ Status check by AP Txn ID successful!")
                        print(f"  Status: {result2.get('status')}")
                    else:
                        print(f"\n❌ Status check by AP Txn ID failed: {result2.get('message')}")
                
                print(f"\n{'='*100}\n")
    
    finally:
        conn.close()
    
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print("\nThe check status API allows you to:")
    print("1. Query transaction status by Order ID")
    print("2. Query transaction status by Airpay Transaction ID")
    print("3. Query transaction status by RRN/UTR")
    print("\nIf the status has changed from INITIATED to SUCCESS/FAILED,")
    print("you should update the transaction in the database and credit wallets.")
    print("\nThe auto status check runs 60 seconds after QR generation.")
    print("=" * 100)

if __name__ == '__main__':
    test_check_status()
