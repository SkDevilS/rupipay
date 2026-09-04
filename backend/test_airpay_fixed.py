#!/usr/bin/env python3
"""
Test Airpay Fixed Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import AirpayService

def test_fixed_airpay():
    """Test the fixed Airpay implementation"""
    print("🧪 Testing Fixed Airpay Implementation")
    print("=" * 50)
    
    try:
        # Initialize service
        airpay = AirpayService()
        
        print(f"✅ Service initialized")
        print(f"  Base URL: {airpay.base_url}")
        print(f"  Merchant ID: {airpay.merchant_id}")
        print(f"  Encryption Key: {'✅ Configured' if airpay.encryption_key else '❌ Missing'}")
        
        # Test with valid data
        test_order = {
            'amount': 100.00,
            'orderid': 'FIXED_TEST_123',
            'payee_fname': 'Test',
            'payee_lname': 'User',
            'payee_mobile': '9876543210',  # Valid 10-digit number
            'payee_email': 'test@example.com'  # Valid email
        }
        
        print(f"\n📋 Creating test order with valid data:")
        print(f"  Amount: ₹{test_order['amount']}")
        print(f"  Mobile: {test_order['payee_mobile']}")
        print(f"  Email: {test_order['payee_email']}")
        
        # Create order (using merchant ID 9000000001 as test)
        result = airpay.create_payin_order('9000000001', test_order)
        
        print(f"\n📊 Result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message')}")
        
        if result.get('success'):
            print("✅ Order created successfully!")
            print(f"  Transaction ID: {result.get('txn_id')}")
            print(f"  Order ID: {result.get('order_id')}")
            if result.get('qr_string'):
                print(f"  QR Code: {result['qr_string'][:50]}...")
            return True
        else:
            print(f"❌ Order creation failed")
            if result.get('debug_response'):
                print(f"🔍 Debug response: {result['debug_response']}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_airpay()
    
    if success:
        print("\n🎉 Airpay integration is working!")
    else:
        print("\n💡 If still failing, check:")
        print("1. Merchant credentials with Airpay")
        print("2. Account activation status")
        print("3. API endpoint accessibility")