"""
Complete Airpay V4 API Integration Test
Tests all endpoints: OAuth2, Generate QR, Verify Payment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service_v4 import airpay_service_v4
import json

def test_oauth2():
    """Test 1: Generate OAuth2 Access Token"""
    print("\n" + "="*60)
    print("TEST 1: Generate OAuth2 Access Token")
    print("="*60)
    
    token = airpay_service_v4.generate_access_token()
    
    if token:
        print(f"✅ SUCCESS: Access token generated")
        print(f"   Token: {token[:30]}...")
        return True
    else:
        print(f"❌ FAILED: Could not generate access token")
        return False

def test_encryption_decryption():
    """Test 2: Encryption and Decryption"""
    print("\n" + "="*60)
    print("TEST 2: Encryption and Decryption")
    print("="*60)
    
    test_data = {
        'orderid': 'TEST123',
        'amount': '100.00',
        'buyer_email': 'test@example.com'
    }
    
    print(f"Original data: {test_data}")
    
    # Encrypt
    encrypted = airpay_service_v4.encrypt_data(test_data)
    if not encrypted:
        print(f"❌ FAILED: Encryption failed")
        return False
    
    print(f"✅ Encrypted: {encrypted[:50]}...")
    
    # Decrypt
    decrypted = airpay_service_v4.decrypt_data(encrypted)
    if not decrypted:
        print(f"❌ FAILED: Decryption failed")
        return False
    
    print(f"✅ Decrypted: {decrypted}")
    
    if decrypted == test_data:
        print(f"✅ SUCCESS: Encryption/Decryption working correctly")
        return True
    else:
        print(f"❌ FAILED: Decrypted data doesn't match original")
        return False

def test_generate_qr():
    """Test 3: Generate QR Code"""
    print("\n" + "="*60)
    print("TEST 3: Generate QR Code")
    print("="*60)
    
    order_data = {
        'orderid': f'TEST_{int(time.time())}',
        'amount': '10.00',
        'tid': '12345678',
        'buyer_email': 'test@example.com',
        'buyer_phone': '9999999999',
        'mer_dom': 'aHR0cDovL2xvY2FsaG9zdA==',  # base64('http://localhost')
        'customvar': 'test_transaction',
        'call_type': 'upiqr'
    }
    
    print(f"Order data: {json.dumps(order_data, indent=2)}")
    
    result = airpay_service_v4.generate_qr(order_data)
    
    if result.get('success'):
        print(f"✅ SUCCESS: QR Code generated")
        print(f"   QR String: {result.get('qrcode_string')}")
        print(f"   AP Transaction ID: {result.get('ap_transactionid')}")
        print(f"   Status: {result.get('status')}")
        return True, result.get('ap_transactionid'), order_data['orderid']
    else:
        print(f"❌ FAILED: {result.get('message')}")
        return False, None, None

def test_verify_payment(ap_transactionid=None, orderid=None):
    """Test 4: Verify Payment Status"""
    print("\n" + "="*60)
    print("TEST 4: Verify Payment Status")
    print("="*60)
    
    if not ap_transactionid and not orderid:
        print(f"⚠️  SKIPPED: No transaction ID available")
        return False
    
    print(f"Verifying payment...")
    print(f"  Order ID: {orderid}")
    print(f"  AP Transaction ID: {ap_transactionid}")
    
    result = airpay_service_v4.verify_payment(
        order_id=orderid,
        ap_transactionid=ap_transactionid
    )
    
    if result.get('success'):
        print(f"✅ SUCCESS: Payment status retrieved")
        print(f"   Status: {result.get('status')}")
        print(f"   Transaction Status: {result.get('transaction_status')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Amount: {result.get('amount')}")
        print(f"   RRN: {result.get('rrn')}")
        return True
    else:
        print(f"❌ FAILED: {result.get('message')}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AIRPAY V4 API COMPLETE INTEGRATION TEST")
    print("="*60)
    
    import time
    
    results = []
    
    # Test 1: OAuth2
    results.append(("OAuth2 Token Generation", test_oauth2()))
    
    # Test 2: Encryption/Decryption
    results.append(("Encryption/Decryption", test_encryption_decryption()))
    
    # Test 3: Generate QR
    qr_success, ap_txn_id, order_id = test_generate_qr()
    results.append(("Generate QR Code", qr_success))
    
    # Test 4: Verify Payment (if QR was generated)
    if qr_success:
        # Wait a bit before checking status
        print(f"\n⏳ Waiting 5 seconds before checking status...")
        time.sleep(5)
        results.append(("Verify Payment", test_verify_payment(ap_txn_id, order_id)))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n🎉 All tests passed! Airpay V4 integration is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Please check the configuration.")

if __name__ == '__main__':
    main()
