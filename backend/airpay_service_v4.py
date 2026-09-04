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

class AirpayServiceV4:
    def __init__(self):
        self.base_url = Config.AIRPAY_BASE_URL  # https://kraken.airpay.co.in
        self.client_id = Config.AIRPAY_CLIENT_ID
        self.client_secret = Config.AIRPAY_CLIENT_SECRET
        self.merchant_id = Config.AIRPAY_MERCHANT_ID
        self.username = Config.AIRPAY_USERNAME
        self.password = Config.AIRPAY_PASSWORD
        self.encryption_key = Config.AIRPAY_ENCRYPTION_KEY  # Provided by Airpay
        
        # Token management
        self.access_token = None
        self.token_expiry = None
    
    def generate_access_token(self):
        """
        Step 1: Generate OAuth2 Access Token
        POST /airpay/pay/v4/api/oauth2
        """
        try:
            # Check if token is still valid
            if self.access_token and self.token_expiry:
                if datetime.now() < self.token_expiry:
                    print(f"✓ Using cached access token (expires in {(self.token_expiry - datetime.now()).seconds}s)")
                    return self.access_token
            
            print(f"🔑 Generating new Airpay access token...")
            
            url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
            
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'merchant_id': int(self.merchant_id),
                'grant_type': 'client_credentials'
            }
            
            print(f"Token request: {url}")
            print(f"Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Token response status: {response.status_code}")
            print(f"Token response: {response.text}")
            
            if response.status_code != 200:
                print(f"❌ Token generation failed: {response.text}")
                return None
            
            result = response.json()
            
            # Check response format
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 300)  # Default 5 minutes
                
                # Set expiry time (subtract 30 seconds for safety)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 30)
                
                print(f"✓ Access token generated successfully")
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

    def encrypt_data(self, data):
        """
        Step 2: Encrypt request data using AES/CBC/PKCS5PADDING
        According to Airpay documentation:
        - IV = bin2hex(openssl_random_pseudo_bytes(8)) - 16 character hex string
        - Encrypt using AES-256-CBC with encryption_key and IV
        - Return: IV + base64(encrypted_data)
        """
        try:
            # Convert data to JSON string if dict
            if isinstance(data, dict):
                data = json.dumps(data)
            
            print(f"📦 Encrypting data: {data[:100]}...")
            
            # Generate 8-byte random IV and convert to hex (16 characters)
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            print(f"  IV (hex): {iv_hex}")
            
            # Prepare encryption key (32 bytes for AES-256)
            key = self.encryption_key.encode('utf-8')
            if len(key) < 32:
                key = key.ljust(32, b'\x00')
            elif len(key) > 32:
                key = key[:32]
            
            # Create 16-byte IV for AES (pad the 8-byte IV)
            aes_iv = iv_bytes + b'\x00' * 8
            
            # Encrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
            
            # Encode to base64
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            # Return IV (hex) + base64(encrypted_data)
            result = iv_hex + encrypted_b64
            
            print(f"  Encrypted length: {len(result)}")
            print(f"  Result preview: {result[:50]}...")
            
            return result
            
        except Exception as e:
            print(f"❌ Encryption error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def decrypt_data(self, encrypted_response):
        """
        Step 3: Decrypt Airpay response
        According to Airpay documentation:
        - IV = first 16 characters (as string)
        - encrypted_data = remaining characters (base64)
        - Decrypt using AES-256-CBC
        """
        try:
            print(f"🔓 Decrypting Airpay response...")
            print(f"  Encrypted data length: {len(encrypted_response)}")
            print(f"  Preview: {encrypted_response[:50]}...")
            
            # Extract IV (first 16 characters as string)
            iv_string = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            print(f"  IV (string): {iv_string}")
            
            # Convert IV string to bytes
            iv_bytes = iv_string.encode('latin-1')
            
            # Decode base64 encrypted data
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Prepare encryption key
            key = self.encryption_key.encode('latin-1')
            if len(key) < 32:
                key = key.ljust(32, b'\x00')
            elif len(key) > 32:
                key = key[:32]
            
            # Decrypt
            cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # Remove PKCS5 padding
            try:
                unpadded_data = unpad(decrypted_data, AES.block_size)
            except ValueError:
                # Manual padding removal
                padding_length = decrypted_data[-1]
                if isinstance(padding_length, str):
                    padding_length = ord(padding_length)
                
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
            
            # Encrypt order data
            encrypted_data = self.encrypt_data(order_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt order data'}
            
            # Prepare request payload
            payload = {
                'data': encrypted_data,
                'encryptionkey': self.encryption_key
            }
            
            print(f"QR generation request: {url}")
            print(f"Payload keys: {list(payload.keys())}")
            
            # Send request
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"QR response status: {response.status_code}")
            print(f"QR response: {response.text}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            # Check if response is encrypted
            if 'response' in result:
                # Decrypt response
                decrypted = self.decrypt_data(result['response'])
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                
                result = decrypted
            
            # Check success
            if result.get('status_code') == '200' and result.get('status') == 'Success':
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
                    'message': result.get('message', 'QR generation failed')
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
        
        At least one of: orderid, ap_transactionid, or rrn is required
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
            
            # Prepare verification data
            verify_data = {}
            if order_id:
                verify_data['orderid'] = order_id
            if ap_transactionid:
                verify_data['ap_transactionid'] = ap_transactionid
            if rrn:
                verify_data['rrn'] = rrn
            
            if not verify_data:
                return {'success': False, 'message': 'At least one identifier required'}
            
            # Encrypt verification data
            encrypted_data = self.encrypt_data(verify_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt verification data'}
            
            # Prepare request payload
            payload = {
                'data': encrypted_data,
                'encryptionkey': self.encryption_key
            }
            
            print(f"Verify request: {url}")
            
            # Send request
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"Verify response status: {response.status_code}")
            print(f"Verify response: {response.text}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            # Check if response is encrypted
            if 'response' in result:
                # Decrypt response
                decrypted = self.decrypt_data(result['response'])
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                
                result = decrypted
            
            # Check success
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
                else:
                    status = 'PENDING'
                
                return {
                    'success': True,
                    'status': status,
                    'transaction_status': transaction_status,
                    'ap_transactionid': data.get('ap_transactionid'),
                    'orderid': data.get('orderid'),
                    'amount': data.get('amount'),
                    'rrn': data.get('rrn'),
                    'message': data.get('message'),
                    'transaction_payment_status': data.get('transaction_payment_status'),
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Verification failed')
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
        Create payin order via Airpay V4 API
        
        order_data should contain:
        - amount: Transaction amount
        - orderid: Merchant order ID
        - payee_fname: Payee first name
        - payee_mobile: Payee mobile (10 digits)
        - payee_email: Payee email
        - callbackurl: Callback URL (optional)
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
                
                # Generate unique order ID
                airpay_order_id = f"AP_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Create internal transaction ID
                txn_id = f"AR_GROS_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Prepare Airpay order data
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                
                # Validate required fields
                if not phone or len(phone) < 10:
                    return {'success': False, 'message': 'Valid mobile number required (10 digits)'}
                
                if not email or '@' not in email:
                    return {'success': False, 'message': 'Valid email address required'}
                
                # Get callback URL
                callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
                if not callback_url:
                    base_url = os.getenv('BACKEND_URL', 'https://admin.moneyone.co.in')
                    callback_url = f"{base_url}/api/callback/airpay/payin"
                
                # Prepare merchant domain (base64 encoded)
                frontend_url = os.getenv('FRONTEND_URL', 'https://client.moneyone.co.in')
                mer_dom = base64.b64encode(frontend_url.encode()).decode()
                
                # Prepare order payload for Airpay
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
                
                # Generate QR code
                qr_result = self.generate_qr(airpay_payload)
                
                if not qr_result.get('success'):
                    return qr_result
                
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
                    'INITIATED', 'Airpay', qr_result.get('ap_transactionid'),
                    callback_url
                ))
                
                conn.commit()
                
                print(f"✓ Transaction created: {txn_id}")
                
                # Schedule automatic status check after 60 seconds
                self.auto_check_status_after_delay(airpay_order_id, delay_seconds=60)
                
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': airpay_order_id,
                    'merchant_order_id': order_data.get('orderid'),
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'qr_string': qr_result.get('qrcode_string'),
                    'upi_link': qr_result.get('qrcode_string'),
                    'airpay_txn_id': qr_result.get('ap_transactionid')
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()

    def auto_check_status_after_delay(self, order_id, delay_seconds=60):
        """Automatically check payment status after a delay"""
        def check_status_task():
            try:
                print(f"[Auto Status Check] Waiting {delay_seconds}s for {order_id}...")
                time.sleep(delay_seconds)
                
                print(f"[Auto Status Check] Checking status for {order_id}...")
                
                conn = get_db_connection()
                if not conn:
                    print(f"[Auto Status Check] Database connection failed")
                    return
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT txn_id, order_id, merchant_id, status, net_amount, charge_amount
                            FROM payin_transactions
                            WHERE order_id = %s AND pg_partner = 'Airpay'
                        """, (order_id,))
                        
                        txn = cursor.fetchone()
                        
                        if not txn or txn['status'] not in ['INITIATED', 'PENDING']:
                            print(f"[Auto Status Check] Transaction already {txn['status'] if txn else 'not found'}")
                            return
                        
                        # Verify payment status
                        status_result = self.verify_payment(order_id=order_id)
                        
                        if not status_result.get('success'):
                            print(f"[Auto Status Check] Status check failed: {status_result.get('message')}")
                            return
                        
                        airpay_status = status_result.get('status', '').upper()
                        print(f"[Auto Status Check] Airpay status: {airpay_status}")
                        
                        if airpay_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
                            print(f"[Auto Status Check] Updating to SUCCESS")
                            
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'SUCCESS',
                                    bank_ref_no = %s,
                                    payment_mode = 'UPI',
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('rrn'), txn['txn_id']))
                            
                            # Check if wallet already credited
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                            """, (txn['txn_id'],))
                            
                            if cursor.fetchone()['count'] == 0:
                                from wallet_service import wallet_service as wallet_svc
                                
                                wallet_svc.credit_unsettled_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=float(txn['net_amount']),
                                    description=f"PayIn received (Auto check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                wallet_svc.credit_admin_unsettled_wallet(
                                    admin_id='admin',
                                    amount=float(txn['charge_amount']),
                                    description=f"PayIn charge (Auto check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                print(f"[Auto Status Check] ✓ Wallets credited")
                            
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Updated to SUCCESS")
                        
                        elif airpay_status == 'FAILED':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'FAILED', completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (txn['txn_id'],))
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Updated to FAILED")
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                print(f"[Auto Status Check] Error: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=check_status_task, daemon=True)
        thread.start()

# Create singleton instance
airpay_service_v4 = AirpayServiceV4()
