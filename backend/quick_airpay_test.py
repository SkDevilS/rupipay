#!/usr/bin/env python3
"""
Quick Airpay Test - Test order creation with improved error handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import AirpayService

def test_order_creation():
    """Test Airpay order creation"""
    print("🧪 Quick Airpay Order Creation Test")
    print("=" * 50)
    
    try:
        # Initialize service
        airpay = AirpayService()
        
        print(f"✅ Service initialized")
        print(f"  Encryption Key: {'✅ Configured' if airpay.encryption_key else '❌ Missing'}")
        print(f"  Key256: {'✅ Generated' if airpay.key256 else '❌ Failed'}")
        
        if not airpay.encryption_key:
            print("\n❌ AIRPAY_ENCRYPTION_KEY not configured")
            return False
        
        # Test order data
        test_order = {
            'amount': 1.00,
            'orderid': 'QUICKTEST123',
            'payee_fname': 'Test',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"\n📋 Creating test order: {test_order}")
        
        # Create order (using merchant ID 9000000001 as test)
        result = airpay.create_payin_order('9000000001', test_order)
        
        print(f"\n📊 Result: {result}")
        
        if result.get('success'):
            print("✅ Order created successfully!")
            if result.get('qr_string'):
                print(f"🎯 QR Code: {result['qr_string'][:50]}...")
            return True
        else:
            print(f"❌ Order creation failed: {result.get('message')}")
            if result.get('debug_response'):
                print(f"🔍 Debug response: {result['debug_response']}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_order_creation()
    
    if not success:
        print("\n💡 Troubleshooting steps:")
        print("1. Run: python3 debug_airpay_response.py")
        print("2. Check AIRPAY_ENCRYPTION_KEY in .env")
        print("3. Verify merchant credentials with Airpay")
        print("4. Check network connectivity to Airpay API")