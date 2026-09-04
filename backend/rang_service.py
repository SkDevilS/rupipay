import requests
import json
import logging
from datetime import datetime, timedelta
import time
import threading
from config import Config
from database import get_db_connection
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RangService:
    def __init__(self):
        self.base_url = os.getenv('RANG_BASE_URL', 'https://api.rangriwaz.in')
        self.secret_key = os.getenv('RANG_SECRET_KEY', 'OJYMJ8M3B9SV18DK')
        self.mid = os.getenv('RANG_MID', 'APIPA100015')
        self.email = os.getenv('RANG_EMAIL', 'indrajeet@mudrape.com')
        self.token = None
        self.token_expires_at = None
        
    def get_headers(self, include_auth=False):
        """Get headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'accept': '*/*'
        }
        
        if include_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        return headers
    
    def generate_token(self):
        """Generate authentication token"""
        try:
            url = f"{self.base_url}/api/Auth/generate-token"
            
            payload = {
                "mid": self.mid,
                "email": self.email,
                "secretkey": self.secret_key
            }
            
            headers = self.get_headers()
            
            logger.info(f"Generating Rang token with URL: {url}")
            logger.info(f"Payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"Token generation response status: {response.status_code}")
            logger.info(f"Token generation response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                expires_in_minutes = data.get('expiresInMinutes', 5)
                
                # Set expiry time (subtract 1 minute for safety)
                self.token_expires_at = datetime.now() + timedelta(minutes=expires_in_minutes - 1)
                
                logger.info(f"Token generated successfully. Expires at: {self.token_expires_at}")
                return True
            else:
                logger.error(f"Failed to generate token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error generating token: {str(e)}")
            return False
    
    def ensure_valid_token(self):
        """Ensure we have a valid token"""
        if not self.token or not self.token_expires_at or datetime.now() >= self.token_expires_at:
            logger.info("Token expired or not available, generating new token")
            return self.generate_token()
        return True
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique 20-digit transaction ID for Rang RefID (same as Mudrape)"""
        import random
        from datetime import datetime
        # Generate a 20-digit unique number (same format as Mudrape)
        # Format: timestamp (14 digits) + random (6 digits) = 20 digits
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')  # 14 digits
        random_part = str(random.randint(100000, 999999))  # 6 digits
        return f"{timestamp}{random_part}"  # Total 20 digits
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """Calculate charges based on commercial_charges table (same as Airpay/Mudrape)"""
        try:
            conn = get_db_connection()
            if not conn:
                return None, None, None
            
            with conn.cursor() as cursor:
                # Get applicable charge from commercial_charges table (same as Airpay/Mudrape)
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
                    # No charges configured - return zero charge (same as Airpay/Mudrape)
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
            logger.error(f"Calculate charges error: {e}")
            return None, None, None
        finally:
            if conn:
                conn.close()
    
    def create_payin_order(self, merchant_id, order_data):
        """Create payin order with Rang"""
        try:
            # Ensure valid token
            if not self.ensure_valid_token():
                return {
                    'success': False,
                    'message': 'Failed to authenticate with Rang'
                }
            
            # Get merchant details (same as Airpay)
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            cursor = conn.cursor()
            
            # Get merchant details including scheme_id
            cursor.execute("""
                SELECT merchant_id, full_name, email, scheme_id, is_active
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            
            if not merchant:
                cursor.close()
                conn.close()
                return {'success': False, 'message': 'Merchant not found'}
            
            if not merchant['is_active']:
                cursor.close()
                conn.close()
                return {'success': False, 'message': 'Merchant account is inactive'}

            # Map field names from your system to expected format
            mapped_order_data = {
                'order_id': order_data.get('orderid'),
                'amount': order_data.get('amount'),
                'customer_name': order_data.get('payee_fname', ''),
                'customer_mobile': order_data.get('payee_mobile'),
                'customer_email': order_data.get('payee_email')
            }
            
            # Validate amount
            amount = float(mapped_order_data['amount'])
            if amount <= 0:
                cursor.close()
                conn.close()
                return {'success': False, 'message': 'Invalid amount'}
            
            # Generate transaction ID
            txn_id = self.generate_txn_id(merchant_id, mapped_order_data['order_id'])
            
            # Calculate charges using merchant's scheme_id (same as Airpay)
            charge_amount, net_amount, charge_type = self.calculate_charges(
                amount, 
                merchant['scheme_id']  # Use merchant's scheme_id from database
            )
            
            if charge_amount is None:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': 'Failed to calculate charges'
                }
            
            # Extract callback URL from order_data (same as Mudrape)
            # If no callback URL provided, use default internal callback URL
            callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
            
            if not callback_url:
                # Use default internal callback URL for dashboard-generated QR codes
                # This ensures Rang can notify us when payment succeeds
                from config import Config
                base_url = os.getenv('BACKEND_URL', 'https://admin.moneyone.co.in')
                callback_url = f"{base_url}/rang-payin-callback"
                logger.info(f"⚠ No callback URL provided, using default: {callback_url}")
            
            # Store transaction in database first
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
                txn_id, merchant_id, mapped_order_data['order_id'], 
                amount, charge_amount, charge_type, net_amount,
                mapped_order_data['customer_name'], mapped_order_data['customer_email'], 
                mapped_order_data['customer_mobile'], 'Rang Payment', 'INITIATED', 'Rang',
                None,  # pg_txn_id will be updated after API response
                callback_url
            ))
            
            logger.info(f"✓ Transaction created:")
            logger.info(f"  - TXN ID: {txn_id}")
            logger.info(f"  - Order ID: {mapped_order_data['order_id']}")
            logger.info(f"  - Amount: {amount}")
            logger.info(f"  - Charge: {charge_amount} ({charge_type})")
            logger.info(f"  - Net Amount: {net_amount}")
            logger.info(f"  - Merchant Scheme: {merchant['scheme_id']}")
            logger.info(f"  - Callback URL: {callback_url if callback_url else 'NOT PROVIDED'}")
            
            conn.commit()
            
            # Create order with Rang API
            url = f"{self.base_url}/api/Payin/create-order"
            
            payload = {
                "RefID": txn_id,
                "Amount": str(amount),
                "Customer_Name": mapped_order_data['customer_name'],
                "Customer_Mobile": mapped_order_data['customer_mobile'],
                "Customer_Email": mapped_order_data['customer_email']
            }
            
            headers = self.get_headers(include_auth=True)
            
            logger.info(f"Creating Rang order with URL: {url}")
            logger.info(f"Payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"Rang order response status: {response.status_code}")
            logger.info(f"Rang order response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 1:
                    # Update transaction with Rang response
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE payin_transactions 
                        SET pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (
                        data['data'].get('txn_id'),
                        txn_id
                    ))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    # Schedule auto status check after 60 seconds
                    self.auto_check_status_after_delay(mapped_order_data['order_id'], 60)
                    
                    return {
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': mapped_order_data['order_id'],
                        'pg_txn_id': data['data'].get('txn_id'),
                        'qr_string': data['data'].get('qrString'),
                        'amount': amount,
                        'charge_amount': charge_amount,
                        'net_amount': net_amount,
                        'message': 'QR Successfully Generated'
                    }
                else:
                    # Update transaction status to failed
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE payin_transactions 
                        SET status = 'failed', updated_at = NOW()
                        WHERE txn_id = %s
                    """, (txn_id,))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    return {
                        'success': False,
                        'message': data.get('message', 'Failed to create order')
                    }
            else:
                return {
                    'success': False,
                    'message': f'API Error: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error creating Rang order: {str(e)}")
            return {
                'success': False,
                'message': f'Internal error: {str(e)}'
            }
    
    def check_payment_status(self, identifier):
        """Check payment status using RefId"""
        try:
            url = f"{self.base_url}/api/payin/v1/status-check"
            
            payload = {
                "RefId": identifier,
                "Service_Id": "1"  # 1 for payin
            }
            
            headers = self.get_headers()
            
            logger.info(f"Checking Rang status with URL: {url}")
            logger.info(f"Payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"Rang status response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': f'Status check failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error checking Rang status: {str(e)}")
            return {
                'success': False,
                'message': f'Status check error: {str(e)}'
            }
    
    def auto_check_status_after_delay(self, order_id, delay_seconds=60):
        """Auto check status after delay"""
        def check_status():
            try:
                time.sleep(delay_seconds)
                
                # Get transaction details
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("""
                    SELECT txn_id, status FROM payin_transactions 
                    WHERE order_id = %s AND pg_partner = 'Rang'
                    ORDER BY created_at DESC LIMIT 1
                """, (order_id,))
                
                txn = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if txn and txn['status'] == 'INITIATED':
                    logger.info(f"Auto checking status for Rang order: {order_id}")
                    self.check_payment_status(txn['txn_id'])
                    
            except Exception as e:
                logger.error(f"Error in auto status check: {str(e)}")
        
        # Start background thread
        thread = threading.Thread(target=check_status)
        thread.daemon = True
        thread.start()