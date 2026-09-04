"""
Test all possible Airpay decryption methods
"""

import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import os
from dotenv import load_dotenv

load_dotenv()

def test_decryption_method(encrypted_response, encryption_key, method_name, key_size, iv_encoding):
    """
    Test a specific decryption method
    
    Args:
        encrypted_response: The encrypted string from Airpay
        encryption_key: The encryption key
        method_name: Description of this method
        key_size: 16 for AES-128, 24 for AES-192, 32 for AES-256, or None for original length
        iv_encoding: 'latin-1', 'utf-8', or 'hex'
    """
    try:
        print(f"\n{'='*60}")
        print(f"Method: {method_name}")
        print(f"{'='*60}")
        
        # Extract IV and encrypted data
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV string: '{iv_string}'")
        
        # Convert IV based on encoding method
        if iv_encoding == 'hex':
            iv_bytes = bytes.fromhex(iv_string)
            # Pad to 16 bytes if needed
            if len(iv_bytes) < 16:
                iv_bytes = iv_bytes + b'\x00' * (16 - len(iv_bytes))
        else:
            iv_bytes = iv_string.encode(iv_encoding)
        
        print(f"IV bytes ({iv_encoding}): {iv_bytes.hex()} (length: {len(iv_bytes)})")
        
        # Decode base64
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)}")
        
        # Prepare key
        if iv_encoding == 'hex':
            key_bytes = encryption_key.encode('utf-8')
        else:
            key_bytes = encryption_key.encode(iv_encoding)
        
        # Adjust key size
        if key_size:
            if len(key_bytes) < key_size:
                key_bytes = key_bytes.ljust(key_size, b'\x00')
            elif len(key_bytes) > key_size:
                key_bytes = key_bytes[:key_size]
        
        print(f"Key bytes: {key_bytes.hex()} (length: {len(key_bytes)})")
        
        # Decrypt
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        print(f"Decrypted length: {len(decrypted_data)}")
        print(f"Last byte: {decrypted_data[-1]}")
        
        # Try to unpad
        try:
            unpadded_data = unpad(decrypted_data, AES.block_size)
        except:
            # Manual unpad
            padding_length = decrypted_data[-1]
            if isinstance(padding_length, str):
                padding_length = ord(padding_length)
            
            if 1 <= padding_length <= 16:
                unpadded_data = decrypted_data[:-padding_length]
            else:
                print(f"❌ Invalid padding: {padding_length}")
                return False
        
        # Try to parse JSON
        try:
            json_str = unpadded_data.decode('utf-8')
            result = json.loads(json_str)
            
            print(f"\n✅ SUCCESS!")
            print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
            return True
            
        except Exception as e:
            print(f"❌ JSON parse failed: {e}")
            print(f"Raw data: {unpadded_data[:100]}")
            return False
            
    except Exception as e:
        print(f"❌ Method failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("AIRPAY DECRYPTION - TRY ALL METHODS")
    print("="*60)
    
    # Get token first
    base_url = os.getenv('AIRPAY_BASE_URL', 'https://kraken.airpay.co.in')
    client_id = os.getenv('AIRPAY_CLIENT_ID')
    client_secret = os.getenv('AIRPAY_CLIENT_SECRET')
    merchant_id = os.getenv('AIRPAY_MERCHANT_ID')
    encryption_key = os.getenv('AIRPAY_ENCRYPTION_KEY')
    
    print(f"\nConfiguration:")
    print(f"  Encryption Key: '{encryption_key}'")
    print(f"  Key Length: {len(encryption_key)}")
    
    # Request token
    print(f"\nRequesting token...")
    url = f"{base_url}/airpay/pay/v4/api/oauth2"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'merchant_id': merchant_id,
        'grant_type': 'client_credentials'
    }
    
    response = requests.post(
        url,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Token request failed: {response.status_code}")
        return False
    
    result = response.json()
    encrypted_response = result.get('response')
    
    print(f"Encrypted response: {encrypted_response[:50]}...")
    print(f"Response length: {len(encrypted_response)}")
    
    # Try different methods
    methods = [
        ("AES-128 with latin-1 IV", 16, 'latin-1'),
        ("AES-256 with latin-1 IV", 32, 'latin-1'),
        ("AES-128 with utf-8 IV", 16, 'utf-8'),
        ("AES-256 with utf-8 IV", 32, 'utf-8'),
        ("AES-128 with hex IV", 16, 'hex'),
        ("AES-256 with hex IV", 32, 'hex'),
        ("AES with original key length (latin-1)", None, 'latin-1'),
        ("AES with original key length (utf-8)", None, 'utf-8'),
    ]
    
    for method_name, key_size, iv_encoding in methods:
        success = test_decryption_method(
            encrypted_response,
            encryption_key,
            method_name,
            key_size,
            iv_encoding
        )
        
        if success:
            print(f"\n🎉 FOUND WORKING METHOD: {method_name}")
            print(f"   Key Size: {key_size or 'original'}")
            print(f"   IV Encoding: {iv_encoding}")
            return True
    
    print(f"\n❌ No working method found")
    print(f"\nPlease contact Airpay support for:")
    print(f"1. Correct encryption key")
    print(f"2. Sample encrypted/decrypted pair")
    print(f"3. Exact decryption algorithm details")
    
    return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
