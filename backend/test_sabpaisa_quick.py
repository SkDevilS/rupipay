"""
Quick Sabpaisa Grosmart API Test
Simple test to verify if the API is working
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

def test_sabpaisa_quick():
    """Quick test of Sabpaisa API"""
    
    print("=" * 70)
    print("SABPAISA GROSMART QUICK TEST")
    print("=" * 70)
    
    # Configuration
    base_url = Config.SABPAISA_GROSMART_BASE_URL
    client_code = Config.SABPAISA_GROSMART_CLIENT_CODE
    api_key = Config.SABPAISA_GROSMART_API_KEY
    secret_key = Config.SABPAISA_GROSMART_SECRET_KEY
    
    print(f"\n📋 Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Client Code: {client_code}")
    print(f"  API Key: {api_key[:15]}...{api_key[-5:]}")
    
    # Test data
    timestamp = int(time.time())
    merchant_txn_id = f"QUICK_TEST_{timestamp}"
    amount_paise = 1000  # ₹10
    currency = "INR"
    
    print(f"\n📦 Test Transaction:")
    print(f"  Txn ID: {merchant_txn_id}")
    print(f"  Amount: ₹{amount_paise/100} ({amount_paise} paise)")
    
    # Generate checksum
    checksum_string = f"{client_code}|{merchant_txn_id}|{amount_paise}|{currency}|{timestamp}"
    checksum = hmac.new(
        secret_key.encode('utf-8'),
        checksum_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().lower()
    
    print(f"\n🔐 Checksum: {checksum}")
    
    # Prepare request
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
        'description': 'Quick Test Payment',
        'upiExpiryMinutes': 5
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
        'X-Merchant-Id': client_code
    }
    
    url = f"{base_url}/api/v1/payments/s2s"
    
    print(f"\n🚀 Sending request to: {url}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"  Status Code: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"\n  Body:")
            print(json.dumps(response_json, indent=4))
            
            # Analyze
            print(f"\n📊 Result:")
            if response.status_code == 201 and response_json.get('success'):
                print(f"  ✅ SUCCESS - Payment created!")
                print(f"  Payment ID: {response_json.get('paymentId')}")
                print(f"  Intent URL: {response_json.get('intentUrl', 'N/A')}")
            elif response.status_code == 500:
                print(f"  ❌ SERVER ERROR - Sabpaisa internal error")
                print(f"  Trace ID: {response_json.get('traceId')}")
                print(f"  Action: Contact Sabpaisa support with trace ID")
            elif response.status_code == 401:
                print(f"  ❌ UNAUTHORIZED - Check credentials")
            else:
                print(f"  ⚠️  Status: {response.status_code}")
                
        except:
            print(response.text)
            
    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT - Server not responding")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    print(f"\n" + "=" * 70)

if __name__ == '__main__':
    test_sabpaisa_quick()
