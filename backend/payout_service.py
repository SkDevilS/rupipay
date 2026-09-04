import requests
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from database import get_db_connection
from config import Config

class PayoutService:
    def __init__(self):
        self.base_url = Config.PAYU_PAYOUT_BASE_URL
        self.auth_url = Config.PAYU_PAYOUT_AUTH_URL
        self.client_id = Config.PAYU_PAYOUT_CLIENT_ID
        self.username = Config.PAYU_PAYOUT_USERNAME
        self.password = Config.PAYU_PAYOUT_PASSWORD
        self.merchant_id = Config.PAYU_PAYOUT_MERCHANT_ID
    
    def generate_hash(self, data_string):
        """Generate SHA-512 hash"""
        return hashlib.sha512(data_string.encode()).hexdigest()
    
    def generate_txn_id(self, merchant_id, reference_id):
        """Generate unique transaction ID"""
        return f"PT2_GROS_{merchant_id}_{reference_id}_{uuid.uuid4().hex[:8].upper()}"
    
    def encrypt_payload(self, data):
        """Encrypt payload using AES"""
        try:
            # This is a placeholder - implement actual encryption if needed
            return json.dumps(data)
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    def get_access_token(self):
        """Get access token from PayU payout service"""
        from payu_payout_service import payu_payout_service
        result = payu_payout_service.get_valid_token()
        if result['success']:
            return {
                'success': True,
                'access_token': result['access_token']
            }
        return result
    
    def get_account_details(self):
        """Get PayU payout account details"""
        from payu_payout_service import payu_payout_service
        return payu_payout_service.get_account_details()
    
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
    
    def create_payout_transaction(self, merchant_id, payout_data, admin_id=None):
        """Create payout transaction - supports both merchant and admin payouts"""
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
                        SELECT scheme_id FROM merchants WHERE merchant_id = %s
                    """, (merchant_id,))
                    merchant = cursor.fetchone()
                    
                    if not merchant or not merchant['scheme_id']:
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
                    
                    # Validate merchant wallet balance (use settled_balance directly)
                    total_deduction = float(payout_data['amount']) + float(charges['charge_amount'])
                    
                    # Get settled balance from merchant_wallet (this already accounts for everything)
                    cursor.execute("""
                        SELECT COALESCE(settled_balance, 0) as available_balance
                        FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (merchant_id,))
                    wallet_result = cursor.fetchone()
                    available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00
                    
                    # Check if settled balance is sufficient
                    if total_deduction > available_balance:
                        conn.close()
                        return {
                            'success': False,
                            'message': f'Insufficient balance in wallet, remaining balance in wallet: ₹{available_balance:.2f}'
                        }
                
                # Validate admin wallet balance for admin payouts
                if is_admin_payout and admin_id:
                    # Calculate admin balance dynamically
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_payin
                        FROM payin_transactions
                        WHERE status = 'SUCCESS'
                    """)
                    total_payin = float(cursor.fetchone()['total_payin'])
                    
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_topup
                        FROM fund_requests
                        WHERE status = 'APPROVED'
                    """)
                    total_topup = float(cursor.fetchone()['total_topup'])
                    
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_fetch
                        FROM merchant_wallet_transactions
                        WHERE txn_type = 'DEBIT' 
                        AND description LIKE '%fetched by admin%'
                    """)
                    total_fetch = float(cursor.fetchone()['total_fetch'])
                    
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_payout
                        FROM payout_transactions
                        WHERE status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
                        AND reference_id LIKE 'ADMIN%'
                    """)
                    total_payout = float(cursor.fetchone()['total_payout'])
                    
                    admin_balance = total_payin + total_fetch - total_topup - total_payout
                    
                    if float(payout_data['amount']) > admin_balance:
                        conn.close()
                        return {
                            'success': False,
                            'message': f'Insufficient balance in wallet, remaining balance in wallet: ₹{admin_balance:.2f}'
                        }
                
                # Generate transaction ID
                identifier = admin_id if is_admin_payout else merchant_id
                txn_id = self.generate_txn_id(identifier, payout_data['reference_id'])
                
                # NEW FLOW: Deduct wallet IMMEDIATELY for merchant payouts (before gateway processing)
                if not is_admin_payout and merchant_id:
                    from wallet_service import WalletService
                    wallet_svc = WalletService()
                    
                    debit_result = wallet_svc.debit_merchant_wallet(
                        merchant_id=merchant_id,
                        amount=total_deduction,
                        description=f"Payout initiated: ₹{payout_data['amount']:.2f} + Charges: ₹{charges['charge_amount']:.2f}",
                        reference_id=txn_id
                    )
                    
                    if not debit_result['success']:
                        conn.close()
                        return {
                            'success': False,
                            'message': f"Wallet deduction failed: {debit_result['message']}"
                        }
                    
                    print(f"✅ WALLET DEBITED ON INITIATION - Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                
                # Insert payout transaction
                cursor.execute("""
                    INSERT INTO payout_transactions (
                        txn_id, merchant_id, admin_id, reference_id, batch_id, amount, charge_amount,
                        charge_type, net_amount, bene_name, bene_email, bene_mobile,
                        bene_bank, ifsc_code, account_no, vpa, payment_type, purpose,
                        status, pg_partner, callback_url, remarks
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    txn_id, merchant_id, admin_id, payout_data['reference_id'],
                    payout_data.get('batch_id', ''),
                    payout_data['amount'], charges['charge_amount'],
                    charges['charge_type'], charges['net_amount'],
                    payout_data['bene_name'],
                    payout_data.get('bene_email', ''),
                    payout_data.get('mobile', ''),
                    payout_data.get('bene_bank', ''),
                    payout_data.get('ifsc_code', ''),
                    payout_data.get('account_no', ''),
                    payout_data.get('vpa', ''),
                    payout_data.get('payment_type', 'IMPS'),
                    payout_data.get('purpose', 'Payment'),
                    'INITIATED', 'PayU',
                    payout_data.get('callback_url', ''),
                    payout_data.get('remarks', '')
                ))
                
                conn.commit()
                
                # Process payout with PayU
                payout_result = self.process_payout(txn_id, payout_data, charges['net_amount'])
                
                conn.close()
                return payout_result
                
        except Exception as e:
            print(f"Payout transaction error: {e}")
            return {'success': False, 'message': str(e)}
    
    def process_payout(self, txn_id, payout_data, net_amount):
        """Process payout through PayU"""
        try:
            from payu_payout_service import payu_payout_service
            
            # Prepare transfer data for PayU
            transfer_data = [{
                'bene_name': payout_data['bene_name'],
                'bene_email': payout_data.get('bene_email', ''),
                'bene_mobile': payout_data.get('mobile', ''),
                'purpose': payout_data.get('purpose', 'Payment'),
                'amount': float(payout_data['amount']),  # Use original amount, not net_amount
                'batch_id': payout_data.get('batch_id', ''),
                'reference_id': payout_data['reference_id'],
                'payment_type': payout_data.get('payment_type', 'IMPS'),
                'retry': False
            }]
            
            # Add payment mode specific fields
            if payout_data.get('payment_type') == 'UPI':
                transfer_data[0]['vpa'] = payout_data.get('vpa')
            else:
                transfer_data[0]['account_no'] = payout_data.get('account_no')
                transfer_data[0]['ifsc_code'] = payout_data.get('ifsc_code')
            
            # Initiate transfer through PayU
            result = payu_payout_service.initiate_transfer(transfer_data)
            
            if result['success']:
                response_data = result.get('data', {})
                
                # Check if request was successful
                if response_data.get('status') == 0:
                    # Update transaction status to QUEUED (PayU processes asynchronously)
                    self.update_transaction_status(
                        txn_id,
                        'QUEUED',
                        pg_txn_id=None,
                        error_message=None
                    )
                    
                    return {
                        'success': True,
                        'message': 'Payout initiated successfully. Status will be updated via webhook.',
                        'txn_id': txn_id,
                        'reference_id': payout_data['reference_id']
                    }
                else:
                    # Handle error response from PayU
                    error_data = response_data.get('data', [])
                    error_msg = 'Payout failed'
                    
                    if error_data and len(error_data) > 0:
                        error_msg = error_data[0].get('error', 'Payout failed')
                    elif response_data.get('msg'):
                        error_msg = response_data.get('msg')
                    
                    self.update_transaction_status(
                        txn_id,
                        'FAILED',
                        error_message=error_msg
                    )
                    
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                # Handle service error
                error_msg = result.get('error', 'Payout service error')
                self.update_transaction_status(
                    txn_id,
                    'FAILED',
                    error_message=error_msg
                )
                
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            error_msg = str(e)
            self.update_transaction_status(
                txn_id,
                'FAILED',
                error_message=error_msg
            )
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def update_transaction_status(self, txn_id, status, pg_txn_id=None, utr=None, bank_ref_no=None, error_message=None):
        """Update payout transaction status"""
        try:
            conn = get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                update_fields = ['status = %s', 'updated_at = NOW()']
                params = [status]
                
                if pg_txn_id:
                    update_fields.append('pg_txn_id = %s')
                    params.append(pg_txn_id)
                
                if utr:
                    update_fields.append('utr = %s')
                    params.append(utr)
                
                if bank_ref_no:
                    update_fields.append('bank_ref_no = %s')
                    params.append(bank_ref_no)
                
                if error_message:
                    update_fields.append('error_message = %s')
                    params.append(error_message)
                
                if status in ['SUCCESS', 'FAILED', 'REVERSED']:
                    update_fields.append('completed_at = NOW()')
                
                params.append(txn_id)
                
                query = f"UPDATE payout_transactions SET {', '.join(update_fields)} WHERE txn_id = %s"
                cursor.execute(query, params)
                conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"Status update error: {e}")
            return False
    
    def get_transaction_status(self, reference_id):
        """Get transaction status from PayU"""
        try:
            from payu_payout_service import payu_payout_service
            
            # Use PayU payout service to check status
            result = payu_payout_service.check_transfer_status(merchant_ref_id=reference_id)
            
            if result['success']:
                response_data = result.get('data', {})
                
                if response_data.get('status') == 0:
                    transactions = response_data.get('data', {}).get('transactionDetails', [])
                    
                    if transactions:
                        txn = transactions[0]
                        
                        # Map PayU status to our status
                        status_map = {
                            'SUCCESS': 'SUCCESS',
                            'FAILED': 'FAILED',
                            'PENDING': 'INPROCESS',
                            'QUEUED': 'QUEUED',
                            'REVERSED': 'REVERSED'
                        }
                        
                        status = status_map.get(txn.get('txnStatus'), 'INPROCESS')
                        
                        return {
                            'success': True,
                            'status': status,
                            'pg_txn_id': txn.get('payuTransactionRefNo'),
                            'utr': txn.get('bankTransactionRefNo'),
                            'bank_ref_no': txn.get('bankTransactionRefNo'),
                            'message': txn.get('msg'),
                            'name_with_bank': txn.get('nameWithBank'),
                            'name_match': txn.get('nameMatch')
                        }
                
                return {
                    'success': False,
                    'error': 'Transaction not found'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Status check failed')
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
payout_service = PayoutService()
