"""
Payplus_Veltrix Payment Gateway Integration Service
PayIn API - Order Creation and Status Check
Base URL: https://payplus.live
"""

import requests
import json
import time
from datetime import datetime
from config import Config
from database import get_db_connection


class PayplusVeltrixService:
    def __init__(self):
        self.base_url = Config.PAYPLUS_VELTRIX_BASE_URL.rstrip('/')
        self.api_key = Config.PAYPLUS_VELTRIX_API_KEY
        
        print(f"🔑 Payplus_Veltrix Service Initialized:")
        print(f"  Base URL: {self.base_url}")
        print(f"  API Key: {self.api_key[:10]}..." if self.api_key else "  API Key: Not Set")

    def get_headers(self):
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """
        Calculate charges based on scheme configuration from commercial_charges table
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            conn.close()
            
            if not charge_config:
                print(f"❌ No charge configuration found for scheme_id: {scheme_id}")
                return {
                    'base_charge': 0.00,
                    'gst_amount': 0.00,
                    'total_charge': 0.00
                }
            
            charge_type = charge_config['charge_type']
            charge_value = float(charge_config['charge_value'])
            
            if charge_type == 'PERCENTAGE':
                base_charge = (float(amount) * charge_value) / 100
            else:  # FIXED
                base_charge = charge_value
            
            total_charge = base_charge
            
            return {
                'base_charge': round(base_charge, 2),
                'gst_amount': 0.00,
                'total_charge': round(total_charge, 2)
            }
            
        except Exception as e:
            print(f"❌ Error calculating charges: {str(e)}")
            return None

    def create_payin_order(self, merchant_id, order_data):
        """
        Create a payin order with Payplus_Veltrix
        order_data should contain:
        - amount
        - orderid
        - payee_fname (or customer_name)
        - payee_mobile (or customer_mobile)
        - payee_email (or customer_email)
        - callbackurl (or callback_url)
        """
        conn = None
        cursor = None
        try:
            print(f"💳 Creating Payplus_Veltrix order for merchant: {merchant_id}")
            print(f"📦 Received order_data: {json.dumps(order_data, indent=2)}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT merchant_id, mobile, email, scheme_id
                FROM merchants
                WHERE merchant_id = %s AND is_active = 1
            """, (merchant_id,))
            
            merchant_row = cursor.fetchone()
            
            if not merchant_row:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Merchant not found or inactive', 'message': 'Merchant not found or inactive'}
            
            merchant = {
                'merchant_id': merchant_row['merchant_id'],
                'mobile': merchant_row['mobile'],
                'email': merchant_row['email'],
                'scheme_id': merchant_row['scheme_id']
            }
            
            amount = float(order_data.get('amount', 0))
            if amount <= 0:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Invalid amount', 'message': 'Invalid amount'}
            
            customer_name = (
                order_data.get('payee_fname', '') or 
                order_data.get('customer_name', '') or 
                'Customer'
            )
            customer_mobile = str(
                order_data.get('payee_mobile', '') or 
                order_data.get('customer_mobile', '') or 
                merchant['mobile']
            ).strip()
            customer_email = (
                order_data.get('payee_email', '') or 
                order_data.get('customer_email', '') or 
                merchant['email']
            )
            merchant_order_id = order_data.get('orderid', '')
            callback_url = order_data.get('callbackurl', '') or order_data.get('callback_url', '')
            
            if not customer_mobile or len(customer_mobile) != 10 or not customer_mobile.isdigit():
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': f'Invalid mobile number: {customer_mobile}. Must be exactly 10 digits.',
                    'error': f'Invalid mobile number: {customer_mobile}. Must be exactly 10 digits.'
                }
            
            scheme_id = merchant['scheme_id']
            charges = self.calculate_charges(amount, scheme_id, 'PAYIN')
            if not charges:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Failed to calculate charges', 'message': 'Failed to calculate charges'}
            
            # Generate transaction ID with prefix PP_VEL_
            txn_id = f"PP_VEL_{int(time.time())}{merchant_id[-4:]}"
            
            print(f"📋 Extracted fields:")
            print(f"  - Amount: ₹{amount}")
            print(f"  - Customer Name: {customer_name}")
            print(f"  - Customer Mobile: {customer_mobile}")
            print(f"  - Transaction ID (prefix PP_VEL_): {txn_id}")
            
            cursor.execute("""
                INSERT INTO payin_transactions (
                    merchant_id, txn_id, order_id, amount, charge_amount, 
                    charge_type, net_amount, payee_name, payee_mobile, payee_email,
                    pg_partner, callback_url, status, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    'PAYPLUS_VELTRIX', %s, 'INITIATED', NOW()
                )
            """, (
                merchant_id,
                txn_id,
                merchant_order_id or txn_id,
                amount,
                charges['total_charge'],
                'PERCENTAGE',
                amount,
                customer_name,
                customer_mobile,
                customer_email,
                callback_url
            ))
            
            conn.commit()
            
            url = f"{self.base_url}/api/v1/payin/create"
            payload = {
                "amount": amount,
                "merchantOrderId": txn_id,
                "username": customer_name,
                "customerMeta": {
                    "merchant_id": merchant_id,
                    "customer_mobile": customer_mobile,
                    "customer_email": customer_email
                }
            }
            
            print(f"📤 Sending request to Payplus_Veltrix API: {url}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=self.get_headers(), timeout=30)
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📥 Response Body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('success'):
                    data = response_data.get('data', {})
                    pg_txn_id = data.get('orderId', '')
                    payment_url = data.get('paymentUrl', '')
                    
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET pg_txn_id = %s, pg_partner = 'PAYPLUS_VELTRIX', updated_at = NOW()
                        WHERE txn_id = %s
                    """, (pg_txn_id, txn_id))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    print(f"✅ Payplus_Veltrix payin order created successfully:")
                    print(f"  - TXN ID: {txn_id}")
                    print(f"  - PG TXN ID (orderId): {pg_txn_id}")
                    print(f"  - Payment URL: {payment_url}")
                    
                    return {
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': merchant_order_id or txn_id,
                        'pg_txn_id': pg_txn_id,
                        'amount': amount,
                        'charge': charges['total_charge'],
                        'charge_amount': charges['total_charge'],
                        'net_amount': amount,
                        'payment_params': {},
                        'qr_string': payment_url,
                        'qr_code_url': payment_url,
                        'upi_link': payment_url,
                        'payment_link': payment_url,
                        'intent_url': payment_url,
                        'tiny_url': payment_url,
                        'redirect_url': payment_url,
                        'payment_url': payment_url,
                        'expires_in': 0,
                        'vpa': '',
                        'pg_partner': 'PAYPLUS_VELTRIX',
                        'data': data
                    }
                else:
                    error_msg = response_data.get('message', 'Payin order creation failed')
                    print(f"❌ Payplus_Veltrix order creation failed: {error_msg}")
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED', remark = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return {'success': False, 'message': error_msg, 'error': error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ HTTP Error: {error_msg}")
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = 'FAILED', remark = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (error_msg, txn_id))
                conn.commit()
                cursor.close()
                conn.close()
                return {'success': False, 'message': error_msg, 'error': error_msg}
                
        except Exception as e:
            print(f"❌ Error in create_payin_order: {str(e)}")
            import traceback
            traceback.print_exc()
            if conn:
                try:
                    conn.rollback()
                    if cursor:
                        cursor.close()
                    conn.close()
                except Exception:
                    pass
            return {'success': False, 'message': str(e), 'error': str(e)}

    def check_payment_status(self, txn_id):
        """
        Check Payin Status by merchantOrderId or orderId
        POST /api/v1/payin/status
        """
        try:
            url = f"{self.base_url}/api/v1/payin/status"
            payload = {
                "merchantOrderId": txn_id
            }
            
            print(f"🔍 Checking Payplus_Veltrix payment status for: {txn_id}")
            response = requests.post(url, json=payload, headers=self.get_headers(), timeout=30)
            
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get('success'):
                    data = res_data.get('data', {})
                    api_status = str(data.get('status', '')).lower()
                    utr = data.get('utr', '')
                    order_id = data.get('orderId', '')
                    
                    if api_status == 'success':
                        mapped_status = 'SUCCESS'
                    elif api_status in ['processing', 'pending', 'initiated']:
                        mapped_status = 'PENDING'
                    elif api_status in ['failed', 'rejected', 'cancelled', 'timeout']:
                        mapped_status = 'FAILED'
                    else:
                        mapped_status = 'PENDING'
                    
                    print(f"✓ Status result for {txn_id}: API Status={api_status} -> Mapped={mapped_status}, UTR={utr}")
                    
                    return {
                        'success': True,
                        'status': mapped_status,
                        'utr': utr,
                        'txnId': order_id,
                        'merchantOrderId': data.get('merchantOrderId', txn_id),
                        'amount': data.get('amount'),
                        'fee': data.get('fee'),
                        'netAmount': data.get('netAmount'),
                        'raw_data': data
                    }
                else:
                    msg = res_data.get('message', 'Status check failed')
                    print(f"✗ Status check unsuccessful: {msg}")
                    return {'success': False, 'message': msg}
            else:
                msg = f"HTTP {response.status_code}: {response.text}"
                print(f"✗ HTTP error during status check: {msg}")
                return {'success': False, 'message': msg}
                
        except Exception as e:
            print(f"❌ Error checking payment status: {str(e)}")
            return {'success': False, 'message': str(e)}


payplus_veltrix_service = PayplusVeltrixService()
