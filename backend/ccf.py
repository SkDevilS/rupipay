#!/usr/bin/env python3
"""
Complete Airpay API Debug Script
Based on user's debug output and new Airpay documentation
"""

import requests
import json
import hashlib
import base64
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config

def encrypt_data_v2(data, encryption_key):
    """
    Encrypt data according to Airpay documentation:
    IV = bin2hex(openssl_random_pseudo_bytes(8));
    raw = openssl_encrypt(json_data, AES-256-CBC, EncryptionKey, options=OPENSSL_RAW_DATA, IV);
    encData = IV.base64_encode(raw);
    """
    try:
        # Convert data to JSON string if it's a dict
        if isinstance(data, dict):
            data = json.dumps(data)
        
        # Generate 8-byte IV and convert to hex (16 characters)
        iv_bytes = get_random_bytes(8)
        iv_hex = iv_bytes.hex()
        
        # Use the encryption key provided by Airpay (not the SHA256 key)
        if not encryption_key:
            print("❌ AIRPAY_ENCRYPTION_KEY not configured")
            return None
        
        # Use first 32 bytes of the encryption key for AES-256
        key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
        
        # Create 16-byte IV for AES (pad the 8-byte IV)
        aes_iv = iv_bytes + b'\x00' * 8  # Pad to 16 bytes
        
        # Create cipher and encrypt
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
        
        # Return IV (hex) + base64(encrypted_data)
        encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        result = iv_hex + encrypted_b64
        
        print(f"✅ Encrypted data: IV hex={iv_hex}, B64 length={len(encrypted_b64)}, Total={len(result)}")
        return result
        
    except Exception as e:
        print(f"❌ Encryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_airpay_complete():
    """Test Airpay API with complete debugging"""
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
    
    # Generate key256 for checksum
    key256 = hashlib.sha256(f"{username}~:~{password}".encode('utf-8')).hexdigest()
    print(f"Key256: {key256[:20]}...")
    
    # Prepare test order data with proper validation
    order_id = f"DEBUG_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    order_data = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',
        'tid': '12345678',
        'buyerPhone': '9876543210',
        'buyerEmail': 'test@example.com',
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
    
    url = f"{base_url}/airpay/api/generateOrder"
    
    # Test 1: Plain JSON (No Encryption)
    print(f"\n🧪 Test 1: Plain JSON (No Encryption)")
    print("-" * 30)
    
    plain_request = order_data.copy()
    plain_request['checksum'] = checksum
    
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
                    print(f"📦 Response contains encrypted data")
                else:
                    print(f"📄 Response is plain JSON (no encryption)")
                    
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: Form Data
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
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Form request failed: {e}")
    
    # Test 3: Minimal Request
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
    
    # Test 4: Encrypted Request (New Documentation Format)
    print(f"\n🧪 Test 4: Encrypted Request (New Format)")
    print("-" * 30)
    
    if encryption_key:
        try:
            # Encrypt the order data
            encrypted_data = encrypt_data_v2(order_data, encryption_key)
            
            if encrypted_data:
                # Prepare encrypted request
                encrypted_request = {
                    'encData': encrypted_data,
                    'checksum': checksum,
                    'mercid': int(merchant_id)
                }
                
                print(f"Encrypted request structure: {list(encrypted_request.keys())}")
                print(f"encData length: {len(encrypted_data)}")
                print(f"encData sample: {encrypted_data[:50]}...")
                
                response = requests.post(
                    url,
                    headers={'Content-Type': 'application/json'},
                    json=encrypted_request,
                    timeout=30
                )
                
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_json = response.json()
                        print(f"JSON Response: {json.dumps(response_json, indent=2)}")
                        
                        # Check if we need to decrypt the response
                        if 'data' in response_json:
                            print(f"📦 Response contains encrypted data field")
                            # Could implement decryption here if needed
                        else:
                            print(f"📄 Response is plain JSON")
                            
                    except json.JSONDecodeError:
                        print("❌ Response is not valid JSON")
            else:
                print("❌ Failed to encrypt data")
                
        except Exception as e:
            print(f"❌ Encrypted request failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No encryption key configured")
    
    # Test 5: Try different field names based on Airpay documentation
    print(f"\n🧪 Test 5: Alternative Field Names")
    print("-" * 30)
    
    # Try with different field names that might be expected
    alt_order_data = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',
        'tid': '12345678',
        'phone': '9876543210',  # Try 'phone' instead of 'buyerPhone'
        'email': 'test@example.com',  # Try 'email' instead of 'buyerEmail'
        'mer_dom': base64.b64encode('https://client.moneyone.co.in'.encode()).decode(),
        'customvar': 'debug_test',
        'call_type': 'upiqr',
        'checksum': checksum
    }
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=alt_order_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Alternative fields request failed: {e}")
    
    # Test 6: Try with buyer_phone and buyer_email
    print(f"\n🧪 Test 6: Underscore Field Names")
    print("-" * 30)
    
    underscore_order_data = {
        'mercid': int(merchant_id),
        'orderid': order_id,
        'amount': '1.00',
        'tid': '12345678',
        'buyer_phone': '9876543210',  # Try with underscore
        'buyer_email': 'test@example.com',  # Try with underscore
        'mer_dom': base64.b64encode('https://client.moneyone.co.in'.encode()).decode(),
        'customvar': 'debug_test',
        'call_type': 'upiqr',
        'checksum': checksum
    }
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=underscore_order_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Underscore fields request failed: {e}")
    
    # Test 7: Check if we need to send as form data with specific field names
    print(f"\n🧪 Test 7: Form Data with All Possible Field Names")
    print("-" * 30)
    
    form_data = {
        'mercid': merchant_id,
        'orderid': order_id,
        'amount': '1.00',
        'tid': '12345678',
        'buyerPhone': '9876543210',
        'buyerEmail': 'test@example.com',
        'phone': '9876543210',
        'email': 'test@example.com',
        'buyer_phone': '9876543210',
        'buyer_email': 'test@example.com',
        'mer_dom': base64.b64encode('https://client.moneyone.co.in'.encode()).decode(),
        'customvar': 'debug_test',
        'call_type': 'upiqr',
        'checksum': checksum
    }
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=form_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Form data with all fields request failed: {e}")

if __name__ == "__main__":
    test_airpay_complete()