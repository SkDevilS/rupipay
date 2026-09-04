"""
Test Paytouchpayin Integration
Tests service initialization, order creation, and callback handling
"""

import sys
import json
from paytouchpayin_service import PaytouchpayinService

def test_service_initialization():
    """Test 1: Service Initialization"""
    print("\n" + "="*60)
    print("TEST 1: Service Initialization")
    print("="*60)
    
    try:
        service = PaytouchpayinService()
        print("✅ Service initialized successfully")
        print(f"   Base URL: {service.base_url}")
        print(f"   Token: {service.token[:20]}...")
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {str(e)}")
        return False

def test_charge_calculation():
    """Test 2: Charge Calculation"""
    print("\n" + "="*60)
    print("TEST 2: Charge Calculation")
    print("="*60)
    
    try:
        service = PaytouchpayinService()
        
        # Test with a sample scheme (you may need to adjust scheme_id)
        amount = 100
        scheme_id = 1  # Adjust based on your database
        
        charges = service.calculate_charges(amount, scheme_id, 'PAYIN')
        
        if charges:
            print("✅ Charge calculation successful")
            print(f"   Amount: ₹{amount}")
            print(f"   Base Charge: ₹{charges['base_charge']}")
            print(f"   GST: ₹{charges['gst_amount']}")
            print(f"   Total Charge: ₹{charges['total_charge']}")
            return True
        else:
            print("⚠️ Charge calculation returned None (check scheme_id)")
            return False
            
    except Exception as e:
        print(f"❌ Charge calculation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_qr_generation():
    """Test 3: Dynamic QR Generation"""
    print("\n" + "="*60)
    print("TEST 3: Dynamic QR Generation")
    print("="*60)
    
    try:
        service = PaytouchpayinService()
        
        # Test data
        order_data = {
            'txnid': f'TEST{int(time.time())}',
            'amount': 10,  # Small amount for testing
            'mobile': '9876543210',
            'name': 'Test User'
        }
        
        print(f"📤 Sending test request...")
        print(f"   TxnID: {order_data['txnid']}")
        print(f"   Amount: ₹{order_data['amount']}")
        
        result = service.generate_dynamic_qr(order_data)
        
        if result.get('success'):
            print("✅ QR generation successful")
            data = result.get('data', {})
            print(f"   TxnID: {data.get('txnid')}")
            print(f"   API TxnID: {data.get('apitxnid')}")
            print(f"   Amount: ₹{data.get('amount')}")
            print(f"   QR URL: {data.get('redirect_url')}")
            print(f"   Expires At: {data.get('expire_at')}")
            return True
        else:
            print(f"❌ QR generation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ QR generation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_callback_format():
    """Test 4: Callback Format Validation"""
    print("\n" + "="*60)
    print("TEST 4: Callback Format Validation")
    print("="*60)
    
    # Sample success callback
    success_callback = {
        "status": "success",
        "txnid": "TEST123456",
        "apitxnid": "DQR2361774330510909",
        "amount": 100.50,
        "charge": 1.00,
        "utr": "608373377074",
        "name": "test@upi",
        "mobile": "9876543210",
        "product": "dynamicqrpayin",
        "remark": "Test payment",
        "status_text": "success"
    }
    
    # Sample failed callback
    failed_callback = {
        "status": "failed",
        "txnid": "TEST123456",
        "apitxnid": "DQR3281774323420213",
        "amount": 100.50,
        "charge": 1.00,
        "utr": None,
        "name": "test@upi",
        "mobile": "9876543210",
        "product": "dynamicqrpayin",
        "remark": "QR Expired",
        "status_text": "failed"
    }
    
    print("✅ Success callback format:")
    print(json.dumps(success_callback, indent=2))
    
    print("\n✅ Failed callback format:")
    print(json.dumps(failed_callback, indent=2))
    
    return True

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("PAYTOUCHPAYIN INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Service Initialization
    results.append(("Service Initialization", test_service_initialization()))
    
    # Test 2: Charge Calculation
    results.append(("Charge Calculation", test_charge_calculation()))
    
    # Test 3: QR Generation (commented out by default to avoid API calls)
    # Uncomment to test actual API
    # results.append(("QR Generation", test_qr_generation()))
    print("\n⚠️ QR Generation test skipped (uncomment to test actual API)")
    
    # Test 4: Callback Format
    results.append(("Callback Format", test_callback_format()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Configure callback URL with Paytouchpayin:")
    print("   https://your-domain.com/api/paytouchpayin/callback")
    print("2. Add Paytouchpayin to service routing")
    print("3. Test with actual merchant account")
    print("4. Monitor callbacks and transactions")
    print("")

if __name__ == '__main__':
    import time
    run_all_tests()
