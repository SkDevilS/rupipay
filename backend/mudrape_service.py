"""
Mudrape Payment Gateway Integration Service
Handles payin transactions through Mudrape
"""

import requests
import json
import os
import threading
import time
from datetime import datetime
from config import Config
from database import get_db_connection
from timezone_utils import parse_mudrape_timestamp, get_ist_now, ist_to_mysql_format
import uuid

class MudrapeService:
    def __init__(self):
        self.base_url = Config.MUDRAPE_BASE_URL
        self.api_key = Config.MUDRAPE_API_KEY
        self.api_secret = Config.MUDRAPE_API_SECRET
        self.user_id = Config.MUDRAPE_USER_ID
        self.merchant_mid = Config.MUDRAPE_MERCHANT_MID
        self.merchant_email = Config.MUDRAPE_MERCHANT_EMAIL
        self.merchant_secret = Config.MUDRAPE_MERCHANT_SECRET
        self.token = None
        self.token_expiry = None
    
    def get_headers(self, include_auth=False):
        """Get request headers"""
        headers = {
            'x-api-key': self.api_key,
            'x-api-secret': self.api_secret,
            'Content-Type': 'application/json'
        }
        
        if include_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        return headers
    
    def generate_token(self):
        """Generate authentication token"""
        try:
            url = f"{self.base_url}/api/api-mudrape/genrate-token"
            
            payload = {
                'mid': self.merchant_mid,
                'email': self.merchant_email,
                'secretkey': self.merchant_secret
            }
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=payload,
                timeout=30
            )
            
            # Accept both 200 and 201 status codes
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success'):
                    self.token = data.get('token')
                    return {'success': True, 'token': self.token}
                else:
                    return {'success': False, 'message': data.get('message', 'Token generation failed')}
            else:
                return {'success': False, 'message': f'Token generation failed: {response.text}'}
                
        except Exception as e:
            print(f"Generate token error: {e}")
            return {'success': False, 'message': f'Token generation error: {str(e)}'}
    
    def generate_txn_id(self, merchant_id, order_id):
        """Generate unique 20-digit transaction ID for Mudrape RefID"""
        import random
        # Generate a 20-digit unique number
        # Format: timestamp (14 digits) + random (6 digits) = 20 digits
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')  # 14 digits
        random_part = str(random.randint(100000, 999999))  # 6 digits
        return f"{timestamp}{random_part}"  # Total 20 digits
    
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
        Create payin order via Mudrape
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_mobile
        - payee_email
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
                
                # Generate unique 20-digit RefID
                ref_id = self.generate_txn_id(merchant_id, order_data.get('orderid'))
                
                # Also create our internal transaction ID
                txn_id = f"MUDRAPE_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Ensure token is valid
                if not self.token:
                    token_result = self.generate_token()
                    if not token_result['success']:
                        return token_result
                
                # Prepare Mudrape order data
                firstname = order_data.get('payee_fname', '')
                lastname = order_data.get('payee_lname', '')
                email = order_data.get('payee_email', '')
                phone = order_data.get('payee_mobile', '')
                
                # Create order on Mudrape using NEW endpoint (updated by Mudrape team)
                url = f"{self.base_url}/api/api-payment/create-order"
                
                payload = {
                    'RefID': ref_id,  # 20-digit unique reference ID (capital R as per new API)
                    'Amount': str(int(amount)),  # Amount as string (as per new API format)
                    'Customer_Name': f"{firstname} {lastname}".strip(),  # Customer name
                    'Customer_Mobile': phone,  # Customer mobile
                    'Customer_Email': email,  # Customer email
                    'userId': self.user_id  # Required by Mudrape API
                }
                
                print(f"Creating Mudrape order with payload: {payload}")
                print(f"Using token: {self.token[:20]}..." if self.token else "No token!")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(include_auth=True),
                    json=payload,
                    timeout=30
                )
                
                print(f"Mudrape API Response Status: {response.status_code}")
                print(f"Mudrape API Response: {response.text}")
                
                # Accept both 200 and 201 status codes
                if response.status_code not in [200, 201]:
                    error_msg = f'Mudrape API error: {response.text}'
                    print(error_msg)
                    return {'success': False, 'message': error_msg}
                
                mudrape_response = response.json()
                print(f"Mudrape Response JSON: {mudrape_response}")
                
                if not mudrape_response.get('success'):
                    error_msg = mudrape_response.get('message', 'Order creation failed')
                    error_details = mudrape_response.get('error', '')
                    full_error = f"{error_msg}. {error_details}" if error_details else error_msg
                    print(f"Mudrape order creation failed: {full_error}")
                    return {'success': False, 'message': full_error}
                
                # Extract QR and UPI data from Mudrape response
                response_data = mudrape_response.get('data', {})
                qr_string = response_data.get('qrString') or response_data.get('qr_string') or response_data.get('qrCode') or ''
                upi_link = response_data.get('upiLink') or response_data.get('upi_link') or response_data.get('upiIntent') or ''
                mudrape_txn_id = response_data.get('txnId') or response_data.get('transactionId') or response_data.get('transaction_id') or ref_id
                
                # Validate that we got the required data
                if not upi_link and not qr_string:
                    print(f"No UPI link or QR string in response: {mudrape_response}")
                    return {'success': False, 'message': 'No payment link received from Mudrape'}
                
                # Extract callback URL from order_data
                # If no callback URL provided, use default internal callback URL
                callback_url = order_data.get('callbackurl') or order_data.get('callback_url')
                
                if not callback_url:
                    # Use default internal callback URL for dashboard-generated QR codes
                    # This ensures Mudrape can notify us when payment succeeds
                    from config import Config
                    base_url = os.getenv('BACKEND_URL', 'https://admin.moneyone.co.in')
                    callback_url = f"{base_url}/api/callback/mudrape/payin"
                    print(f"⚠ No callback URL provided, using default: {callback_url}")
                
                # IMPORTANT: Store ref_id as order_id because Mudrape sends ref_id in callbacks
                # The merchant's original orderid is stored in txn_id for reference
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
                    txn_id, merchant_id, ref_id, amount,  # Store ref_id as order_id
                    charge_amount, charge_type, net_amount,
                    f"{firstname} {lastname}".strip(), email, phone, 
                    order_data.get('productinfo', 'Payment'),
                    'INITIATED', 'Mudrape', mudrape_txn_id,
                    callback_url
                ))
                
                print(f"✓ Transaction created:")
                print(f"  - TXN ID: {txn_id}")
                print(f"  - Order ID (ref_id): {ref_id}")
                print(f"  - Merchant Order ID: {order_data.get('orderid')}")
                print(f"  - Callback URL: {callback_url if callback_url else 'NOT PROVIDED'}")
                
                conn.commit()
                
                # Schedule automatic status check after 60 seconds
                # This ensures status gets updated even if callback fails or is delayed
                self.auto_check_status_after_delay(ref_id, delay_seconds=60)
                print(f"✓ Scheduled automatic status check for {ref_id} in 60 seconds")
                
                return {
                    'success': True,
                    'txn_id': txn_id,
                    'order_id': ref_id,  # Return ref_id as order_id (this is what Mudrape will use in callbacks)
                    'merchant_order_id': order_data.get('orderid'),  # Original merchant order ID for reference
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'net_amount': net_amount,
                    'qr_string': qr_string,
                    'upi_link': upi_link,
                    'mudrape_txn_id': mudrape_txn_id
                }
                
        except Exception as e:
            print(f"Create payin order error: {e}")
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def check_payment_status(self, identifier):
        """
        Check payment status on Mudrape using new GET endpoint
        
        Args:
            identifier: Can be order_id (refId) or Mudrape transaction ID (txnId)
        
        Returns:
            dict: Status information
        """
        try:
            # Ensure token is valid
            if not self.token:
                token_result = self.generate_token()
                if not token_result['success']:
                    return token_result
            
            print(f"Checking Mudrape payin status for identifier: {identifier}")
            
            # NEW: Use GET endpoint with query parameter
            # URL format: https://agentmudrape.com/api/api-mudrape/status?txnId=MPAY31716296742
            url = f"{self.base_url}/api/api-mudrape/status"
            
            # Try with txnId first (if identifier looks like a Mudrape transaction ID)
            if identifier.startswith('TPA') or identifier.startswith('MUDRAPE_TXN') or identifier.startswith('MPAY'):
                print(f"Attempting with txnId as query parameter...")
                params = {'txnId': identifier}
                print(f"Request URL: {url}?txnId={identifier}")
                
                response = requests.get(
                    url,
                    headers=self.get_headers(include_auth=True),
                    params=params,
                    timeout=30
                )
                
                print(f"Response: {response.status_code} - {response.text[:500]}")
                
                if response.status_code in [200, 201] and response.json().get('success'):
                    mudrape_response = response.json()
                else:
                    # Fall through to try refId
                    print(f"txnId failed, trying refId as query parameter...")
                    params = {'refId': identifier}
                    print(f"Request URL: {url}?refId={identifier}")
                    
                    response = requests.get(
                        url,
                        headers=self.get_headers(include_auth=True),
                        params=params,
                        timeout=30
                    )
                    
                    print(f"Response: {response.status_code} - {response.text[:500]}")
                    
                    if response.status_code not in [200, 201]:
                        return {
                            'success': False,
                            'message': f'Transaction not found in Mudrape. This usually means the payment was not initiated yet or the transaction ID is incorrect.',
                            'note': 'Callbacks from Mudrape are required to get the Mudrape transaction ID'
                        }
                    
                    mudrape_response = response.json()
            else:
                # Assume it's a refId (order_id)
                print(f"Attempting with refId as query parameter...")
                params = {'refId': identifier}
                print(f"Request URL: {url}?refId={identifier}")
                
                response = requests.get(
                    url,
                    headers=self.get_headers(include_auth=True),
                    params=params,
                    timeout=30
                )
                
                print(f"Response: {response.status_code} - {response.text[:500]}")
                
                if response.status_code not in [200, 201]:
                    return {
                        'success': False,
                        'message': f'Transaction not found in Mudrape. This usually means the payment was not initiated yet.',
                        'note': 'The transaction may not exist in Mudrape system until customer scans QR and initiates payment'
                    }
                
                mudrape_response = response.json()
            
            # Extract data from Mudrape response
            if not mudrape_response.get('success'):
                return {
                    'success': False,
                    'message': mudrape_response.get('message', 'Status check failed')
                }
            
            data = mudrape_response.get('data', {})
            
            # Extract status
            status = data.get('status', 'INITIATED')
            if status.upper() == 'PENDING':
                status = 'INITIATED'  # Map PENDING to INITIATED
            else:
                status = status.upper()
            
            # Extract timestamps
            created_at = data.get('createdAt')
            processed_at = data.get('processedAt') or data.get('transactionDate') or data.get('completedAt')
            
            # Convert timestamps from UTC to IST using timezone utilities
            created_at_ist = parse_mudrape_timestamp(created_at) if created_at else None
            processed_at_ist = parse_mudrape_timestamp(processed_at) if processed_at else None
            
            # Extract UTR - Mudrape may not provide it directly, try multiple sources
            utr = data.get('utr') or data.get('bankRefNo') or data.get('bank_ref_no') or data.get('UTR')
            
            # If no UTR, try to extract transaction reference from UPI string
            if not utr:
                qr_string = data.get('qrString') or data.get('upiLink')
                if qr_string and 'tr=' in qr_string:
                    # Extract tr parameter from UPI string
                    import re
                    match = re.search(r'tr=([^&]+)', qr_string)
                    if match:
                        utr = match.group(1)
                        print(f"Extracted UTR from UPI string: {utr}")
            
            result = {
                'success': True,
                'status': status,
                'txnId': data.get('txnId') or data.get('transactionId'),
                'refId': data.get('refId') or data.get('RefID') or identifier,
                'amount': data.get('amount'),
                'utr': utr,
                'payment_mode': data.get('paymentMode') or data.get('channel') or 'UPI',
                'created_at': created_at_ist,
                'completed_at': processed_at_ist,
                'message': mudrape_response.get('message', 'Status retrieved successfully')
            }
            
            print(f"Parsed Mudrape Status: {result}")
            
            return result
            
        except Exception as e:
            print(f"Check payment status error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}
    
    def auto_check_status_after_delay(self, order_id, delay_seconds=60):
        """
        Automatically check payment status after a delay
        This ensures status gets updated even if callback fails
        
        Args:
            order_id: The order_id (ref_id) to check
            delay_seconds: Delay before checking (default 60 seconds)
        """
        def check_status_task():
            try:
                print(f"[Auto Status Check] Waiting {delay_seconds} seconds before checking {order_id}...")
                time.sleep(delay_seconds)
                
                print(f"[Auto Status Check] Checking status for {order_id}...")
                
                # Get transaction from database
                conn = get_db_connection()
                if not conn:
                    print(f"[Auto Status Check] Database connection failed")
                    return
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT txn_id, order_id, merchant_id, status, pg_txn_id, net_amount, charge_amount
                            FROM payin_transactions
                            WHERE order_id = %s AND pg_partner = 'Mudrape'
                        """, (order_id,))
                        
                        txn = cursor.fetchone()
                        
                        if not txn:
                            print(f"[Auto Status Check] Transaction not found: {order_id}")
                            return
                        
                        # Only check if still pending
                        if txn['status'] not in ['INITIATED', 'PENDING']:
                            print(f"[Auto Status Check] Transaction already {txn['status']}, skipping")
                            return
                        
                        # Use pg_txn_id if available, otherwise use order_id
                        identifier = txn.get('pg_txn_id') or order_id
                        
                        print(f"[Auto Status Check] Checking Mudrape with identifier: {identifier}")
                        
                        # Check status from Mudrape
                        status_result = self.check_payment_status(identifier)
                        
                        if not status_result.get('success'):
                            print(f"[Auto Status Check] Status check failed: {status_result.get('message')}")
                            return
                        
                        mudrape_status = status_result.get('status', '').upper()
                        print(f"[Auto Status Check] Mudrape status: {mudrape_status}")
                        
                        # Update if status changed to SUCCESS
                        if mudrape_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
                            print(f"[Auto Status Check] Updating {txn['txn_id']} to SUCCESS")
                            
                            # Update transaction
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'SUCCESS',
                                    bank_ref_no = %s,
                                    pg_txn_id = %s,
                                    payment_mode = 'UPI',
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('utr'), status_result.get('txnId'), txn['txn_id']))
                            
                            # Check if wallet already credited (idempotency)
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                            """, (txn['txn_id'],))
                            
                            wallet_already_credited = cursor.fetchone()['count'] > 0
                            
                            if not wallet_already_credited:
                                # Credit merchant unsettled wallet
                                from wallet_service import wallet_service as wallet_svc
                                wallet_result = wallet_svc.credit_unsettled_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=float(txn['net_amount']),
                                    description=f"PayIn received (Auto status check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                if wallet_result['success']:
                                    print(f"[Auto Status Check] ✓ Merchant wallet credited: ₹{txn['net_amount']}")
                                else:
                                    print(f"[Auto Status Check] ✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                                
                                # Credit admin unsettled wallet
                                admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                                    admin_id='admin',
                                    amount=float(txn['charge_amount']),
                                    description=f"PayIn charge (Auto status check) - {order_id}",
                                    reference_id=txn['txn_id']
                                )
                                
                                if admin_wallet_result['success']:
                                    print(f"[Auto Status Check] ✓ Admin wallet credited: ₹{txn['charge_amount']}")
                                else:
                                    print(f"[Auto Status Check] ✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                            else:
                                print(f"[Auto Status Check] ⚠ Wallet already credited, skipping")
                            
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Successfully updated {txn['txn_id']} to SUCCESS")
                        
                        elif mudrape_status == 'FAILED' and txn['status'] != 'FAILED':
                            print(f"[Auto Status Check] Updating {txn['txn_id']} to FAILED")
                            
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'FAILED',
                                    pg_txn_id = %s,
                                    completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status_result.get('txnId'), txn['txn_id']))
                            
                            conn.commit()
                            print(f"[Auto Status Check] ✓ Updated {txn['txn_id']} to FAILED")
                        else:
                            print(f"[Auto Status Check] Status unchanged: {mudrape_status}")
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                print(f"[Auto Status Check] Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Start background thread
        thread = threading.Thread(target=check_status_task, daemon=True)
        thread.start()
        print(f"[Auto Status Check] Scheduled status check for {order_id} in {delay_seconds} seconds")
    
    # ==================== PAYOUT METHODS ====================
    
    def call_upi_payout_api(self, upi_id, client_txn_id, amount, beneficiary_name):
        """
        Simple UPI payout API call to Mudrape (no database operations)
        Returns the API response
        """
        try:
            url = f"{self.base_url}/api/payout/upi"
            
            payload = {
                'userId': 'cmlujaiqv00tw01s6up9o7376',  # Fixed userId for all payouts
                'p1': upi_id,  # UPI ID
                'p3': client_txn_id,  # Client Transaction ID
                'p4': str(amount),  # Amount
                'p5': beneficiary_name  # Beneficiary Name
            }
            
            print(f"Calling Mudrape UPI payout API: {payload}")
            print(f"URL: {url}")
            
            response = requests.post(
                url,
                headers=self.get_headers(include_auth=False),  # No auth token needed, only API keys
                json=payload,
                timeout=30
            )
            
            print(f"Mudrape UPI Payout Response: {response.status_code} - {response.text}")
            
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Mudrape API error: {response.text}'
                }
            
            mudrape_response = response.json()
            
            # Extract status and transaction ID
            status_code = str(mudrape_response.get('status', '10001'))
            mudrape_txn_id = mudrape_response.get('txnId') or mudrape_response.get('transactionId') or ''
            
            # Map Mudrape status to our status
            # Database ENUM: INITIATED, QUEUED, INPROCESS, SUCCESS, FAILED, REVERSED
            if status_code == '10000':
                status = 'SUCCESS'
            elif status_code == '10003':
                status = 'FAILED'
            else:
                status = 'INITIATED'  # Default to INITIATED instead of PENDING
            
            return {
                'success': True,
                'status': status,
                'status_code': status_code,
                'mudrape_txn_id': mudrape_txn_id,
                'message': mudrape_response.get('message', 'Payout initiated'),
                'data': mudrape_response
            }
            
        except Exception as e:
            print(f"UPI payout API call error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'API call error: {str(e)}'}
    
    def call_imps_payout_api(self, account_number, ifsc_code, client_txn_id, amount, beneficiary_name):
        """
        Simple IMPS payout API call to Mudrape (no database operations)
        Returns the API response
        """
        try:
            url = f"{self.base_url}/api/payout/imps"
            
            payload = {
                'userId': 'cmlujaiqv00tw01s6up9o7376',  # Fixed userId for all payouts
                'p1': account_number,  # Account Number
                'p2': ifsc_code,  # IFSC Code
                'p3': client_txn_id,  # Client Transaction ID
                'p4': str(amount),  # Amount
                'p5': beneficiary_name  # Beneficiary Name
            }
            
            print(f"Calling Mudrape IMPS payout API: {payload}")
            print(f"URL: {url}")
            
            response = requests.post(
                url,
                headers=self.get_headers(include_auth=False),  # No auth token needed, only API keys
                json=payload,
                timeout=30
            )
            
            print(f"Mudrape IMPS Payout Response: {response.status_code} - {response.text}")
            
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Mudrape API error: {response.text}'
                }
            
            mudrape_response = response.json()
            
            # Check if Mudrape returned success=false in response body
            if not mudrape_response.get('success', True):
                error_msg = mudrape_response.get('message', 'Payout failed')
                print(f"Mudrape returned success=false: {error_msg}")
                return {
                    'success': False,
                    'message': error_msg
                }
            
            # Extract status - Mudrape uses 'statuscode' (numeric) and 'payoutStatus' (string)
            status_code = str(mudrape_response.get('statuscode', '10001'))
            payout_status = mudrape_response.get('payoutStatus', '')
            mudrape_txn_id = (mudrape_response.get('transactionId') or 
                            mudrape_response.get('apiTxnId') or 
                            mudrape_response.get('txnId') or '')
            
            print(f"Parsed - Status Code: {status_code}, Payout Status: {payout_status}, Mudrape TxnID: {mudrape_txn_id}")
            
            # Map Mudrape status to our status
            # Database ENUM: INITIATED, QUEUED, INPROCESS, SUCCESS, FAILED, REVERSED
            if payout_status and payout_status.strip():
                payout_status_upper = payout_status.upper()
                if payout_status_upper == 'PENDING':
                    status = 'INITIATED'  # Map PENDING to INITIATED
                elif payout_status_upper in ['SUCCESS', 'FAILED']:
                    status = payout_status_upper
                else:
                    status = 'INITIATED'
            elif status_code == '10000':
                status = 'SUCCESS'
            elif status_code == '10003':
                status = 'FAILED'
            else:
                status = 'INITIATED'  # Default to INITIATED instead of PENDING
            
            print(f"Mapped Status: {status}")
            
            return {
                'success': True,
                'status': status,
                'status_code': status_code,
                'mudrape_txn_id': mudrape_txn_id,
                'message': mudrape_response.get('message', 'Payout initiated'),
                'data': mudrape_response
            }
            
        except Exception as e:
            print(f"IMPS payout API call error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'API call error: {str(e)}'}
    
    def create_upi_payout(self, merchant_id, payout_data):
        """
        Create UPI payout via Mudrape
        payout_data should contain:
        - upi_id
        - amount
        - beneficiary_name
        - client_txn_id (optional, will be generated if not provided)
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
                amount = float(payout_data.get('amount', 0))
                if amount <= 0:
                    return {'success': False, 'message': 'Invalid amount'}
                
                # Calculate charges
                charge_amount, net_amount, charge_type = self.calculate_charges(
                    amount, merchant['scheme_id'], 'PAYOUT'
                )
                
                if charge_amount is None:
                    return {'success': False, 'message': 'Failed to calculate charges'}
                
                # Total deduction from wallet = amount + charges
                total_deduction = amount + charge_amount
                
                # Check wallet balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                if not wallet or float(wallet['balance']) < total_deduction:
                    return {'success': False, 'message': 'Insufficient wallet balance'}
                
                # Generate transaction ID
                client_txn_id = payout_data.get('client_txn_id') or f"PAYOUT_{merchant_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Ensure token is valid
                if not self.token:
                    token_result = self.generate_token()
                    if not token_result['success']:
                        return token_result
                
                # Create payout on Mudrape
                url = f"{self.base_url}/api/payout/upi"
                
                payload = {
                    'userId': 'cmlujaiqv00tw01s6up9o7376',  # Fixed userId for all payouts
                    'p1': payout_data.get('upi_id'),  # UPI ID
                    'p3': client_txn_id,  # Client Transaction ID
                    'p4': str(amount),  # Amount
                    'p5': payout_data.get('beneficiary_name')  # Beneficiary Name
                }
                
                print(f"Creating Mudrape UPI payout: {payload}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(include_auth=True),
                    json=payload,
                    timeout=30
                )
                
                print(f"Mudrape Payout Response: {response.status_code} - {response.text}")
                
                if response.status_code not in [200, 201]:
                    return {'success': False, 'message': f'Mudrape payout API error: {response.text}'}
                
                mudrape_response = response.json()
                
                # Extract status and transaction ID
                status_code = mudrape_response.get('status', '10001')  # Default to PENDING
                mudrape_txn_id = mudrape_response.get('txnId') or mudrape_response.get('transactionId') or ''
                
                # Map Mudrape status to our status
                if status_code == '10000':
                    payout_status = 'SUCCESS'
                elif status_code == '10003':
                    payout_status = 'FAILED'
                else:
                    payout_status = 'PENDING'
                
                # Deduct from wallet
                cursor.execute("""
                    UPDATE merchant_wallet
                    SET balance = balance - %s,
                        last_updated = NOW()
                    WHERE merchant_id = %s
                """, (total_deduction, merchant_id))
                
                # Get updated balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet = cursor.fetchone()
                balance_after = float(wallet['balance'])
                balance_before = balance_after + total_deduction
                
                # Create wallet transaction for debit
                cursor.execute("""
                    INSERT INTO wallet_transactions
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, created_at)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, NOW())
                """, (
                    merchant_id,
                    client_txn_id,
                    total_deduction,
                    balance_before,
                    balance_after,
                    f'UPI Payout to {payout_data.get("upi_id")} (Amount: {amount}, Charges: {charge_amount})'
                ))
                
                # Insert payout transaction record
                cursor.execute("""
                    INSERT INTO payout_transactions (
                        txn_id, merchant_id, amount, charge_amount, charge_type,
                        total_deduction, beneficiary_name, beneficiary_account,
                        payout_mode, status, pg_partner, pg_txn_id, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (
                    client_txn_id, merchant_id, amount, charge_amount, charge_type,
                    total_deduction, payout_data.get('beneficiary_name'),
                    payout_data.get('upi_id'), 'UPI', payout_status,
                    'Mudrape', mudrape_txn_id
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'txn_id': client_txn_id,
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'total_deduction': total_deduction,
                    'status': payout_status,
                    'mudrape_txn_id': mudrape_txn_id,
                    'message': 'Payout initiated successfully'
                }
                
        except Exception as e:
            print(f"Create UPI payout error: {e}")
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def create_imps_payout(self, merchant_id, payout_data):
        """
        Create IMPS payout via Mudrape
        payout_data should contain:
        - account_number
        - ifsc_code
        - amount
        - beneficiary_name
        - client_txn_id (optional)
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
                amount = float(payout_data.get('amount', 0))
                if amount <= 0:
                    return {'success': False, 'message': 'Invalid amount'}
                
                # Calculate charges
                charge_amount, net_amount, charge_type = self.calculate_charges(
                    amount, merchant['scheme_id'], 'PAYOUT'
                )
                
                if charge_amount is None:
                    return {'success': False, 'message': 'Failed to calculate charges'}
                
                # Total deduction from wallet = amount + charges
                total_deduction = amount + charge_amount
                
                # Check wallet balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                if not wallet or float(wallet['balance']) < total_deduction:
                    return {'success': False, 'message': 'Insufficient wallet balance'}
                
                # Generate transaction ID
                client_txn_id = payout_data.get('client_txn_id') or f"PAYOUT_{merchant_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Ensure token is valid
                if not self.token:
                    token_result = self.generate_token()
                    if not token_result['success']:
                        return token_result
                
                # Create payout on Mudrape
                url = f"{self.base_url}/api/payout/imps"
                
                payload = {
                    'userId': 'cmlujaiqv00tw01s6up9o7376',  # Fixed userId for all payouts
                    'p1': payout_data.get('account_number'),  # Account Number
                    'p2': payout_data.get('ifsc_code'),  # IFSC Code
                    'p3': client_txn_id,  # Client Transaction ID
                    'p4': str(amount),  # Amount
                    'p5': payout_data.get('beneficiary_name')  # Beneficiary Name
                }
                
                print(f"Creating Mudrape IMPS payout: {payload}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(include_auth=True),
                    json=payload,
                    timeout=30
                )
                
                print(f"Mudrape Payout Response: {response.status_code} - {response.text}")
                
                if response.status_code not in [200, 201]:
                    return {'success': False, 'message': f'Mudrape payout API error: {response.text}'}
                
                mudrape_response = response.json()
                
                # Extract status and transaction ID
                status_code = mudrape_response.get('status', '10001')
                mudrape_txn_id = mudrape_response.get('txnId') or mudrape_response.get('transactionId') or ''
                
                # Map Mudrape status to our status
                if status_code == '10000':
                    payout_status = 'SUCCESS'
                elif status_code == '10003':
                    payout_status = 'FAILED'
                else:
                    payout_status = 'PENDING'
                
                # Deduct from wallet
                cursor.execute("""
                    UPDATE merchant_wallet
                    SET balance = balance - %s,
                        last_updated = NOW()
                    WHERE merchant_id = %s
                """, (total_deduction, merchant_id))
                
                # Get updated balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet = cursor.fetchone()
                balance_after = float(wallet['balance'])
                balance_before = balance_after + total_deduction
                
                # Create wallet transaction for debit
                cursor.execute("""
                    INSERT INTO wallet_transactions
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, created_at)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, NOW())
                """, (
                    merchant_id,
                    client_txn_id,
                    total_deduction,
                    balance_before,
                    balance_after,
                    f'IMPS Payout to {payout_data.get("account_number")} (Amount: {amount}, Charges: {charge_amount})'
                ))
                
                # Insert payout transaction record
                cursor.execute("""
                    INSERT INTO payout_transactions (
                        txn_id, merchant_id, amount, charge_amount, charge_type,
                        total_deduction, beneficiary_name, beneficiary_account,
                        beneficiary_ifsc, payout_mode, status, pg_partner, pg_txn_id, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (
                    client_txn_id, merchant_id, amount, charge_amount, charge_type,
                    total_deduction, payout_data.get('beneficiary_name'),
                    payout_data.get('account_number'), payout_data.get('ifsc_code'),
                    'IMPS', payout_status, 'Mudrape', mudrape_txn_id
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'txn_id': client_txn_id,
                    'amount': amount,
                    'charge_amount': charge_amount,
                    'total_deduction': total_deduction,
                    'status': payout_status,
                    'mudrape_txn_id': mudrape_txn_id,
                    'message': 'Payout initiated successfully'
                }
                
        except Exception as e:
            print(f"Create IMPS payout error: {e}")
            return {'success': False, 'message': f'Internal error: {str(e)}'}
        finally:
            if conn:
                conn.close()
    
    def check_payout_status(self, client_txn_id):
        """Check payout status on Mudrape"""
        try:
            # Ensure token is valid
            if not self.token:
                token_result = self.generate_token()
                if not token_result['success']:
                    return token_result
            
            url = f"{self.base_url}/api/payout/status"
            
            params = {
                'clientTxnId': client_txn_id
            }
            
            print(f"Checking payout status for: {client_txn_id}")
            print(f"URL: {url}")
            
            response = requests.get(
                url,
                headers=self.get_headers(include_auth=True),
                params=params,
                timeout=30
            )
            
            print(f"Mudrape Status Check Response: {response.status_code} - {response.text}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'Status check failed: {response.text}'}
            
            data = response.json()
            
            # Extract status - check multiple possible fields
            status_code = data.get('statusCode') or data.get('statuscode')
            payout_status = data.get('payoutStatus')
            status_string = data.get('status')
            
            print(f"Extracted - statusCode: {status_code}, payoutStatus: {payout_status}, status: {status_string}")
            
            # Map status to our database ENUM: INITIATED, QUEUED, INPROCESS, SUCCESS, FAILED, REVERSED
            if status_code == 10000 or (payout_status and payout_status.upper() == 'SUCCESS'):
                status_text = 'SUCCESS'
            elif status_code == 10003 or (payout_status and payout_status.upper() == 'FAILED'):
                status_text = 'FAILED'
            elif payout_status and payout_status.upper() == 'PENDING':
                status_text = 'INITIATED'
            else:
                status_text = 'INITIATED'  # Default to INITIATED
            
            print(f"Mapped Status: {status_text}")
            
            # Extract UTR from multiple possible locations
            utr = (data.get('utr') or 
                   data.get('uniqueId') or
                   (data.get('data', {}).get('txnId') if data.get('data') else None) or
                   (data.get('data', {}).get('bankRefNo') if data.get('data') else None))
            
            # Extract timestamps from data
            created_at = None
            completed_at = None
            
            if data.get('data'):
                # Extract creation time (when payout was initiated)
                created_at_raw = data['data'].get('createdAt')
                if created_at_raw:
                    created_at = parse_mudrape_timestamp(created_at_raw)
                    print(f"Created At (IST): {created_at}")
                
                # Extract completion time (when payout was processed)
                if status_text in ['SUCCESS', 'FAILED']:
                    processed_at_raw = (data['data'].get('processedAt') or 
                                       data['data'].get('transactionDate'))
                    if processed_at_raw:
                        completed_at = parse_mudrape_timestamp(processed_at_raw)
                        print(f"Completed At (IST): {completed_at}")
            
            return {
                'success': True,
                'status': status_text,
                'status_code': status_code,
                'txnId': data.get('txnId'),
                'clientTxnId': client_txn_id,
                'amount': data.get('amount'),
                'utr': utr,
                'message': data.get('message'),
                'created_at': created_at,
                'completed_at': completed_at,
                'raw_data': data  # Include raw data for debugging
            }
            
        except Exception as e:
            print(f"Check payout status error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}
    
    def update_payout_status(self, txn_id, status, pg_txn_id=None, utr=None, error_message=None):
        """Update payout transaction status in database"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                update_fields = ['status = %s', 'updated_at = NOW()']
                params = [status]
                
                if status in ['SUCCESS', 'FAILED', 'CANCELLED']:
                    update_fields.append('completed_at = NOW()')
                
                if pg_txn_id:
                    update_fields.append('pg_txn_id = %s')
                    params.append(pg_txn_id)
                
                if utr:
                    update_fields.append('utr = %s')
                    params.append(utr)
                
                if error_message:
                    update_fields.append('error_message = %s')
                    params.append(error_message)
                
                params.append(txn_id)
                
                query = f"""
                    UPDATE payout_transactions 
                    SET {', '.join(update_fields)}
                    WHERE txn_id = %s
                """
                
                cursor.execute(query, params)
                conn.commit()
                
                return True
                
        except Exception as e:
            print(f"Update payout status error: {e}")
            return False
        finally:
            if conn:
                conn.close()

# Create singleton instance
mudrape_service = MudrapeService()
