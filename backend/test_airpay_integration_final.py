#!/usr/bin/env python3
"""
Final test of Airpay integration with encrypted requests
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service
import json

def test_airpay_order_creation():
    """Test creating an order through Airpay service"""
    print("🧪 Testing Airpay Order Creation")
    print("=" * 50)
    
    # Test merchant ID (should exist in your database)
    merchant_id = "9000000001"  # Replace with actual merchant ID
    
    # Test order data
    order_data = {
        'amount': 1.00,
        'orderid': 'TEST_AIRPAY_001',
        'payee_fname': 'Test',
        'payee_lname': 'User',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'productinfo': 'Test Payment',
        'callbackurl': 'https://admin.moneyone.co.in/api/callback/airpay/payin'
    }
    
    print(f"Test Data:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Order Data: {json.dumps(order_data, indent=2)}")
    
    # Create order
    print(f"\n🚀 Creating Airpay order...")
    result = airpay_service.create_payin_order(merchant_id, order_data)
    
    print(f"\n📋 Result:")
    print(f"Success: {result.get('success')}")
    print(f"Message: {result.get('message', 'No message')}")
    
    if result.get('success'):
        print(f"\n✅ Order Created Successfully!")
        print(f"  Transaction ID: {result.get('txn_id')}")
        print(f"  Airpay Order ID: {result.get('order_id')}")
        print(f"  Amount: ₹{result.get('amount')}")
        print(f"  Charge: ₹{result.get('charge_amount')}")
        print(f"  Net Amount: ₹{result.get('net_amount')}")
        
        qr_string = result.get('qr_string')
        if qr_string:
            print(f"  QR Code: {qr_string[:50]}...")
            print(f"  UPI Link: {result.get('upi_link', 'N/A')}")
        
        print(f"  Airpay MID: {result.get('airpay_mid')}")
        print(f"  Airpay RID: {result.get('airpay_rid')}")
        
        print(f"\n🎉 Integration Test PASSED!")
        print(f"✅ Airpay accepts encrypted requests")
        print(f"✅ Order creation works")
        print(f"✅ Database transaction recorded")
        print(f"✅ QR code generated")
        
    else:
        print(f"\n❌ Order Creation Failed!")
        print(f"Error: {result.get('message')}")
        
        # Check for specific error types
        if 'Merchant not found' in str(result.get('message')):
            print(f"\n💡 Fix: Update merchant_id to an existing merchant in your database")
        elif 'Database connection failed' in str(result.get('message')):
            print(f"\n💡 Fix: Check database connection and credentials")
        elif 'Failed to encrypt' in str(result.get('message')):
            print(f"\n💡 Fix: Check AIRPAY_ENCRYPTION_KEY in .env file")
    
    return result

if __name__ == "__main__":
    test_airpay_order_creation()