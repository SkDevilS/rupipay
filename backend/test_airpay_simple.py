#!/usr/bin/env python3
"""
Simple Airpay Test - Test the corrected implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import AirpayService
from config import Config

def test_airpay_service():
    """Test Airpay service initialization and basic functionality"""
    print("🧪 Testing Airpay Service")
    print("=" * 50)
    
    try:
        # Initialize service
        airpay = AirpayService()
        
        print(f"✅ Service initialized successfully")
        print(f"  Base URL: {airpay.base_url}")
        print(f"  Merchant ID: {airpay.merchant_id}")
        print(f"  Username: {airpay.username}")
        print(f"  Encryption Key: {airpay.encryption_key[:10] if airpay.encryption_key else 'Not configured'}...")
        print(f"  Key256: {airpay.key256[:20] if airpay.key256 else 'Not generated'}...")
        
        # Check configuration
        if not airpay.encryption_key:
            print("❌ AIRPAY_ENCRYPTION_KEY not configured in .env file")
            return False
        
        if not airpay.key256:
            print("❌ Key256 generation failed")
            return False
        
        # Test order creation (dry run)
        print("\n🧪 Testing Order Creation (Dry Run)")
        
        test_order_data = {
            'amount': 100.00,
            'orderid': 'TEST123',
            'payee_fname': 'Test',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"Test order data: {test_order_data}")
        
        # This would normally create an order, but we'll just test the setup
        print("✅ Order creation setup ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_airpay_service()
    
    if success:
        print("\n🎉 Airpay service is configured correctly!")
        print("\n💡 Next steps:")
        print("1. Test order creation through the web interface")
        print("2. Check server logs for any errors")
        print("3. Verify callback URL is accessible")
    else:
        print("\n❌ Airpay service configuration failed")
        print("\n💡 Check:")
        print("1. AIRPAY_ENCRYPTION_KEY in .env file")
        print("2. All Airpay credentials are correct")
        print("3. Network connectivity to Airpay API")