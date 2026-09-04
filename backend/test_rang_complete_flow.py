#!/usr/bin/env python3
"""
Complete test of Rang integration:
1. Create a test transaction
2. Test the callback with that transaction
3. Verify the results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import requests
import json
from datetime import datetime

def create_test_rang_transaction():
    """Create a test Rang transaction in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate test data
        from rang_service import RangService
        rang_service = RangService()
        
        # Generate 20-digit RefID (same format as Mudrape)
        test_txn_id = rang_service.generate_txn_id("TEST_MERCHANT", "TEST_ORDER")
        
        print("Creating test Rang transaction...")
        print(f"TXN ID (RefID): {test_txn_id}")
        
        # Insert test transaction
        cursor.execute("""
            INSERT INTO payin_transactions (
                txn_id, merchant_id, order_id, amount, charge_amount, 
                charge_type, net_amount, payee_name, payee_email, 
                payee_mobile, product_info, status, pg_partner,
                pg_txn_id, callback_url, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """, (
            f"RANG_TEST_{test_txn_id}", "TEST_MERCHANT", test_txn_id, 500.00, 10.00, 
            'percentage', 490.00, "Test Customer", "test@example.com", 
            "9999999999", "Test Payment", "INITIATED", "Rang",
            None, "https://api.moneyone.co.in/rang-payin-callback"
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Test transaction created successfully!")
        print(f"   TXN ID: RANG_TEST_{test_txn_id}")
        print(f"   Order ID (RefID): {test_txn_id}")
        print(f"   Amount: ₹500.00")
        print(f"   Status: INITIATED")
        
        return test_txn_id
        
    except Exception as e:
        print(f"❌ Error creating test transaction: {e}")
        return None

def test_callback_with_transaction(ref_id):
    """Test callback with the created transaction"""
    
    print("\n" + "=" * 80)
    print("TESTING RANG CALLBACK WITH REAL TRANSACTION")
    print("=" * 80)
    
    # Callback URL
    callback_url = "https://api.moneyone.co.in/rang-payin-callback"
    
    # Simulate SUCCESS callback (matching your provided format)
    callback_data = {
        'status_id': '1',  # 1 = Success
        'amount': '500',
        'utr': 'TEST123456789',  # Test UTR
        'report_id': '12345',
        'client_id': ref_id,  # Our RefID (order_id)
        'message': 'Payment success'
    }
    
    print(f"Sending callback to: {callback_url}")
    print(f"Callback data: {callback_data}")
    print()
    
    try:
        response = requests.post(
            callback_url,
            data=callback_data,  # Use data= for form-data
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Callback processed successfully!")
            return True
        else:
            print(f"\n❌ Callback failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def verify_transaction_update(ref_id):
    """Verify that the transaction was updated correctly"""
    
    print("\n" + "=" * 80)
    print("VERIFYING TRANSACTION UPDATE")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check transaction status
        cursor.execute("""
            SELECT txn_id, status, bank_ref_no, pg_txn_id, completed_at
            FROM payin_transactions 
            WHERE order_id = %s AND pg_partner = 'Rang'
        """, (ref_id,))
        
        txn = cursor.fetchone()
        
        if txn:
            print(f"Transaction Status:")
            print(f"  TXN ID: {txn['txn_id']}")
            print(f"  Status: {txn['status']}")
            print(f"  UTR: {txn['bank_ref_no']}")
            print(f"  PG TXN ID: {txn['pg_txn_id']}")
            print(f"  Completed At: {txn['completed_at']}")
            
            if txn['status'] == 'SUCCESS':
                print("\n✅ Transaction status updated correctly!")
            else:
                print(f"\n⚠️ Transaction status is {txn['status']}, expected SUCCESS")
        else:
            print("❌ Transaction not found!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying transaction: {e}")

if __name__ == "__main__":
    print("RANG COMPLETE FLOW TEST")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Create test transaction
    ref_id = create_test_rang_transaction()
    
    if ref_id:
        # Step 2: Test callback
        callback_success = test_callback_with_transaction(ref_id)
        
        if callback_success:
            # Step 3: Verify results
            verify_transaction_update(ref_id)
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED")
        print("=" * 80)
    else:
        print("❌ Test failed - could not create transaction")