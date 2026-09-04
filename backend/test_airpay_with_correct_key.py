"""
Test Airpay decryption with CORRECT key generation
Key = MD5(username~:~password)
"""

import requests
import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import os
from dotenv import load_dotenv

load_dotenv()

def generate_encryption_key(username, password):
    """
    Generate encryption key using MD5 hash
    Key = MD5(username~:~password)
    """
    key_string = f"{username}~:~{password}"
    md5_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
    return md5_hash

def decrypt_airpay_response(encrypted_response, encryption_key):
    """
    Decrypt Airpay response using AES-256-CBC
    """
    try:
        print(f"🔓 Decrypting Airpay response...")
        
        # Extract IV (first 16 characters as raw string)
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"  IV (string): '{iv_string}'")
        
        # Convert IV to bytes using latin-1 encoding
        iv_bytes = iv_string.encode('latin-1')
        print(f"  IV bytes: {iv_bytes.hex()} (length: {len(iv_bytes)})")
        
        # Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"  Encrypted data length: {len(encrypted_data)}")
        
        # Prepare encryption key (32 bytes for AES-256)
        # MD5 hash produces 32 hex characters = 16 bytes when converted
        # But we use the hex string directly as the key
        key_bytes = encryption_key.encode('latin-1')
        print(f"  Key: {encryption_key}")
        print(f"  Key bytes: {key_bytes.hex()} (length: {len(key_bytes)})")
        
        # Decrypt using AES-256-CBC
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
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
        
        print(f"\n✅ DECRYPTION SUCCESSFUL!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Decryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*60)
    print("AIRPAY TOKEN GENERATION - WITH CORRECT KEY")
    print("="*60)
    
    # Get credentials
    base_url = os.getenv('AIRPAY_BASE_URL', 'https://kraken.airpay.co.in')
    client_id = os.getenv('AIRPAY_CLIENT_ID')
    client_secret = os.getenv('AIRPAY_CLIENT_SECRET')
    merchant_id = os.getenv('AIRPAY_MERCHANT_ID')
    username = os.getenv('AIRPAY_USERNAME')
    password = os.getenv('AIRPAY_PASSWORD')
    
    print(f"\nStep 1: Generate encryption key")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    # Generate correct encryption key
    encryption_key = generate_encryption_key(username, password)
    
    print(f"  Key String: {username}~:~{password}")
    print(f"  Encryption Key (MD5): {encryption_key}")
    print(f"  Key Length: {len(encryption_key)} characters")
    
    # Request token
    print(f"\nStep 2: Request OAuth2 token...")
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
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Token request failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    result = response.json()
    encrypted_response = result.get('response')
    
    print(f"  Encrypted response: {encrypted_response[:50]}...")
    
    # Decrypt response
    print(f"\nStep 3: Decrypt response...")
    decrypted = decrypt_airpay_response(encrypted_response, encryption_key)
    
    if decrypted:
        # Extract token
        if decrypted.get('status_code') == '200' and decrypted.get('status') == 'success':
            data = decrypted.get('data', {})
            access_token = data.get('access_token')
            expires_in = data.get('expires_in', 300)
            
            print(f"\n🎉 SUCCESS!")
            print(f"="*60)
            print(f"Access Token: {access_token[:30]}...")
            print(f"Token Length: {len(access_token)}")
            print(f"Expires In: {expires_in} seconds")
            print(f"="*60)
            
            print(f"\n✅ Airpay V4 integration is WORKING!")
            print(f"\nNext steps:")
            print(f"1. Update backend/.env with correct encryption key")
            print(f"2. Update airpay_service.py to generate key from username/password")
            print(f"3. Test QR generation")
            print(f"4. Test payment verification")
            print(f"5. Test callback handling")
            
            return True
        else:
            print(f"\n❌ Unexpected response format: {decrypted}")
            return False
    else:
        print(f"\n❌ Decryption failed")
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
