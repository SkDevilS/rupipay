"""
Oxymoney_Barringer Payment Gateway Integration Service
Handles payin transactions through TransXT API with VPA rotation logic

Key Features:
- 5 VPAs with 9.9 Lakh daily limit per VPA (Total: 49.5 Lakh)
- Automatic VPA rotation when approaching limit (98% threshold)
- Token management (15-minute expiry)
- Checksum generation and validation
- UPI Intent generation
- Status check API
"""

import requests
import json
import os
import hashlib
import threading
from datetime import datetime, timedelta
from config import Config
from database import get_db_connection

class OxymoneyBarringerService:
    # Class-level token storage
    _access_token = None
    _token_expiry = None
    _token_lock = threading.Lock()
    
    def __init__(self):
        """Initialize Oxymoney_Barringer Service"""
        self.base_url = Config.OXY_BAR_BASE_URL
        self.username = Config.OXY_BAR_USERNAME
        self.password = Config.OXY_BAR_PASSWORD
        self.secret_key = Config.OXY_BAR_SECRET_KEY
        
        # Load 5 VPAs from environment
        self.vpas = [
            Config.OXY_BAR_VPA1,
            Config.OXY_BAR_VPA2,
            Config.OXY_BAR_VPA3,
            Config.OXY_BAR_VPA4,
            Config.OXY_BAR_VPA5
        ]
        
        # VPA limit (9.9 Lakh = 990000)
        self.vpa_daily_limit = 990000.00
        # Safety threshold (99.5% of limit = 985000)
        self.vpa_safety_threshold = 985000.00
        
        # Total daily limit across all 5 VPAs (9.9 Lakh × 5 = 49.5 Lakh)
        self.total_daily_limit = 4950000.00
        # Maximum allowed usage before blocking (49.5 Lakh - full capacity)
        self.total_max_threshold = 4950000.00
        
        print(f"🔐 Oxymoney_Barringer Service Initialized")
        print(f"  Base URL: {self.base_url}")
        print(f"  Username: {self.username}")
        print(f"  VPAs loaded: {len(self.vpas)}")
        print(f"  VPA Daily Limit: ₹{self.vpa_daily_limit:,.2f}")
        print(f"  Safety Threshold: ₹{self.vpa_safety_threshold:,.2f}")
        print(f"  Total Daily Limit (All VPAs): ₹{self.total_daily_limit:,.2f}")
        print(f"  Total Max Threshold: ₹{self.total_max_threshold:,.2f}")
    
    def generate_access_token(self, force_refresh=False):
        """
        Generate JWT access token from TransXT
        POST /api/1.0/auth
        
        Token is valid for 15 minutes. This method uses thread-safe locking.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
        
        Returns:
            Access token string or None
        """
        try:
            # Thread-safe token check and generation
            with self._token_lock:
                # Check if token is still valid (unless force refresh)
                if not force_refresh and self._access_token and self._token_expiry:
                    if datetime.now() < self._token_expiry:
                        remaining_seconds = (self._token_expiry - datetime.now()).seconds
                        print(f"✓ Using cached access token (expires in {remaining_seconds}s)")
                        return self._access_token
                
                print(f"🔑 Generating new Oxymoney_Barringer access token...")
                
                url = f"{self.base_url}/api/1.0/auth"
                
                # Prepare payload
                payload = {
                    "payload": {
                        "userName": self.username,
                        "password": self.password
                    },
                    "checksum": "92992"  # Hardcoded as per documentation
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {Config.OXY_BAR_INITIAL_AUTH_TOKEN}'
                }
                
                print(f"📤 Token request to: {url}")
                
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                print(f"📥 Token response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Token generation failed: {response.text}")
                    return None
                
                result = response.json()
                
                # Check response
                if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                    self._access_token = result.get('token')
                    
                    if not self._access_token:
                        print(f"❌ No access token in response: {result}")
                        return None
                    
                    # Token expires in 15 minutes (subtract 60 seconds for safety)
                    self._token_expiry = datetime.now() + timedelta(seconds=840)  # 14 minutes
                    
                    print(f"✅ Access token generated successfully")
                    print(f"  Token: {self._access_token[:20]}...")
                    print(f"  Expires in: 15 minutes")
                    
                    return self._access_token
                else:
                    print(f"❌ Token generation error: {result.get('errorMsg', 'Unknown error')}")
                    return None
                
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_checksum(self, payload_dict):
        """
        Generate checksum for request
        POST /api/1.0/checksum
        
        Args:
            payload_dict: Dictionary of request parameters
            
        Returns:
            str: Checksum string or None
        """
        try:
            # Get access token
            token = self.generate_access_token()
            if not token:
                return None
            
            url = f"{self.base_url}/api/1.0/checksum"
            
            # Prepare request
            request_body = {
                "payload": payload_dict,
                "checksum": "92992"  # Hardcoded as per documentation
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.post(url, json=request_body, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Checksum generation failed: {response.text}")
                return None
            
            result = response.json()
            
            if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                checksum = result.get('response', {}).get('checksum')
                print(f"✓ Checksum generated: {checksum[:20]}...")
                return checksum
            else:
                print(f"❌ Checksum error: {result.get('errorMsg', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Checksum generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_available_vpa(self, amount):
        """
        Get available VPA based on daily usage
        Automatically rotates to next VPA if current one is near limit
        
        Args:
            amount: Transaction amount
            
        Returns:
            tuple: (vpa_string, vpa_index) or (None, None) if all VPAs are at limit
        """
        try:
            conn = get_db_connection()
            if not conn:
                return None, None
            
            with conn.cursor() as cursor:
                # Get today's date
                today = datetime.now().date()
                
                # FIRST: Check total usage across all VPAs
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_usage
                    FROM oxymoney_barringer_vpa_usage
                    WHERE DATE(created_at) = %s
                """, (today,))
                
                result = cursor.fetchone()
                total_usage_all_vpas = float(result['total_usage'])
                
                # Check if total usage + new amount exceeds the maximum threshold (45 Lakh)
                if (total_usage_all_vpas + amount) > self.total_max_threshold:
                    print(f"❌ TOTAL VPA LIMIT EXCEEDED!")
                    print(f"  Current total usage: ₹{total_usage_all_vpas:,.2f}")
                    print(f"  Transaction amount: ₹{amount:,.2f}")
                    print(f"  Would be: ₹{(total_usage_all_vpas + amount):,.2f}")
                    print(f"  Maximum allowed: ₹{self.total_max_threshold:,.2f} (45 Lakh)")
                    print(f"  Total capacity: ₹{self.total_daily_limit:,.2f} (49.5 Lakh)")
                    print(f"⚠️  Payment gateway limit reached. Please try again after midnight (00:00 IST)")
                    return None, None
                
                # SECOND: Check individual VPA usage and find available VPA
                for idx, vpa in enumerate(self.vpas):
                    # Get today's usage for this VPA
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_usage
                        FROM oxymoney_barringer_vpa_usage
                        WHERE vpa = %s AND DATE(created_at) = %s
                    """, (vpa, today))
                    
                    result = cursor.fetchone()
                    total_usage = float(result['total_usage'])
                    
                    # Check if this VPA can handle the transaction
                    if (total_usage + amount) <= self.vpa_safety_threshold:
                        print(f"✓ Selected VPA {idx + 1}: {vpa}")
                        print(f"  Current VPA usage: ₹{total_usage:,.2f}")
                        print(f"  After transaction: ₹{(total_usage + amount):,.2f}")
                        print(f"  Remaining VPA capacity: ₹{(self.vpa_safety_threshold - total_usage - amount):,.2f}")
                        print(f"  Total usage (all VPAs): ₹{total_usage_all_vpas:,.2f} / ₹{self.total_max_threshold:,.2f}")
                        return vpa, idx
                    else:
                        print(f"⚠ VPA {idx + 1} near limit: ₹{total_usage:,.2f} / ₹{self.vpa_daily_limit:,.2f}")
                
                # All VPAs are at or near limit
                print(f"❌ All VPAs are at or near daily limit!")
                print(f"⚠️  Total daily capacity: ₹{self.vpa_daily_limit * len(self.vpas):,.2f} (5 VPAs × ₹9.9 Lakh)")
                print(f"⚠️  Total capacity used: ₹{total_usage_all_vpas:,.2f}")
                print(f"⚠️  VPA usage will automatically reset at midnight (00:00 IST)")
                print(f"⚠️  After reset, all 5 VPAs will start fresh with ₹9.9 Lakh limit each")
                return None, None
                
        except Exception as e:
            print(f"❌ Get available VPA error: {e}")
            import traceback
            traceback.print_exc()
            return None, None
        finally:
            if conn:
                conn.close()
    
    def record_vpa_usage(self, vpa, amount, txn_id, merchant_id):
        """
        Record VPA usage in database
        
        Args:
            vpa: VPA string
            amount: Transaction amount
            txn_id: Transaction ID
            merchant_id: Merchant ID
        """
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO oxymoney_barringer_vpa_usage (
                        vpa, amount, txn_id, merchant_id, created_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                """, (vpa, amount, txn_id, merchant_id))
                
                conn.commit()
                print(f"✓ VPA usage recorded: {vpa} - ₹{amount}")
                return True
                
        except Exception as e:
            print(f"❌ Record VPA usage error: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_vpa_usage_stats(self):
        """
        Get usage statistics for all VPAs (today)
        Only counts successful transactions
        
        Returns:
            dict: VPA usage stats with total usage information
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'vpa_stats': [], 'total_usage': 0}
            
            with conn.cursor() as cursor:
                today = datetime.now().date()
                
                # Get total usage across all VPAs
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_usage
                    FROM oxymoney_barringer_vpa_usage
                    WHERE DATE(created_at) = %s
                """, (today,))
                
                total_result = cursor.fetchone()
                total_usage_all_vpas = float(total_result['total_usage'])
                
                stats = []
                for idx, vpa in enumerate(self.vpas):
                    # Get today's usage (only from oxymoney_barringer_vpa_usage table which records SUCCESS only)
                    cursor.execute("""
                        SELECT 
                            COALESCE(SUM(amount), 0) as total_usage,
                            COUNT(*) as transaction_count
                        FROM oxymoney_barringer_vpa_usage
                        WHERE vpa = %s AND DATE(created_at) = %s
                    """, (vpa, today))
                    
                    result = cursor.fetchone()
                    total_usage = float(result['total_usage'])
                    transaction_count = result['transaction_count']
                    
                    # Calculate percentage
                    usage_percentage = (total_usage / self.vpa_daily_limit) * 100
                    remaining = self.vpa_daily_limit - total_usage
                    
                    stats.append({
                        'vpa_index': idx + 1,
                        'vpa': vpa,
                        'total_usage': total_usage,
                        'transaction_count': transaction_count,
                        'daily_limit': self.vpa_daily_limit,
                        'remaining': remaining,
                        'usage_percentage': round(usage_percentage, 2),
                        'status': 'AVAILABLE' if total_usage < self.vpa_safety_threshold else 'NEAR_LIMIT',
                        'note': 'Only successful transactions counted'
                    })
                
                # Calculate total usage percentage
                total_usage_percentage = (total_usage_all_vpas / self.total_daily_limit) * 100
                total_remaining = self.total_daily_limit - total_usage_all_vpas
                
                # Check if approaching max threshold
                approaching_limit = total_usage_all_vpas >= self.total_max_threshold
                
                return {
                    'vpa_stats': stats,
                    'total_usage': total_usage_all_vpas,
                    'total_daily_limit': self.total_daily_limit,
                    'total_max_threshold': self.total_max_threshold,
                    'total_remaining': total_remaining,
                    'total_usage_percentage': round(total_usage_percentage, 2),
                    'approaching_limit': approaching_limit,
                    'limit_status': 'BLOCKED' if approaching_limit else 'AVAILABLE'
                }
                
        except Exception as e:
            print(f"❌ Get VPA usage stats error: {e}")
            return {'vpa_stats': [], 'total_usage': 0}
        finally:
            if conn:
                conn.close()
    
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
        Create payment intent via Oxymoney_Barringer
        POST /api/1.2/upi/intent/{bpmidentifier}/{uniqueClientRefId}
        
        order_data should contain:
        - amount
        - orderid
        - payee_fname
        - payee_mobile
        - payee_email
        - note (optional)
        - expiryValue (optional, default 1 minute)
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
                
                # Get available VPA
                selected_vpa, vpa_index = self.get_available_vpa(amount)
                
                if not selected_vpa:
                    return {
                        'success': False,
                        'message': 'Payment gateway limit reached. Please try again later.'
                    }
                
                # Generate transaction ID
                txn_id = f"OXY_BAR_{merchant_id}_{order_data.get('orderid')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Generate unique client ref ID
                client_ref_id = f"OXBAR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{merchant_id}"
                
                # Get access token
                token = self.generate_access_token()
                if not token:
                    return {'success': False, 'message': 'Failed to generate access token'}
                
                # Prepare intent data
                intent_payload = {
                    "merchantVpa": selected_vpa,
                    "mid": Config.OXY_BAR_MID,
                    "amount": f"{amount:.2f}",
                    "note": order_data.get('note', 'Payment'),
                    "clientRefId": client_ref_id,
                    "expiryValue": str(order_data.get('expiryValue', 1))
                }
                
                # Generate checksum
                checksum = self.generate_checksum(intent_payload)
                if not checksum:
                    return {'success': False, 'message': 'Failed to generate checksum'}
                
                # Prepare request body
                request_body = {
                    "payload": intent_payload,
                    "checksum": checksum
                }
                
                # BPM identifier from config
                bpm_identifier = Config.OXY_BAR_BPM_IDENTIFIER
                
                url = f"{self.base_url}/api/1.2/upi/intent/{bpm_identifier}/{client_ref_id}"
                
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {token}'
                }
                
                print(f"📤 Creating payment intent: {url}")
                print(f"📦 Order ID: {order_data.get('orderid')}")
                print(f"💰 Amount: ₹{amount}")
                print(f"🏦 VPA: {selected_vpa}")
                
                response = requests.post(url, json=request_body, headers=headers, timeout=30)
                
                print(f"📥 Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ API error: {response.text}")
                    return {'success': False, 'message': f'API error: {response.text}'}
                
                result = response.json()
                
                # Check response
                if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                    response_data = result.get('response', {})
                    api_status = response_data.get('apiStatus', {})
                    
                    # Extract payment details
                    ox_txn_id = response_data.get('txnId')
                    intent_url = response_data.get('intentUrl')
                    qr_expiry = response_data.get('qrExpiryDate')
                    rrn = response_data.get('rrn', '')
                    
                    # Extract callback URL from order_data if provided
                    callback_url = order_data.get('callback_url') or order_data.get('callbackurl', '')
                    
                    # Insert transaction into database
                    # Store selected VPA in payment_url field for later reference
                    cursor.execute("""
                        INSERT INTO payin_transactions (
                            txn_id, merchant_id, order_id, amount, charge_amount,
                            net_amount, charge_type, status, pg_partner, pg_txn_id,
                            payee_name, payee_email, payee_mobile,
                            product_info, payment_url, callback_url, 
                            bank_ref_no, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                    """, (
                        txn_id,
                        merchant_id,
                        order_data.get('orderid'),
                        amount,
                        charge_amount,
                        net_amount,
                        charge_type,
                        'INITIATED',
                        'Oxymoney_Barringer',
                        ox_txn_id,
                        order_data.get('payee_fname', ''),
                        order_data.get('payee_email', ''),
                        order_data.get('payee_mobile', ''),
                        order_data.get('note', 'Payment'),
                        f"{intent_url}|VPA:{selected_vpa}",  # Store VPA in payment_url for later use
                        callback_url,
                        rrn
                    ))
                    
                    # DO NOT record VPA usage here - only record on SUCCESS callback
                    # VPA usage will be recorded in callback handler when status = SUCCESS
                    
                    conn.commit()
                    
                    print(f"✅ Payment intent created successfully")
                    print(f"  Oxymoney Txn ID: {ox_txn_id}")
                    print(f"  Intent URL: {intent_url}")
                    print(f"  VPA Used: {selected_vpa}")
                    print(f"  ⚠️  VPA limit will be utilized only on SUCCESS callback")
                    
                    return {
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': order_data.get('orderid'),
                        'amount': amount,
                        'charge_amount': charge_amount,
                        'net_amount': net_amount,
                        'payment_params': {},
                        'qr_string': '',
                        'qr_code_url': '',
                        'upi_link': intent_url,
                        'payment_link': intent_url,
                        'intent_url': intent_url,
                        'expires_in': 0,
                        'vpa': selected_vpa,
                        'pg_partner': 'OXYMONEY_BARRINGER'
                    }
                else:
                    error_msg = result.get('errorMsg', 'Payment intent creation failed')
                    print(f"❌ Error: {error_msg}")
                    return {'success': False, 'message': error_msg}
                    
        except Exception as e:
            print(f"❌ Create payment intent error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def check_transaction_status(self, client_ref_id=None, txn_id=None):
        """
        Check transaction status
        POST /api/1.0/checktxndetails
        
        Args:
            client_ref_id: Client reference ID
            txn_id: Oxymoney transaction ID
            
        Returns:
            dict: Status response
        """
        try:
            # Get access token
            token = self.generate_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to generate access token'}
            
            # Prepare payload
            status_payload = {}
            if client_ref_id:
                status_payload['clientrefid'] = client_ref_id
            if txn_id:
                status_payload['txnid'] = txn_id
            
            if not status_payload:
                return {'success': False, 'message': 'Either client_ref_id or txn_id is required'}
            
            # Generate checksum
            checksum = self.generate_checksum(status_payload)
            if not checksum:
                return {'success': False, 'message': 'Failed to generate checksum'}
            
            # Prepare request body
            request_body = {
                "payload": status_payload,
                "checksum": checksum
            }
            
            url = f"{self.base_url}/api/1.0/checktxndetails"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            print(f"🔍 Checking transaction status: {url}")
            
            response = requests.post(url, json=request_body, headers=headers, timeout=30)
            
            print(f"📥 Status response: {response.status_code}")
            
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.text}'}
            
            result = response.json()
            
            if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                response_data = result.get('response', {})
                return {
                    'success': True,
                    'status': response_data.get('status'),
                    'amount': response_data.get('amount'),
                    'txn_id': response_data.get('txnId'),
                    'rrn': response_data.get('rrn'),
                    'data': response_data
                }
            else:
                return {'success': False, 'message': result.get('errorMsg', 'Status check failed')}
                
        except Exception as e:
            print(f"❌ Check status error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

# Create singleton instance
oxymoney_barringer_service = OxymoneyBarringerService()
