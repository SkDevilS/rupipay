"""
Airpay Payment Gateway Integration Service - V4 API
Complete implementation based on official Airpay documentation
Supports: OAuth2, AES encryption/decryption, QR generation, status check, callbacks
"""

import requests
import json
import os
import threading
import time
import hashlib
import base64
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config
from database import get_db_connection

class AirpayTruaxisService:
    def __init__(self, config_prefix='AIRPAY'):
        """
        Initialize Airpay Service with specified configuration
        
        Args:
            config_prefix: 'AIRPAY' for original Airpay, 'AIRPAY_GROSMART2' for Grosmart2
        """
        self.config_prefix = config_prefix
        if config_prefix == 'AIRPAY':
            self.pg_partner_name = 'Airpay'
            self.txn_prefix = 'AR_GROS_'
            self.order_prefix = 'AP_'
        elif config_prefix == 'AIRPAY_TRUAXIS':
            self.pg_partner_name = 'Airpay_Truaxis'
            self.txn_prefix = 'AP_TRU_'
            self.order_prefix = 'AP_TRU_'
        else:
            self.pg_partner_name = 'Airpay_Grosmart2'
            self.txn_prefix = 'AR_GROS2_'
            self.order_prefix = 'AP_GROS2_'
        
        # Load configuration based on prefix
        self.base_url = getattr(Config, f'{config_prefix}_BASE_URL')
        self.client_id = getattr(Config, f'{config_prefix}_CLIENT_ID')
        self.client_secret = getattr(Config, f'{config_prefix}_CLIENT_SECRET')
        self.merchant_id = getattr(Config, f'{config_prefix}_MERCHANT_ID')
        self.username = getattr(Config, f'{config_prefix}_USERNAME')
        self.password = getattr(Config, f'{config_prefix}_PASSWORD')
        self.secret = getattr(Config, f'{config_prefix}_SECRET')
        
        # Generate encryption key from username and password
        # Key = MD5(username~:~password)
        key_string = f"{self.username}~:~{self.password}"
        self.encryption_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        # New Truaxis specific keys from Qrgennew.php
        self.secret_key_md5 = hashlib.md5(self.secret.encode('utf-8')).hexdigest()
        self.key256 = hashlib.sha256(key_string.encode('utf-8')).hexdigest()
        
        # Generate privatekey for verify API
        # privatekey = SHA256(secret@username:|:password)
        privatekey_string = f"{self.secret}@{self.username}:|:{self.password}"
        self.privatekey = hashlib.sha256(privatekey_string.encode('utf-8')).hexdigest()
        
        print(f"🔑 {self.pg_partner_name} Service Initialized:")
        print(f"  Config Prefix: {config_prefix}")
        print(f"  PG Partner: {self.pg_partner_name}")
        print(f"  Merchant ID: {self.merchant_id}")
        print(f"  Username: {self.username}")
        print(f"  Encryption Key: {self.encryption_key}")
        print(f"  Private Key: {self.privatekey[:20]}...")
        
        # Token management
        self.access_token = None
        self.token_expiry = None
    
    def generate_access_token(self):
        """
        Step 1: Generate OAuth2 Access Token
        POST /airpay/pay/v4/api/oauth2
        
        According to PHP documentation:
        1. Create data array with credentials
        2. JSON encode and encrypt the data
        3. Generate checksum from data array (before encryption)
        4. Send: merchant_id, encdata, checksum as form-urlencoded
        """
        try:
            # Check if token is still valid
            if self.access_token and self.token_expiry:
                if datetime.now() < self.token_expiry:
                    print(f"✓ Using cached access token (expires in {(self.token_expiry - datetime.now()).seconds}s)")
                    return self.access_token
            
            print(f"🔑 Generating new Airpay access token...")
            
            url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
            
            # Step 1: Prepare data array (exactly as PHP does)
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'merchant_id': self.merchant_id,
                'grant_type': 'client_credentials'
            }
            
            print(f"📦 Data array: {data}")
            
            # Step 2: JSON encode and encrypt the data
            json_data = json.dumps(data)
            print(f"📝 JSON data: {json_data}")
            
            encdata = self.encrypt_oauth_data(json_data)
            if not encdata:
                print(f"❌ Failed to encrypt data")
                return None
            
            print(f"🔐 Encrypted data length: {len(encdata)}")
            
            # Step 3: Generate checksum from data array (before encryption)
            checksum = self.generate_checksum(data)
            if not checksum:
                print(f"❌ Failed to generate checksum")
                return None
            
            print(f"✓ Checksum: {checksum}")
            
            # Step 4: Prepare payload with merchant_id, encdata, checksum
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encdata,
                'checksum': checksum
            }
            
            print(f"🌐 Token request: {url}")
            print(f"📤 Sending payload with keys: {list(payload.keys())}")
            
            # Send as form-urlencoded (as PHP does with CURLOPT_POSTFIELDS)
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 Token response status: {response.status_code}")
            print(f"📥 Token response: {response.text[:200]}...")
            
            if response.status_code != 200:
                print(f"❌ Token generation failed: {response.text}")
                return None
            
            result = response.json()
            
            # Check if response is encrypted
            if 'response' in result:
                # Response is encrypted, decrypt it
                encrypted_response = result.get('response')
                decrypted_data = self.decrypt_oauth_data(encrypted_response)
                
                if not decrypted_data:
                    print(f"❌ Failed to decrypt token response")
                    return None
                
                result = decrypted_data
            
            # Check response format
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                
                # Check if data contains success flag (nested response)
                if isinstance(data, dict) and 'success' in data:
                    if not data.get('success'):
                        print(f"❌ OAuth2 error: {data.get('msg', 'Unknown error')}")
                        return None
                
                # Extract access token
                self.access_token = data.get('access_token')
                
                if not self.access_token:
                    print(f"❌ No access token in response: {result}")
                    return None
                
                expires_in = data.get('expires_in', 300)  # Default 5 minutes
                
                # Set expiry time (subtract 30 seconds for safety)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 30)
                
                print(f"✅ Access token generated successfully")
                print(f"  Token: {self.access_token[:20]}...")
                print(f"  Expires in: {expires_in} seconds")
                
                return self.access_token
            else:
                print(f"❌ Unexpected token response format: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def encrypt_oauth_data(self, data):
        """
        Original V4 encryption for OAuth endpoints
        """
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
                
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            key = self.encryption_key.encode('latin-1')
            aes_iv = iv_hex.encode('latin-1')
            
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            return iv_hex + encrypted_b64
        except Exception as e:
            print(f"❌ OAuth encryption error: {e}")
            return None

    def decrypt_oauth_data(self, encrypted_response):
        """
        Original V4 decryption for OAuth endpoints
        """
        try:
            iv_string = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            iv_bytes = iv_string.encode('latin-1')
            encrypted_data = base64.b64decode(encrypted_data_b64)
            key_bytes = self.encryption_key.encode('latin-1')
            
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            try:
                unpadded_data = unpad(decrypted_data, AES.block_size)
            except ValueError:
                padding_length = decrypted_data[-1]
                if isinstance(padding_length, str):
                    padding_length = ord(padding_length)
                if 1 <= padding_length <= 16:
                    unpadded_data = decrypted_data[:-padding_length]
                else:
                    raise ValueError(f"Invalid padding: {padding_length}")
            
            return json.loads(unpadded_data.decode('utf-8'))
        except Exception as e:
            print(f"❌ OAuth decryption error: {e}")
            return None

    def encrypt_data(self, data):
        """
        Encrypt request data using AES-256-CBC with MD5(secret)
        According to Qrgennew.php
        """
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
            
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            # The key is md5(secret)
            key = self.secret_key_md5.encode('latin-1')
            aes_iv = iv_hex.encode('latin-1')
            
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
            
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            return iv_hex + encrypted_b64
        except Exception as e:
            print(f"❌ Encryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_checksum(self, data_dict):
        """
        Generate SHA-256 checksum for request data
        According to Airpay documentation:
        1. Collect all key-value pairs
        2. Arrange in alphabetical order by keys
        3. Combine values into a single string
        4. Append current date in YYYY-MM-DD format
        5. Use SHA-256 to compute hash
        
        Args:
            data_dict: Dictionary of request parameters
            
        Returns:
            str: SHA-256 checksum hash
        """
        try:
            # Sort dictionary by keys alphabetically
            sorted_keys = sorted(data_dict.keys())
            
            # Combine values in sorted order
            checksum_data = ''
            for key in sorted_keys:
                value = str(data_dict[key])
                checksum_data += value
            
            # Append current date in YYYY-MM-DD format
            current_date = datetime.now().strftime('%Y-%m-%d')
            checksum_data += current_date
            
            # Generate SHA-256 hash
            checksum = hashlib.sha256(checksum_data.encode('utf-8')).hexdigest()
            
            print(f"📝 Checksum generated:")
            print(f"  Data string: {checksum_data}")
            print(f"  Checksum: {checksum}")
            
            return checksum
            
        except Exception as e:
            print(f"❌ Checksum generation error: {e}")
            return None
    
    def decrypt_data(self, encrypted_response):
        """
        Decrypt Airpay response using MD5(secret)
        """
        try:
            print(f"🔓 Decrypting Airpay Truaxis response...")
            print(f"  Encrypted data length: {len(encrypted_response)}")
            print(f"  Preview: {encrypted_response[:50]}...")
            
            iv_string = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            iv_bytes = iv_string.encode('latin-1')
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Key is md5(secret)
            key_bytes = self.secret_key_md5.encode('latin-1')
            
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            try:
                unpadded_data = unpad(decrypted_data, AES.block_size)
            except ValueError:
                padding_length = decrypted_data[-1]
                if isinstance(padding_length, str):
                    padding_length = ord(padding_length)
                
                if 1 <= padding_length <= 16:
                    unpadded_data = decrypted_data[:-padding_length]
                else:
                    raise ValueError(f"Invalid padding: {padding_length}")
            
            result = json.loads(unpadded_data.decode('utf-8'))
            
            print(f"✓ Decryption successful!")
            return result
            
        except Exception as e:
            print(f"❌ Decryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_qr(self, order_data):
        """
        Step 4: Generate QR Code for UPI payment
        POST /airpay/pay/v4/api/generateorder/?token=<access_token>
        
        order_data should contain:
        - orderid: Merchant generated transaction ID
        - amount: Amount with two decimals
        - tid: Terminal ID (optional)
        - buyer_email: Buyer email
        - buyer_phone: Buyer phone
        - mer_dom: Base64 encoded merchant domain
        - customvar: Custom variables
        - call_type: 'upiqr' for QR generation
        """
        try:
            print(f"📱 Generating Airpay QR code...")
            
            # Get access token
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            # Prepare request URL
            url = f"{self.base_url}/airpay/pay/v4/api/generateorder/?token={token}"
            
            print(f"📦 Order data to encrypt: {order_data}")
            
            # JSON encode and encrypt order data
            json_data = json.dumps(order_data)
            encrypted_data = self.encrypt_oauth_data(json_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt order data'}
            
            # Generate checksum from order data
            checksum = self.generate_checksum(order_data)
            if not checksum:
                return {'success': False, 'message': 'Failed to generate checksum'}
            
            # Prepare request payload (form-urlencoded like OAuth2)
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encrypted_data,
                'checksum': checksum
            }
            
            print(f"🌐 QR generation request: {url}")
            print(f"📤 Payload keys: {list(payload.keys())}")
            
            # Send request as form-urlencoded
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 QR response status: {response.status_code}")
            print(f"📥 QR response: {response.text[:200]}...")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            # Check if response is encrypted
            if 'response' in result:
                # Decrypt response
                decrypted = self.decrypt_oauth_data(result['response'])
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                
                result = decrypted
            
            print(f"✓ Decrypted result: {json.dumps(result, indent=2)}")
            
            # Check success
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                
                return {
                    'success': True,
                    'qrcode_string': data.get('qrcode_string'),
                    'ap_transactionid': data.get('ap_transactionid'),
                    'status': data.get('status')
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'QR generation failed'),
                    'details': result
                }
                
        except Exception as e:
            print(f"❌ QR generation error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def verify_payment(self, order_id=None, ap_transactionid=None, rrn=None):
        """
        Step 5: Verify payment status (Check Status)
        POST /airpay/pay/v4/api/verify/?token=<access_token>
        
        According to documentation:
        - Request: merchant_id, encdata (encrypted JSON with orderid/ap_transactionid/rrn), checksum
        - Response: Encrypted response with transaction details
        - At least one of: orderid, ap_transactionid, or rrn is required
        """
        try:
            print(f"🔍 Verifying payment status...")
            print(f"  Order ID: {order_id}")
            print(f"  AP Transaction ID: {ap_transactionid}")
            print(f"  RRN: {rrn}")
            
            # Get access token
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            # Prepare request URL
            url = f"{self.base_url}/airpay/pay/v4/api/verify/?token={token}"
            
            # Prepare verification data (at least one identifier required)
            verify_data = {}
            if order_id:
                verify_data['orderid'] = order_id
            if ap_transactionid:
                verify_data['ap_transactionid'] = ap_transactionid
            if rrn:
                verify_data['rrn'] = rrn
            
            if not verify_data:
                return {'success': False, 'message': 'At least one identifier required (orderid, ap_transactionid, or rrn)'}
            
            print(f"📦 Verify data: {verify_data}")
            
            # JSON encode and encrypt verification data
            json_data = json.dumps(verify_data)
            encrypted_data = self.encrypt_oauth_data(json_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt verification data'}
            
            # Generate checksum from verify_data
            checksum = self.generate_checksum(verify_data)
            if not checksum:
                return {'success': False, 'message': 'Failed to generate checksum'}
            
            # Prepare request payload (form-urlencoded with privatekey)
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encrypted_data,
                'checksum': checksum,
                'privatekey': self.privatekey  # Required for verify API
            }
            
            print(f"🌐 Verify request: {url}")
            print(f"📤 Payload keys: {list(payload.keys())}")
            print(f"📤 Private Key: {self.privatekey[:20]}...")
            
            # Send request as form-urlencoded
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 Verify response status: {response.status_code}")
            print(f"📥 Verify response: {response.text[:500]}...")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            # Check if response is encrypted (it should be according to docs)
            if 'response' in result:
                # Decrypt response
                encrypted_response = result.get('response')
                decrypted_data = self.decrypt_oauth_data(encrypted_response)
                
                if not decrypted_data:
                    return {'success': False, 'message': 'Failed to decrypt verification response'}
                
                # Check status inside decrypted payload
                data = decrypted_data
                status = data.get('TRANSACTIONSTATUS', data.get('status'))
                transaction_status = data.get('TRANSACTIONSTATUS', data.get('status'))
                
                result = decrypted_data
                print(f"✓ Decrypted verify result: {json.dumps(result, indent=2)}")
            
            # Check success (status_code: "200", status: "success")
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                
                # Map transaction_status to our status
                transaction_status = data.get('transaction_status')
                if transaction_status == 200:
                    status = 'SUCCESS'
                elif transaction_status in [400, 401, 402, 403, 405]:
                    status = 'FAILED'
                elif transaction_status == 211:
                    status = 'PROCESSING'
                elif transaction_status == 503:
                    status = 'NOT_FOUND'
                else:
                    status = 'PENDING'
                
                return {
                    'success': True,
                    'status': status,
                    'transaction_status': transaction_status,
                    'ap_transactionid': data.get('ap_transactionid'),
                    'orderid': data.get('orderid'),
                    'amount': data.get('amount'),
                    'rrn': data.get('rrn') or data.get('utr_no'),
                    'message': data.get('message'),
                    'transaction_payment_status': data.get('transaction_payment_status'),
                    'chmod': data.get('chmod'),
                    'bank_name': data.get('pgbank_name') or data.get('bank_name'),
                    'customer_vpa': data.get('customer_vpa'),
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Verification failed'),
                    'response_code': result.get('response_code'),
                    'details': result
                }
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """Calculate charges based on scheme"""
        try:
            conn = get_db_connection()
            if not conn:
                return None, None, None
            
            with conn.cursor() as cursor:
                # Get applicable charge
                cursor.execute("""
                    SELECT charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s 
                    AND service_type = %s
                    AND %s BETWEEN min_amount AND max_amount
                    ORDER BY min_amount DESC
                    LIMIT 1
                """, (scheme_id, service_type, amount))
                
                charge_config = cursor.fetchone()
                
                if not charge_config:
                    # No charges configured
                    return 0.00, amount, 'FIXED'
                
                charge_type = charge_config['charge_type']
                charge_value = float(charge_config['charge_value'])
                
                if charge_type == 'PERCENTAGE':
                    charge_amount = (amount * charge_value) / 100
                else:  # FIXED
                    charge_amount = charge_value
                
                net_amount = amount - charge_amount
                
                return round(charge_amount, 2), round(net_amount, 2), charge_type
                
        except Exception as e:
            print(f"Calculate charges error: {e}")
            return None, None, None
        finally:
            if conn:
                conn.close()
    
    def create_payin_order(self, merchant_id, order_data):
        """
        Create payin order via Airpay using the correct generateOrder API
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_mobile
        - payee_email
        - callbackurl (optional)
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get merchant details
                cursor.execute("""
                    SELECT merchant_id, full_name, email, scheme_id, is_active
                    FROM merchants
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                merchant = cursor.fetchone()
                
                if not merchant:
                    return {'success': False, 'message': 'Merchant not found'}
                
                if not merchant['is_active']:
                    return {'success': False, 'message': 'Merchant account is inactive'}
                
                # Validate amount
                amount = float(order_data.get('amount', 0))
                if amount <= 0:
                    return {'success': False, 'message': 'Invalid amount'}
                
                # Calculate charges
                charge_amount, net_amount, charge_type = self.calculate_charges(
                    amount, merchant['scheme_id']
                )
                
                if charge_amount is None:
                    return {'success': False, 'message': 'Failed to calculate charges'}
                
                # Generate unique order ID for Airpay
                airpay_order_id = f"{self.order_prefix}{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Create internal transaction ID
                txn_id = f"{self.txn_prefix}{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Prepare Airpay order data according to new documentation
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                
                # Extract callback URL from order_data
                callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
                
                if not callback_url:
                    # Use default internal callback URL
                    base_url = os.getenv('BACKEND_URL', 'https://api.rupipay.shop')
                    if self.config_prefix == 'AIRPAY':
                        callback_suffix = 'payin'
                    elif self.config_prefix == 'AIRPAY_TRUAXIS':
                        callback_suffix = 'truaxis/payin'
                    else:
                        callback_suffix = 'grosmart2/payin'
                    callback_url = f"{base_url}/api/callback/airpay/{callback_suffix}"
                    print(f"⚠ No callback URL provided, using default: {callback_url}")
                
                # Prepare merchant domain (base64 encoded)
                # Using API domain since it's already whitelisted with Airpay
                frontend_url = 'https://api.rupipay.shop'
                mer_dom = base64.b64encode(frontend_url.encode()).decode()
                
                # Validate required fields
                if not phone or len(phone) < 10:
                    return {'success': False, 'message': 'Valid mobile number is required (10 digits)'}
                
                if not email or '@' not in email:
                    return {'success': False, 'message': 'Valid email address is required'}
                
                # Prepare order payload for Airpay V4 API
                airpay_payload = {
                    'orderid': airpay_order_id,
                    'amount': f"{amount:.2f}",
                    'tid': '12345678',  # Terminal ID
                    'buyer_email': email,
                    'buyer_phone': phone,
                    'mer_dom': mer_dom,
                    'customvar': f"merchant_id={merchant_id}|txn_id={txn_id}|callback_url={callback_url}",
                    'call_type': 'upiqr'
                }
                
                print(f"Creating Airpay order: {airpay_payload}")
                
                # Generate QR code using V4 API
                qr_result = self.generate_qr(airpay_payload)
                
                if not qr_result.get('success'):
                    return qr_result
                
                # Extract QR data
                qr_string = qr_result.get('qrcode_string')
                airpay_txn_id = qr_result.get('ap_transactionid')
                
                # Insert transaction record
                cursor.execute("""
                    INSERT INTO payin_transactions (
                        txn_id, merchant_id, order_id, amount, charge_amount, 
                        charge_type, net_amount, payee_name, payee_email, 
                        payee_mobile, product_info, status, pg_partner,
                        pg_txn_id, callback_url, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (
                    txn_id, merchant_id, airpay_order_id, amount,
                    charge_amount, charge_type, net_amount,
                    f"{firstname} {lastname}".strip(), email, phone, 
                    order_data.get('productinfo', 'Payment'),
                    'INITIATED', self.pg_partner_name, airpay_txn_id,
                    callback_url
                ))
                
                print(f"✓ Transaction created:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - Order ID: {airpay_order_id}")
                print(f"  - Merchant Order ID: {order_data.get('orderid')}")
                print(f"  - Airpay Txn ID: {airpay_txn_id}")
                print(f"  - Callback URL: {callback_url}")
                
                conn.commit()
                
                # Schedule automatic status check after 60 seconds
                self.auto_check_status_after_delay(airpay_order_id, delay_seconds=60)
                print(f"✓ Scheduled automatic status check for {airpay_order_id} in 60 seconds")
                
                # For Airpay and Airpay_Grosmart2, copy the UPI link to all payment parameters
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': airpay_order_id,
                    'merchant_order_id': order_data.get('orderid'),
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'payment_params': {},
                    'qr_string': qr_string,
                    'qr_code_url': qr_string,
                    'upi_link': qr_string,
                    'payment_link': qr_string,
                    'intent_url': qr_string,
                    'tiny_url': '',
                    'expires_in': 0,
                    'vpa': '',
                    'airpay_txn_id': airpay_txn_id,
                    'pg_partner': self.pg_partner_name.upper()
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    

    def check_payment_status(self, identifier):
        """
        Check payment status on Airpay using V4 API
        
        Args:
            identifier: Can be order_id or Airpay transaction ID
        
        Returns:
            dict: Status information
        """
        try:
            print(f"Checking Airpay payin status for identifier: {identifier}")
            
            # Use the V4 verify_payment method
            result = self.verify_payment(order_id=identifier)
            
            if result.get('success'):
                return {
                    'success': True,
                    'status': result.get('status'),
                    'utr': result.get('rrn'),
                    'txnId': result.get('ap_transactionid'),
                    'message': result.get('message')
                }
            else:
                return result
            
        except Exception as e:
            print(f"Check payment status error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}
    
    def auto_check_status_after_delay(self, order_id, delay_seconds=60):
        """
        Automatically check payment status after a delay
        This ensures status gets updated even if callback fails
        """
        def check_status_task():
            try:
                print(f"[Auto Status Check] Waiting {delay_seconds} seconds before checking {order_id}...")
                time.sleep(delay_seconds)
                
                print(f"[Auto Status Check] Checking status for {order_id}...")
                
                # Get transaction from database
                conn = get_db_connection()
                if not conn:
                    print(f"[Auto Status Check] Database connection failed")
                    return
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT txn_id, order_id, merchant_id, status, pg_txn_id, net_amount, charge_amount
                            FROM payin_transactions
                            WHERE order_id = %s AND pg_partner = 'Airpay'
                        """, (order_id,))
                        
                        txn = cursor.fetchone()
                        
                        if not txn:
                            print(f"[Auto Status Check] Transaction not found: {order_id}")
                            return
                        
                        # Only check if still pending
                        if txn['status'] not in ['INITIATED', 'PENDING']:
                            print(f"[Auto Status Check] Transaction already {txn['status']}, skipping")
                            return
                        
                        print(f"[Auto Status Check] Checking Airpay with order_id: {order_id}")
                        
                        # Check status from Airpay
                        status_result = self.check_payment_status(order_id)
                        
                        if not status_result.get('success'):
                            print(f"[Auto Status Check] Status check failed: {status_result.get('message')}")
                            return
                        
                        airpay_status = status_result.get('status', '').upper()
                        print(f"[Auto Status Check] Airpay status: {airpay_status}")
                        
                        # Update if status changed to SUCCESS
                        if airpay_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
                            print(f"[Auto Status Check] Updating {txn['txn_id']} to SUCCESS")
                            
                            # Update transaction
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'SUCCESS',
                                    bank_ref_no = %s,
                                    pg_txn_id = %s,
                                    payment_mode = 'UPI',
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('utr'), status_result.get('txnId'), txn['txn_id']))
                            
                            # Check if wallet already credited (idempotency)
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                            """, (txn['txn_id'],))
                            
                            wallet_already_credited = cursor.fetchone()['count'] > 0
                            
                            if not wallet_already_credited:
                                # Credit merchant unsettled wallet
                                from wallet_service import wallet_service as wallet_svc
                                wallet_result = wallet_svc.credit_unsettled_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=float(txn['net_amount']),
                                    description=f"PayIn received (Auto status check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                if wallet_result['success']:
                                    print(f"[Auto Status Check] ✓ Merchant wallet credited: ₹{txn['net_amount']}")
                                else:
                                    print(f"[Auto Status Check] ✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                                
                                # Credit admin unsettled wallet
                                admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                                    admin_id='admin',
                                    amount=float(txn['charge_amount']),
                                    description=f"PayIn charge (Auto status check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                if admin_wallet_result['success']:
                                    print(f"[Auto Status Check] ✓ Admin wallet credited: ₹{txn['charge_amount']}")
                                else:
                                    print(f"[Auto Status Check] ✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                            else:
                                print(f"[Auto Status Check] ⚠ Wallet already credited, skipping")
                            
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Successfully updated {txn['txn_id']} to SUCCESS")
                        
                        elif airpay_status == 'FAILED' and txn['status'] != 'FAILED':
                            print(f"[Auto Status Check] Updating {txn['txn_id']} to FAILED")
                            
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'FAILED',
                                    pg_txn_id = %s,
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('txnId'), txn['txn_id']))
                            
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Updated {txn['txn_id']} to FAILED")
                        else:
                            print(f"[Auto Status Check] Status unchanged: {airpay_status}")
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                print(f"[Auto Status Check] Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Start background thread
        thread = threading.Thread(target=check_status_task, daemon=True)
        thread.start()
        print(f"[Auto Status Check] Scheduled status check for {order_id} in {delay_seconds} seconds")

# Create singleton instances
airpay_truaxis_service = AirpayTruaxisService(config_prefix='AIRPAY_TRUAXIS')