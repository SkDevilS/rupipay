"""
VIYONAPAY Payment Gateway Integration Service
Handles payin transactions through VIYONAPAY with end-to-end encryption

Security Features:
- RSA-OAEP for session key encryption
- AES-GCM for data encryption/decryption
- Digital signatures for request integrity
- JWT token management (30-minute expiry)
- Singleton pattern with shared token cache to prevent token invalidation
"""

import requests
import json
import os
import base64
import hashlib
import uuid
import threading
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA as CryptoRSA
from config import Config
from database import get_db_connection

class ViyonapayService:
    """
    Service for VIYONAPAY integration with support for multiple configurations.
    
    Supports two configurations:
    - VIYONAPAY (Truaxis) - Original credentials
    - VIYONAPAY_BARRINGER - Barringer credentials
    
    IMPORTANT: Viyonapay tokens are valid for 30 minutes, but generating a new token
    invalidates ALL previous tokens immediately for that configuration.
    """
    
    # Class-level token storage for each configuration
    _tokens = {
        'TRUAXIS': {'access_token': None, 'token_expiry': None},
        'BARRINGER': {'access_token': None, 'token_expiry': None}
    }
    _token_lock = threading.Lock()
    
    def __init__(self, config_type='TRUAXIS'):
        """
        Initialize service with specific configuration
        
        Args:
            config_type: 'TRUAXIS' or 'BARRINGER'
        """
        self.config_type = config_type.upper()
        
        if self.config_type == 'BARRINGER':
            # Use Barringer credentials
            self.base_url = Config.VIYONAPAY_BASE_URL  # Same base URL
            self.client_id = Config.VIYONAPAY_BARRINGER_CLIENT_ID
            self.client_secret = Config.VIYONAPAY_BARRINGER_CLIENT_SECRET
            self.api_key = Config.VIYONAPAY_BARRINGER_API_KEY
            self.vpa = Config.VIYONAPAY_BARRINGER_VPA
            
            # Load Barringer RSA keys
            self.client_private_key = self._load_private_key(Config.VIYONAPAY_BARRINGER_CLIENT_PRIVATE_KEY_PATH)
            self.server_public_key = self._load_public_key(Config.VIYONAPAY_BARRINGER_SERVER_PUBLIC_KEY_PATH)
            
            print(f"🔐 VIYONAPAY Service Initialized (BARRINGER)")
        else:
            # Use Truaxis credentials (original)
            self.config_type = 'TRUAXIS'
            self.base_url = Config.VIYONAPAY_BASE_URL  # https://core.viyonapay.com
            self.client_id = Config.VIYONAPAY_CLIENT_ID
            self.client_secret = Config.VIYONAPAY_CLIENT_SECRET
            self.api_key = Config.VIYONAPAY_API_KEY
            self.vpa = Config.VIYONAPAY_VPA
            
            # Load Truaxis RSA keys
            self.client_private_key = self._load_private_key(Config.VIYONAPAY_CLIENT_PRIVATE_KEY_PATH)
            self.server_public_key = self._load_public_key(Config.VIYONAPAY_SERVER_PUBLIC_KEY_PATH)
            
            print(f"🔐 VIYONAPAY Service Initialized (TRUAXIS)")
        
        print(f"  Base URL: {self.base_url}")
        print(f"  Client ID: {self.client_id}")
        print(f"  VPA: {self.vpa}")
    
    def _load_private_key(self, key_path):
        """Load client's RSA private key from file (for signing with PyCryptodome)"""
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            return CryptoRSA.import_key(key_data)
        except Exception as e:
            print(f"❌ Failed to load client private key: {e}")
            return None
    
    def _load_public_key(self, key_path):
        """Load server's RSA public key from file (for encryption with cryptography)"""
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            return serialization.load_pem_public_key(key_data, backend=default_backend())
        except Exception as e:
            print(f"❌ Failed to load server public key: {e}")
            return None
    
    def _generate_session_key(self):
        """Generate random 256-bit AES session key"""
        return os.urandom(32)  # 32 bytes = 256 bits
    
    def _encrypt_session_key(self, session_key):
        """Encrypt session key using server's RSA public key with RSA-OAEP"""
        try:
            encrypted_key = self.server_public_key.encrypt(
                session_key,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return base64.b64encode(encrypted_key).decode('utf-8')
        except Exception as e:
            print(f"❌ Session key encryption error: {e}")
            return None
    
    def _encrypt_data(self, data_dict, session_key, aad_dict):
        """
        Encrypt data using AES-GCM with session key and AAD
        
        Args:
            data_dict: Dictionary to encrypt
            session_key: AES session key (32 bytes)
            aad_dict: Additional Authenticated Data dictionary
        
        Returns:
            Base64-encoded encrypted data
        """
        try:
            # Convert data to JSON (no spaces) - MUST match test script exactly
            plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
            
            # Convert AAD to canonical JSON (sorted keys, no spaces) - MUST match test script exactly
            aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
            aad_bytes = aad_json.encode('utf-8')
            
            # Generate random 12-byte nonce for AES-GCM
            nonce = os.urandom(12)
            
            # Create AES-GCM cipher using cryptography library (SAME as test script)
            aesgcm = AESGCM(session_key)
            
            # Encrypt data (this includes the tag automatically)
            ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
            
            # Combine: nonce + ciphertext (ciphertext already includes tag)
            encrypted_data = nonce + ciphertext
            
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            print(f"❌ Data encryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _decrypt_data(self, encrypted_b64, session_key, aad_dict):
        """
        Decrypt data using AES-GCM with session key and AAD
        
        Args:
            encrypted_b64: Base64-encoded encrypted data
            session_key: AES session key (32 bytes)
            aad_dict: Additional Authenticated Data dictionary
        
        Returns:
            Decrypted dictionary
        """
        try:
            # Decode base64
            encrypted_data = base64.b64decode(encrypted_b64)
            
            # Extract components (nonce is first 12 bytes, rest is ciphertext+tag)
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Convert AAD to canonical JSON (sorted keys, no spaces)
            aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
            aad_bytes = aad_json.encode('utf-8')
            
            # Create AES-GCM cipher using cryptography library
            aesgcm = AESGCM(session_key)
            
            # Decrypt and verify (automatically verifies tag)
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
            
            return json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            print(f"❌ Data decryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _sign_request(self, request_body):
        """
        Generate digital signature of request body using client's private key
        
        Args:
            request_body: Dictionary to sign
        
        Returns:
            Base64-encoded signature
        """
        try:
            # Convert to canonical JSON
            json_data = json.dumps(request_body, separators=(',', ':'), sort_keys=True)
            
            # Create SHA-256 hash
            hash_obj = SHA256.new(json_data.encode('utf-8'))
            
            # Sign with private key
            signature = pkcs1_15.new(self.client_private_key).sign(hash_obj)
            
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"❌ Signature generation error: {e}")
            return None
    
    def generate_access_token(self, force_refresh=False):
        """
        Generate JWT access token from VIYONAPAY
        POST /v1/auth/token
        
        CRITICAL: Viyonapay tokens are valid for 30 minutes, but generating a new token
        invalidates ALL previous tokens immediately for that configuration. This method uses 
        thread-safe locking to ensure only ONE token generation happens at a time per configuration.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
        
        Returns:
            Access token string or None
        """
        try:
            # Thread-safe token check and generation
            with self._token_lock:
                # Get token storage for this configuration
                token_data = self._tokens[self.config_type]
                
                # Check if token is still valid (unless force refresh)
                if not force_refresh and token_data['access_token'] and token_data['token_expiry']:
                    if datetime.now() < token_data['token_expiry']:
                        remaining_seconds = (token_data['token_expiry'] - datetime.now()).seconds
                        print(f"✓ Using cached access token for {self.config_type} (expires in {remaining_seconds}s)")
                        return token_data['access_token']
                
                print(f"🔑 Generating new VIYONAPAY access token for {self.config_type} (this will invalidate any existing tokens for this config)...")
            
                url = f"{self.base_url}/v1/auth/token"
                
                # Generate unique request ID
                request_id = str(uuid.uuid4())
                timestamp = int(datetime.now().timestamp())
                
                # Generate session key
                session_key = self._generate_session_key()
                
                # Encrypt session key with server's public key
                encrypted_session_key = self._encrypt_session_key(session_key)
                if not encrypted_session_key:
                    return None
                
                # Prepare data to encrypt
                data_to_encrypt = {
                    'client_secret': self.client_secret,
                    'scopes': ['PAYMENT_GATEWAY']
                }
                
                # Prepare AAD
                aad = {
                    'client_id': self.client_id,
                    'request_id': request_id,
                    'timestamp': timestamp
                }
                
                # Encrypt data
                encrypted_data = self._encrypt_data(data_to_encrypt, session_key, aad)
                if not encrypted_data:
                    return None
                
                # Prepare request body
                request_body = {
                    'client_id': self.client_id,
                    'request_id': request_id,
                    'timestamp': timestamp,
                    'encrypted_data': encrypted_data,
                    'encrypted_session_key': encrypted_session_key
                }
                
                # Generate signature
                signature = self._sign_request(request_body)
                if not signature:
                    return None
                
                # Prepare headers
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-SIGNATURE': signature,
                    'X-API-TYPE': 'PAYMENT_GATEWAY',
                    'X-Request-ID': request_id
                }
                
                print(f"📤 Token request to: {url}")
                
                # Send request with single attempt only (no retries)
                try:
                    # Use tuple for (connection_timeout, read_timeout)
                    response = requests.post(url, json=request_body, headers=headers, timeout=30)
                except requests.exceptions.Timeout as timeout_error:
                    print(f"❌ Request timeout: {timeout_error}")
                    return None
                except Exception as e:
                    print(f"❌ Request error: {e}")
                    return None
                
                print(f"📥 Token response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Token generation failed: {response.text}")
                    return None
                
                result = response.json()
                
                # Check if response is encrypted
                if result.get('response_status') == 1 and 'encrypted_data' in result:
                    # Decrypt response
                    decrypted = self._decrypt_data(result['encrypted_data'], session_key, aad)
                    if not decrypted:
                        return None
                    
                    # Extract access token and store for this configuration
                    token_data['access_token'] = decrypted.get('data', {}).get('access_token')
                    expires_in = decrypted.get('data', {}).get('expires_in', 1800)
                    
                    # Set expiry time (subtract 60 seconds for safety)
                    token_data['token_expiry'] = datetime.now() + timedelta(seconds=expires_in - 60)
                    
                    print(f"✅ Access token generated successfully for {self.config_type}")
                    print(f"  Token: {token_data['access_token'][:20]}...")
                    print(f"  Expires in: {expires_in} seconds")
                    print(f"  ⚠️  All previous tokens for {self.config_type} are now INVALID")
                    
                    return token_data['access_token']
                    return self._access_token
                else:
                    print(f"❌ Unexpected token response: {result}")
                    return None
                
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_charges(self, amount, scheme_id):
        """Calculate charges based on scheme"""
        try:
            conn = get_db_connection()
            if not conn:
                return None, None, None
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s 
                    AND service_type = 'PAYIN'
                    AND %s BETWEEN min_amount AND max_amount
                    ORDER BY min_amount DESC
                    LIMIT 1
                """, (scheme_id, amount))
                
                charge_config = cursor.fetchone()
                
                if not charge_config:
                    return 0.00, amount, 'FIXED'
                
                charge_type = charge_config['charge_type']
                charge_value = float(charge_config['charge_value'])
                
                if charge_type == 'PERCENTAGE':
                    charge_amount = (amount * charge_value) / 100
                else:
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
        Create payment intent via VIYONAPAY
        POST /v1/payin/create_intent
        
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_mobile
        - payee_email
        - payinType (optional, defaults to ['paymentGateway'])
        - vpa (required if payinType is ['upiMasterMerchant'])
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
                
                # Generate transaction ID based on config type
                if self.config_type == 'BARRINGER':
                    txn_id = f"VY_BAR_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                else:  # TRUAXIS
                    txn_id = f"VY_TRU_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Get access token
                token = self.generate_access_token()
                if not token:
                    return {'success': False, 'message': 'Failed to generate access token'}
                
                # Prepare customer details
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                customer_name = f"{firstname} {lastname}".strip()
                customer_email = order_data.get('payee_email', '')
                customer_phone = order_data.get('payee_mobile', '')
                
                # Validate required fields
                if not customer_phone or len(customer_phone) != 10:
                    return {'success': False, 'message': 'Valid 10-digit mobile number is required'}
                
                if not customer_email or '@' not in customer_email:
                    return {'success': False, 'message': 'Valid email address is required'}
                
                # Generate unique request ID
                request_id = str(uuid.uuid4())
                timestamp = int(datetime.now().timestamp())
                
                # Generate session key
                session_key = self._generate_session_key()
                
                # Encrypt session key
                encrypted_session_key = self._encrypt_session_key(session_key)
                if not encrypted_session_key:
                    return {'success': False, 'message': 'Failed to encrypt session key'}
                
                # Prepare payment intent data
                # Use upiMasterMerchant mode with VPA
                intent_data = {
                    'orderId': order_data.get('orderid'),
                    'amount': str(amount),
                    'currency': 'INR',
                    'name': customer_name,
                    'email': customer_email,
                    'phone': customer_phone,
                    'payinType': 'upiMasterMerchant',
                    'note': order_data.get('productinfo', 'Payment'),
                    'vpa': self.vpa
                }
                
                # Prepare AAD
                aad = {
                    'client_id': self.client_id,
                    'request_id': request_id,
                    'timestamp': timestamp
                }
                
                # Encrypt intent data
                encrypted_data = self._encrypt_data(intent_data, session_key, aad)
                if not encrypted_data:
                    return {'success': False, 'message': 'Failed to encrypt payment data'}
                
                # Prepare request body
                request_body = {
                    'client_id': self.client_id,
                    'request_id': request_id,
                    'timestamp': timestamp,
                    'encrypted_data': encrypted_data,
                    'encrypted_session_key': encrypted_session_key
                }
                
                # Generate signature
                signature = self._sign_request(request_body)
                if not signature:
                    return {'success': False, 'message': 'Failed to generate signature'}
                
                # Prepare headers
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-API-KEY': self.api_key,
                    'Authorization': f'Bearer {token}',
                    'X-SIGNATURE': signature,
                    'X-Request-ID': request_id
                }
                
                url = f"{self.base_url}/v1/payin/create_intent"
                
                print(f"📤 Creating payment intent: {url}")
                print(f"📦 Order ID: {order_data.get('orderid')}")
                print(f"💰 Amount: ₹{amount}")
                
                # Send request with single attempt only (no retries)
                max_retries = 0  # Changed from 1 to 0 - no retries
                for attempt in range(max_retries + 1):
                    try:
                        response = requests.post(url, json=request_body, headers=headers, timeout=30)
                    except requests.exceptions.Timeout as timeout_error:
                        print(f"❌ Request timeout: {timeout_error}")
                        return {'success': False, 'message': 'Request timeout - ViyonaPay server not responding'}
                    except Exception as e:
                        print(f"❌ Request error: {e}")
                        return {'success': False, 'message': f'Network error: {str(e)}'}
                    
                    print(f"📥 Response status: {response.status_code}")
                    
                    # No retry logic - just break after first attempt
                    break
                
                # Parse response (ViyonaPay returns encrypted errors even with 400 status)
                try:
                    result = response.json()
                except:
                    print(f"❌ Failed to parse response: {response.text}")
                    return {'success': False, 'message': f'API error: {response.text}'}
                
                # Check for error response (responseStatus: 0 means error, 1 means success)
                # But ViyonaPay may return 400 status with encrypted error data
                if response.status_code != 200 or result.get('responseStatus') == 0 or result.get('response_status') == 0:
                    # Try to decrypt error if encrypted_data is present
                    if 'encrypted_data' in result:
                        decrypted = self._decrypt_data(result['encrypted_data'], session_key, aad)
                        if decrypted:
                            error_msg = decrypted.get('result', decrypted.get('message', 'Payment intent creation failed'))
                            print(f"❌ ViyonaPay Error (decrypted): {error_msg}")
                        else:
                            error_msg = 'Failed to decrypt error response'
                            print(f"❌ {error_msg}")
                    else:
                        error_msg = result.get('result', result.get('message', 'Payment intent creation failed'))
                        print(f"❌ ViyonaPay Error: {error_msg}")
                    
                    return {'success': False, 'message': error_msg}
                
                # Check if response is encrypted (success response)
                if 'encrypted_data' in result:
                    # Decrypt response
                    decrypted = self._decrypt_data(result['encrypted_data'], session_key, aad)
                    if not decrypted:
                        return {'success': False, 'message': 'Failed to decrypt response'}
                    
                    # Handle both response formats
                    response_body = decrypted.get('response_body', decrypted)
                    
                    # Extract payment details (handle both formats)
                    payment_intent_id = response_body.get('payment_intent_id') or response_body.get('paymentRefNumber')
                    payment_url = response_body.get('payment_url') or response_body.get('upiIntentUrl')
                    status = response_body.get('status', 'PENDING')
                    
                    # Insert transaction into database
                    # Extract callback_url from order_data if provided
                    # Support both 'callback_url' and 'callbackurl' formats
                    callback_url = order_data.get('callback_url') or order_data.get('callbackurl', '')
                    
                    cursor.execute("""
                        INSERT INTO payin_transactions (
                            txn_id, merchant_id, order_id, amount, charge_amount,
                            net_amount, charge_type, status, pg_partner, pg_txn_id,
                            payee_name, payee_email, payee_mobile,
                            product_info, payment_url, callback_url, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                    """, (
                        txn_id,
                        merchant_id,
                        order_data.get('orderid'),
                        amount,
                        charge_amount,
                        net_amount,
                        charge_type,
                        'INITIATED',
                        'VIYONAPAY',
                        payment_intent_id,
                        customer_name,
                        customer_email,
                        customer_phone,
                        order_data.get('productinfo', 'Payment'),
                        payment_url,
                        callback_url
                    ))
                    
                    conn.commit()
                    
                    print(f"✅ Payment intent created successfully")
                    print(f"  Intent ID: {payment_intent_id}")
                    print(f"  Payment URL: {payment_url}")
                    
                    return {
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': order_data.get('orderid'),
                        'amount': amount,
                        'charge_amount': charge_amount,
                        'net_amount': net_amount,
                        'payment_intent_id': payment_intent_id,
                        'payment_url': payment_url,
                        'payment_link': payment_url,
                        'status': status,
                        'pg_partner': 'VIYONAPAY'
                    }
                else:
                    error_msg = result.get('result', 'Payment intent creation failed')
                    print(f"❌ Error: {error_msg}")
                    return {'success': False, 'message': error_msg}
                    
        except Exception as e:
            print(f"❌ Create payment intent error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def check_payment_status(self, order_id):
        """
        Check payment status via VIYONAPAY
        POST /v1/payin/status_check
        
        Args:
            order_id: Merchant order ID
        
        Returns:
            Status information dictionary
        """
        try:
            print(f"🔍 Checking payment status for order: {order_id}")
            
            # Get access token
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            timestamp = int(datetime.now().timestamp())
            
            # Generate session key
            session_key = self._generate_session_key()
            
            # Encrypt session key
            encrypted_session_key = self._encrypt_session_key(session_key)
            if not encrypted_session_key:
                return {'success': False, 'message': 'Failed to encrypt session key'}
            
            # Prepare status check data
            status_data = {
                'order_id': order_id
            }
            
            # Prepare AAD
            aad = {
                'client_id': self.client_id,
                'request_id': request_id,
                'timestamp': timestamp
            }
            
            # Encrypt status data
            encrypted_data = self._encrypt_data(status_data, session_key, aad)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt status data'}
            
            # Prepare request body
            request_body = {
                'client_id': self.client_id,
                'request_id': request_id,
                'timestamp': timestamp,
                'encrypted_data': encrypted_data,
                'encrypted_session_key': encrypted_session_key
            }
            
            # Generate signature
            signature = self._sign_request(request_body)
            if not signature:
                return {'success': False, 'message': 'Failed to generate signature'}
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-API-KEY': self.api_key,
                'Authorization': f'Bearer {token}',
                'X-SIGNATURE': signature,
                'X-Request-ID': request_id
            }
            
            url = f"{self.base_url}/v1/payin/status_check"
            
            # Send request with single attempt only (no retries)
            max_retries = 0  # Changed from 1 to 0 - no retries
            for attempt in range(max_retries + 1):
                try:
                    response = requests.post(url, json=request_body, headers=headers, timeout=30)
                except requests.exceptions.Timeout as timeout_error:
                    print(f"❌ Status check timeout: {timeout_error}")
                    return {'success': False, 'message': 'Status check timeout - ViyonaPay server not responding'}
                except Exception as e:
                    print(f"❌ Status check error: {e}")
                    return {'success': False, 'message': f'Network error: {str(e)}'}
                
                print(f"📥 Status response: {response.status_code}")
                
                # No retry logic - just break after first attempt
                break
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            # Check if response is encrypted
            if result.get('response_status') == 1 and 'encrypted_data' in result:
                # Decrypt response
                decrypted = self._decrypt_data(result['encrypted_data'], session_key, aad)
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                
                status_result = decrypted.get('result', {})
                
                return {
                    'success': True,
                    'status': status_result.get('status'),
                    'transaction_id': status_result.get('transaction_id'),
                    'payment_mode': status_result.get('payment_mode'),
                    'order_id': status_result.get('order_id'),
                    'amount': status_result.get('amount'),
                    'bank_reference_number': status_result.get('bank_reference_number'),
                    'message': status_result.get('message')
                }
            else:
                error_msg = result.get('result', 'Status check failed')
                return {'success': False, 'message': error_msg}
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Error: {str(e)}'}

# Create service instances for both configurations
viyonapay_service = ViyonapayService('TRUAXIS')  # Original Viyonapay
viyonapay_barringer_service = ViyonapayService('BARRINGER')  # Barringer configuration
