"""
HDFC Paytouch_Barringer Payin Service Integration
Handles payin transactions through HDFC Paytouch_Barringer gateway
"""

import requests
import json
from datetime import datetime
from database import get_db_connection
from config import Config
import uuid

class HDFCPaytouchBarringerService:
    def __init__(self):
        self.base_url = Config.HDFC_PAYTOUCH_BARRINGER_BASE_URL
        self.token = Config.HDFC_PAYTOUCH_BARRINGER_TOKEN
    
    def get_headers(self):
        """Get request headers"""
        return {
            'Content-Type': 'application/json'
        }
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique transaction ID with HDPT_BAR_ prefix"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"HDPT_BAR_{merchant_id}_{order_id}_{timestamp}"
    
    def calculate_charges(self, amount, scheme_id):
        """Calculate payin charges based on scheme"""
        try:
            conn = get_db_connection()
            if not conn:
                print(f"Charge calculation error: Database connection failed")
                return None
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s 
                    AND service_type = 'PAYIN'
                    AND %s BETWEEN min_amount AND max_amount
                    LIMIT 1
                """, (scheme_id, amount))
                
                charge = cursor.fetchone()
                
                if charge:
                    charge_amount = 0
                    if charge['charge_type'] == 'PERCENTAGE':
                        charge_amount = (amount * float(charge['charge_value'])) / 100
                    else:
                        charge_amount = float(charge['charge_value'])
                    
                    # For payin: merchant receives less (net_amount = amount - charge)
                    net_amount = amount - charge_amount
                    
                    conn.close()
                    return {
                        'charge_amount': round(charge_amount, 2),
                        'charge_type': charge['charge_type'],
                        'net_amount': round(net_amount, 2)
                    }
                else:
                    # No charge configuration found, return zero charges
                    print(f"No charge configuration found for scheme_id={scheme_id}, service_type=PAYIN, amount={amount}")
                    conn.close()
                    return {
                        'charge_amount': 0.00,
                        'charge_type': 'FIXED',
                        'net_amount': round(amount, 2)
                    }
            
        except Exception as e:
            print(f"Charge calculation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_payin_order(self, merchant_id, order_data):
        """
        Create payin order via HDFC Paytouch_Barringer
        
        Args:
            merchant_id: Merchant ID
            order_data: Dictionary containing:
                - amount: Payment amount
                - orderid: Unique order ID
                - payee_fname: Customer first name
                - payee_lname: Customer last name (optional)
                - payee_mobile: Customer mobile
                - payee_email: Customer email
                - callbackurl: Callback URL (optional)
        
        Returns:
            dict: Result with success status and payment details
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get merchant scheme
                cursor.execute("""
                    SELECT scheme_id, is_active FROM merchants WHERE merchant_id = %s
                """, (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    conn.close()
                    return {'success': False, 'message': 'Merchant not found'}
                
                if not merchant['is_active']:
                    conn.close()
                    return {'success': False, 'message': 'Merchant account is inactive'}
                
                if not merchant['scheme_id']:
                    conn.close()
                    return {'success': False, 'message': 'Merchant scheme not found'}
                
                # Calculate charges
                amount = float(order_data['amount'])
                charges = self.calculate_charges(amount, merchant['scheme_id'])
                
                if not charges:
                    conn.close()
                    return {'success': False, 'message': 'Unable to calculate charges'}
                
                # Generate transaction ID
                txn_id = self.generate_txn_id(merchant_id, order_data['orderid'])
                
                # Combine first and last name
                customer_name = f"{order_data['payee_fname']} {order_data.get('payee_lname', '')}".strip()
                
                # Insert payin transaction
                cursor.execute("""
                    INSERT INTO payin_transactions (
                        txn_id, merchant_id, order_id, amount, charge_amount,
                        charge_type, net_amount, payee_name, payee_email, payee_mobile,
                        status, pg_partner, callback_url
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    txn_id, merchant_id, order_data['orderid'],
                    amount, charges['charge_amount'],
                    charges['charge_type'], charges['net_amount'],
                    customer_name,
                    order_data.get('payee_email', ''),
                    order_data.get('payee_mobile', ''),
                    'INITIATED', 'HDFCPaytouch_Barringer',
                    order_data.get('callbackurl', '')
                ))
                
                conn.commit()
                print(f"Created transaction: {txn_id}")
                
                # Prepare HDFC API payload
                payload = {
                    'token': self.token,
                    'request_id': order_data['orderid'],  # Use merchant's order ID
                    'amount': str(amount),
                    'name': customer_name,
                    'email': order_data.get('payee_email', ''),
                    'mobile': order_data.get('payee_mobile', ''),
                    'payment_mode': 'UPI'  # Use UPI as payment mode
                }
                
                print(f"HDFC Paytouch_Barringer API Request: {json.dumps(payload, indent=2)}")
                
                # Call HDFC API
                url = f"{self.base_url}/api/payin/hdfc/payment"
                
                print(f"=" * 80)
                print(f"CALLING HDFC PAYTOUCH_BARRINGER API")
                print(f"=" * 80)
                print(f"URL: {url}")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )
                
                print(f"\nHDFC Paytouch_Barringer API Response:")
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print(f"Raw Response: {response.text}")
                print(f"=" * 80)
                
                if response.status_code not in [200, 201]:
                    error_msg = f'HDFC API error: HTTP {response.status_code} - {response.text}'
                    
                    # Update transaction status to FAILED
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    
                    conn.close()
                    return {'success': False, 'message': error_msg}
                
                # Parse JSON response
                try:
                    if not response.text or response.text.strip() == '':
                        error_msg = 'HDFC API returned empty response'
                        print(f"ERROR: {error_msg}")
                        
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, txn_id))
                        conn.commit()
                        conn.close()
                        return {'success': False, 'message': error_msg}
                    
                    hdfc_response = response.json()
                    print(f"HDFC Response JSON: {json.dumps(hdfc_response, indent=2)}")
                except json.JSONDecodeError as e:
                    error_msg = f'HDFC API returned invalid JSON: {str(e)} - Response: {response.text[:200]}'
                    print(f"ERROR: {error_msg}")
                    
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    conn.close()
                    return {'success': False, 'message': error_msg}
                
                # Check response status
                status = hdfc_response.get('status', '').upper()
                
                if status == 'ERR':
                    error_msg = hdfc_response.get('message', 'Payment order creation failed')
                    
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    conn.close()
                    return {'success': False, 'message': error_msg}
                
                # Extract transaction details
                apitxnid = hdfc_response.get('apitxnid')  # Merchant's request_id
                transaction_id = hdfc_response.get('transaction_id')  # Gateway transaction ID
                redirect_url = hdfc_response.get('redirect_url', '')
                
                print(f"Extracted from HDFC response:")
                print(f"  - apitxnid: {apitxnid}")
                print(f"  - transaction_id: {transaction_id}")
                print(f"  - redirect_url: {redirect_url}")
                
                # Update transaction with HDFC transaction ID
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = 'PENDING', pg_txn_id = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (transaction_id, txn_id))
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Order created successfully',
                    'txn_id': txn_id,
                    'order_id': order_data['orderid'],
                    'amount': amount,
                    'charge_amount': charges['charge_amount'],
                    'net_amount': charges['net_amount'],
                    'hdfc_txn_id': transaction_id,
                    'redirect_url': redirect_url,
                    'payment_link': redirect_url,  # For compatibility
                    'pg_partner': 'HDFCPaytouch_Barringer'
                }
                
        except Exception as e:
            print(f"HDFC Paytouch_Barringer payin error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
    
    def check_payment_status(self, order_id=None, transaction_id=None):
        """
        Check payment status from HDFC Paytouch_Barringer
        
        Args:
            order_id: Merchant's order ID (request_id)
            transaction_id: HDFC transaction ID
        
        Returns:
            dict: Status information
        """
        try:
            print(f"Checking HDFC Paytouch_Barringer payment status - order_id: {order_id}, transaction_id: {transaction_id}")
            
            # Note: HDFC API documentation doesn't specify a status check endpoint
            # You may need to contact HDFC support for status check API details
            # For now, return pending status
            
            return {
                'success': True,
                'status': 'PENDING',
                'message': 'Status check not implemented - waiting for callback'
            }
            
        except Exception as e:
            print(f"HDFC Paytouch_Barringer status check error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}

# Global instance
hdfcpaytouch_barringer_service = HDFCPaytouchBarringerService()
