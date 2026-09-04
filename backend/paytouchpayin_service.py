"""
Paytouchpayin Payment Gateway Integration Service
QR PAYIN API - Dynamic QR Generation with Instant Callback
Base URL: https://dashboard.shreefintechsolutions.com
"""

import requests
import json
import time
from datetime import datetime, timedelta
from config import Config
from database import get_db_connection

class PaytouchpayinService:
    def __init__(self):
        self.base_url = Config.PAYTOUCHPAYIN_BASE_URL  # https://dashboard.shreefintechsolutions.com
        self.token = Config.PAYTOUCHPAYIN_TOKEN
        
        print(f"🔑 Paytouchpayin Service Initialized:")
        print(f"  Base URL: {self.base_url}")
        print(f"  Token: {self.token[:20]}...")
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYIN'):
        """
        Calculate charges based on scheme configuration from commercial_charges table
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            conn.close()
            
            if not charge_config:
                print(f"❌ No charge configuration found for scheme_id: {scheme_id}")
                # Return zero charges if no config found
                return {
                    'base_charge': 0.00,
                    'gst_amount': 0.00,
                    'total_charge': 0.00
                }
            
            # DictCursor returns dict, access by column name
            charge_type = charge_config['charge_type']
            charge_value = float(charge_config['charge_value'])
            
            # Calculate base charge
            if charge_type == 'PERCENTAGE':
                base_charge = (float(amount) * charge_value) / 100
            else:  # FIXED
                base_charge = charge_value
            
            # For payin, we don't add GST separately (it's included in the charge)
            # Total charge is just the base charge
            total_charge = base_charge
            
            return {
                'base_charge': round(base_charge, 2),
                'gst_amount': 0.00,  # GST included in charge
                'total_charge': round(total_charge, 2)
            }
            
        except Exception as e:
            print(f"❌ Error calculating charges: {str(e)}")
            return None
    
    def generate_dynamic_qr(self, qr_data):
        """
        Generate Dynamic UPI QR code for payment
        POST /api/payin/dynamic-qr-simple (Updated 2026)
        
        qr_data should contain (already mapped to Paytouchpayin API format):
        - token: API authentication token
        - mobile: User mobile number (10 digits)
        - amount: Payment amount (as number)
        - txnid: Unique transaction ID
        - name: Customer name
        
        Response:
        {
            "status": "SUCCESS",
            "message": "Dynamic QR Generated",
            "data": {
                "txnid": "TXN2026032540002135",
                "apitxnid": "DQR2361774598543258",
                "amount": "20.37",
                "upi_string": "upi://pay?ver=01&mode=04&tr=DQR2361774598543258&pa=vyapar.173506865983@hdfcbank&pn=Raj Kumar Singh&mc=6540&am=20.37&qrMedium=02",
                "name": "Raj Kumar Singh",
                "expire_at": 1774598843
            }
        }
        """
        try:
            print(f"🚀 Generating Paytouchpayin Dynamic QR...")
            print(f"📦 QR Data (already mapped): {json.dumps(qr_data, indent=2)}")
            
            url = f"{self.base_url}/api/payin/dynamic-qr-simple"
            
            # qr_data is already in the correct format for Paytouchpayin API
            payload = qr_data
            
            print(f"📤 Sending request to: {url}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📥 Response Body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('status') == 'SUCCESS':
                    print(f"✅ Dynamic QR generated successfully")
                    return {
                        'success': True,
                        'data': response_data.get('data'),
                        'message': response_data.get('message')
                    }
                else:
                    print(f"❌ QR generation failed: {response_data.get('message')}")
                    return {
                        'success': False,
                        'error': response_data.get('message', 'QR generation failed')
                    }
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_payin_order(self, merchant_id, order_data):
        """
        Create a payin order and generate Dynamic QR
        order_data should contain (from merchant API):
        - amount
        - orderid
        - payee_fname (or customer_name)
        - payee_mobile (or customer_mobile)
        - payee_email (or customer_email)
        """
        try:
            print(f"💳 Creating Paytouchpayin order for merchant: {merchant_id}")
            print(f"📦 Received order_data: {json.dumps(order_data, indent=2)}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get merchant details
            cursor.execute("""
                SELECT merchant_id, mobile, email, scheme_id
                FROM merchants
                WHERE merchant_id = %s AND is_active = 1
            """, (merchant_id,))
            
            merchant_row = cursor.fetchone()
            
            if not merchant_row:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Merchant not found or inactive'}
            
            # DictCursor returns dict, access by column name
            merchant = {
                'merchant_id': merchant_row['merchant_id'],
                'mobile': merchant_row['mobile'],
                'email': merchant_row['email'],
                'scheme_id': merchant_row['scheme_id']
            }
            
            # Extract fields from order_data (following Mudrape pattern)
            # Support both payee_* and customer_* field names
            amount = float(order_data.get('amount', 0))
            if amount <= 0:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Invalid amount'}
            
            # Extract customer details with fallbacks
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
            callback_url = order_data.get('callbackurl', '') or order_data.get('callback_url', '')  # Get callback URL from order data
            
            # Validate mobile number (must be exactly 10 digits)
            if not customer_mobile or len(customer_mobile) != 10 or not customer_mobile.isdigit():
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': f'Invalid mobile number: {customer_mobile}. Must be exactly 10 digits.',
                    'error': f'Invalid mobile number: {customer_mobile}. Must be exactly 10 digits.'
                }
            
            print(f"📋 Extracted fields:")
            print(f"  - Amount: {amount}")
            print(f"  - Customer Name: {customer_name}")
            print(f"  - Customer Mobile: {customer_mobile}")
            print(f"  - Customer Email: {customer_email}")
            print(f"  - Merchant Order ID: {merchant_order_id}")
            print(f"  - Callback URL: {callback_url if callback_url else 'NOT PROVIDED'}")
            
            # Calculate charges
            scheme_id = merchant['scheme_id']
            
            charges = self.calculate_charges(amount, scheme_id, 'PAYIN')
            if not charges:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Failed to calculate charges'}
            
            # Calculate final amount (amount + charges)
            final_amount = amount + charges['total_charge']
            
            # Generate unique transaction ID
            txn_id = f"PTPIN{int(time.time())}{merchant_id[-4:]}"
            
            print(f"💰 Charges calculated:")
            print(f"  - Base Amount: ₹{amount}")
            print(f"  - Charges: ₹{charges['total_charge']}")
            print(f"  - Final Amount: ₹{final_amount}")
            print(f"  - Transaction ID: {txn_id}")
            
            # Insert into payin_transactions table (same as all other payin services)
            cursor.execute("""
                INSERT INTO payin_transactions (
                    merchant_id, txn_id, order_id, amount, charge_amount, 
                    charge_type, net_amount, payee_name, payee_mobile, payee_email,
                    pg_partner, callback_url, status, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    'paytouchpayin', %s, 'INITIATED', NOW()
                )
            """, (
                merchant_id,
                txn_id,
                merchant_order_id or txn_id,
                amount,
                charges['total_charge'],
                'PERCENTAGE',  # Charge type from scheme
                amount,  # Net amount (what merchant receives)
                customer_name,
                customer_mobile,
                customer_email,
                callback_url  # Store callback URL
            ))
            
            conn.commit()
            
            # Prepare payload for Paytouchpayin API (map to their field names)
            # IMPORTANT: Send BASE amount - Paytouchpayin API will add its own charges
            # API will return final amount (base + their charges) in response
            qr_data = {
                'token': self.token,  # API token (not from order_data)
                'mobile': customer_mobile,  # 10 digits string
                'amount': amount,  # NUMBER - send BASE amount, API adds charges
                'txnid': txn_id,  # Unique transaction ID
                'name': customer_name  # Customer name
            }
            
            print(f"🚀 Calling Paytouchpayin API with mapped fields:")
            print(f"  - token: {self.token[:20]}...")
            print(f"  - mobile: {customer_mobile} (type: {type(customer_mobile).__name__})")
            print(f"  - amount: {amount} (BASE amount - API will add their charges)")
            print(f"  - txnid: {txn_id}")
            print(f"  - name: {customer_name}")
            print(f"\n📤 Full API Request Payload:")
            print(json.dumps(qr_data, indent=2))
            
            qr_result = self.generate_dynamic_qr(qr_data)
            
            if qr_result.get('success'):
                # Update payin with pg_txn_id (apitxnid) from API response
                pg_txn_id = qr_result['data'].get('apitxnid')
                upi_string = qr_result['data'].get('upi_string')
                api_final_amount = float(qr_result['data'].get('amount', final_amount))
                
                # Update transaction with pg_txn_id only (no payment_url column in table)
                cursor.execute("""
                    UPDATE payin_transactions
                    SET pg_txn_id = %s, pg_partner = 'paytouchpayin', updated_at = NOW()
                    WHERE txn_id = %s
                """, (pg_txn_id, txn_id))
                
                conn.commit()
                
                cursor.close()
                conn.close()
                
                print(f"✅ Paytouchpayin order created successfully:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - PG TXN ID: {pg_txn_id}")
                print(f"  - Base Amount: ₹{amount}")
                print(f"  - Our Charges: ₹{charges['total_charge']}")
                print(f"  - API Final Amount: ₹{api_final_amount} (customer pays this)")
                print(f"  - UPI String: {upi_string[:50]}...")
                
                # Copy payment_link to all payment-related fields so merchants can use any field
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': merchant_order_id or txn_id,
                    'pg_txn_id': pg_txn_id,
                    'amount': amount,
                    'charge': charges['total_charge'],
                    'charge_amount': charges['total_charge'],
                    'net_amount': amount,  # Net amount merchant receives
                    'payment_params': {},
                    'qr_string': upi_string,  # Copy payment_link here
                    'qr_code_url': upi_string,  # Copy payment_link here
                    'upi_link': upi_string,  # Copy payment_link here
                    'payment_link': upi_string,  # Main payment link
                    'intent_url': upi_string,  # Copy payment_link here
                    'tiny_url': upi_string,  # Copy payment_link here
                    'redirect_url': upi_string,  # For backward compatibility
                    'expires_in': 0,
                    'vpa': '',
                    'pg_partner': 'PAYTOUCHPAYIN',
                    'qr_data': qr_result['data']
                }
            else:
                # Update status to failed
                error_message = qr_result.get('error', 'QR generation failed')
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = 'FAILED', remark = %s
                    WHERE txn_id = %s
                """, (error_message, txn_id))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                # Return error in the format expected by payin_routes.py
                return {
                    'success': False,
                    'message': error_message,  # payin_routes.py expects 'message' not 'error'
                    'error': error_message
                }
                
        except Exception as e:
            print(f"❌ Error creating payin order: {str(e)}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
            return {
                'success': False,
                'message': str(e),  # payin_routes.py expects 'message' not 'error'
                'error': str(e)
            }
