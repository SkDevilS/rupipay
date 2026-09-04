"""
Test Paytouchpayin API - Direct API Testing
Tests the actual Paytouchpayin API to verify credentials and response format
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_config_loading():
    """Test 1: Verify configuration is loaded"""
    print_section("TEST 1: Configuration Loading")
    
    try:
        base_url = Config.PAYTOUCHPAYIN_BASE_URL
        token = Config.PAYTOUCHPAYIN_TOKEN
        
        print(f"✓ Base URL: {base_url}")
        print(f"✓ Token: {token[:20]}...{token[-10:]}")
        print(f"✓ Token Length: {len(token)} characters")
        
        if not base_url or not token:
            print("❌ Configuration missing!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading config: {str(e)}")
        return False

def test_api_connectivity():
    """Test 2: Test basic API connectivity"""
    print_section("TEST 2: API Connectivity")
    
    try:
        base_url = Config.PAYTOUCHPAYIN_BASE_URL
        
        print(f"🌐 Testing connection to: {base_url}")
        
        # Try to connect to base URL
        response = requests.get(base_url, timeout=10)
        
        print(f"✓ Connection successful")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Time: {response.elapsed.total_seconds():.2f}s")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ Connection timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_dynamic_qr_generation():
    """Test 3: Test Dynamic QR Generation API"""
    print_section("TEST 3: Dynamic QR Generation")
    
    try:
        base_url = Config.PAYTOUCHPAYIN_BASE_URL
        token = Config.PAYTOUCHPAYIN_TOKEN
        
        url = f"{base_url}/api/payin/dynamic-qr"
        
        # Generate unique transaction ID
        txnid = f"TEST{int(time.time())}"
        
        # Prepare payload
        payload = {
            'token': token,
            'mobile': '9876543210',
            'amount': '10',
            'txnid': txnid,
            'name': 'Test User'
        }
        
        print(f"📤 Request URL: {url}")
        print(f"📦 Request Payload:")
        print(json.dumps(payload, indent=2))
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print(f"\n🚀 Sending request...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\n📥 Response Body:")
        print(response.text)
        
        # Try to parse JSON
        try:
            response_data = response.json()
            print(f"\n✓ JSON Response:")
            print(json.dumps(response_data, indent=2))
            
            # Check response structure
            if response_data.get('status') == 'SUCCESS':
                print(f"\n✅ QR Generation Successful!")
                data = response_data.get('data', {})
                print(f"  TxnID: {data.get('txnid')}")
                print(f"  API TxnID: {data.get('apitxnid')}")
                print(f"  Amount: ₹{data.get('amount')}")
                print(f"  QR URL: {data.get('redirect_url')}")
                print(f"  Expires At: {data.get('expire_at')}")
                return True
            else:
                print(f"\n⚠️ QR Generation Failed")
                print(f"  Status: {response_data.get('status')}")
                print(f"  Message: {response_data.get('message')}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON response")
            print(f"  Error: {str(e)}")
            print(f"  Raw Response: {response.text[:500]}")
            return False
        
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_with_different_amounts():
    """Test 4: Test with different amount values"""
    print_section("TEST 4: Testing Different Amounts")
    
    amounts = ['1', '10', '100', '500']
    
    for amount in amounts:
        print(f"\n--- Testing with amount: ₹{amount} ---")
        
        try:
            base_url = Config.PAYTOUCHPAYIN_BASE_URL
            token = Config.PAYTOUCHPAYIN_TOKEN
            
            url = f"{base_url}/api/payin/dynamic-qr"
            txnid = f"TEST{int(time.time())}{amount}"
            
            payload = {
                'token': token,
                'mobile': '9876543210',
                'amount': amount,
                'txnid': txnid,
                'name': 'Test User'
            }
            
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'SUCCESS':
                    print(f"✓ Success - API TxnID: {data.get('data', {}).get('apitxnid')}")
                else:
                    print(f"✗ Failed - {data.get('message')}")
            else:
                print(f"✗ HTTP Error - {response.text[:200]}")
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    return True

def test_error_scenarios():
    """Test 5: Test error scenarios"""
    print_section("TEST 5: Error Scenarios")
    
    base_url = Config.PAYTOUCHPAYIN_BASE_URL
    token = Config.PAYTOUCHPAYIN_TOKEN
    url = f"{base_url}/api/payin/dynamic-qr"
    
    # Test 1: Missing token
    print("\n--- Test: Missing Token ---")
    try:
        payload = {
            'mobile': '9876543210',
            'amount': '10',
            'txnid': f"TEST{int(time.time())}",
            'name': 'Test'
        }
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    time.sleep(1)
    
    # Test 2: Invalid token
    print("\n--- Test: Invalid Token ---")
    try:
        payload = {
            'token': 'INVALID_TOKEN_12345',
            'mobile': '9876543210',
            'amount': '10',
            'txnid': f"TEST{int(time.time())}",
            'name': 'Test'
        }
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    time.sleep(1)
    
    # Test 3: Missing required fields
    print("\n--- Test: Missing Amount ---")
    try:
        payload = {
            'token': token,
            'mobile': '9876543210',
            'txnid': f"TEST{int(time.time())}",
            'name': 'Test'
        }
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return True

def diagnose_not_enough_segments_error():
    """Diagnose the 'Not enough segments' error"""
    print_section("DIAGNOSING: Not enough segments error")
    
    print("""
The "Not enough segments" error typically occurs when:

1. JWT Token Parsing Issue
   - The error suggests JWT token parsing problem
   - Check if the token format is correct
   - Verify token is not being split incorrectly

2. URL Path Issue
   - Check if the endpoint URL is correct
   - Verify no extra slashes or missing segments

3. Request Format Issue
   - Check Content-Type header
   - Verify JSON payload structure

Let's check the token format:
""")
    
    token = Config.PAYTOUCHPAYIN_TOKEN
    
    print(f"Token: {token}")
    print(f"Token Length: {len(token)}")
    print(f"Token Type: {type(token)}")
    
    # Check if token looks like JWT
    if '.' in token:
        parts = token.split('.')
        print(f"\n⚠️ Token contains dots (JWT-like): {len(parts)} parts")
        print(f"  This might be causing the 'Not enough segments' error")
        print(f"  JWT tokens typically have 3 parts: header.payload.signature")
    else:
        print(f"\n✓ Token is a simple string (not JWT)")
    
    # Check token characters
    import string
    valid_chars = string.ascii_letters + string.digits
    invalid_chars = [c for c in token if c not in valid_chars]
    
    if invalid_chars:
        print(f"\n⚠️ Token contains special characters: {set(invalid_chars)}")
    else:
        print(f"\n✓ Token contains only alphanumeric characters")
    
    return True

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("  PAYTOUCHPAYIN API TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    results = []
    
    # Test 1: Config Loading
    results.append(("Configuration Loading", test_config_loading()))
    
    if not results[0][1]:
        print("\n❌ Configuration test failed. Cannot proceed.")
        return
    
    # Test 2: API Connectivity
    results.append(("API Connectivity", test_api_connectivity()))
    
    # Test 3: Dynamic QR Generation
    results.append(("Dynamic QR Generation", test_dynamic_qr_generation()))
    
    # Test 4: Different Amounts
    # results.append(("Different Amounts", test_with_different_amounts()))
    
    # Test 5: Error Scenarios
    # results.append(("Error Scenarios", test_error_scenarios()))
    
    # Diagnose error
    diagnose_not_enough_segments_error()
    
    # Summary
    print_section("TEST SUMMARY")
    
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
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print("""
1. If you see "Not enough segments" error:
   - This is likely a JWT parsing error in your backend
   - Check if you're accidentally trying to decode the token as JWT
   - The token should be sent as-is in the request body

2. If API returns error:
   - Verify the token with Paytouchpayin support
   - Check if your IP is whitelisted
   - Verify the API endpoint URL is correct

3. Next Steps:
   - Contact Paytouchpayin support with the test results
   - Share the exact error message and request/response
   - Ask them to verify your token and API access
""")

if __name__ == '__main__':
    run_all_tests()
