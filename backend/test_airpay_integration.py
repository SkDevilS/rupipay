#!/usr/bin/env python3
"""
Test Airpay Integration
Tests Airpay payin functionality including order creation and status checking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from airpay_service import airpay_service
from database import get_db_connection

def test_token_generation():
    """Test Airpay access token generation"""
    try:
        print("🔑 Testing Airpay token generation...")
        
        result = airpay_service.generate_access_token()
        
        if result['success']:
            print(f"✅ Token generated successfully!")
            print(f"   Token: {result['token'][:20]}...")
            return True
        else:
            print(f"❌ Token generation failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Token generation error: {e}")
        return False

def test_order_creation():
    """Test Airpay order creation"""
    try:
        print("\n📦 Testing Airpay order creation...")
        
        # Test merchant ID (use a test merchant)
        test_merchant_id = "TEST_MERCHANT_001"
        
        # Test order data
        order_data = {
            'amount': 100.00,
            'orderid': f'TEST_ORDER_{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9999999999',
            'payee_email': 'test@example.com',
            'productinfo': 'Test Payment',
            'callbackurl': 'https://admin.moneyone.co.in/api/callback/airpay/payin'
        }
        
        print(f"Order data: {order_data}")
        
        result = airpay_service.create_payin_order(test_merchant_id, order_data)
        
        if result['success']:
            print(f"✅ Order created successfully!")
            print(f"   TXN ID: {result['txn_id']}")
            print(f"   Order ID: {result['order_id']}")
            print(f"   Amount: ₹{result['amount']}")
            print(f"   Charges: ₹{result['charge_amount']}")
            print(f"   Net Amount: ₹{result['net_amount']}")
            print(f"   QR String: {result['qr_string'][:50]}..." if result.get('qr_string') else "   No QR String")
            
            return result
        else:
            print(f"❌ Order creation failed: {result['message']}")
            return None
            
    except Exception as e:
        print(f"❌ Order creation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_status_check(order_id):
    """Test Airpay status checking"""
    try:
        print(f"\n🔍 Testing Airpay status check for order: {order_id}")
        
        result = airpay_service.check_payment_status(order_id)
        
        if result['success']:
            print(f"✅ Status check successful!")
            print(f"   Status: {result['status']}")
            print(f"   Transaction ID: {result.get('txnId', 'N/A')}")
            print(f"   Amount: {result.get('amount', 'N/A')}")
            print(f"   UTR: {result.get('utr', 'N/A')}")
            print(f"   Message: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ Status check failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return False

def test_encryption_decryption():
    """Test Airpay encryption/decryption"""
    try:
        print("\n🔐 Testing Airpay encryption/decryption...")
        
        # Test data
        test_data = {
            'orderid': 'TEST123',
            'amount': '100.00',
            'buyer_email': 'test@example.com'
        }
        
        print(f"Original data: {test_data}")
        
        # Encrypt
        encrypted = airpay_service.encrypt_data(test_data)
        if not encrypted:
            print("❌ Encryption failed")
            return False
        
        print(f"Encrypted: {encrypted[:50]}...")
        
        # Decrypt
        decrypted = airpay_service.decrypt_data(encrypted)
        if not decrypted:
            print("❌ Decryption failed")
            return False
        
        print(f"Decrypted: {decrypted}")
        
        # Verify
        if decrypted == test_data:
            print("✅ Encryption/Decryption test passed!")
            return True
        else:
            print("❌ Decrypted data doesn't match original")
            return False
            
    except Exception as e:
        print(f"❌ Encryption test error: {e}")
        return False

def test_database_integration():
    """Test database integration"""
    try:
        print("\n💾 Testing database integration...")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if payin_transactions table exists and has required columns
            cursor.execute("""
                SHOW COLUMNS FROM payin_transactions LIKE 'pg_partner'
            """)
            
            if not cursor.fetchone():
                print("❌ payin_transactions table missing pg_partner column")
                return False
            
            # Check service routing
            cursor.execute("""
                SELECT * FROM service_routing 
                WHERE pg_partner = 'Airpay' AND service_type = 'PAYIN'
            """)
            
            routing = cursor.fetchone()
            if routing:
                print(f"✅ Airpay routing configured (Active: {routing['is_active']})")
            else:
                print("⚠️  Airpay routing not configured")
            
            print("✅ Database integration looks good!")
            return True
            
    except Exception as e:
        print(f"❌ Database test error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def run_comprehensive_test():
    """Run comprehensive Airpay integration test"""
    print("🧪 Airpay Integration Comprehensive Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Encryption/Decryption
    if test_encryption_decryption():
        tests_passed += 1
    
    # Test 2: Database Integration
    if test_database_integration():
        tests_passed += 1
    
    # Test 3: Token Generation
    if test_token_generation():
        tests_passed += 1
    
    # Test 4: Order Creation (only if token works)
    if airpay_service.access_token:
        order_result = test_order_creation()
        if order_result:
            tests_passed += 1
            
            # Bonus: Test status check
            if order_result.get('order_id'):
                test_status_check(order_result['order_id'])
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Airpay integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")
        return False

if __name__ == "__main__":
    import time
    
    # Check if configuration is available
    if not airpay_service.encryption_key:
        print("❌ Airpay configuration missing!")
        print("Please set the following environment variables:")
        print("- AIRPAY_BASE_URL")
        print("- AIRPAY_CLIENT_ID")
        print("- AIRPAY_CLIENT_SECRET")
        print("- AIRPAY_MERCHANT_ID")
        print("- AIRPAY_USERNAME")
        print("- AIRPAY_PASSWORD")
        print("- AIRPAY_ENCRYPTION_KEY")
        sys.exit(1)
    
    # Run tests
    success = run_comprehensive_test()
    
    if success:
        print("\n✅ Airpay integration is ready for production!")
        print("\nNext steps:")
        print("1. Configure callback URL in Airpay dashboard:")
        print("   https://your-domain.com/api/callback/airpay/payin")
        print("2. Activate Airpay routing in admin panel")
        print("3. Test with real transactions")
    else:
        print("\n❌ Please fix the issues and run the test again.")
        sys.exit(1)