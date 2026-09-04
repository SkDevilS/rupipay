"""
Upilnk Coco Payment Gateway Integration Service
"""

import requests
import json
import os
from datetime import datetime
from config import Config
from database import get_db_connection

class UpilnkCocoService:
    def __init__(self):
        self.pg_partner_name = 'Upilnk_Coco'
        self.txn_prefix = 'UP_COC_'
        self.order_prefix = 'UP_COC_'
        
        self.base_url = Config.UPILNK_COCO_BASE_URL
        self.client_id = Config.UPILNK_COCO_CLIENT_ID
        self.client_secret = Config.UPILNK_COCO_CLIENT_SECRET
        
        print(f"🔑 {self.pg_partner_name} Service Initialized:")
        print(f"  PG Partner: {self.pg_partner_name}")
        print(f"  ClientID: {self.client_id}")

    def get_auth_token(self):
        try:
            url = f"{self.base_url}/auth"
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get('token') or result.get('access_token')
                if token:
                    return token
                # Handle possible nested token structure
                if result.get('data') and isinstance(result.get('data'), dict):
                    return result['data'].get('token') or result['data'].get('access_token')
            print(f"❌ Upilnk Auth failed: {response.text}")
            return None
        except Exception as e:
            print(f"❌ Upilnk Auth error: {e}")
            return None

    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        try:
            conn = get_db_connection()
            if not conn: return None, None, None
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT charge_value, charge_type FROM commercial_charges
                    WHERE scheme_id = %s AND service_type = %s AND %s BETWEEN min_amount AND max_amount
                    ORDER BY min_amount DESC LIMIT 1
                """, (scheme_id, service_type, amount))
                charge_config = cursor.fetchone()
                if not charge_config: return 0.00, amount, 'FIXED'
                
                charge_type = charge_config['charge_type']
                charge_value = float(charge_config['charge_value'])
                charge_amount = (amount * charge_value) / 100 if charge_type == 'PERCENTAGE' else charge_value
                return round(charge_amount, 2), round(amount - charge_amount, 2), charge_type
        except Exception as e:
            print(f"❌ Charge calculation error: {e}")
            return None, None, None
        finally:
            if conn: conn.close()

    def create_payin_order(self, merchant_id, order_data):
        try:
            conn = get_db_connection()
            if not conn: return {'success': False, 'message': 'Database connection failed'}
            with conn.cursor() as cursor:
                cursor.execute("SELECT merchant_id, full_name, email, scheme_id, is_active FROM merchants WHERE merchant_id = %s", (merchant_id,))
                merchant = cursor.fetchone()
                if not merchant or not merchant['is_active']: return {'success': False, 'message': 'Merchant inactive/not found'}
                
                amount = float(order_data.get('amount', 0))
                if amount <= 0: return {'success': False, 'message': 'Invalid amount'}
                
                charge_amount, net_amount, charge_type = self.calculate_charges(amount, merchant['scheme_id'])
                if charge_amount is None: return {'success': False, 'message': 'Charge calculation failed'}
                
                original_order_id = str(order_data.get('orderid', ''))
                txn_id = f"{self.txn_prefix}{merchant_id}_{original_order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                email = order_data.get('payee_email', '') or merchant['email'] or 'test@gmail.com'
                phone = order_data.get('payee_mobile', '') or '9999999999'
                name = order_data.get('payee_fname', '') or merchant['full_name'] or 'Customer'
                
                callback_url = f"{os.getenv('BACKEND_URL', 'https://api.rupipay.shop')}/api/callback/upilnk-coco"
                
                token = self.get_auth_token()
                if not token:
                    return {'success': False, 'message': 'Failed to authenticate with PG'}

                url = f"{self.base_url}/create-order"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "client_id": self.client_id,
                    "amount": str(int(amount)) if amount.is_integer() else f"{amount:.2f}",
                    "order_id": original_order_id,
                    "callback_url": callback_url,
                    "customer_details": {
                        "email": email,
                        "mobile": phone,
                        "name": name
                    }
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code not in [200, 201]:
                    return {'success': False, 'message': f'API error: {response.text}'}
                
                try:
                    result = response.json()
                except Exception as e:
                    return {'success': False, 'message': f'Invalid JSON response: {response.text}'}
                
                # Try to extract payment URL robustly prioritizing bhim from intents
                payment_url = None
                
                if result.get('intents') and isinstance(result.get('intents'), dict):
                    payment_url = result['intents'].get('bhim')
                
                if not payment_url:
                    payment_url = result.get('payment_link') or result.get('payment_url') or result.get('url') or result.get('intent_url') or result.get('upi_link')
                
                if not payment_url and result.get('data') and isinstance(result.get('data'), dict):
                    data = result['data']
                    if data.get('intents') and isinstance(data.get('intents'), dict):
                        payment_url = data['intents'].get('bhim')
                    if not payment_url:
                        payment_url = data.get('payment_link') or data.get('payment_url') or data.get('url') or data.get('intent_url') or data.get('upi_link')
                
                pg_txn_id = result.get('tr_id') or result.get('txn_id') or result.get('pg_order_id')
                
                if payment_url:
                    cursor.execute("""
                        INSERT INTO payin_transactions (
                            txn_id, merchant_id, order_id, amount, charge_amount, 
                            charge_type, net_amount, payee_name, payee_email, 
                            payee_mobile, product_info, status, pg_partner,
                            pg_txn_id, callback_url, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (txn_id, merchant_id, original_order_id, amount, charge_amount, charge_type, net_amount, 
                          name, email, phone, order_data.get('productinfo', 'Payment'), 
                          'INITIATED', self.pg_partner_name, pg_txn_id, order_data.get('callbackurl')))
                    
                    conn.commit()
                    return {
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': original_order_id,
                        'merchant_order_id': order_data.get('orderid'),
                        'amount': amount,
                        'charge_amount': charge_amount,
                        'net_amount': net_amount,
                        'qr_string': payment_url,
                        'qr_code_url': payment_url,
                        'upi_link': payment_url,
                        'payment_link': payment_url,
                        'intent_url': payment_url,
                        'pg_txn_id': pg_txn_id,
                        'pg_partner': self.pg_partner_name
                    }
                else:
                    return {'success': False, 'message': 'Payment URL not received from PG', 'details': result}
        except Exception as e:
            print(f"❌ Upilnk order generation error: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn: conn.close()
            
    def check_payment_status(self, order_id=None):
        try:
            token = self.get_auth_token()
            if not token:
                return {'success': False, 'message': 'Auth failed during status check'}

            url = f"{self.base_url}/check-order-status"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "client_id": self.client_id,
                "order_id": order_id
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
                
            result = response.json()
            
            api_status = str(result.get('status') or (result.get('data', {}).get('status') if isinstance(result.get('data'), dict) else '')).lower()
            
            if api_status in ['paid', 'success', 'successful', 'completed']:
                status = 'SUCCESS'
            elif api_status in ['failed', 'failure']:
                status = 'FAILED'
            elif api_status in ['pending', 'processing']:
                status = 'PENDING'
            else:
                status = 'INITIATED'
                
            return {
                'success': True,
                'status': status,
                'transaction_status': api_status,
                'ap_transactionid': result.get('tr_id') or (result.get('data', {}).get('tr_id') if isinstance(result.get('data'), dict) else None),
                'orderid': order_id,
                'message': result.get('message') or 'Status checked successfully'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

# Create singleton instance
upilnk_coco_service = UpilnkCocoService()
