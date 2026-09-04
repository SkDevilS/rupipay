"""
Vega Payin Service
Integrates with Vega payment gateway for payin transactions
Uses Mudrape headers (x-api-key, x-api-secret) as Vega is founded by Mudrape team
"""

import requests
import json
import random
import string
from datetime import datetime
from database import get_db_connection
from config import Config
import os


class VegaService:
    def __init__(self):
        # Vega uses same credentials and base URL as Mudrape (founded by Mudrape team)
        self.base_url = Config.MUDRAPE_BASE_URL
        self.api_key = Config.MUDRAPE_API_KEY
        self.api_secret = Config.MUDRAPE_API_SECRET
        self.user_id = Config.MUDRAPE_USER_ID
        self.action_picker = int(os.getenv('VEGA_ACTION_PICKER', '1'))
        
    def get_headers(self):
        """
        Get headers for Vega API requests
        Uses same format as Mudrape (x-api-key, x-api-secret)
        """
        return {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'x-api-secret': self.api_secret
        }
    
    def generate_track_id(self, merchant_id, order_id):
        """
        Generate unique track ID for Vega
        Format: TRACK-{timestamp}-{random}
        """
        timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
        random_suffix = ''.join(random.choices(string.ascii_uppercase, k=7))
        track_id = f"TRACK-{timestamp}-{random_suffix}"
        return track_id
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """
        Calculate charges based on scheme
        Returns: (charge_amount, net_amount, charge_type)
        """
        try:
            conn = get_db_connection()
            if not conn:
                return None, None, None
            
            with conn.cursor() as cursor:
                # Get applicable charge from commercial_charges table
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
                    # No charges configured - return 0 charge
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
        Create payin order via Vega
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_lname (optional)
        - payee_mobile
        - payee_email
        - address (optional)
        - city (optional)
        - state (optional)
        - zipCode (optional)
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
                
                # Generate unique track ID
                track_id = self.generate_track_id(merchant_id, order_data.get('orderid'))
                
                # Create internal transaction ID
                txn_id = f"VEGA_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Prepare customer details
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                address = order_data.get('address', '')
                city = order_data.get('city', '')
                state = order_data.get('state', '')
                zip_code = order_data.get('zipCode', '')
                
                # Create order on Vega
                url = f"{self.base_url}/api/generate-payment-link"
                
                payload = {
                    'firstName': firstname,
                    'lastName': lastname,
                    'address': address,
                    'city': city,
                    'state': state,
                    'zipCode': zip_code,
                    'phoneNumber': phone,
                    'email': email,
                    'trackID': track_id,
                    'actionPicker': self.action_picker,
                    'currency': 'INR',
                    'country': 'IN',
                    'amount': amount,
                    'userId': self.user_id
                }
                
                print(f"Creating Vega payment link with payload: {payload}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )
                
                print(f"Vega API Response Status: {response.status_code}")
                print(f"Vega API Response: {response.text}")
                
                if response.status_code != 200:
                    error_msg = f'Vega API error: {response.text}'
                    print(error_msg)
                    return {'success': False, 'message': error_msg}
                
                vega_response = response.json()
                print(f"Vega Response JSON: {vega_response}")
                
                if not vega_response.get('success'):
                    error_msg = vega_response.get('message', 'Payment link generation failed')
                    print(f"Vega payment link generation failed: {error_msg}")
                    return {'success': False, 'message': error_msg}
                
                # Extract payment URL and details from Vega response
                payment_url = vega_response.get('paymentUrl', '')
                vega_order_id = vega_response.get('orderId', track_id)
                vega_amount = vega_response.get('amount', str(amount))
                expires_in = vega_response.get('expiresIn', 600)
                
                # Validate that we got the payment URL
                if not payment_url:
                    print(f"No payment URL in response: {vega_response}")
                    return {'success': False, 'message': 'No payment link received from Vega'}
                
                # Extract callback URL from order_data
                # Vega uses Mudrape's callback system (configured with Vega team)
                callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
                
                if not callback_url:
                    # Use Mudrape's callback URL as Vega is configured to send callbacks there
                    base_url = os.getenv('BACKEND_URL', 'https://admin.moneyone.co.in')
                    callback_url = f"{base_url}/api/callback/mudrape/payin"
                    print(f"⚠ No callback URL provided, using Mudrape callback (configured for Vega): {callback_url}")
                
                # Insert transaction record
                # Store track_id as order_id (Vega will send this in callbacks via Mudrape callback system)
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
                    txn_id, merchant_id, track_id, amount,
                    charge_amount, charge_type, net_amount,
                    f"{firstname} {lastname}".strip(), email, phone,
                    order_data.get('productinfo', 'Payment'),
                    'INITIATED', 'Vega', vega_order_id,
                    callback_url
                ))
                
                print(f"✓ Transaction created:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - Order ID (track_id): {track_id}")
                print(f"  - Merchant Order ID: {order_data.get('orderid')}")
                print(f"  - Payment URL: {payment_url}")
                print(f"  - Expires In: {expires_in} seconds")
                print(f"  - Callback URL: {callback_url}")
                
                conn.commit()
                
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': track_id,  # Return track_id as order_id
                    'merchant_order_id': order_data.get('orderid'),
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'payment_url': payment_url,
                    'expires_in': expires_in,
                    'vega_order_id': vega_order_id
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
