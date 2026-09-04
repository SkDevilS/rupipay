"""
Sabpaisa Grosmart Webhook Callback Handler
Handles real-time payment notifications from Sabpaisa Grosmart
"""

from flask import Blueprint, request, jsonify
import hmac
import hashlib
import base64
import time
import json
from database import get_db_connection
from config import Config
import requests

sabpaisa_grosmart_callback_bp = Blueprint('sabpaisa_grosmart_callback', __name__, url_prefix='/api/callback/sabpaisa-grosmart')


def verify_webhook_signature(signature_header, raw_body, secret_key):
    """
    Verify Sabpaisa webhook signature
    
    Format: X-SabPaisa-Signature = timestamp.base64_signature
    
    Args:
        signature_header: Value of X-SabPaisa-Signature header
        raw_body: Raw request body (bytes)
        secret_key: Webhook secret key
    
    Returns:
        Boolean indicating if signature is valid
    """
    try:
        if not signature_header:
            print("❌ Missing signature header")
            return False
        
        # Split signature header
        parts = signature_header.split('.')
        if len(parts) != 2:
            print("❌ Invalid signature format")
            return False
        
        timestamp_str, received_signature = parts
        
        # Validate timestamp (within 5 minutes)
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            print("❌ Invalid timestamp")
            return False
        
        current_time = int(time.time() * 1000)  # milliseconds
        time_diff = abs(current_time - timestamp)
        
        if time_diff > 300000:  # 5 minutes in milliseconds
            print(f"❌ Signature expired (time diff: {time_diff}ms)")
            return False
        
        # Construct signed payload
        signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
        
        # Compute HMAC-SHA256
        expected_signature = base64.b64encode(
            hmac.new(
                secret_key.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        # Constant-time comparison
        return hmac.compare_digest(expected_signature, received_signature)
        
    except Exception as e:
        print(f"❌ Signature verification error: {e}")
        return False


@sabpaisa_grosmart_callback_bp.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle Sabpaisa Grosmart webhook notifications
    
    Events:
    - payment.success: Payment completed successfully
    - payment.failed: Payment failed
    - payment.expired: Payment session expired
    - payment.timeout: Payment processing timed out
    """
    try:
        # Get raw body for signature verification
        raw_body = request.get_data()
        
        # Get signature header
        signature_header = request.headers.get('X-SabPaisa-Signature')
        
        # Verify signature
        webhook_secret = Config.SABPAISA_GROSMART_WEBHOOK_SECRET
        if not verify_webhook_signature(signature_header, raw_body, webhook_secret):
            print("❌ Invalid webhook signature")
            return jsonify({'success': False, 'message': 'Invalid signature'}), 401
        
        # Parse payload
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except:
            print("❌ Failed to parse webhook payload")
            return jsonify({'success': False, 'message': 'Invalid payload'}), 400
        
        # Extract webhook data
        event = payload.get('event')
        merchant_txn_id = payload.get('merchant_txn_id')
        sp_txn_id = payload.get('txn_id')
        status = payload.get('status')
        paid_amount = payload.get('paid_amount', 0)
        bank_txn_id = payload.get('bank_txn_id')
        bank_rrn = payload.get('bank_rrn')
        payment_mode = payload.get('payment_mode', 'UPI')
        completed_at = payload.get('completed_at')
        idempotency_key = payload.get('idempotency_key')
        
        print(f"📥 Sabpaisa Webhook Received")
        print(f"  Event: {event}")
        print(f"  Merchant Txn ID: {merchant_txn_id}")
        print(f"  Status: {status}")
        print(f"  Amount: ₹{paid_amount}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE txn_id = %s AND pg_partner = 'SABPAISA_GROSMART'
                """, (merchant_txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Transaction not found: {merchant_txn_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                # Check idempotency - prevent duplicate processing
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (merchant_txn_id,))
                
                wallet_already_credited = cursor.fetchone()['count'] > 0
                
                # Update transaction based on event
                if event == 'payment.success' and status == 'SUCCESS':
                    # Update transaction status
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'SUCCESS',
                            pg_txn_id = %s,
                            bank_ref_no = %s,
                            payment_mode = %s,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (sp_txn_id, bank_rrn, payment_mode, merchant_txn_id))
                    
                    # Credit wallets if not already done
                    if not wallet_already_credited:
                        from wallet_service import wallet_service as wallet_svc
                        
                        # Credit merchant unsettled wallet
                        wallet_result = wallet_svc.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=float(txn['net_amount']),
                            description=f"PayIn received (Sabpaisa) - {merchant_txn_id}",
                            reference_id=merchant_txn_id
                        )
                        
                        if wallet_result['success']:
                            print(f"✓ Merchant unsettled wallet credited: ₹{txn['net_amount']}")
                        else:
                            print(f"✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                        
                        # Credit admin unsettled wallet
                        admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=float(txn['charge_amount']),
                            description=f"PayIn charge (Sabpaisa) - {merchant_txn_id}",
                            reference_id=merchant_txn_id
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✓ Admin unsettled wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"⚠ Wallet already credited - skipping (idempotency)")
                    
                    conn.commit()
                    
                    # Forward callback to merchant
                    if txn.get('callback_url'):
                        forward_callback_to_merchant(txn, 'SUCCESS', bank_rrn, sp_txn_id)
                    
                    print(f"✅ Payment success processed: {merchant_txn_id}")
                    
                elif event in ['payment.failed', 'payment.expired', 'payment.timeout']:
                    # Update transaction status to FAILED
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED',
                            pg_txn_id = %s,
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (sp_txn_id, merchant_txn_id))
                    
                    conn.commit()
                    
                    # Forward callback to merchant
                    if txn.get('callback_url'):
                        forward_callback_to_merchant(txn, 'FAILED', None, sp_txn_id)
                    
                    print(f"✅ Payment failure processed: {merchant_txn_id}")
                
                return jsonify({'success': True, 'message': 'Webhook processed'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


def forward_callback_to_merchant(txn, status, utr, pg_txn_id):
    """Forward payment callback to merchant's callback URL"""
    try:
        if not txn.get('callback_url'):
            return
        
        callback_data = {
            'txn_id': txn['txn_id'],
            'order_id': txn['order_id'],
            'amount': str(txn['amount']),
            'status': status,
            'pg_txn_id': pg_txn_id,
            'bank_ref_no': utr,
            'payment_mode': txn.get('payment_mode', 'UPI'),
            'pg_partner': 'SABPAISA_GROSMART'
        }
        
        print(f"📤 Forwarding callback to merchant: {txn['callback_url']}")
        
        response = requests.post(
            txn['callback_url'],
            json=callback_data,
            timeout=10
        )
        
        print(f"📥 Merchant callback response: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Failed to forward callback: {e}")
