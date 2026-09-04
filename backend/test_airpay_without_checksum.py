"""
Test Airpay OAuth2 WITHOUT checksum
Some OAuth2 endpoints don't require checksum
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

def decrypt_airpay_response(encrypted_response, encryption_key):
    """Decrypt Airpay response"""
    try:
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        iv_bytes = iv_string.encode('latin-1')
        encrypted_data = base64.b64decode(encrypted_data_b64)
        key_bytes = encryption_key.encode('latin-1')
        
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        unpadded_data = unpad(decrypted_data, AES.block_size)
        
        return json.loads(unpadded_data.decode('utf-8'))
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def main():
    print("\n" + "="*60)
    print("TEST: OAuth2 WITHOUT Checksum")
    print("="*60)
    
    # Get credentials
    base_url = os.getenv('AIRPAY_BASE_URL')
    client_id = os.getenv('AIRPAY_CLIENT_ID')
    client_secret = os.getenv('AIRPAY_CLIENT_SECRET')
    merchant_id = os.getenv('AIRPAY_MERCHANT_ID')
    username = os.getenv('AIRPAY_USERNAME')
    password = os.getenv('AIRPAY_PASSWORD')
    
    # Generate encryption key
    key_string = f"{username}~:~{password}"
    encryption_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    print(f"\nEncryption Key: {encryption_key}")
    
    # Request token WITHOUT checksum
    url = f"{base_url}/airpay/pay/v4/api/oauth2"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'merchant_id': merchant_id,
        'grant_type': 'client_credentials'
    }
    
    print(f"\nRequesting token WITHOUT checksum...")
    print(f"Payload: {payload}")
    
    response = requests.post(
        url,
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        if 'response' in result:
            decrypted = decrypt_airpay_response(result['response'], encryption_key)
            
            if decrypted:
                print(f"\nDecrypted response:")
                print(json.dumps(decrypted, indent=2))
                
                if decrypted.get('status') == 'success':
                    print(f"\n✅ SUCCESS! OAuth2 works WITHOUT checksum!")
                    return True
                else:
                    print(f"\n❌ Still getting error: {decrypted.get('message')}")
                    return False
    
    print(f"\n❌ Failed")
    return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
