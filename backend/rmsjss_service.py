"""
RMS_JSS Payment Gateway Integration Service
Handles payin transactions through RMS_JSS
"""

import requests
import json
from datetime import datetime
from config import Config
from database import get_db_connection

class RMSJSSService:
    def __init__(self):
        self.base_url = Config.RMSJSS_BASE_URL  # https://rmstrade.online
        self.api_token = Config.RMSJSS_API_TOKEN
    
    def get_headers(self):
        """Get request headers"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
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
        Create payin order via RMS_JSS
        POST /api/add-money/v3/createOrder
        
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
                
                # Log full order_data for debugging
                print(f"DEBUG: Full order_data received:")
                print(json.dumps(order_data, indent=2, default=str))
                
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
                
                # Use merchant's order ID as client_id
                merchant_order_id = order_data.get('orderid', '')
                
                if not merchant_order_id:
                    return {'success': False, 'message': 'Order ID is required'}
                
                # Generate transaction ID with RM_JS prefix
                txn_id = f"RM_JS_{merchant_id}_{merchant_order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Use merchant's order ID as client_id for RMS_JSS
                client_id = merchant_order_id
                
                # Prepare customer details
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                customer_name = f"{firstname} {lastname}".strip()
                customer_email = order_data.get('payee_email', '')
                customer_mobile = order_data.get('payee_mobile', '')
                
                # Validate required fields
                if not customer_mobile or len(customer_mobile) != 10:
                    return {'success': False, 'message': 'Valid 10-digit mobile number is required'}
                
                if not customer_email or '@' not in customer_email:
                    return {'success': False, 'message': 'Valid email address is required'}
                
                # Get callback URLs
                import os
                base_url = os.getenv('BACKEND_URL', 'https://api.moneyone.co.in')
                
                # Our callback URL (for RMS_JSS to send callbacks to us)
                our_callback_url = f"{base_url}/api/callback/rmsjss/payin"
                
                # Merchant's callback URL (where we forward the callback)
                # Try multiple field name variations that merchants might use
                merchant_callback_url = (
                    order_data.get('callback_url') or 
                    order_data.get('callbackurl') or 
                    order_data.get('callbackUrl') or 
                    order_data.get('callback') or 
                    order_data.get('webhook_url') or 
                    order_data.get('webhookurl') or
                    ''
                )
                
                print(f"DEBUG: Extracting callback URL from order_data")
                print(f"  - callback_url: {order_data.get('callback_url', 'NOT SET')}")
                print(f"  - callbackurl: {order_data.get('callbackurl', 'NOT SET')}")
                print(f"  - callbackUrl: {order_data.get('callbackUrl', 'NOT SET')}")
                print(f"  - callback: {order_data.get('callback', 'NOT SET')}")
                print(f"  - webhook_url: {order_data.get('webhook_url', 'NOT SET')}")
                print(f"  - Final extracted: {merchant_callback_url if merchant_callback_url else 'EMPTY'}")
                
                # Get redirect URL from order_data or use default
                redirect_url = order_data.get('redirect_url', f"{base_url}/payment-status")
                
                # Create order on RMS_JSS
                url = f"{self.base_url}/api/add-money/v3/createOrder"
                
                payload = {
                    'api_token': self.api_token,
                    'amount': amount,
                    'redirect_url': redirect_url,
                    'callback_url': our_callback_url,  # Send OUR callback URL to RMS_JSS
                    'client_id': client_id,
                    'customer_name': customer_name,
                    'customer_mobile': customer_mobile,
                    'customer_email': customer_email
                }
                
                print(f"Creating RMS_JSS order with payload: {json.dumps(payload, indent=2)}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )
                
                print(f"RMS_JSS API Response Status: {response.status_code}")
                print(f"RMS_JSS API Response: {response.text}")
                
                if response.status_code not in [200, 201]:
                    error_msg = f'RMS_JSS API error: {response.text}'
                    print(error_msg)
                    return {'success': False, 'message': error_msg}
                
                rmsjss_response = response.json()
                print(f"RMS_JSS Response JSON: {json.dumps(rmsjss_response, indent=2)}")
                
                if rmsjss_response.get('status') != 'success':
                    error_msg = rmsjss_response.get('message', 'Order creation failed')
                    print(f"RMS_JSS order creation failed: {error_msg}")
                    return {'success': False, 'message': error_msg}
                
                # Extract data from RMS_JSS response
                response_data = rmsjss_response.get('data', {})
                order_id = response_data.get('order_id')
                qr_string = response_data.get('qrString', '')
                
                # Extract intents (optional)
                intents = response_data.get('intents', {})
                
                # Validate that we got the required data
                if not qr_string:
                    print(f"No QR string in response: {rmsjss_response}")
                    return {'success': False, 'message': 'No payment QR received from RMS_JSS'}
                
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
                    txn_id, merchant_id, client_id, amount,
                    charge_amount, charge_type, net_amount,
                    customer_name, customer_email, customer_mobile,
                    order_data.get('productinfo', 'Payment'),
                    'INITIATED', 'RMS_JSS', str(order_id),
                    merchant_callback_url  # Store MERCHANT's callback URL for forwarding
                ))
                
                print(f"✓ Transaction created:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - Order ID (client_id): {client_id}")
                print(f"  - RMS_JSS Order ID: {order_id}")
                print(f"  - Our Callback URL (to RMS_JSS): {our_callback_url}")
                print(f"  - Merchant Callback URL (for forwarding): {merchant_callback_url}")
                
                conn.commit()
                
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': client_id,
                    'rmsjss_order_id': order_id,
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'qr_string': qr_string,
                    'qr_code_url': qr_string,
                    'payment_link': qr_string,
                    'intent_url': qr_string,
                    'upi_link': qr_string,  # QR string is also the UPI link
                    'intents': intents
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def check_payment_status(self, client_id):
        """
        Check payment status on RMS_JSS
        POST /api/add-money/v3/status-enquiry
        
        Args:
            client_id: The client_id used during order creation
        
        Returns:
            dict: Status information
        """
        try:
            print(f"Checking RMS_JSS payin status for client_id: {client_id}")
            
            url = f"{self.base_url}/api/add-money/v3/status-enquiry"
            
            payload = {
                'api_token': self.api_token,
                'client_id': client_id
            }
            
            print(f"Request URL: {url}")
            print(f"Request Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=payload,
                timeout=30
            )
            
            print(f"Response: {response.status_code} - {response.text[:500]}")
            
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Transaction not found in RMS_JSS'
                }
            
            rmsjss_response = response.json()
            
            # Extract data from RMS_JSS response
            if not rmsjss_response.get('status'):
                return {
                    'success': False,
                    'message': rmsjss_response.get('message', 'Status check failed')
                }
            
            data = rmsjss_response.get('data', {})
            
            # Extract status
            status = data.get('status', 'pending')
            if status.lower() == 'completed':
                status = 'SUCCESS'
            elif status.lower() == 'failed':
                status = 'FAILED'
            else:
                status = 'INITIATED'
            
            # Extract UTR
            utr = data.get('utr', '')
            
            result = {
                'success': True,
                'status': status,
                'client_id': data.get('client_id', client_id),
                'amount': data.get('amount'),
                'utr': utr,
                'payment_mode': 'UPI',
                'message': rmsjss_response.get('message', 'Status retrieved successfully')
            }
            
            print(f"Parsed RMS_JSS Status: {result}")
            
            return result
            
        except Exception as e:
            print(f"Check payment status error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}

# Create singleton instance
rmsjss_service = RMSJSSService()
