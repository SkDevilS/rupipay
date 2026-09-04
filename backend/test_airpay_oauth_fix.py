#!/usr/bin/env python3
"""
Test Airpay OAuth2 Token Generation - Comprehensive Fix
Based on user feedback about "Invalid Checksum" errors
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

class AirpayOAuth2Tester:
    def __init__(self):
        self.base_url = Config.AIRPAY_BASE_URL
        self.client_id = Config.AIRPAY_CLIENT_ID
        self.client_secret = Config.AIRPAY_CLIENT_SECRET
        self.merchant_id = Config.AIRPAY_MERCHANT_ID
        self.username = Config.AIRPAY_USERNAME
        self.password = Config.AIRPAY_PASSWORD
        # Generate encryption key using MD5 hash
        self.encryption_key = self.generate_encryption_key()
    
    def generate_encryption_key(self):
        """Generate encryption key using MD5 hash: md5(username . "~:~" . password)"""
        try:
            hash_string = f"{self.username}~:~{self.password}"
            return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        except Exception as e:
            print(f"Encryption key generation error: {e}")
            return None
    
    def encrypt_data(self, data):
        """Encrypt data using AES/CBC/PKCS5PADDING"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            
            # Generate random 16-byte IV
            iv = get_random_bytes(16)
            
            # Create cipher using the generated encryption key
            key = self.encryption_key.encode('utf-8')[:32].ljust(32, b'\0')
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Encrypt data with PKCS5 padding
            encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
            
            # Return IV (raw bytes as string) + base64(encrypted_data)
            iv_str = iv.decode('latin-1')
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            result = iv_str + encrypted_b64
            print(f"Encrypted data: IV length={len(iv_str)}, B64 length={len(encrypted_b64)}, Total={len(result)}")
            return result
            
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    def decrypt_data(self, encrypted_response):
        """Decrypt Airpay response"""
        try:
            # Extract IV (first 16 bytes as raw bytes)
            iv = encrypted_response[:16].encode('latin-1')
            encrypted_data_b64 = encrypted_response[16:]
            
            print(f"IV length: {len(iv)}, Encrypted data length: {len(encrypted_data_b64)}")
            
            # Decode base64 encrypted data
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Use the encryption key (32 bytes for AES-256)
            key = self.encryption_key.encode('utf-8')[:32].ljust(32, b'\0')
            
            print(f"Key length: {len(key)}, Encrypted data length: {len(encrypted_data)}")
            
            # Create cipher and decrypt
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            # Parse JSON
            result = json.loads(decrypted_data.decode('utf-8'))
            print(f"Decrypted successfully: {result}")
            return result
            
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def generate_checksum(self, data):
        """Generate checksum according to Airpay documentation"""
        try:
            # Sort data by keys alphabetically
            sorted_data = dict(sorted(data.items()))
            
            # Concatenate all values
            checksum_string = ''
            for key, value in sorted_data.items():
                checksum_string += str(value)
            
            # Append current date in YYYY-MM-DD format
            current_date = datetime.now().strftime('%Y-%m-%d')
            checksum_string += current_date
            
            # Generate SHA-256 hash
            checksum = hashlib.sha256(checksum_string.encode('utf-8')).hexdigest()
            
            print(f"Checksum calculation:")
            print(f"  Sorted data: {sorted_data}")
            print(f"  Values concatenated: {checksum_string}")
            print(f"  SHA-256 checksum: {checksum}")
            
            return checksum
            
        except Exception as e:
            print(f"Checksum generation error: {e}")
            return ""
    
    def test_simple_oauth2_no_encryption(self):
        """Test OAuth2 without encryption first"""
        print("\n🧪 Testing Simple OAuth2 (No Encryption)")
        print("=" * 50)
        
        url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
        
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'merchant_id': int(self.merchant_id),
            'grant_type': 'client_credentials'
        }
        
        print(f"URL: {url}")
        print(f"Payload: {payload}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=payload,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                if 'response' in response_json:
                    print("📦 Response is encrypted - need to decrypt")
                    return response_json
                else:
                    print("📄 Response is plain JSON")
                    return response_json
            else:
                print(f"❌ Request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def test_oauth2_with_encryption(self):
        """Test OAuth2 with encryption and checksum"""
        print("\n🧪 Testing OAuth2 with Encryption")
        print("=" * 50)
        
        url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
        
        # OAuth2 data for encryption
        oauth_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'merchant_id': int(self.merchant_id),
            'grant_type': 'client_credentials'
        }
        
        print(f"OAuth2 data for encryption: {oauth_data}")
        
        # Encrypt the data
        encrypted_data = self.encrypt_data(oauth_data)
        if not encrypted_data:
            print("❌ Failed to encrypt OAuth2 data")
            return None
        
        # Generate checksum
        checksum = self.generate_checksum(oauth_data)
        
        # Prepare request payload
        request_payload = {
            'merchant_id': int(self.merchant_id),
            'encdata': encrypted_data,
            'checksum': checksum,
            'privatekey': self.generate_private_key()
        }
        
        print(f"Sending OAuth2 request with payload keys: {list(request_payload.keys())}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=request_payload,
                timeout=30
            )
            
            print(f"Airpay Token Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                
                if 'response' in response_json:
                    encrypted_response = response_json['response']
                    print(f"Decrypting token response: {encrypted_response[:50]}...")
                    
                    decrypted_data = self.decrypt_data(encrypted_response)
                    if decrypted_data:
                        print(f"Decrypted token data: {decrypted_data}")
                        return decrypted_data
                    else:
                        print("❌ Failed to decrypt response")
                        return None
                else:
                    print(f"Plain response: {response_json}")
                    return response_json
            else:
                print(f"❌ Request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def generate_private_key(self):
        """Generate private key for Airpay request"""
        try:
            # Try different private key formats
            # Format 1: Simple hash of credentials
            hash_string1 = f"{self.username}:{self.password}"
            private_key1 = hashlib.sha256(hash_string1.encode()).hexdigest()
            
            # Format 2: With merchant ID
            hash_string2 = f"{self.merchant_id}:{self.username}:{self.password}"
            private_key2 = hashlib.sha256(hash_string2.encode()).hexdigest()
            
            # Format 3: With API key if available
            api_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
            if api_key:
                hash_string3 = f"{api_key}:{self.username}:{self.password}"
                private_key3 = hashlib.sha256(hash_string3.encode()).hexdigest()
            else:
                private_key3 = private_key1
            
            print(f"Private key options:")
            print(f"  Format 1 (user:pass): {private_key1[:20]}...")
            print(f"  Format 2 (mid:user:pass): {private_key2[:20]}...")
            print(f"  Format 3 (api:user:pass): {private_key3[:20]}...")
            
            # Return the first format for now
            return private_key1
            
        except Exception as e:
            print(f"Private key generation error: {e}")
            return ""
    
    def test_alternative_oauth2_formats(self):
        """Test different OAuth2 request formats"""
        print("\n🧪 Testing Alternative OAuth2 Formats")
        print("=" * 50)
        
        # Format 1: Form data with different field names
        formats = [
            {
                'name': 'Standard Form Data',
                'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                'data': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'merchant_id': self.merchant_id,
                    'grant_type': 'client_credentials'
                }
            },
            {
                'name': 'JSON Format',
                'headers': {'Content-Type': 'application/json'},
                'data': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'merchant_id': int(self.merchant_id),
                    'grant_type': 'client_credentials'
                }
            },
            {
                'name': 'With Username/Password',
                'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                'data': {
                    'username': self.username,
                    'password': self.password,
                    'merchant_id': self.merchant_id,
                    'grant_type': 'client_credentials'
                }
            }
        ]
        
        url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
        
        for fmt in formats:
            print(f"\n📋 Testing {fmt['name']}:")
            print(f"Data: {fmt['data']}")
            
            try:
                if fmt['headers']['Content-Type'] == 'application/json':
                    response = requests.post(url, headers=fmt['headers'], json=fmt['data'], timeout=30)
                else:
                    response = requests.post(url, headers=fmt['headers'], data=fmt['data'], timeout=30)
                
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    print("✅ This format worked!")
                    return response.json()
                    
            except Exception as e:
                print(f"Error: {e}")
        
        return None

def main():
    """Main test function"""
    print("🚀 Airpay OAuth2 Comprehensive Testing")
    print("=" * 60)
    
    tester = AirpayOAuth2Tester()
    
    print(f"Configuration:")
    print(f"  Base URL: {tester.base_url}")
    print(f"  Client ID: {tester.client_id}")
    print(f"  Client Secret: {tester.client_secret[:10]}...")
    print(f"  Merchant ID: {tester.merchant_id}")
    print(f"  Username: {tester.username}")
    print(f"  Encryption Key: {tester.encryption_key[:10]}...")
    
    # Test 1: Simple OAuth2 without encryption
    result1 = tester.test_simple_oauth2_no_encryption()
    
    # Test 2: OAuth2 with encryption
    if result1 and 'response' in result1:
        print("\n📦 Response is encrypted, testing decryption...")
        encrypted_response = result1['response']
        decrypted = tester.decrypt_data(encrypted_response)
        if decrypted:
            print(f"✅ Decryption successful: {decrypted}")
        else:
            print("❌ Decryption failed")
    
    # Test 3: OAuth2 with full encryption flow
    result2 = tester.test_oauth2_with_encryption()
    
    # Test 4: Alternative formats
    result3 = tester.test_alternative_oauth2_formats()
    
    print("\n" + "=" * 60)
    print("🏁 Testing Complete")
    
    if any([result1, result2, result3]):
        print("✅ At least one method worked!")
    else:
        print("❌ All methods failed - contact Airpay support")
        print("\n💡 Recommendations:")
        print("1. Verify Client ID is complete (currently 6 chars)")
        print("2. Check if OAuth2 is enabled for your account")
        print("3. Confirm you're using the correct environment (prod/sandbox)")
        print("4. Contact Airpay support with these test results")

if __name__ == "__main__":
    main()