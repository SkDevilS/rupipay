"""
Test Paytouchpayin Complete Integration Flow
Tests the full flow from service to database to API
"""

import sys
from paytouchpayin_service import PaytouchpayinService
from database_pooled import get_db_connection
import json

def test_complete_flow():
    """Test complete payin flow"""
    
    print("="*80)
    print("PAYTOUCHPAYIN COMPLETE FLOW TEST")
    print("="*80)
    
    # Test merchant (use a real merchant_id from your database)
    test_merchant_id = "9000000001"  # Change this to a real merchant ID
    
    print(f"\n📋 Test Configuration:")
    print(f"  Merchant ID: {test_merchant_id}")
    
    # Check if merchant exists
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT merchant_id, name, scheme_id, status
        FROM merchants
        WHERE merchant_id = %s
    """, (test_merchant_id,))
    
    merchant = cursor.fetchone()
    
    if not merchant:
        print(f"\n❌ Merchant {test_merchant_id} not found")
        print("   Please update test_merchant_id in the script")
        cursor.close()
        conn.close()
        return False
    
    print(f"\n✓ Merchant Found:")
    print(f"  Name: {merchant['name']}")
    print(f"  Scheme ID: {merchant['scheme_id']}")
    print(f"  Status: {merchant['status']}")
    
    # Test order data
    order_data = {
        'amount': 100,
        'order_id': 'TEST_ORDER_123',
        'customer_name': 'Test Customer',
        'customer_mobile': '9876543210',
        'customer_email': 'test@example.com'
    }
    
    print(f"\n📦 Order Data:")
    print(json.dumps(order_data, indent=2))
    
    # Initialize service
    print(f"\n🔧 Initializing Paytouchpayin Service...")
    service = PaytouchpayinService()
    
    # Create order
    print(f"\n🚀 Creating Payin Order...")
    result = service.create_payin_order(test_merchant_id, order_data)
    
    if result.get('success'):
        print(f"\n✅ Order Created Successfully!")
        print(f"\n📋 Order Details:")
        print(f"  TxnID: {result['txn_id']}")
        print(f"  PG TxnID: {result['pg_txn_id']}")
        print(f"  Order ID: {result['order_id']}")
        print(f"  Amount: ₹{result['amount']}")
        print(f"  Charge: ₹{result['charge']}")
        print(f"  Final Amount: ₹{result['final_amount']}")
        print(f"  QR URL: {result['redirect_url']}")
        
        # Verify in database
        print(f"\n🔍 Verifying in Database...")
        cursor.execute("""
            SELECT txn_id, pg_txn_id, amount, charge, status, payment_url
            FROM payin
            WHERE txn_id = %s
        """, (result['txn_id'],))
        
        db_record = cursor.fetchone()
        
        if db_record:
            print(f"✓ Record found in database:")
            print(f"  TxnID: {db_record['txn_id']}")
            print(f"  PG TxnID: {db_record['pg_txn_id']}")
            print(f"  Amount: ₹{db_record['amount']}")
            print(f"  Charge: ₹{db_record['charge']}")
            print(f"  Status: {db_record['status']}")
            print(f"  Payment URL: {db_record['payment_url'][:50]}...")
            
            print(f"\n✅ Complete Flow Test PASSED!")
            cursor.close()
            conn.close()
            return True
        else:
            print(f"❌ Record not found in database")
            cursor.close()
            conn.close()
            return False
    else:
        print(f"\n❌ Order Creation Failed")
        print(f"  Error: {result.get('error')}")
        cursor.close()
        conn.close()
        return False

if __name__ == '__main__':
    print("\n⚠️  IMPORTANT: Update test_merchant_id with a real merchant ID")
    print("   from your database before running this test.\n")
    
    input("Press Enter to continue...")
    
    test_complete_flow()
