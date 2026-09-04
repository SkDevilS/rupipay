#!/usr/bin/env python3
"""
Test Rang callback with existing transaction from database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import requests
from datetime import datetime

def get_existing_rang_transaction():
    """Get an existing Rang transaction"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, merchant_id, order_id, amount, status
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return txn
        
    except Exception as e:
        print(f"Error getting transaction: {e}")
        return None

def create_test_transaction_with_real_merchant():
    """Create test transaction with a real merchant"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get first active merchant
        cursor.execute("""
            SELECT merchant_id FROM merchants 
            WHERE is_active = 1 
            LIMIT 1
        """)
        
        merchant = cursor.fetchone()
        
        if not merchant:
            print("❌ No active merchants found")
            return None
        
        merchant_id = merchant['merchant_id']
        
        # Generate test data
        from rang_service import RangService
        rang_service = RangService()
        
        # Generate 20-digit RefID (same format as Mudrape)
        test_txn_id = rang_service.generate_txn_id(merchant_id, "TEST_ORDER")
        
        print(f"Creating test transaction with merchant: {merchant_id}")
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
            f"RANG_TEST_{test_txn_id}", merchant_id, test_txn_id, 500.00, 10.00, 
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
        print(f"   Merchant: {merchant_id}")
        print(f"   Amount: ₹500.00")
        
        return test_txn_id
        
    except Exception as e:
        print(f"❌ Error creating test transaction: {e}")
        return None

def test_callback_with_transaction(ref_id):
    """Test callback with the transaction"""
    
    print("\n" + "=" * 80)
    print("TESTING RANG CALLBACK")
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
    print("RANG CALLBACK TEST WITH EXISTING DATA")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # First try to use existing transaction
    existing_txn = get_existing_rang_transaction()
    
    if existing_txn:
        print("Found existing Rang transaction:")
        print(f"  TXN ID: {existing_txn['txn_id']}")
        print(f"  Order ID: {existing_txn['order_id']}")
        print(f"  Merchant: {existing_txn['merchant_id']}")
        print(f"  Status: {existing_txn['status']}")
        
        ref_id = existing_txn['order_id']
    else:
        print("No existing Rang transaction found, creating new one...")
        ref_id = create_test_transaction_with_real_merchant()
    
    if ref_id:
        # Test callback
        callback_success = test_callback_with_transaction(ref_id)
        
        if callback_success:
            # Verify results
            verify_transaction_update(ref_id)
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED")
        print("=" * 80)
    else:
        print("❌ Test failed - could not get or create transaction")