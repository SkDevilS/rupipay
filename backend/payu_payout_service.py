import requests
import json
from datetime import datetime, timedelta
from config import Config
from database import get_db_connection

class PayUPayoutService:
    def __init__(self):
        self.client_id = Config.PAYU_PAYOUT_CLIENT_ID
        self.username = Config.PAYU_PAYOUT_USERNAME
        self.password = Config.PAYU_PAYOUT_PASSWORD
        self.merchant_id = Config.PAYU_PAYOUT_MERCHANT_ID
        self.base_url = Config.PAYU_PAYOUT_BASE_URL
        self.auth_url = Config.PAYU_PAYOUT_AUTH_URL
        self.access_token = None
        self.token_expires_at = None
        self.refresh_token = None
    
    def generate_access_token(self):
        """Generate authentication token using merchant credentials"""
        try:
            url = f"{self.auth_url}/oauth/token"
            
            payload = {
                'grant_type': 'password',
                'scope': 'create_payout_transactions',
                'client_id': self.client_id,
                'username': self.username,
                'password': self.password
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'cache-control': 'no-cache'
            }
            
            response = requests.post(url, data=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                expires_in = data.get('expires_in', 7199)  # Default 2 hours
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return {
                    'success': True,
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_in': expires_in,
                    'token_type': data.get('token_type'),
                    'user_uuid': data.get('user_uuid')
                }
            else:
                return {
                    'success': False,
                    'error': f"Token generation failed: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        try:
            if not self.refresh_token:
                return self.generate_access_token()
            
            url = f"{self.auth_url}/oauth/token"
            
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'cache-control': 'no-cache'
            }
            
            response = requests.post(url, data=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                expires_in = data.get('expires_in', 7199)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return {
                    'success': True,
                    'access_token': self.access_token
                }
            else:
                # If refresh fails, generate new token
                return self.generate_access_token()
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_valid_token(self):
        """Get a valid access token, refreshing if necessary"""
        if not self.access_token or not self.token_expires_at:
            return self.generate_access_token()
        
        # Refresh token if it expires in less than 5 minutes
        if datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            return self.refresh_access_token()
        
        return {
            'success': True,
            'access_token': self.access_token
        }
    
    def get_account_details(self):
        """Get PayU payout account details"""
        try:
            token_result = self.get_valid_token()
            if not token_result['success']:
                return token_result
            
            url = f"{self.base_url}/payout/merchant/getAccountDetail"
            
            headers = {
                'Authorization': f"Bearer {self.access_token}",
                'Content-Type': 'application/x-www-form-urlencoded',
                'payoutMerchantId': self.merchant_id,
                'cache-control': 'no-cache'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to get account details: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def initiate_transfer(self, transfer_data):
        """Initiate a single transfer"""
        try:
            token_result = self.get_valid_token()
            if not token_result['success']:
                return token_result
            
            url = f"{self.base_url}/payout/v2/payment"
            
            headers = {
                'Authorization': f"Bearer {self.access_token}",
                'Content-Type': 'application/json',
                'payoutMerchantId': self.merchant_id
            }
            
            # Prepare payload based on payment type
            payload = []
            
            for transfer in transfer_data:
                payment_request = {
                    'beneficiaryName': transfer['bene_name'],
                    'beneficiaryEmail': transfer.get('bene_email', ''),
                    'beneficiaryMobile': transfer.get('bene_mobile', ''),
                    'purpose': transfer.get('purpose', 'Payment'),
                    'amount': float(transfer['amount']),
                    'batchId': transfer.get('batch_id', ''),
                    'merchantRefId': transfer['reference_id'],
                    'paymentType': transfer.get('payment_type', 'IMPS'),
                    'retry': transfer.get('retry', False)
                }
                
                # Add payment mode specific fields
                if transfer.get('payment_type') == 'UPI':
                    payment_request['vpa'] = transfer.get('vpa')
                else:
                    payment_request['beneficiaryAccountNumber'] = transfer.get('account_no')
                    payment_request['beneficiaryIfscCode'] = transfer.get('ifsc_code')
                
                payload.append(payment_request)
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"Transfer initiation failed: {response.text}",
                    'response': response.json() if response.text else None
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_transfer_status(self, merchant_ref_id=None, batch_id=None, transfer_status=None, from_date=None, to_date=None, page=1, page_size=100):
        """Check transfer status"""
        try:
            token_result = self.get_valid_token()
            if not token_result['success']:
                return token_result
            
            url = f"{self.base_url}/payout/payment/listTransactions"
            
            headers = {
                'Authorization': f"Bearer {self.access_token}",
                'Content-Type': 'application/x-www-form-urlencoded',
                'payoutMerchantId': self.merchant_id,
                'cache-control': 'no-cache'
            }
            
            data = {
                'page': str(page),
                'pageSize': str(page_size)
            }
            
            if merchant_ref_id:
                data['merchantRefId'] = merchant_ref_id
            if batch_id:
                data['batchId'] = batch_id
            if transfer_status:
                data['transferStatus'] = transfer_status
            if from_date:
                data['from'] = from_date
            if to_date:
                data['to'] = to_date
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"Status check failed: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_transaction_from_webhook(self, webhook_data):
        """Update transaction status from webhook data"""
        try:
            connection = get_db_connection()
            if not connection:
                return {'success': False, 'error': 'Database connection failed'}
            
            with connection.cursor() as cursor:
                event = webhook_data.get('event')
                merchant_ref_id = webhook_data.get('merchantReferenceId')
                payu_ref_id = webhook_data.get('payuRefId')
                bank_ref_no = webhook_data.get('bankReferenceId')
                msg = webhook_data.get('msg')
                
                # Determine status based on event
                status_map = {
                    'TRANSFER_SUCCESS': 'SUCCESS',
                    'TRANSFER_FAILED': 'FAILED',
                    'TRANSFER_REVERSED': 'REVERSED',
                    'REQUEST_PROCESSING_FAILED': 'FAILED'
                }
                
                status = status_map.get(event, 'INPROCESS')
                
                # Update transaction
                update_query = """
                    UPDATE payout_transactions 
                    SET status = %s, pg_txn_id = %s, bank_ref_no = %s, 
                        error_message = %s, updated_at = NOW()
                """
                params = [status, payu_ref_id, bank_ref_no, msg]
                
                # Add name match data if available
                if 'nameMatch' in webhook_data:
                    update_query += ", name_match_score = %s"
                    params.append(webhook_data['nameMatch'])
                
                if 'nameWithBank' in webhook_data:
                    update_query += ", name_with_bank = %s"
                    params.append(webhook_data['nameWithBank'])
                
                # Set completed_at for final statuses
                if status in ['SUCCESS', 'FAILED', 'REVERSED']:
                    update_query += ", completed_at = NOW()"
                
                update_query += " WHERE reference_id = %s"
                params.append(merchant_ref_id)
                
                cursor.execute(update_query, params)
                connection.commit()
                
                return {
                    'success': True,
                    'message': 'Transaction updated successfully'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if connection:
                connection.close()

# Global instance
payu_payout_service = PayUPayoutService()
