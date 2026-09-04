"""
Direct test of Sabpaisa Grosmart API to diagnose the error
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
import requests
import hashlib
import hmac
import time
import json

def test_sabpaisa_api():
    """Test Sabpaisa API directly"""
    
    print("=" * 70)
    print("SABPAISA GROSMART DIRECT API TEST")
    print("=" * 70)
    
    # Configuration
    base_url = Config.SABPAISA_GROSMART_BASE_URL
    client_code = Config.SABPAISA_GROSMART_CLIENT_CODE
    api_key = Config.SABPAISA_GROSMART_API_KEY
    secret_key = Config.SABPAISA_GROSMART_SECRET_KEY
    
    print(f"\n📋 Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Client Code: {client_code}")
    print(f"  API Key: {api_key[:20]}...")
    print(f"  Secret Key: {secret_key[:20]}...")
    
    # Test data
    merchant_txn_id = f"TEST_{int(time.time())}"
    amount_paise = 1000  # ₹10.00
    currency = "INR"
    timestamp = int(time.time())
    
    print(f"\n📦 Test Transaction:")
    print(f"  Merchant Txn ID: {merchant_txn_id}")
    print(f"  Amount: {amount_paise} paise (₹{amount_paise/100})")
    print(f"  Currency: {currency}")
    print(f"  Timestamp: {timestamp}")
    
    # Generate checksum
    checksum_string = f"{client_code}|{merchant_txn_id}|{amount_paise}|{currency}|{timestamp}"
    print(f"\n🔐 Checksum String: {checksum_string}")
    
    checksum = hmac.new(
        secret_key.encode('utf-8'),
        checksum_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().lower()
    
    print(f"🔐 Generated Checksum: {checksum}")
    
    # Prepare payload
    payload = {
        'merchantId': client_code,
        'merchantTxnId': merchant_txn_id,
        'amount': amount_paise,
        'currency': currency,
        'customerName': 'Test Customer',
        'customerEmail': 'test@example.com',
        'customerPhone': '9999999999',
        'paymentMode': 'UPI_INTENT',
        'timestamp': timestamp,
        'checksum': checksum,
        'description': 'Test Payment',
        'upiExpiryMinutes': 5
    }
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
        'X-Merchant-Id': client_code
    }
    
    # API endpoint
    url = f"{base_url}/api/v1/payments/s2s"
    
    print(f"\n📤 API Request:")
    print(f"  URL: {url}")
    print(f"  Method: POST")
    print(f"\n  Headers:")
    for key, value in headers.items():
        if 'Key' in key:
            print(f"    {key}: {value[:20]}...")
        else:
            print(f"    {key}: {value}")
    
    print(f"\n  Payload:")
    print(json.dumps(payload, indent=4))
    
    # Send request
    print(f"\n🚀 Sending request...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers:")
        for key, value in response.headers.items():
            print(f"    {key}: {value}")
        
        print(f"\n  Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=4))
            
            # Analyze response
            print(f"\n📊 Analysis:")
            if response.status_code == 201:
                print(f"  ✅ SUCCESS - Payment created")
                if response_json.get('success'):
                    print(f"  ✅ API returned success=true")
                    print(f"  Payment ID: {response_json.get('paymentId')}")
                    print(f"  Txn ID: {response_json.get('txnId')}")
                    print(f"  Intent URL: {response_json.get('intentUrl')}")
                else:
                    print(f"  ⚠️ API returned success=false")
                    print(f"  Message: {response_json.get('message')}")
            elif response.status_code == 400:
                print(f"  ❌ BAD REQUEST - Invalid parameters")
                print(f"  Message: {response_json.get('message')}")
                print(f"  Errors: {response_json.get('errors')}")
            elif response.status_code == 401:
                print(f"  ❌ UNAUTHORIZED - Invalid credentials")
                print(f"  Check API Key and Client Code")
            elif response.status_code == 403:
                print(f"  ❌ FORBIDDEN - Access denied")
                print(f"  Check if merchant account is active")
            elif response.status_code == 500:
                print(f"  ❌ SERVER ERROR - Sabpaisa server issue")
            else:
                print(f"  ❌ UNEXPECTED STATUS CODE")
                
        except:
            print(response.text)
            print(f"\n  ❌ Failed to parse JSON response")
        
    except requests.exceptions.Timeout:
        print(f"\n❌ REQUEST TIMEOUT")
        print(f"  The API server did not respond within 30 seconds")
        print(f"  This could indicate:")
        print(f"    - Network connectivity issues")
        print(f"    - Sabpaisa server is down")
        print(f"    - Firewall blocking the request")
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR")
        print(f"  Could not connect to {base_url}")
        print(f"  Error: {str(e)}")
        print(f"  This could indicate:")
        print(f"    - Invalid base URL")
        print(f"    - Network connectivity issues")
        print(f"    - DNS resolution failure")
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    test_sabpaisa_api()
