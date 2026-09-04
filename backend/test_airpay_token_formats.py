"""
Test different request formats for Airpay token generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
import requests
import json

def test_format_1_json():
    """Test 1: JSON format (current implementation)"""
    print("\n" + "="*60)
    print("TEST 1: JSON Format")
    print("="*60)
    
    url = f"{Config.AIRPAY_BASE_URL}/airpay/pay/v4/api/oauth2"
    
    payload = {
        'client_id': Config.AIRPAY_CLIENT_ID,
        'client_secret': Config.AIRPAY_CLIENT_SECRET,
        'merchant_id': int(Config.AIRPAY_MERCHANT_ID),
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True, response.json()
        else:
            print("❌ FAILED")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_format_2_form_urlencoded():
    """Test 2: Form URL-encoded format"""
    print("\n" + "="*60)
    print("TEST 2: Form URL-encoded Format")
    print("="*60)
    
    url = f"{Config.AIRPAY_BASE_URL}/airpay/pay/v4/api/oauth2"
    
    payload = {
        'client_id': Config.AIRPAY_CLIENT_ID,
        'client_secret': Config.AIRPAY_CLIENT_SECRET,
        'merchant_id': Config.AIRPAY_MERCHANT_ID,
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(
            url,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True, response.json()
        else:
            print("❌ FAILED")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_format_3_json_string_merchant_id():
    """Test 3: JSON format with merchant_id as string"""
    print("\n" + "="*60)
    print("TEST 3: JSON Format (merchant_id as string)")
    print("="*60)
    
    url = f"{Config.AIRPAY_BASE_URL}/airpay/pay/v4/api/oauth2"
    
    payload = {
        'client_id': Config.AIRPAY_CLIENT_ID,
        'client_secret': Config.AIRPAY_CLIENT_SECRET,
        'merchant_id': str(Config.AIRPAY_MERCHANT_ID),
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True, response.json()
        else:
            print("❌ FAILED")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def test_format_4_different_endpoint():
    """Test 4: Try without /v4/ in path"""
    print("\n" + "="*60)
    print("TEST 4: Different Endpoint (without /v4/)")
    print("="*60)
    
    url = f"{Config.AIRPAY_BASE_URL}/airpay/pay/api/oauth2"
    
    payload = {
        'client_id': Config.AIRPAY_CLIENT_ID,
        'client_secret': Config.AIRPAY_CLIENT_SECRET,
        'merchant_id': int(Config.AIRPAY_MERCHANT_ID),
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True, response.json()
        else:
            print("❌ FAILED")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def main():
    print("\n" + "="*60)
    print("AIRPAY TOKEN GENERATION - FORMAT TESTING")
    print("="*60)
    
    tests = [
        ("JSON Format", test_format_1_json),
        ("Form URL-encoded", test_format_2_form_urlencoded),
        ("JSON (string merchant_id)", test_format_3_json_string_merchant_id),
        ("Different Endpoint", test_format_4_different_endpoint)
    ]
    
    results = []
    working_format = None
    
    for test_name, test_func in tests:
        success, data = test_func()
        results.append((test_name, success))
        if success and not working_format:
            working_format = (test_name, data)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    if working_format:
        print(f"\n🎉 Working format found: {working_format[0]}")
        print(f"Token data: {json.dumps(working_format[1], indent=2)}")
    else:
        print("\n❌ No working format found!")
        print("\nPossible issues:")
        print("1. IP address not whitelisted with Airpay")
        print("2. Credentials are incorrect")
        print("3. API endpoint has changed")
        print("4. Account not activated")
        print("\nContact Airpay support: support@airpay.co.in")

if __name__ == '__main__':
    main()
