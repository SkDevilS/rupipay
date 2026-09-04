"""
Airpay Grosmart2 Payment Gateway Integration Service - V4 API
Separate configuration for Airpay Grosmart2 with different credentials
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

class AirpayGrosmart2Service:
    def __init__(self):
        self.base_url = Config.AIRPAY_GROSMART2_BASE_URL  # https://kraken.airpay.co.in
        self.client_id = Config.AIRPAY_GROSMART2_CLIENT_ID
        self.client_secret = Config.AIRPAY_GROSMART2_CLIENT_SECRET
        self.merchant_id = Config.AIRPAY_GROSMART2_MERCHANT_ID
        self.username = Config.AIRPAY_GROSMART2_USERNAME
        self.password = Config.AIRPAY_GROSMART2_PASSWORD
        self.secret = Config.AIRPAY_GROSMART2_SECRET  # Secret for privatekey generation
        
        # Generate encryption key from username and password
        # Key = MD5(username~:~password)
        key_string = f"{self.username}~:~{self.password}"
        self.encryption_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        # Generate privatekey for verify API
        # privatekey = SHA256(secret@username:|:password)
        privatekey_string = f"{self.secret}@{self.username}:|:{self.password}"
        self.privatekey = hashlib.sha256(privatekey_string.encode('utf-8')).hexdigest()
        
        print(f"🔑 Airpay Grosmart2 Service Initialized:")
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
        """
        try:
            # Check if token is still valid
            if self.access_token and self.token_expiry:
                if datetime.now() < self.token_expiry:
                    print(f"✓ Using cached access token (expires in {(self.token_expiry - datetime.now()).seconds}s)")
                    return self.access_token
            
            print(f"🔑 Generating new Airpay Grosmart2 access token...")
            
            url = f"{self.base_url}/airpay/pay/v4/api/oauth2"
            
            # Step 1: Prepare data array
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'merchant_id': self.merchant_id,
                'grant_type': 'client_credentials'
            }
            
            print(f"📦 Data array: {data}")
            
            # Step 2: JSON encode and encrypt the data
            json_data = json.dumps(data)
            encdata = self.encrypt_data(json_data)
            if not encdata:
                print(f"❌ Failed to encrypt data")
                return None
            
            # Step 3: Generate checksum from data array
            checksum = self.generate_checksum(data)
            if not checksum:
                print(f"❌ Failed to generate checksum")
                return None
            
            # Step 4: Prepare payload
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encdata,
                'checksum': checksum
            }
            
            print(f"🌐 Token request: {url}")
            
            # Send as form-urlencoded
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 Token response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Token generation failed: {response.text}")
                return None
            
            result = response.json()
            
            # Check if response is encrypted
            if 'response' in result:
                encrypted_response = result.get('response')
                decrypted_data = self.decrypt_data(encrypted_response)
                
                if not decrypted_data:
                    print(f"❌ Failed to decrypt token response")
                    return None
                
                result = decrypted_data
            
            # Check response format
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                
                if isinstance(data, dict) and 'success' in data:
                    if not data.get('success'):
                        print(f"❌ OAuth2 error: {data.get('msg', 'Unknown error')}")
                        return None
                
                self.access_token = data.get('access_token')
                
                if not self.access_token:
                    print(f"❌ No access token in response: {result}")
                    return None
                
                expires_in = data.get('expires_in', 300)
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
    
    def encrypt_data(self, data):
        """Encrypt request data using AES/CBC/PKCS5PADDING"""
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
            
            # Generate 8-byte random IV and convert to hex (16 characters)
            iv_bytes = get_random_bytes(8)
            iv_hex = iv_bytes.hex()
            
            # Prepare encryption key
            key = self.encryption_key.encode('latin-1')
            aes_iv = iv_hex.encode('latin-1')
            
            # Encrypt data
            cipher = AES.new(key, AES.MODE_CBC, aes_iv)
            encrypted_data = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
            
            # Encode to base64
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            # Return IV + base64(encrypted_data)
            result = iv_hex + encrypted_b64
            
            return result
            
        except Exception as e:
            print(f"❌ Encryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_checksum(self, data_dict):
        """Generate SHA-256 checksum for request data"""
        try:
            sorted_keys = sorted(data_dict.keys())
            checksum_data = ''
            for key in sorted_keys:
                value = str(data_dict[key])
                checksum_data += value
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            checksum_data += current_date
            
            checksum = hashlib.sha256(checksum_data.encode('utf-8')).hexdigest()
            
            return checksum
            
        except Exception as e:
            print(f"❌ Checksum generation error: {e}")
            return None
    
    def decrypt_data(self, encrypted_response):
        """Decrypt Airpay response"""
        try:
            # Extract IV (first 16 characters)
            iv_string = encrypted_response[:16]
            encrypted_data_b64 = encrypted_response[16:]
            
            iv_bytes = iv_string.encode('latin-1')
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            key_bytes = self.encryption_key.encode('latin-1')
            
            # Decrypt using AES-256-CBC
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # Remove PKCS5 padding
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
            
            return result
            
        except Exception as e:
            print(f"❌ Decryption error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_qr(self, order_data):
        """Generate QR Code for UPI payment"""
        try:
            print(f"📱 Generating Airpay Grosmart2 QR code...")
            
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            url = f"{self.base_url}/airpay/pay/v4/api/generateorder/?token={token}"
            
            json_data = json.dumps(order_data)
            encrypted_data = self.encrypt_data(json_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt order data'}
            
            checksum = self.generate_checksum(order_data)
            if not checksum:
                return {'success': False, 'message': 'Failed to generate checksum'}
            
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encrypted_data,
                'checksum': checksum
            }
            
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 QR response status: {response.status_code}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            if 'response' in result:
                decrypted = self.decrypt_data(result['response'])
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                result = decrypted
            
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
        """Verify payment status (Check Status)"""
        try:
            print(f"🔍 Verifying Airpay Grosmart2 payment status...")
            
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            url = f"{self.base_url}/airpay/pay/v4/api/verify/?token={token}"
            
            verify_data = {}
            if order_id:
                verify_data['orderid'] = order_id
            if ap_transactionid:
                verify_data['ap_transactionid'] = ap_transactionid
            if rrn:
                verify_data['rrn'] = rrn
            
            if not verify_data:
                return {'success': False, 'message': 'At least one identifier required'}
            
            json_data = json.dumps(verify_data)
            encrypted_data = self.encrypt_data(json_data)
            if not encrypted_data:
                return {'success': False, 'message': 'Failed to encrypt verification data'}
            
            checksum = self.generate_checksum(verify_data)
            if not checksum:
                return {'success': False, 'message': 'Failed to generate checksum'}
            
            payload = {
                'merchant_id': self.merchant_id,
                'encdata': encrypted_data,
                'checksum': checksum,
                'privatekey': self.privatekey
            }
            
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            print(f"📥 Verify response status: {response.status_code}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            if 'response' in result:
                decrypted = self.decrypt_data(result.get('response'))
                if not decrypted:
                    return {'success': False, 'message': 'Failed to decrypt response'}
                result = decrypted
            
            if result.get('status_code') == '200' and result.get('status') == 'success':
                data = result.get('data', {})
                
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
        """Create payin order via Airpay Grosmart2"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
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
                
                amount = float(order_data.get('amount', 0))
                if amount <= 0:
                    return {'success': False, 'message': 'Invalid amount'}
                
                charge_amount, net_amount, charge_type = self.calculate_charges(
                    amount, merchant['scheme_id']
                )
                
                if charge_amount is None:
                    return {'success': False, 'message': 'Failed to calculate charges'}
                
                # Generate unique order ID with AR_GROS2_ prefix
                airpay_order_id = f"AP_GROS2_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Create internal transaction ID with AR_GROS2_ prefix
                txn_id = f"AR_GROS2_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                
                # Extract callback URL from order_data
                callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
                
                if not callback_url:
                    # Use Grosmart2-specific callback URL
                    base_url = os.getenv('BACKEND_URL', 'https://api.moneyone.co.in')
                    callback_url = f"{base_url}/api/callback/airpay_grosmart2/payin"
                    print(f"⚠ No callback URL provided, using Grosmart2 callback: {callback_url}")
                
                # Prepare merchant domain
                frontend_url = 'https://api.moneyone.co.in'
                mer_dom = base64.b64encode(frontend_url.encode()).decode()
                
                if not phone or len(phone) < 10:
                    return {'success': False, 'message': 'Valid mobile number is required (10 digits)'}
                
                if not email or '@' not in email:
                    return {'success': False, 'message': 'Valid email address is required'}
                
                # Prepare order payload for Airpay V4 API
                airpay_payload = {
                    'orderid': airpay_order_id,
                    'amount': f"{amount:.2f}",
                    'tid': '12345678',
                    'buyer_email': email,
                    'buyer_phone': phone,
                    'mer_dom': mer_dom,
                    'customvar': f"merchant_id={merchant_id}|txn_id={txn_id}|callback_url={callback_url}",
                    'call_type': 'upiqr'
                }
                
                print(f"Creating Airpay Grosmart2 order: {airpay_payload}")
                
                # Generate QR code
                qr_result = self.generate_qr(airpay_payload)
                
                if not qr_result.get('success'):
                    return qr_result
                
                qr_string = qr_result.get('qrcode_string')
                airpay_txn_id = qr_result.get('ap_transactionid')
                
                # Insert transaction record with Airpay_Grosmart2 as pg_partner
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
                    'INITIATED', 'Airpay_Grosmart2', airpay_txn_id,
                    callback_url
                ))
                
                print(f"✓ Transaction created:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - Order ID: {airpay_order_id}")
                print(f"  - PG Partner: Airpay_Grosmart2")
                print(f"  - Callback URL: {callback_url}")
                
                conn.commit()
                
                # Schedule automatic status check
                self.auto_check_status_after_delay(airpay_order_id, delay_seconds=60)
                
                # For Airpay_Grosmart2, copy the UPI link to all payment parameters
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
                    'pg_partner': 'AIRPAY_GROSMART2'
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
        """Check payment status on Airpay Grosmart2"""
        try:
            print(f"Checking Airpay Grosmart2 payin status for identifier: {identifier}")
            
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
        """Automatically check payment status after a delay"""
        def check_status_task():
            try:
                time.sleep(delay_seconds)
                
                print(f"[Auto Status Check Grosmart2] Checking status for {order_id}...")
                
                conn = get_db_connection()
                if not conn:
                    return
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT txn_id, order_id, merchant_id, status, pg_txn_id, net_amount, charge_amount
                            FROM payin_transactions
                            WHERE order_id = %s AND pg_partner = 'Airpay_Grosmart2'
                        """, (order_id,))
                        
                        txn = cursor.fetchone()
                        
                        if not txn or txn['status'] not in ['INITIATED', 'PENDING']:
                            return
                        
                        status_result = self.check_payment_status(order_id)
                        
                        if not status_result.get('success'):
                            return
                        
                        airpay_status = status_result.get('status', '').upper()
                        
                        if airpay_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
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
                            
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                            """, (txn['txn_id'],))
                            
                            wallet_already_credited = cursor.fetchone()['count'] > 0
                            
                            if not wallet_already_credited:
                                from wallet_service import wallet_service as wallet_svc
                                wallet_svc.credit_unsettled_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=float(txn['net_amount']),
                                    description=f"PayIn received (Grosmart2 Auto check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                wallet_svc.credit_admin_unsettled_wallet(
                                    admin_id='admin',
                                    amount=float(txn['charge_amount']),
                                    description=f"PayIn charge (Grosmart2 Auto check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                            
                            conn.commit()
                        
                        elif airpay_status == 'FAILED' and txn['status'] != 'FAILED':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'FAILED',
                                    pg_txn_id = %s,
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('txnId'), txn['txn_id']))
                            
                            conn.commit()
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                print(f"[Auto Status Check Grosmart2] Error: {e}")
        
        thread = threading.Thread(target=check_status_task, daemon=True)
        thread.start()

# Create singleton instance
airpay_grosmart2_service = AirpayGrosmart2Service()
