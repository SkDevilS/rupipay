#!/usr/bin/env python3
"""
Debug Airpay API Response
Test the actual response format from Airpay to understand the issue
"""

import requests
import json
import hashlib
import base64
from datetime import datetime
from config import Config

def test_airpay_raw_response():
    """Test Airpay API and examine raw response"""
    print("🔍 Debugging Airpay API Response")
    print("=" * 50)
    
    # Configuration
    base_url = Config.AIRPAY_BASE_URL
    merchant_id = Config.AIRPAY_MERCHANT_ID
    username = Config.AIRPAY_USERNAME
    password = Config.AIRPAY_PASSWORD
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    print(f"Base URL: {base_url}")
    print(f"Merchant ID: {merchant_id}")
    print(f"Username: {username}")
    print(f"Encryption Key: {encryption_key[:10]}..." if encryption_key else "❌ Not configured")
    
    if not encryption_key:
        print("\n❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    # Generate key256 for checksum
    key256 = hashlib.sha256(f"{username}~:~{password}".encode('utf-8')).hexdigest()
    print(f"Key256: {key256[:20]}...")
    
    # Prepare test order data with proper validation
    order_id = f"DEBUG_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    order_data = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',  # Minimum amount for testing
        'tid': '12345678',
        'buyerPhone': '9876543210',  # Ensure 10 digits
        'buyerEmail': 'test@example.com',  # Ensure valid email format
        'mer_dom': base64.b64encode('https://client.moneyone.co.in'.encode()).decode(),
        'customvar': 'debug_test',
        'call_type': 'upiqr'
    }
    
    print(f"\nTest order data: {order_data}")
    
    # Generate checksum
    alldata = (
        str(order_data['mercid']) +
        str(order_data['orderid']) +
        str(order_data['amount']) +
        str(order_data['tid']) +
        str(order_data['buyerPhone']) +
        str(order_data['buyerEmail']) +
        str(order_data['mer_dom']) +
        str(order_data['customvar']) +
        str(order_data['call_type'])
    )
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    checksum_string = f"{key256}@{alldata}{current_date}"
    checksum = hashlib.sha256(checksum_string.encode('utf-8')).hexdigest()
    
    print(f"\nChecksum calculation:")
    print(f"  Alldata: {alldata}")
    print(f"  Date: {current_date}")
    print(f"  Checksum: {checksum}")
    
    # Try WITHOUT encryption first (to see if API accepts plain JSON)
    print(f"\n🧪 Test 1: Plain JSON with Checksum")
    print("-" * 30)
    
    plain_request = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',
        'tid': '12345678',
        'buyerPhone': '9876543210',
        'buyerEmail': 'test@example.com',
        'mer_dom': order_data['mer_dom'],
        'customvar': 'debug_test',
        'call_type': 'upiqr',
        'checksum': checksum
    }
    
    url = f"{base_url}/airpay/api/generateOrder"
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=plain_request,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                print(f"JSON Response: {json.dumps(response_json, indent=2)}")
                
                # Check if response has 'data' field (encrypted)
                if 'data' in response_json:
                    print(f"\n📦 Response contains 'data' field (likely encrypted)")
                    encrypted_data = response_json['data']
                    print(f"Encrypted data length: {len(encrypted_data)}")
                    print(f"First 50 chars: {encrypted_data[:50]}")
                    
                    # Try to identify the format
                    if len(encrypted_data) > 16:
                        iv_part = encrypted_data[:16]
                        data_part = encrypted_data[16:]
                        print(f"Possible IV (hex): {iv_part}")
                        print(f"Possible data part length: {len(data_part)}")
                        
                        # Check if IV is valid hex
                        try:
                            bytes.fromhex(iv_part)
                            print("✅ IV appears to be valid hex")
                        except ValueError:
                            print("❌ IV is not valid hex - different format?")
                    
                else:
                    print(f"\n📄 Response is plain JSON (no encryption)")
                    
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Try with different request formats
    print(f"\n🧪 Test 2: Form Data")
    print("-" * 30)
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=plain_request,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
    except Exception as e:
        print(f"❌ Form request failed: {e}")
    
    # Test with minimal data
    print(f"\n🧪 Test 3: Minimal Request")
    print("-" * 30)
    
    minimal_request = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',
        'call_type': 'upiqr'
    }
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=minimal_request,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Minimal request failed: {e}")

if __name__ == "__main__":
    test_airpay_raw_response()