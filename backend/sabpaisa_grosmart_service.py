"""
Sabpaisa Grosmart Payment Gateway Integration Service
Handles payin transactions through Sabpaisa Grosmart with HMAC-SHA256 checksum

API Documentation: https://merchant-api.sabpaisa.in
"""

import requests
import json
import hmac
import hashlib
import time
from datetime import datetime
from config import Config
from database import get_db_connection


class SabpaisaGrosmartService:
    """Service for Sabpaisa Grosmart payin integration"""
    
    def __init__(self):
        self.base_url = Config.SABPAISA_GROSMART_BASE_URL
        self.client_code = Config.SABPAISA_GROSMART_CLIENT_CODE
        self.api_key = Config.SABPAISA_GROSMART_API_KEY
        self.secret_key = Config.SABPAISA_GROSMART_SECRET_KEY
        
        print(f"🔐 Sabpaisa Grosmart Service Initialized")
        print(f"  Base URL: {self.base_url}")
        print(f"  Client Code: {self.client_code}")
    
    def generate_checksum(self, merchant_id, merchant_txn_id, amount, currency, timestamp):
        """
        Generate HMAC-SHA256 checksum for request authentication
        
        Formula: HMAC-SHA256(secretKey, merchantId|merchantTxnId|amount|currency|timestamp)
        
        Args:
            merchant_id: Merchant/Client code
            merchant_txn_id: Unique transaction ID
            amount: Amount in paise (100 = ₹1)
            currency: Currency code (INR)
            timestamp: Unix timestamp in seconds
        
        Returns:
            64-character lowercase hex string
        """
        try:
            # Build message string with pipe separator
            message = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
            
            # Generate HMAC-SHA256 signature
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return signature.lower()
        except Exception as e:
            print(f"❌ Checksum generation error: {e}")
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
        Create UPI Intent payment via Sabpaisa Grosmart S2S API
        POST /api/v1/payments/s2s
        
        order_data should contain:
        - amount: Amount in rupees (will be converted to paise)
        - orderid: Merchant order ID
        - payee_fname: Customer first name
        - payee_lname: Customer last name (optional)
        - payee_mobile: Customer phone number (10 digits)
        - payee_email: Customer email address
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
                
                # Generate transaction ID with SBP_GROS prefix
                timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
                txn_id = f"SBP_GROS_{merchant_id}_{order_data.get('orderid')}_{timestamp_str}"
                
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
                
                if not customer_name:
                    return {'success': False, 'message': 'Customer name is required'}
                
                # Convert amount to paise (Sabpaisa expects amount in paise)
                amount_paise = int(amount * 100)
                
                # Generate timestamp (Unix seconds)
                timestamp = int(time.time())
                
                # Generate checksum
                checksum = self.generate_checksum(
                    self.client_code,
                    txn_id,
                    amount_paise,
                    'INR',
                    timestamp
                )
                
                if not checksum:
                    return {'success': False, 'message': 'Failed to generate checksum'}
                
                # Prepare request payload for UPI Intent
                payload = {
                    'merchantId': self.client_code,
                    'merchantTxnId': txn_id,
                    'amount': amount_paise,
                    'currency': 'INR',
                    'customerName': customer_name,
                    'customerEmail': customer_email,
                    'customerPhone': customer_phone,
                    'paymentMode': 'UPI_INTENT',
                    'timestamp': timestamp,
                    'checksum': checksum,
                    'description': order_data.get('productinfo', 'Payment'),
                    'upiExpiryMinutes': 5
                }
                
                # Prepare headers (exactly as per Sabpaisa documentation)
                headers = {
                    'Content-Type': 'application/json',
                    'X-Api-Key': self.api_key,
                    'X-Merchant-Id': self.client_code
                }
                
                # Use correct endpoint as per documentation
                url = f"{self.base_url}/api/v2/payments/s2s"
                
                print(f"📤 Creating Sabpaisa payment: {url}")
                print(f"📦 Merchant Txn ID: {txn_id}")
                print(f"💰 Amount: ₹{amount} ({amount_paise} paise)")
                
                # Send request
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                except requests.exceptions.Timeout:
                    print(f"❌ Request timeout")
                    return {'success': False, 'message': 'Request timeout - Sabpaisa server not responding'}
                except Exception as e:
                    print(f"❌ Request error: {e}")
                    return {'success': False, 'message': f'Network error: {str(e)}'}
                
                print(f"📥 Response status: {response.status_code}")
                
                # Parse response
                try:
                    result = response.json()
                except:
                    print(f"❌ Failed to parse response: {response.text}")
                    return {'success': False, 'message': f'API error: {response.text}'}
                
                # Check for error response
                if response.status_code != 201 or not result.get('success'):
                    error_msg = result.get('message', 'Payment creation failed')
                    print(f"❌ Sabpaisa Error: {error_msg}")
                    return {'success': False, 'message': error_msg}
                
                # Extract payment details
                payment_id = result.get('paymentId')
                sp_txn_id = result.get('txnId')
                intent_url = result.get('intentUrl', '')
                status = result.get('status', 'PROCESSING')
                
                # Insert transaction into database
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
                    'SABPAISA_GROSMART',
                    sp_txn_id,
                    customer_name,
                    customer_email,
                    customer_phone,
                    order_data.get('productinfo', 'Payment'),
                    intent_url,
                    callback_url
                ))
                
                conn.commit()
                
                print(f"✅ Payment created successfully")
                print(f"  Payment ID: {payment_id}")
                print(f"  SP Txn ID: {sp_txn_id}")
                print(f"  Intent URL: {intent_url}")
                
                # Copy the same URL to all parameters except tiny_url
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': order_data.get('orderid'),
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'payment_params': {},
                    'qr_string': intent_url,
                    'qr_code_url': intent_url,
                    'upi_link': intent_url,
                    'payment_link': intent_url,
                    'intent_url': intent_url,
                    'tiny_url': '',
                    'expires_in': 0,
                    'vpa': '',
                    'pg_partner': 'SABPAISA_GROSMART'
                }
                
        except Exception as e:
            print(f"❌ Create payment error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': 'Internal server error'}
        finally:
            if conn:
                conn.close()
    
    def check_payment_status(self, merchant_txn_id):
        """
        Check payment status via Transaction Enquiry API
        POST /api/v2/payments/enquiry
        
        Args:
            merchant_txn_id: Merchant transaction ID
        
        Returns:
            Dictionary with status information
        """
        try:
            url = f"{self.base_url}/api/v2/payments/enquiry"
            
            payload = {
                'clientCode': self.client_code,
                'merchantTxnId': merchant_txn_id
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': self.api_key
            }
            
            print(f"📤 Checking payment status: {merchant_txn_id}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"📥 Status check response: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Status check failed: {response.text}")
                return {'success': False, 'message': 'Status check failed'}
            
            result = response.json()
            
            if not result.get('success'):
                return {'success': False, 'message': result.get('message', 'Status check failed')}
            
            # Map Sabpaisa status to our status
            sabpaisa_status = result.get('status', 'PENDING')
            
            if sabpaisa_status == 'SUCCESS':
                status = 'SUCCESS'
            elif sabpaisa_status in ['FAILED', 'EXPIRED', 'TIMEOUT']:
                status = 'FAILED'
            else:
                status = 'PENDING'
            
            return {
                'success': True,
                'status': status,
                'txnId': result.get('txnId'),
                'utr': result.get('bankRrn'),
                'bank_txn_id': result.get('bankTxnId'),
                'payment_mode': result.get('paymentMode', 'UPI'),
                'completed_at': result.get('completedAt')
            }
            
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return {'success': False, 'message': 'Status check failed'}


# Create singleton instance
sabpaisa_grosmart_service = SabpaisaGrosmartService()
