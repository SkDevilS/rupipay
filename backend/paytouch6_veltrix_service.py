"""
PayTouch6_Veltrix Payout Service Integration
Handles payout transactions through PayTouch6 (Veltrix)
This is a duplicate of PayTouch2/PayTouch3/PayTouch4/PayTouch5 service with different credentials and PT6_VE_TXN prefix
"""

import requests
import json
from datetime import datetime
from database import get_db_connection
from config import Config
import uuid

class PayTouch6Service:
    def __init__(self):
        self.base_url = Config.PAYTOUCH6_VELTRIX_BASE_URL
        self.token = Config.PAYTOUCH6_VELTRIX_TOKEN
    
    def get_headers(self):
        """Get request headers"""
        return {
            'Content-Type': 'application/json'
        }
    
    def generate_txn_id(self, merchant_id, reference_id):
        """Generate unique transaction ID with PT6_VE_TXN prefix"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"PT6_VE_TXN_{merchant_id}_{reference_id}_{timestamp}"
    
    def calculate_charges(self, amount, scheme_id, service_type='PAYOUT'):
        """Calculate payout charges based on scheme"""
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
                    AND service_type = %s
                    AND %s BETWEEN min_amount AND max_amount
                    LIMIT 1
                """, (scheme_id, service_type, amount))
                
                charge = cursor.fetchone()
                
                if charge:
                    charge_amount = 0
                    if charge['charge_type'] == 'PERCENTAGE':
                        charge_amount = (amount * float(charge['charge_value'])) / 100
                    else:
                        charge_amount = float(charge['charge_value'])
                    
                    net_amount = amount + charge_amount
                    
                    conn.close()
                    return {
                        'charge_amount': round(charge_amount, 2),
                        'charge_type': charge['charge_type'],
                        'net_amount': round(net_amount, 2)
                    }
                else:
                    # No charge configuration found, return zero charges
                    print(f"No charge configuration found for scheme_id={scheme_id}, service_type={service_type}, amount={amount}")
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
    
    def initiate_payout(self, merchant_id, payout_data, admin_id=None):
        """
        Initiate payout transaction via PayTouch6_Veltrix
        
        Args:
            merchant_id: Merchant ID (or None for admin payouts)
            payout_data: Dictionary containing:
                - reference_id: Unique reference ID
                - amount: Payout amount
                - bene_name: Beneficiary name
                - bene_account: Beneficiary account number
                - bene_ifsc: IFSC code
                - payment_mode: IMPS/NEFT/RTGS
                - bank_name: Bank name
                - bank_branch: Bank branch
                - narration: Payment description
                - callback_url: Optional callback URL
            admin_id: Admin ID (if admin payout)
        
        Returns:
            dict: Result with success status and transaction details
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Check if this is an admin payout
                is_admin_payout = admin_id is not None or (merchant_id and merchant_id.startswith('ADMIN_'))
                
                if is_admin_payout:
                    # For admin payouts, use default scheme or no charges
                    charges = {
                        'charge_amount': 0.00,
                        'charge_type': 'FIXED',
                        'net_amount': payout_data['amount']
                    }
                    
                    # Extract admin_id if passed as merchant_id
                    if merchant_id and merchant_id.startswith('ADMIN_'):
                        admin_id = merchant_id.replace('ADMIN_', '')
                        merchant_id = None
                else:
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
                    charges = self.calculate_charges(
                        payout_data['amount'],
                        merchant['scheme_id'],
                        'PAYOUT'
                    )
                    
                    if not charges:
                        conn.close()
                        return {'success': False, 'message': 'Unable to calculate charges'}
                    
                    # Skip validation if transaction already exists (caller handled it)
                    cursor.execute("""
                        SELECT txn_id FROM payout_transactions
                        WHERE reference_id = %s AND pg_partner = 'PayTouch6_Veltrix'
                    """, (payout_data['reference_id'],))
                    
                    if not cursor.fetchone():
                        # Validate merchant wallet balance
                        total_deduction = float(payout_data['amount']) + float(charges['charge_amount'])
                        
                        cursor.execute("""
                            SELECT COALESCE(settled_balance, 0) as available_balance
                            FROM merchant_wallet
                            WHERE merchant_id = %s
                        """, (merchant_id,))
                        wallet_result = cursor.fetchone()
                        available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00
                        
                        if total_deduction > available_balance:
                            conn.close()
                            return {
                                'success': False,
                                'message': f'Insufficient balance in wallet, remaining balance: â‚¹{available_balance:.2f}'
                            }
                
                # Check if transaction already exists (created by payout_routes.py)
                cursor.execute("""
                    SELECT txn_id FROM payout_transactions
                    WHERE reference_id = %s AND pg_partner = 'PayTouch6_Veltrix'
                """, (payout_data['reference_id'],))
                
                existing_txn = cursor.fetchone()
                
                if existing_txn:
                    # Transaction already exists, use existing txn_id
                    txn_id = existing_txn['txn_id']
                    print(f"Using existing transaction: {txn_id}")
                else:
                    # Generate transaction ID (only if not exists)
                    identifier = admin_id if is_admin_payout else merchant_id
                    txn_id = self.generate_txn_id(identifier, payout_data['reference_id'])
                    
                    # Insert payout transaction
                    cursor.execute("""
                        INSERT INTO payout_transactions (
                            txn_id, merchant_id, admin_id, reference_id, amount, charge_amount,
                            charge_type, net_amount, bene_name, bene_email, bene_mobile,
                            bene_bank, ifsc_code, account_no, payment_type, purpose,
                            status, pg_partner, callback_url, remarks
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        txn_id, merchant_id, admin_id, payout_data['reference_id'],
                        payout_data['amount'], charges['charge_amount'],
                        charges['charge_type'], charges['net_amount'],
                        payout_data['bene_name'],
                        payout_data.get('bene_email', ''),
                        payout_data.get('bene_mobile', ''),
                        payout_data.get('bank_name', ''),
                        payout_data['bene_ifsc'],
                        payout_data['bene_account'],
                        payout_data.get('payment_mode', 'IMPS'),
                        payout_data.get('narration', 'Payment'),
                        'INITIATED', 'PayTouch6_Veltrix',
                        payout_data.get('callback_url', ''),
                        payout_data.get('remarks', '')
                    ))
                    
                    conn.commit()
                    print(f"Created new transaction: {txn_id}")
                
                # Prepare PayTouch6 API payload
                # IMPORTANT: PayTouch specific requirements (same as PayTouch2/PayTouch3/PayTouch4/PayTouch5):
                # - request_id = order_id (unique identifier)
                # - currency = always "INR"
                # - narration = always "Truaxis"
                # - payment_mode = always "IMPS"
                # - bank_branch = always "oooo"
                payload = {
                    'token': self.token,
                    'request_id': payout_data['reference_id'],  # Use reference_id as order_id
                    'bene_account': payout_data['bene_account'],
                    'bene_ifsc': payout_data['bene_ifsc'],
                    'bene_name': payout_data['bene_name'],
                    'amount': float(payout_data['amount']),
                    'currency': 'INR',  # Always INR
                    'narration': 'Truaxis',  # Always Truaxis
                    'payment_mode': 'IMPS',  # Always IMPS
                    'bank_name': payout_data.get('bank_name', ''),
                    'bank_branch': 'oooo'  # Always oooo
                }
                
                print(f"PayTouch6_Veltrix API Request: {json.dumps(payload, indent=2)}")
                
                # Call PayTouch6 API
                url = f"{self.base_url}/api/payout/v2/transaction"
                
                print(f"=" * 80)
                print(f"CALLING PAYTOUCH6_VELTRIX API")
                print(f"=" * 80)
                print(f"URL: {url}")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                
                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )
                
                print(f"\nPayTouch6_Veltrix API Response:")
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print(f"Raw Response: {response.text}")
                print(f"=" * 80)
                
                if response.status_code not in [200, 201]:
                    error_msg = f'PayTouch6_Veltrix API error: HTTP {response.status_code} - {response.text}'
                    
                    # Update transaction status to FAILED
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    
                    conn.close()
                    return {'success': False, 'message': error_msg}
                
                # Try to parse JSON response
                try:
                    if not response.text or response.text.strip() == '':
                        error_msg = 'PayTouch6_Veltrix API returned empty response'
                        print(f"ERROR: {error_msg}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, txn_id))
                        conn.commit()
                        conn.close()
                        return {'success': False, 'message': error_msg}
                    
                    paytouch6_response = response.json()
                    print(f"PayTouch6_Veltrix Response JSON: {json.dumps(paytouch6_response, indent=2)}")
                except json.JSONDecodeError as e:
                    error_msg = f'PayTouch6_Veltrix API returned invalid JSON: {str(e)} - Response: {response.text[:200]}'
                    print(f"ERROR: {error_msg}")
                    
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    conn.close()
                    return {'success': False, 'message': error_msg}
                
                # Check for explicit error in statuscode
                statuscode = (paytouch6_response.get('statuscode') or 
                            paytouch6_response.get('statusCode') or '').upper()
                status_field = (paytouch6_response.get('status') or 
                              paytouch6_response.get('Status') or
                              paytouch6_response.get('data', {}).get('status'))
                              
                if statuscode in ['ERR', 'ERROR'] or (status_field and status_field.upper() == 'FAILED'):
                    error_msg = paytouch6_response.get('message', 'Gateway returned error status')
                    print(f"ERROR from gateway: {error_msg}")
                    
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()
                    conn.close()
                    
                    return {'success': False, 'message': error_msg}
                
                # Extract transaction_id from response - try multiple field names
                transaction_id = (paytouch6_response.get('transaction_id') or 
                                paytouch6_response.get('transactionId') or
                                paytouch6_response.get('txn_id') or
                                paytouch6_response.get('data', {}).get('transaction_id'))
                
                # Use extracted status or default to PENDING
                status = status_field or 'PENDING'
                
                print(f"Extracted from PayTouch6_Veltrix response:")
                print(f"  - transaction_id: {transaction_id}")
                print(f"  - status: {status}")
                
                # Map PayTouch6 status to our status
                status_map = {
                    'SUCCESS': 'SUCCESS',
                    'PENDING': 'QUEUED',
                    'FAILED': 'FAILED',
                    'PROCESSING': 'INPROCESS',
                    'INITIATED': 'QUEUED',
                    'QUEUED': 'QUEUED'
                }
                mapped_status = status_map.get(status.upper(), 'QUEUED')
                
                print(f"Mapped status: {status} -> {mapped_status}")
                
                # Update transaction with PayTouch6 transaction ID
                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = %s, pg_txn_id = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, transaction_id, txn_id))
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Payout initiated successfully',
                    'txn_id': txn_id,
                    'reference_id': payout_data['reference_id'],
                    'paytouch6_txn_id': transaction_id,
                    'status': mapped_status,
                    'amount': payout_data['amount'],
                    'charge_amount': charges['charge_amount']
                }
                
        except Exception as e:
            print(f"PayTouch6_Veltrix payout error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}
    
    def check_payout_status(self, transaction_id=None, external_ref=None):
        """
        Check payout status from PayTouch6_Veltrix
        
        Args:
            transaction_id: PayTouch6 transaction ID
            external_ref: Your system's reference ID
        
        Returns:
            dict: Status information
        """
        try:
            print(f"Checking PayTouch6_Veltrix payout status - transaction_id: {transaction_id}, external_ref: {external_ref}")
            
            # Prepare request payload
            payload = {
                'token': self.token,
                'transaction_id': transaction_id or '',
                'external_ref': external_ref or ''
            }
            
            print(f"PayTouch6_Veltrix Status Check Request: {json.dumps(payload, indent=2)}")
            
            # Call PayTouch6 status API
            url = f"{self.base_url}/api/payout/v2/get-report-status"  # Correct endpoint with hyphen
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=payload,
                timeout=30
            )
            
            print(f"PayTouch6_Veltrix Status Response: {response.status_code} - {response.text}")
            
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Status check failed: {response.text}'
                }
            
            paytouch6_response = response.json()
            
            # Log all available fields for debugging
            print(f"PayTouch6_Veltrix Response Fields: {list(paytouch6_response.keys())}")
            
            # Extract status information
            status = paytouch6_response.get('status', 'PENDING')
            
            # Extract UTR - check multiple possible field names
            utr = (
                paytouch6_response.get('utr_no') or  # PayTouch uses utr_no
                paytouch6_response.get('utr') or
                paytouch6_response.get('bank_ref_no') or
                paytouch6_response.get('bankRefNo') or
                paytouch6_response.get('bank_reference_number') or
                paytouch6_response.get('rrn') or
                paytouch6_response.get('reference_number') or
                paytouch6_response.get('utr_number')
            )
            
            print(f"Extracted UTR: {utr}")
            
            # Map PayTouch status to our status
            status_map = {
                'SUCCESS': 'SUCCESS',
                'PENDING': 'QUEUED',
                'FAILED': 'FAILED',
                'PROCESSING': 'INPROCESS'
            }
            mapped_status = status_map.get(status.upper(), 'QUEUED')
            
            return {
                'success': True,
                'status': mapped_status,
                'transaction_id': paytouch6_response.get('transaction_id'),
                'external_ref': paytouch6_response.get('external_ref'),
                'utr': utr,
                'amount': paytouch6_response.get('amount'),
                'message': paytouch6_response.get('message', 'Status retrieved successfully')
            }
            
        except Exception as e:
            print(f"PayTouch6_Veltrix status check error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}

# Global instance
paytouch6_service = PayTouch6Service()