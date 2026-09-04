"""
PayU Payment Gateway Integration Service
Handles payin transactions through PayU
"""

import hashlib
import requests
import json
from datetime import datetime
from config import Config
from database import get_db_connection
import uuid

class PayUService:
    def __init__(self):
        self.merchant_key = Config.PAYU_MERCHANT_KEY
        self.merchant_salt = Config.PAYU_MERCHANT_SALT
        self.base_url = Config.PAYU_BASE_URL
        self.test_mode = Config.PAYU_TEST_MODE
    
    def generate_hash(self, data_string):
        """Generate SHA512 hash for PayU"""
        hash_string = data_string + self.merchant_salt
        return hashlib.sha512(hash_string.encode('utf-8')).hexdigest()
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"PAYIN_{merchant_id}_{order_id}_{timestamp}"
    
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
        Create payin order
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_lname
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
                
                # Generate transaction ID
                txn_id = self.generate_txn_id(merchant_id, order_data.get('orderid'))
                
                # Prepare PayU payment data
                productinfo = order_data.get('productinfo', 'Payment')
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                surl = order_data.get('callbackurl', f"http://localhost:5000/api/payin/callback/success")
                furl = order_data.get('callbackurl', f"http://localhost:5000/api/payin/callback/failure")
                
                # Generate hash
                hash_string = f"{self.merchant_key}|{txn_id}|{amount}|{productinfo}|{firstname}|{email}|||||||||||"
                hash_value = self.generate_hash(hash_string)
                
                # Insert transaction record
                cursor.execute("""
                    INSERT INTO payin_transactions (
                        txn_id, merchant_id, order_id, amount, charge_amount, 
                        charge_type, net_amount, payee_name, payee_email, 
                        payee_mobile, product_info, status, pg_partner,
                        callback_url, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (
                    txn_id, merchant_id, order_data.get('orderid'), amount,
                    charge_amount, charge_type, net_amount,
                    f"{firstname} {lastname}", email, phone, productinfo,
                    'INITIATED', 'PayU', order_data.get('callbackurl')
                ))
                
                conn.commit()
                
                # Prepare PayU payment URL
                payment_url = f"{self.base_url}/_payment"
                
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': order_data.get('orderid'),
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'payment_url': payment_url,
                    'payment_params': {
                        'key': self.merchant_key,
                        'txnid': txn_id,
                        'amount': str(amount),
                        'productinfo': productinfo,
                        'firstname': firstname,
                        'lastname': lastname,
                        'email': email,
                        'phone': phone,
                        'surl': surl,
                        'furl': furl,
                        'hash': hash_value
                    }
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def verify_payment_hash(self, response_data):
        """Verify PayU response hash"""
        try:
            status = response_data.get('status')
            key = response_data.get('key')
            txnid = response_data.get('txnid')
            amount = response_data.get('amount')
            productinfo = response_data.get('productinfo')
            firstname = response_data.get('firstname')
            email = response_data.get('email')
            received_hash = response_data.get('hash')
            
            # Generate hash for verification
            hash_string = f"{self.merchant_salt}|{status}|||||||||||{email}|{firstname}|{productinfo}|{amount}|{txnid}|{key}"
            calculated_hash = hashlib.sha512(hash_string.encode('utf-8')).hexdigest()
            
            return calculated_hash == received_hash
            
        except Exception as e:
            print(f"Verify hash error: {e}")
            return False
    
    def update_transaction_status(self, txn_id, status, pg_txn_id=None, bank_ref_no=None, 
                                  payment_mode=None, error_message=None):
        """Update transaction status after payment"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                # Get transaction details
                cursor.execute("""
                    SELECT merchant_id, amount, net_amount, status as current_status
                    FROM payin_transactions
                    WHERE txn_id = %s
                """, (txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    return False
                
                # Update transaction
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = %s,
                        pg_txn_id = %s,
                        bank_ref_no = %s,
                        payment_mode = %s,
                        error_message = %s,
                        updated_at = NOW(),
                        completed_at = CASE WHEN %s = 'SUCCESS' THEN NOW() ELSE completed_at END
                    WHERE txn_id = %s
                """, (status, pg_txn_id, bank_ref_no, payment_mode, error_message, status, txn_id))
                
                # If payment successful, no need to credit admin wallet
                # Admin balance is calculated from PayIN transactions directly
                if status == 'SUCCESS' and txn['current_status'] != 'SUCCESS':
                    pass  # Balance calculated on-the-fly from payin_transactions
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Update transaction status error: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_transaction_status(self, txn_id):
        """Get transaction status"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT txn_id, order_id, amount, charge_amount, net_amount,
                           status, pg_txn_id, bank_ref_no, payment_mode,
                           payee_name, payee_email, payee_mobile,
                           error_message, created_at, completed_at
                    FROM payin_transactions
                    WHERE txn_id = %s
                """, (txn_id,))
                
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Get transaction status error: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def send_callback_notification(self, merchant_id, txn_data):
        """Send callback notification to merchant"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                # Get merchant callback URL
                cursor.execute("""
                    SELECT payin_callback_url
                    FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                callback_config = cursor.fetchone()
                
                if not callback_config or not callback_config.get('payin_callback_url'):
                    return False
                
                callback_url = callback_config['payin_callback_url']
                
                # Prepare callback data
                callback_data = {
                    'txn_id': txn_data['txn_id'],
                    'order_id': txn_data['order_id'],
                    'amount': str(txn_data['amount']),
                    'status': txn_data['status'],
                    'pg_txn_id': txn_data.get('pg_txn_id'),
                    'bank_ref_no': txn_data.get('bank_ref_no'),
                    'payment_mode': txn_data.get('payment_mode'),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send callback (with timeout)
                response = requests.post(
                    callback_url,
                    json=callback_data,
                    timeout=10
                )
                
                # Log callback attempt
                cursor.execute("""
                    INSERT INTO callback_logs (
                        merchant_id, txn_id, callback_url, request_data,
                        response_code, response_data, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    merchant_id, txn_data['txn_id'], callback_url,
                    json.dumps(callback_data), response.status_code,
                    response.text[:1000]
                ))
                
                conn.commit()
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"Send callback error: {e}")
            return False
        finally:
            if conn:
                conn.close()

# Create singleton instance
payu_service = PayUService()
