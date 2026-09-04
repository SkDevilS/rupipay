"""
Test Sabpaisa Grosmart API with correct parameters as per documentation
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
    """Test Sabpaisa API with correct format"""
    
    print("=" * 70)
    print("SABPAISA GROSMART API TEST (CORRECTED)")
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
    
    # Test data (as per documentation)
    merchant_txn_id = f"TEST_{int(time.time())}"
    amount_paise = 1000  # ₹10.00 in paise (INTEGER as per docs)
    currency = "INR"
    timestamp = int(time.time())  # Unix timestamp in seconds (INTEGER)
    
    print(f"\n📦 Test Transaction:")
    print(f"  Merchant Txn ID: {merchant_txn_id}")
    print(f"  Amount: {amount_paise} paise (₹{amount_paise/100})")
    print(f"  Currency: {currency}")
    print(f"  Timestamp: {timestamp}")
    
    # Generate checksum (as per documentation)
    checksum_string = f"{client_code}|{merchant_txn_id}|{amount_paise}|{currency}|{timestamp}"
    print(f"\n🔐 Checksum String: {checksum_string}")
    
    checksum = hmac.new(
        secret_key.encode('utf-8'),
        checksum_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().lower()
    
    print(f"🔐 Generated Checksum: {checksum}")
    
    # Prepare payload (exactly as per documentation)
    payload = {
        'merchantId': client_code,
        'merchantTxnId': merchant_txn_id,
        'amount': amount_paise,  # INTEGER in paise
        'currency': currency,
        'customerName': 'Test Customer',
        'customerEmail': 'test@example.com',
        'customerPhone': '9999999999',
        'paymentMode': 'UPI_INTENT',  # As per documentation
        'timestamp': timestamp,  # INTEGER
        'checksum': checksum,
        'description': 'Test Payment',
        'upiExpiryMinutes': 5
    }
    
    # Prepare headers (exactly as per documentation)
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
        'X-Merchant-Id': client_code  # REQUIRED header
    }
    
    # Correct endpoint as per documentation
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
        
        print(f"\n  Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=4))
            
            # Analyze response
            print(f"\n📊 Analysis:")
            if response.status_code == 201:
                print(f"  ✅ SUCCESS - Payment created (HTTP 201)")
                if response_json.get('success'):
                    print(f"  ✅ API returned success=true")
                    print(f"  Payment ID: {response_json.get('paymentId')}")
                    print(f"  Txn ID: {response_json.get('txnId')}")
                    print(f"  Intent URL: {response_json.get('intentUrl')}")
                else:
                    print(f"  ⚠️ API returned success=false")
                    print(f"  Message: {response_json.get('message')}")
            elif response.status_code == 200:
                print(f"  ✅ SUCCESS - Payment created (HTTP 200)")
                print(f"  Response: {response_json}")
            elif response.status_code == 400:
                print(f"  ❌ BAD REQUEST - Invalid parameters")
                print(f"  Message: {response_json.get('errorMessage') or response_json.get('message')}")
            elif response.status_code == 401:
                print(f"  ❌ UNAUTHORIZED - Invalid credentials or missing header")
                print(f"  Message: {response_json.get('errorMessage') or response_json.get('message')}")
                print(f"\n  💡 Check:")
                print(f"     - API Key is correct")
                print(f"     - X-Merchant-Id header is present")
                print(f"     - Client Code is correct")
            elif response.status_code == 403:
                print(f"  ❌ FORBIDDEN - Access denied")
                print(f"  Check if merchant account is active")
            else:
                print(f"  ❌ UNEXPECTED STATUS CODE: {response.status_code}")
                
        except:
            print(response.text)
            print(f"\n  ❌ Failed to parse JSON response")
        
    except requests.exceptions.Timeout:
        print(f"\n❌ REQUEST TIMEOUT")
        print(f"  The API server did not respond within 30 seconds")
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR")
        print(f"  Could not connect to {base_url}")
        print(f"  Error: {str(e)}")
        
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
