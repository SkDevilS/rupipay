#!/usr/bin/env python3
"""
Complete Airpay Integration Test
Tests the full flow: Order creation -> Status check -> Callback simulation
"""

import requests
import json
import hashlib
import base64
import time
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config

class AirpayCompleteTester:
    def __init__(self):
        self.base_url = Config.AIRPAY_BASE_URL
        self.merchant_id = Config.AIRPAY_MERCHANT_ID
        self.username = Config.AIRPAY_USERNAME
        self.password = Config.AIRPAY_PASSWORD
        self.encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
        
    def generate_key256(self):
        """Generate key256 = hash('SHA256', username."~:~".password)"""
        hash_string = f"{self.username}~:~{self.password}"
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    def encrypt_data(self, data):
        """Encrypt data according to Airpay documentation"""
        try:
            if isinstance(data, dict):
                json_data = json.dumps(data)
            else:
                json_data = data
            
            # Generate 8-byte IV and convert to hex
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            # Use encryption key for AES-256-CBC
            key = self.encryption_key[:32].encode('utf-8').ljust(32, b'\0')
            
            # Create 16-byte IV for AES (pad the 8-byte IV)
            aes_iv = iv_bytes + b'\x00' * 8
            
            # Encrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(json_data.encode('utf-8'), AES.block_size))
            
            # Return IV (hex) + base64(encrypted_data)
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            return iv_hex + encrypted_b64
            
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    def decrypt_data(self, encrypted_response):
        """Decrypt Airpay response"""
        try:
            # Extract IV (first 16 hex characters = 8 bytes)
            iv_hex = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            # Convert hex IV to bytes and pad to 16 bytes
            iv_bytes = bytes.fromhex(iv_hex)
            aes_iv = iv_bytes + b'\x00' * 8
            
            # Decode base64 encrypted data
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Use encryption key for AES-256-CBC
            key = self.encryption_key[:32].encode('utf-8').ljust(32, b'\0')
            
            # Decrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            
            # Parse JSON
            return json.loads(decrypted_data.decode('utf-8'))
            
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def generate_checksum(self, data):
        """Generate checksum according to Airpay documentation"""
        try:
            key256 = self.generate_key256()
            
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
            return hashlib.sha256(checksum_string.encode('utf-8')).hexdigest()
            
        except Exception as e:
            print(f"Checksum generation error: {e}")
            return ""
    
    def test_create_order(self):
        """Test order creation"""
        print("\n🧪 Step 1: Testing Order Creation")
        print("=" * 50)
        
        # Generate unique order ID
        order_id = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Prepare order data
        order_data = {
            'mercid': int(self.merchant_id),
            'orderid': order_id,
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
        print(f"Sending request to: {url}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=request_data,
                timeout=30
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                
                if 'data' in response_json:
                    decrypted = self.decrypt_data(response_json['data'])
                    if decrypted:
                        print(f"✅ Order created successfully!")
                        print(f"QR Code: {decrypted.get('QRCODE_STRING', 'Not found')[:50]}...")
                        return {
                            'order_id': order_id,
                            'response': decrypted
                        }
                    else:
                        print("❌ Failed to decrypt response")
                        return None
                else:
                    print(f"Plain response: {response_json}")
                    return {
                        'order_id': order_id,
                        'response': response_json
                    }
            else:
                print(f"❌ Request failed with status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def test_status_check(self, order_id):
        """Test status check API"""
        print(f"\n🧪 Step 2: Testing Status Check for {order_id}")
        print("=" * 50)
        
        url = f"{self.base_url}/airpay/order/verify.php"
        
        # Generate private key
        secret = "airpay_secret"  # Placeholder
        private_key_string = f"{secret}@{self.username}:|:{self.password}"
        private_key = hashlib.sha256(private_key_string.encode()).hexdigest()
        
        # Generate checksum
        current_date = datetime.now().strftime('%Y-%m-%d')
        key256 = self.generate_key256()
        alldata = f"{self.merchant_id}.{order_id}....pos.{current_date}"
        checksum_string = f"{key256}@{alldata}"
        checksum = hashlib.sha256(checksum_string.encode()).hexdigest()
        
        # Prepare request
        request_data = {
            'merchant_id': self.merchant_id,
            'merchant_txn_id': order_id,
            'private_key': private_key,
            'terminal_id': '12345678',
            'txn_type': 'pos',
            'checksum': checksum
        }
        
        print(f"Status check request: {request_data}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=request_data,
                timeout=30
            )
            
            print(f"Status Response: {response.status_code}")
            print(f"Status Response Text: {response.text}")
            
            if response.status_code == 200:
                # Try to parse XML
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response.text)
                    transaction = root.find('TRANSACTION')
                    if transaction is not None:
                        status = transaction.find('TRANSACTIONSTATUS')
                        message = transaction.find('MESSAGE')
                        print(f"✅ Status check successful!")
                        print(f"Status: {status.text if status is not None else 'Unknown'}")
                        print(f"Message: {message.text if message is not None else 'No message'}")
                        return True
                    else:
                        print("❌ Invalid XML response format")
                        return False
                except ET.ParseError:
                    print("❌ Failed to parse XML response")
                    return False
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Status check error: {e}")
            return False
    
    def simulate_callback(self, order_id):
        """Simulate an IPN callback"""
        print(f"\n🧪 Step 3: Simulating IPN Callback for {order_id}")
        print("=" * 50)
        
        # Simulate callback data
        callback_data = {
            'MERCID': int(self.merchant_id),
            'APTRANSACTIONID': '12345678',
            'AMOUNT': '100.00',
            'TRANSACTIONSTATUS': 200,
            'MESSAGE': 'Success',
            'TRANSACTIONID': order_id,
            'CUSTOMVAR': 'test_transaction',
            'CHMOD': 'upi',
            'BANKNAME': 'Test Bank',
            'CARDISSUER': 'UPI',
            'CUSTOMER': 'Test Customer',
            'CUSTOMEREMAIL': 'test@example.com',
            'CUSTOMERPHONE': '9876543210',
            'CURRENCYCODE': 356,
            'RISK': 0,
            'TRANSACTIONTYPE': 320,
            'TRANSACTIONPAYMENTSTATUS': 'SUCCESS',
            'CARD_NUMBER': '',
            'CARDTYPE': '',
            'TRANSACTIONTIME': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            'RRN': '123456789012345',
            'CUSTOMERVPA': 'test@upi'
        }
        
        # Generate hash for callback
        import zlib
        hash_string = f"{order_id}:12345678:100.00:200:Success:{self.merchant_id}:{self.username}:test@upi"
        callback_data['ap_SecureHash'] = str(zlib.crc32(hash_string.encode('utf-8')) & 0xffffffff)
        
        print(f"Simulated callback data: {json.dumps(callback_data, indent=2)}")
        
        # Send to our callback endpoint
        callback_url = "http://localhost:5000/api/callback/airpay/payin"
        
        try:
            response = requests.post(
                callback_url,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=callback_data,
                timeout=30
            )
            
            print(f"Callback Response: {response.status_code}")
            print(f"Callback Response Text: {response.text}")
            
            if response.status_code == 200:
                print("✅ Callback processed successfully!")
                return True
            else:
                print(f"❌ Callback failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Callback simulation error: {e}")
            return False

def main():
    """Main test function"""
    print("🚀 Airpay Complete Integration Test")
    print("=" * 60)
    
    tester = AirpayCompleteTester()
    
    # Verify configuration
    print(f"Configuration:")
    print(f"  Base URL: {tester.base_url}")
    print(f"  Merchant ID: {tester.merchant_id}")
    print(f"  Username: {tester.username}")
    print(f"  Encryption Key: {tester.encryption_key[:10]}..." if tester.encryption_key else "  ❌ Encryption Key: Not configured")
    
    if not tester.encryption_key:
        print("\n❌ AIRPAY_ENCRYPTION_KEY not configured in .env file")
        return
    
    # Test 1: Create Order
    order_result = tester.test_create_order()
    if not order_result:
        print("\n❌ Order creation failed - stopping tests")
        return
    
    order_id = order_result['order_id']
    
    # Wait a moment
    print("\n⏳ Waiting 5 seconds before status check...")
    time.sleep(5)
    
    # Test 2: Check Status
    status_result = tester.test_status_check(order_id)
    
    # Test 3: Simulate Callback
    callback_result = tester.simulate_callback(order_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Summary")
    print(f"✅ Order Creation: {'PASS' if order_result else 'FAIL'}")
    print(f"✅ Status Check: {'PASS' if status_result else 'FAIL'}")
    print(f"✅ Callback Simulation: {'PASS' if callback_result else 'FAIL'}")
    
    if order_result and status_result and callback_result:
        print("\n🎉 All tests passed! Airpay integration is working correctly.")
    else:
        print("\n⚠ Some tests failed. Check the logs above for details.")
        print("\n💡 Next steps:")
        print("1. Verify AIRPAY_ENCRYPTION_KEY is correct")
        print("2. Check merchant credentials with Airpay")
        print("3. Ensure API endpoints are accessible")
        print("4. Contact Airpay support if issues persist")

if __name__ == "__main__":
    main()