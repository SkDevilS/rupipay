"""
SkrillPe Payment Gateway Integration Service
Handles payin transactions through SkrillPe
"""

import requests
import json
from datetime import datetime
from config import Config
from database import get_db_connection
import uuid
from io import BytesIO
import hashlib
import base64

# Optional QR decoding support
try:
    from PIL import Image
    from pyzbar.pyzbar import decode
    QR_DECODE_AVAILABLE = True
except ImportError as e:
    print(f"⚠ QR decoding not available: {e}")
    print("⚠ Install with: pip install pillow pyzbar && sudo apt-get install -y libzbar0")
    QR_DECODE_AVAILABLE = False

class SkrillPeService:
    def __init__(self):
        self.base_url = Config.SKRILLPE_BASE_URL
        self.mid = Config.SKRILLPE_MID  # Merchant ID
        self.mobile_number = Config.SKRILLPE_MOBILE_NUMBER
        self.company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    def generate_basic_auth_token(self):
        """
        Generate Basic Authentication token as per SkrillPE specification
        Steps:
        1. Hash mobile number with SHA1
        2. Base64 encode the hash
        3. Combine MID:hashed_password
        4. Base64 encode the combination with ISO-8859-1 encoding
        5. Return as "Basic <token>"
        """
        try:
            # Step 1: SHA1 hash of mobile number
            sha1_hash = hashlib.sha1(self.mobile_number.encode('utf-8')).digest()
            
            # Step 2: Base64 encode the hash
            password = base64.b64encode(sha1_hash).decode('utf-8')
            
            # Step 3: Combine MID:password
            credentials = f"{self.mid}:{password}"
            
            # Step 4: Base64 encode with ISO-8859-1
            basic_auth = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
            
            # Step 5: Return with "Basic" prefix
            return f"Basic {basic_auth}"
            
        except Exception as e:
            print(f"Error generating Basic Auth token: {e}")
            return None
    
    def get_headers(self):
        """Get request headers for SkrillPe API"""
        auth_token = self.generate_basic_auth_token()
        
        return {
            'Authorization': auth_token,
            'Content-Type': 'application/json'
        }
    
    def download_qr_and_convert_to_string(self, qr_url):
        """Download QR image from URL and decode to extract UPI string"""
        if not QR_DECODE_AVAILABLE:
            print("⚠ QR decoding libraries not available, skipping QR decode")
            return None
            
        try:
            print(f"📥 Downloading QR image from: {qr_url}")
            
            # Download the QR image
            response = requests.get(qr_url, timeout=30)
            
            if response.status_code == 200:
                # Open image from bytes
                image = Image.open(BytesIO(response.content))
                
                # Decode QR code
                decoded_objects = decode(image)
                
                if decoded_objects:
                    # Extract the UPI string from QR code
                    qr_data = decoded_objects[0].data.decode('utf-8')
                    print(f"✓ QR decoded successfully: {qr_data[:50]}...")
                    return qr_data
                else:
                    print(f"✗ No QR code found in image")
                    return None
            else:
                print(f"✗ Failed to download QR image: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"✗ Error downloading/decoding QR image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"SKRILLPE_{merchant_id}_{order_id}_{timestamp}"
    
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
        """Create payin order via SkrillPe"""
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
                
                # Generate transaction ID
                txn_id = self.generate_txn_id(merchant_id, order_data.get('orderid'))
                
                # Prepare customer details
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                customer_name = f"{firstname} {lastname}".strip()
                customer_mobile = order_data.get('payee_mobile', '')
                
                # Create QR via SkrillPe API (Correct endpoint: GET intent)
                url = f"{self.base_url}/api/skrill/upi/qr/send/intent/WL"
                
                payload = {
                    'transactionId': txn_id,
                    'amount': str(amount),
                    'customerNumber': customer_mobile,
                    'CompanyAlise': self.company_alias
                }
                
                print(f"SkrillPe QR Request: {json.dumps(payload, indent=2)}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )
                
                print(f"SkrillPe Response Status: {response.status_code}")
                print(f"SkrillPe Response: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"🔍 SkrillPe API Response Debug:")
                    print(f"   Raw response: {json.dumps(data, indent=2)}")
                    
                    # Check multiple success conditions
                    code = data.get('code', '')
                    reason = data.get('reason', '')
                    intent_url = data.get('intentUrl', '')
                    tiny_url = data.get('tinyUrl', '')
                    
                    # Success indicators - check for success message or code
                    success_indicators = [
                        'Successful' in reason,
                        'successful' in reason.lower(),
                        code == '0',  # SkrillPe success code
                        code and code != 'null' and code != ''
                    ]
                    
                    is_successful = any(success_indicators)
                    
                    print(f"   Success indicators: {success_indicators}")
                    print(f"   Is successful: {is_successful}")
                    
                    if is_successful:
                        print(f"   Intent URL: '{intent_url}'")
                        print(f"   Tiny URL: '{tiny_url}'")
                        print(f"   Code: '{code}'")
                        print(f"   Reason: '{reason}'")
                        
                        # Determine the best UPI string to use
                        # Priority: intent_url > tiny_url > fallback message
                        qr_string = intent_url or tiny_url or reason
                        
                        print(f"   Final QR String: '{qr_string}'")
                        
                        # Check if we have usable URLs
                        has_usable_urls = bool(intent_url or tiny_url)
                        if not has_usable_urls:
                            print(f"   ⚠️  WARNING: No usable URLs in response (SkrillPe issue)")
                            print(f"   ⚠️  This may prevent users from completing payments")
                        
                        # Insert transaction into database
                        cursor.execute("""
                            INSERT INTO payin_transactions (
                                txn_id, merchant_id, order_id, amount, charge_amount, 
                                net_amount, charge_type, status, pg_partner, pg_txn_id,
                                payee_name, payee_mobile, payee_email,
                                remarks, created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
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
                            'SkrillPe',
                            code or txn_id,  # Use code if available, otherwise txn_id
                            customer_name,
                            customer_mobile,
                            order_data.get('payee_email', ''),
                            json.dumps(data)  # Store full response for debugging
                        ))
                        
                        conn.commit()
                        
                        return {
                            'success': True,
                            'message': reason or 'UPI intent generated successfully',
                            'txn_id': txn_id,
                            'order_id': order_data.get('orderid'),
                            'amount': amount,
                            'charge_amount': charge_amount,
                            'net_amount': net_amount,
                            'payment_url': intent_url,  # Primary payment URL
                            'payment_params': {},
                            'qr_string': qr_string,
                            'qr_code_url': '',  # Not provided by SkrillPe
                            'upi_link': intent_url or tiny_url,  # UPI intent link
                            'payment_link': tiny_url,  # Shortened payment link
                            'intent_url': intent_url,
                            'tiny_url': tiny_url,
                            'expires_in': 0,  # Not provided by SkrillPe
                            'vpa': '',  # Not provided by SkrillPe
                            'pg_partner': 'SKRILLPE',
                            'pg_txn_id': code or txn_id,
                            'status': 'INITIATED',
                            'raw_response': data  # Include raw response for debugging
                        }
                    else:
                        error_message = data.get('reason') or message or 'UPI intent generation failed'
                        print(f"   Error: {error_message}")
                        
                        return {
                            'success': False,
                            'message': error_message,
                            'raw_response': data
                        }
                else:
                    return {
                        'success': False,
                        'message': f'SkrillPe API error: {response.text}'
                    }
                    
        except Exception as e:
            print(f"Create payin order error: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def check_payment_status(self, transaction_id):
        """Check payment status via SkrillPe API"""
        try:
            url = f"{self.base_url}/api/skrill/au/dynamicqr/transaction/WL"
            
            payload = {
                'TransactionId': transaction_id
            }
            
            print(f"SkrillPe Status Check Request: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=payload,
                timeout=30
            )
            
            print(f"SkrillPe Status Response: {response.status_code}")
            print(f"SkrillPe Status Data: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Map SkrillPe status to our status
                # Status codes from SkrillPe team:
                # 0 = QR Payment Successful (SUCCESS)
                # 1 = QR Payment Failed (FAILED)
                # 2 = QR Payment Pending (INITIATED)
                # 3 = QR Generate (INITIATED)
                status_code = data.get('Status')
                if status_code == '0':
                    status = 'SUCCESS'
                elif status_code == '1':
                    status = 'FAILED'
                elif status_code == '2':
                    status = 'INITIATED'
                elif status_code == '3':
                    status = 'INITIATED'
                else:
                    status = 'INITIATED'
                
                return {
                    'success': True,
                    'status': status,
                    'amount': data.get('Amount'),
                    'rrn': data.get('Rrn'),
                    'payer_vpa': data.get('PayerVpa'),
                    'payer_name': data.get('PayerVerifiedName'),
                    'payer_mobile': data.get('PayerMobile'),
                    'message': data.get('Message'),
                    'txn_datetime': data.get('TxnDateTime'),
                    'trans_ref_id': data.get('TransRefId')
                }
            else:
                return {
                    'success': False,
                    'message': f'Status check failed: {response.text}'
                }
                
        except Exception as e:
            print(f"Check payment status error: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}

# Create singleton instance
skrillpe_service = SkrillPeService()
