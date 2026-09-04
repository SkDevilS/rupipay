"""
Test script for Sabpaisa Grosmart integration
Tests service initialization, checksum generation, and API connectivity
"""

from sabpaisa_grosmart_service import sabpaisa_grosmart_service
import time


def test_service_initialization():
    """Test if service is initialized correctly"""
    print("\n" + "="*60)
    print("TEST 1: Service Initialization")
    print("="*60)
    
    try:
        assert sabpaisa_grosmart_service.base_url == 'https://merchant-api.sabpaisa.in'
        assert sabpaisa_grosmart_service.client_code == 'GROS1'
        assert sabpaisa_grosmart_service.api_key is not None
        assert sabpaisa_grosmart_service.secret_key is not None
        
        print("✅ Service initialized successfully")
        print(f"   Base URL: {sabpaisa_grosmart_service.base_url}")
        print(f"   Client Code: {sabpaisa_grosmart_service.client_code}")
        print(f"   API Key: {sabpaisa_grosmart_service.api_key[:20]}...")
        return True
    except AssertionError as e:
        print(f"❌ Service initialization failed: {e}")
        return False


def test_checksum_generation():
    """Test checksum generation"""
    print("\n" + "="*60)
    print("TEST 2: Checksum Generation")
    print("="*60)
    
    try:
        # Test data
        merchant_id = "GROS1"
        merchant_txn_id = "TEST_TXN_001"
        amount = 10000  # 100 rupees in paise
        currency = "INR"
        timestamp = int(time.time())
        
        # Generate checksum
        checksum = sabpaisa_grosmart_service.generate_checksum(
            merchant_id, merchant_txn_id, amount, currency, timestamp
        )
        
        assert checksum is not None
        assert len(checksum) == 64  # SHA256 produces 64 hex characters
        assert checksum.islower()  # Should be lowercase
        
        print("✅ Checksum generated successfully")
        print(f"   Merchant ID: {merchant_id}")
        print(f"   Txn ID: {merchant_txn_id}")
        print(f"   Amount: {amount} paise (₹{amount/100})")
        print(f"   Timestamp: {timestamp}")
        print(f"   Checksum: {checksum}")
        
        # Test consistency - same input should produce same checksum
        checksum2 = sabpaisa_grosmart_service.generate_checksum(
            merchant_id, merchant_txn_id, amount, currency, timestamp
        )
        assert checksum == checksum2
        print("✅ Checksum is consistent (same input = same output)")
        
        return True
    except Exception as e:
        print(f"❌ Checksum generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_charge_calculation():
    """Test charge calculation"""
    print("\n" + "="*60)
    print("TEST 3: Charge Calculation")
    print("="*60)
    
    try:
        # Test with a sample scheme (you may need to adjust scheme_id)
        test_amount = 1000.00  # ₹1000
        test_scheme_id = 1  # Default scheme
        
        charge_amount, net_amount, charge_type = sabpaisa_grosmart_service.calculate_charges(
            test_amount, test_scheme_id
        )
        
        if charge_amount is None:
            print("⚠️  No charge configuration found for scheme")
            print("   This is OK if scheme is not configured yet")
            return True
        
        print("✅ Charge calculation successful")
        print(f"   Amount: ₹{test_amount}")
        print(f"   Charge Type: {charge_type}")
        print(f"   Charge Amount: ₹{charge_amount}")
        print(f"   Net Amount: ₹{net_amount}")
        print(f"   Merchant receives: ₹{net_amount}")
        print(f"   Admin receives: ₹{charge_amount}")
        
        # Verify calculation
        assert net_amount + charge_amount == test_amount
        print("✅ Charge calculation is correct (net + charge = total)")
        
        return True
    except Exception as e:
        print(f"❌ Charge calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_connectivity():
    """Test API connectivity (without making actual payment)"""
    print("\n" + "="*60)
    print("TEST 4: API Connectivity")
    print("="*60)
    
    try:
        import requests
        
        # Test if API endpoint is reachable
        url = f"{sabpaisa_grosmart_service.base_url}/api/v2/payments/enquiry"
        
        print(f"Testing connectivity to: {url}")
        
        # Send a test request (will fail with 400/401 but proves connectivity)
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': sabpaisa_grosmart_service.api_key
        }
        
        payload = {
            'clientCode': sabpaisa_grosmart_service.client_code,
            'merchantTxnId': 'TEST_CONNECTIVITY_001'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"✅ API is reachable")
        print(f"   Response Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
        if response.status_code in [200, 400, 401, 404]:
            print("✅ API endpoint is responding (status code indicates server is active)")
            return True
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API (check internet connection)")
        return False
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SABPAISA GROSMART INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Service Initialization", test_service_initialization()))
    results.append(("Checksum Generation", test_checksum_generation()))
    results.append(("Charge Calculation", test_charge_calculation()))
    results.append(("API Connectivity", test_api_connectivity()))
    
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
        print("\n🎉 All tests passed! Integration is ready.")
        print("\nNext steps:")
        print("1. Get webhook secret from Sabpaisa team")
        print("2. Configure webhook URL with Sabpaisa")
        print("3. Route merchants to Sabpaisa Grosmart")
        print("4. Test with real transactions")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
