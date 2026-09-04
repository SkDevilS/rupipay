"""
Tourquest Payment Gateway Service
Handles payin operations through Tourquest API
"""

import requests
import hashlib
import json
from datetime import datetime
from database import get_db_connection
from config import Config

class TourquestService:
    def __init__(self):
        self.base_url = Config.TOURQUEST_BASE_URL
        self.secret_key = Config.TOURQUEST_SECRET_KEY
        self.salt_key = Config.TOURQUEST_SALT_KEY
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"TQ_{merchant_id}_{order_id}_{timestamp}"
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """Calculate charges based on commercial scheme"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
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
                    return {
                        'charge_amount': 0.00,
                        'net_amount': float(amount)
                    }
                
                charge_type = charge_config['charge_type']
                charge_value = float(charge_config['charge_value'])
                
                if charge_type == 'PERCENTAGE':
                    charge_amount = (float(amount) * charge_value) / 100
                else:  # FIXED
                    charge_amount = charge_value
                
                net_amount = float(amount) - charge_amount
                
                return {
                    'charge_amount': round(charge_amount, 2),
                    'net_amount': round(net_amount, 2)
                }
                
        except Exception as e:
            print(f"Calculate charges error: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def create_payin_order(self, merchant_id, order_data):
        """
        Create Tourquest payin order
        
        Args:
            merchant_id: Merchant ID
            order_data: Dict with amount, orderid, payee_fname, payee_mobile, etc.
        
        Returns:
            Dict with success status and order details
        """
        try:
            amount = float(order_data.get('amount'))
            order_id = order_data.get('orderid')
            customer_name = f"{order_data.get('payee_fname', '')} {order_data.get('payee_lname', '')}".strip()
            customer_mobile = order_data.get('payee_mobile')
            
            # Validate inputs
            if not all([amount, order_id, customer_name, customer_mobile]):
                return {'success': False, 'message': 'Missing required fields'}
            
            # Get merchant details
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            try:
                with conn.cursor() as cursor:
                    # Get merchant scheme
                    cursor.execute("""
                        SELECT scheme_id FROM merchants WHERE merchant_id = %s
                    """, (merchant_id,))
                    
                    merchant = cursor.fetchone()
                    if not merchant:
                        return {'success': False, 'message': 'Merchant not found'}
                    
                    # Calculate charges
                    charges = self.calculate_charges(amount, merchant['scheme_id'], 'PAYIN')
                    if not charges:
                        return {'success': False, 'message': 'Failed to calculate charges'}
                    
                    # Generate transaction ID
                    txn_id = self.generate_txn_id(merchant_id, order_id)
                    
                    # Generate clientrefno (unique reference for Tourquest)
                    clientrefno = f"TQ{datetime.now().strftime('%Y%m%d%H%M%S')}{merchant_id[:4]}"
                    
                    # Prepare Tourquest API request
                    api_payload = {
                        "secret_key": self.secret_key,
                        "amount": f"{amount:.2f}",
                        "clientrefno": clientrefno,
                        "salt_key": self.salt_key,
                        "customername": customer_name,
                        "customermobile": customer_mobile,
                        "txntype": "payment",
                        "remark": f"Payment for order {order_id}"
                    }
                    
                    print(f"Tourquest API Request: {json.dumps(api_payload, indent=2)}")
                    
                    # Call Tourquest API
                    response = requests.post(
                        f"{self.base_url}/api/version/upi/apicall",
                        json=api_payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    print(f"Tourquest API Response Status: {response.status_code}")
                    print(f"Tourquest API Response: {response.text}")
                    
                    if response.status_code != 200:
                        return {
                            'success': False,
                            'message': f'Tourquest API error: HTTP {response.status_code} - {response.text}'
                        }
                    
                    try:
                        api_response = response.json()
                    except json.JSONDecodeError as e:
                        return {
                            'success': False,
                            'message': f'Invalid JSON response from Tourquest: {response.text}'
                        }
                    
                    print(f"Tourquest API Response JSON: {json.dumps(api_response, indent=2)}")
                    
                    # Check if API call was successful
                    # Tourquest may return different status indicators
                    status_ok = (
                        api_response.get('status') == True or 
                        api_response.get('status') == 'true' or
                        api_response.get('statuscode') == 200 or
                        api_response.get('statusCode') == 200 or
                        api_response.get('statuscode') == 'TXN'
                    )
                    
                    if not status_ok:
                        error_msg = api_response.get('message') or api_response.get('msg') or 'Payment initiation failed'
                        return {
                            'success': False,
                            'message': error_msg,
                            'api_response': api_response
                        }
                    
                    # Extract payment details - Tourquest returns payment_link (not upi_link)
                    # The payment_link contains the QR code URL
                    payment_link = api_response.get('payment_link', '')
                    
                    # For backward compatibility, also check data object
                    if not payment_link:
                        data = api_response.get('data', {})
                        payment_link = data.get('payment_link') or data.get('upi_link') or data.get('upiLink') or ''
                    
                    # The payment_link IS the QR code URL, use it for both
                    upi_link = payment_link
                    qr_string = payment_link
                    
                    # Extract transaction ID
                    tourquest_txn_id = clientrefno  # Use clientrefno as default
                    
                    print(f"Extracted payment_link: {payment_link}")
                    print(f"Extracted tourquest_txn_id: {tourquest_txn_id}")
                    
                    # Insert transaction into database
                    cursor.execute("""
                        INSERT INTO payin_transactions (
                            txn_id, merchant_id, order_id, amount, charge_amount,
                            net_amount, status, pg_partner, pg_txn_id,
                            payee_name, payee_mobile, payee_email, callback_url,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, 'INITIATED', 'Tourquest', %s,
                            %s, %s, %s, %s, NOW(), NOW()
                        )
                    """, (
                        txn_id, merchant_id, order_id, amount,
                        charges['charge_amount'], charges['net_amount'],
                        tourquest_txn_id, customer_name, customer_mobile,
                        order_data.get('payee_email', ''),
                        order_data.get('callbackurl')
                    ))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'message': 'Order created successfully',
                        'txn_id': txn_id,
                        'order_id': order_id,
                        'amount': amount,
                        'charge_amount': charges['charge_amount'],
                        'net_amount': charges['net_amount'],
                        'qr_string': qr_string,
                        'upi_link': upi_link,
                        'payment_link': payment_link,  # Tourquest payment link
                        'tourquest_txn_id': tourquest_txn_id,
                        'clientrefno': clientrefno
                    }
                    
            finally:
                conn.close()
                
        except requests.exceptions.RequestException as e:
            print(f"Tourquest API request error: {e}")
            return {'success': False, 'message': f'API request failed: {str(e)}'}
        except Exception as e:
            print(f"Create Tourquest order error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def check_payment_status(self, clientrefno):
        """
        Check payment status from Tourquest
        
        Args:
            clientrefno: Client reference number used in payment initiation
        
        Returns:
            Dict with success status and payment details
        """
        try:
            # Prepare status check request
            api_payload = {
                "secret_key": self.secret_key,
                "salt_key": self.salt_key,
                "clientrefno": clientrefno,
                "txntype": "status"
            }
            
            print(f"Tourquest Status Check Request: {json.dumps(api_payload, indent=2)}")
            
            # Call Tourquest status API
            response = requests.post(
                f"{self.base_url}/api/version/upi/apicall",
                json=api_payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Tourquest Status Response: {response.text}")
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Status check failed: {response.status_code}'
                }
            
            api_response = response.json()
            
            # Parse response
            if api_response.get('statuscode') == 200:
                data = api_response.get('data', {})
                status = data.get('status', 'PENDING').upper()
                
                return {
                    'success': True,
                    'status': status,
                    'txnId': data.get('txnid', ''),
                    'utr': data.get('utr', ''),
                    'amount': data.get('amount', ''),
                    'message': api_response.get('message', '')
                }
            else:
                return {
                    'success': False,
                    'message': api_response.get('message', 'Status check failed')
                }
                
        except Exception as e:
            print(f"Tourquest status check error: {e}")
            return {'success': False, 'message': str(e)}


# Create singleton instance
tourquest_service = TourquestService()
