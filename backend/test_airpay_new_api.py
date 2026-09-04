#!/usr/bin/env python3
"""
Test Airpay New API Implementation
Based on the correct Airpay documentation provided by the team
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

class AirpayNewAPITester:
    def __init__(self):
        self.base_url = Config.AIRPAY_BASE_URL
        self.merchant_id = Config.AIRPAY_MERCHANT_ID
        self.username = Config.AIRPAY_USERNAME
        self.password = Config.AIRPAY_PASSWORD
        
    def generate_key256(self):
        """Generate key256 = hash('SHA256', username."~:~".password)"""
        try:
            hash_string = f"{self.username}~:~{self.password}"
            return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        except Exception as e:
            print(f"Key256 generation error: {e}")
            return None
    
    def encrypt_data(self, data):
        """
        Encrypt according to Airpay documentation:
        IV = bin2hex(openssl_random_pseudo_bytes(8));
        raw = openssl_encrypt(json_data, AES-256-CBC, EncryptionKey, options=OPENSSL_RAW_DATA, IV);
        encData = IV.base64_encode(raw);
        """
        try:
            # Convert data to JSON string
            if isinstance(data, dict):
                json_data = json.dumps(data)
            else:
                json_data = data
            
            # Generate 8-byte IV and convert to hex
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            # Get encryption key (should be provided by Airpay)
            encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
            if not encryption_key:
                print("❌ AIRPAY_ENCRYPTION_KEY not found in config")
                return None
            
            # Use encryption key for AES-256-CBC (need 32 bytes)
            key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
            
            # Create 16-byte IV for AES (pad the 8-byte IV)
            aes_iv = iv_bytes + b'\x00' * 8
            
            # Encrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(json_data.encode('utf-8'), AES.block_size))
            
            # Return IV (hex) + base64(encrypted_data)
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            result = iv_hex + encrypted_b64
            
            print(f"Encryption:")
            print(f"  IV hex: {iv_hex}")
            print(f"  Encrypted B64 length: {len(encrypted_b64)}")
            print(f"  Total length: {len(result)}")
            
            return result
            
        except Exception as e:
            print(f"Encryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def decrypt_data(self, encrypted_response):
        """
        Decrypt according to Airpay documentation:
        IV = substr(encryptedData, 0, 16);
        data = substr(encryptedData, 16);
        DecryptedData = openssl_decrypt(base64_decode(data), AES-256-CBC, EncryptionKey, options=OPENSSL_RAW_DATA, IV);
        """
        try:
            # Extract IV (first 16 hex characters = 8 bytes)
            iv_hex = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            print(f"Decryption:")
            print(f"  IV hex: {iv_hex}")
            print(f"  Encrypted data length: {len(encrypted_data_b64)}")
            
            # Convert hex IV to bytes and pad to 16 bytes
            iv_bytes = bytes.fromhex(iv_hex)
            aes_iv = iv_bytes + b'\x00' * 8
            
            # Decode base64 encrypted data
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Get encryption key
            encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
            if not encryption_key:
                print("❌ AIRPAY_ENCRYPTION_KEY not found in config")
                return None
            
            # Use encryption key for AES-256-CBC
            key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
            
            # Decrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            # Parse JSON
            result = json.loads(decrypted_data.decode('utf-8'))
            print(f"  Decrypted: {result}")
            return result
            
        except Exception as e:
            print(f"Decryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_checksum(self, data):
        """
        Generate checksum according to Airpay documentation:
        key256 = hash('SHA256', username."~:~".password);
        alldata = mercid.orderid.amount.tid.buyerPhone.buyerEmail.mer_dom.customvar.call_type;
        checksum = hash('SHA256', key256.'@'.alldata.date('Y-m-d'));
        """
        try:
            # Generate key256
            key256 = self.generate_key256()
            if not key256:
                return ""
            
            # Build alldata string in exact order
            alldata = (
                str(data.get('mercid', '')) +
                str(data.get('orderid', '')) +
                str(data.get('amount', '')) +
                str(data.get('tid', '')) +
                str(data.get('buyerPhone', '')) +
                str(data.get('buyerEmail', '')) +
                str(data.get('mer_dom', '')) +
                str(data.get('customvar', '')) +
                str(data.get('call_type', ''))
            )
            
            # Get current date
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Generate checksum
            checksum_string = f"{key256}@{alldata}{current_date}"
            checksum = hashlib.sha256(checksum_string.encode('utf-8')).hexdigest()
            
            print(f"Checksum generation:")
            print(f"  Key256: {key256[:20]}...")
            print(f"  Alldata: {alldata}")
            print(f"  Date: {current_date}")
            print(f"  Checksum: {checksum}")
            
            return checksum
            
        except Exception as e:
            print(f"Checksum generation error: {e}")
            return ""
    
    def test_generate_order(self):
        """Test the generateOrder API"""
        print("\n🧪 Testing Airpay generateOrder API")
        print("=" * 50)
        
        # Prepare test order data
        order_data = {
            'mercid': int(self.merchant_id),
            'orderid': f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount': '100.00',
            'tid': '12345678',
            'buyerPhone': '9876543210',
            'buyerEmail': 'test@example.com',
            'mer_dom': base64.b64encode('https://client.moneyone.co.in'.encode()).decode(),
            'customvar': 'test_transaction',
            'call_type': 'upiqr'
        }
        
        print(f"Order data: {order_data}")
        
        # Generate checksum
        checksum = self.generate_checksum(order_data)
        if not checksum:
            print("❌ Failed to generate checksum")
            return None
        
        # Encrypt data
        encrypted_data = self.encrypt_data(order_data)
        if not encrypted_data:
            print("❌ Failed to encrypt data")
            return None
        
        # Prepare request
        request_data = {
            'encData': encrypted_data,
            'checksum': checksum,
            'mercid': int(self.merchant_id)
        }
        
        # Make API call
        url = f"{self.base_url}/airpay/api/generateOrder"
        print(f"\nSending request to: {url}")
        print(f"Request keys: {list(request_data.keys())}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=request_data,
                timeout=30
            )
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                
                if 'data' in response_json:
                    print("\n📦 Response is encrypted, decrypting...")
                    decrypted = self.decrypt_data(response_json['data'])
                    if decrypted:
                        print(f"✅ Decrypted response: {decrypted}")
                        return decrypted
                    else:
                        print("❌ Failed to decrypt response")
                        return None
                else:
                    print(f"📄 Plain response: {response_json}")
                    return response_json
            else:
                print(f"❌ Request failed with status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None

def main():
    """Main test function"""
    print("🚀 Airpay New API Testing")
    print("=" * 60)
    
    tester = AirpayNewAPITester()
    
    print(f"Configuration:")
    print(f"  Base URL: {tester.base_url}")
    print(f"  Merchant ID: {tester.merchant_id}")
    print(f"  Username: {tester.username}")
    
    # Test key generation
    key256 = tester.generate_key256()
    if key256:
        print(f"  Key256: {key256[:20]}...")
    else:
        print("  ❌ Failed to generate key256")
        return
    
    # Test encryption key
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    if encryption_key:
        print(f"  Encryption Key: {encryption_key[:10]}...")
    else:
        print("  ❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    # Test generateOrder API
    result = tester.test_generate_order()
    
    print("\n" + "=" * 60)
    if result:
        print("✅ Test completed successfully!")
        if result.get('QRCODE_STRING'):
            print(f"🎯 QR Code received: {result['QRCODE_STRING'][:50]}...")
        if result.get('status') == 200:
            print("🎉 Order creation successful!")
        else:
            print(f"⚠ Order status: {result.get('status')}")
    else:
        print("❌ Test failed")
        print("\n💡 Troubleshooting:")
        print("1. Verify AIRPAY_ENCRYPTION_KEY is correct")
        print("2. Check merchant credentials")
        print("3. Confirm API endpoint URL")
        print("4. Contact Airpay support if issues persist")

if __name__ == "__main__":
    main()