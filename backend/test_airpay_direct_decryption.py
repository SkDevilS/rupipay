"""
Direct test of Airpay decryption without module imports
Tests the exact decryption logic needed
"""

import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def decrypt_airpay_response(encrypted_response, encryption_key):
    """
    Decrypt Airpay response with correct IV handling
    KEY INSIGHT: IV is first 16 characters as RAW STRING, not hex!
    """
    try:
        print(f"🔓 Decrypting Airpay response...")
        print(f"  Encrypted data length: {len(encrypted_response)}")
        print(f"  Preview: {encrypted_response[:50]}...")
        
        # Extract IV (first 16 characters as RAW STRING)
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"  IV (string): '{iv_string}'")
        
        # Convert IV string to bytes using latin-1 encoding
        # In PHP, each character becomes one byte - we preserve this with latin-1
        iv_bytes = iv_string.encode('latin-1')
        print(f"  IV bytes length: {len(iv_bytes)}")
        print(f"  IV bytes (hex): {iv_bytes.hex()}")
        
        # Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"  Encrypted data length: {len(encrypted_data)}")
        
        # Prepare encryption key (32 bytes for AES-256)
        key = encryption_key.encode('latin-1')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        print(f"  Key length: {len(key)}")
        
        # Decrypt using AES-256-CBC
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        print(f"  Decrypted data length: {len(decrypted_data)}")
        print(f"  Last byte (padding): {decrypted_data[-1]}")
        
        # Remove PKCS5 padding
        try:
            unpadded_data = unpad(decrypted_data, AES.block_size)
        except ValueError as e:
            print(f"  Unpad failed: {e}")
            # Manual padding removal
            padding_length = decrypted_data[-1]
            if isinstance(padding_length, str):
                padding_length = ord(padding_length)
            
            print(f"  Manual padding removal: {padding_length} bytes")
            
            if 1 <= padding_length <= 16:
                unpadded_data = decrypted_data[:-padding_length]
            else:
                raise ValueError(f"Invalid padding: {padding_length}")
        
        # Parse JSON
        result = json.loads(unpadded_data.decode('utf-8'))
        
        print(f"✓ Decryption successful!")
        print(f"  Decrypted data: {json.dumps(result, indent=2)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_token_generation():
    """
    Test complete token generation with decryption
    """
    print("\n" + "="*60)
    print("AIRPAY TOKEN GENERATION - DIRECT TEST")
    print("="*60 + "\n")
    
    # Get credentials from environment
    base_url = os.getenv('AIRPAY_BASE_URL', 'https://kraken.airpay.co.in')
    client_id = os.getenv('AIRPAY_CLIENT_ID')
    client_secret = os.getenv('AIRPAY_CLIENT_SECRET')
    merchant_id = os.getenv('AIRPAY_MERCHANT_ID')
    encryption_key = os.getenv('AIRPAY_ENCRYPTION_KEY')
    
    print(f"Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Client ID: {client_id}")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Encryption Key Length: {len(encryption_key) if encryption_key else 0}")
    
    # Step 1: Request token
    print(f"\nStep 1: Requesting OAuth2 token...")
    
    url = f"{base_url}/airpay/pay/v4/api/oauth2"
    
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'merchant_id': merchant_id,
        'grant_type': 'client_credentials'
    }
    
    print(f"  URL: {url}")
    print(f"  Payload: {payload}")
    
    # Use form-urlencoded format
    response = requests.post(
        url,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    print(f"\nStep 2: Response received")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}...")
    
    if response.status_code != 200:
        print(f"\n❌ FAILED: HTTP {response.status_code}")
        return False
    
    result = response.json()
    
    # Step 3: Decrypt response
    if 'response' in result:
        print(f"\nStep 3: Decrypting response...")
        encrypted_response = result.get('response')
        
        decrypted = decrypt_airpay_response(encrypted_response, encryption_key)
        
        if decrypted:
            # Extract token
            if decrypted.get('status_code') == '200' and decrypted.get('status') == 'success':
                data = decrypted.get('data', {})
                access_token = data.get('access_token')
                expires_in = data.get('expires_in', 300)
                
                print(f"\n✅ SUCCESS!")
                print(f"  Access Token: {access_token[:30]}...")
                print(f"  Token Length: {len(access_token)}")
                print(f"  Expires In: {expires_in} seconds")
                
                return True
            else:
                print(f"\n❌ Unexpected response format: {decrypted}")
                return False
        else:
            print(f"\n❌ Decryption failed")
            return False
    else:
        print(f"\n❌ No encrypted response in result")
        return False

if __name__ == '__main__':
    import sys
    success = test_token_generation()
    sys.exit(0 if success else 1)
