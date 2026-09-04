"""
Bridgmoney Coco Callback Routes
Handles webhook callbacks from Bridgmoney Coco for payout status updates.
Forwards webhook callbacks to merchant in the same format as PayTouch.
"""

import time
import hmac
import hashlib
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from config import Config

bridgmoney_coco_callback_bp = Blueprint('bridgmoney_coco_callback', __name__, url_prefix='/api/callback')


def verify_webhook_signature(timestamp, raw_body, signature, signature_v2, webhook_secret):
    """Verify HMAC SHA256 webhook signature from Bridgmoney Coco"""
    if not webhook_secret:
        return True
    
    tolerance = 5 * 60 * 1000  # 5 minutes
    try:
        if timestamp and abs(int(time.time() * 1000) - int(timestamp)) > tolerance:
            print("Webhook timestamp outside tolerance window")
            return False
    except (ValueError, TypeError):
        pass

    if signature_v2 and timestamp:
        canonical = f"{timestamp}|sha256|{raw_body}"
        expected = hmac.new(webhook_secret.encode('utf-8'), canonical.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature_v2, expected)
    elif signature and timestamp:
        canonical = f"{timestamp}|{raw_body}"
        expected = hmac.new(webhook_secret.encode('utf-8'), canonical.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    return True


@bridgmoney_coco_callback_bp.route('/bridgmoney-coco/payout', methods=['POST'])
@bridgmoney_coco_callback_bp.route('/bridgmoney_coco/payout', methods=['POST'])
def bridgmoney_coco_payout_callback():
    """
    Webhook endpoint for Bridgmoney_Coco payout callbacks.
    Handles payout status updates and forwards callbacks to merchant in PayTouch format.
    """
    try:
        raw_body = request.get_data(as_text=True)
        callback_data = request.json or request.form.to_dict()
        
        print("=" * 80)
        print("Bridgmoney_Coco Payout Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Check signature verification if configured
        timestamp = request.headers.get('x-webhook-timestamp')
        sig = request.headers.get('x-webhook-signature')
        sig_v2 = request.headers.get('x-webhook-signature-v2')
        
        if (sig or sig_v2) and Config.BRIDGMONEY_COCO_WEBHOOK_SECRET:
            if not verify_webhook_signature(timestamp, raw_body, sig, sig_v2, Config.BRIDGMONEY_COCO_WEBHOOK_SECRET):
                print("ERROR: Invalid Bridgmoney Coco webhook signature")
                return jsonify({'success': False, 'message': 'Invalid signature'}), 401
        
        # Extract data from callback (supports both Bridgmoney wrapper and direct format)
        data_obj = callback_data.get('data') if isinstance(callback_data.get('data'), dict) else callback_data
        
        transaction_id = (
            data_obj.get('payoutTransactionId') or
            data_obj.get('transactionId') or
            callback_data.get('transaction_id') or
            callback_data.get('transactionId')
        )
        external_ref = (
            data_obj.get('merchantReferenceId') or
            data_obj.get('request_id') or
            callback_data.get('external_ref') or
            callback_data.get('merchantReferenceId')
        )
        status_val = data_obj.get('status', callback_data.get('status', 'PENDING'))
        event_str = callback_data.get('event')
        
        utr = (
            data_obj.get('utr') or
            data_obj.get('transactionReference') or
            data_obj.get('utr_no') or
            callback_data.get('utr') or
            callback_data.get('transactionReference') or
            callback_data.get('utr_no')
        )
        amount = data_obj.get('amount') or callback_data.get('amount')
        message = data_obj.get('responseMessage') or callback_data.get('message', '')
        
        if not transaction_id and not external_ref:
            print("ERROR: No transaction_id or external_ref in callback")
            return jsonify({'success': False, 'message': 'Missing transaction identifier'}), 400
        
        print(f"Transaction ID: {transaction_id}")
        print(f"External Ref: {external_ref}")
        print(f"Status Val: {status_val}, Event: {event_str}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        print(f"Message: {message}")
        
        # Map Bridgmoney Coco status to our status
        status_map = {
            3: 'QUEUED', '3': 'QUEUED',
            11: 'SUCCESS', '11': 'SUCCESS',
            12: 'FAILED', '12': 'FAILED',
            'SUCCESS': 'SUCCESS', 'SUCCESSFUL': 'SUCCESS',
            'PENDING': 'QUEUED', 'INITIATED': 'QUEUED', 'QUEUED': 'QUEUED',
            'FAILED': 'FAILED'
        }
        mapped_status = status_map.get(status_val, 'QUEUED')
        if isinstance(status_val, str):
            mapped_status = status_map.get(status_val.upper(), mapped_status)
        if event_str:
            if str(event_str).upper() == 'SUCCESSFUL':
                mapped_status = 'SUCCESS'
            elif str(event_str).upper() == 'FAILED':
                mapped_status = 'FAILED'
            elif str(event_str).upper() == 'INITIATED':
                mapped_status = 'QUEUED'
                
        print(f"Mapped Status: {mapped_status}")
        
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
            
        try:
            with conn.cursor() as cursor:
                # Find transaction by pg_txn_id or reference_id
                if transaction_id:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id
                        FROM payout_transactions
                        WHERE pg_txn_id = %s AND pg_partner = 'Bridgmoney_Coco'
                    """, (transaction_id,))
                else:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id
                        FROM payout_transactions
                        WHERE reference_id = %s AND pg_partner = 'Bridgmoney_Coco'
                    """, (external_ref,))
                
                txn = cursor.fetchone()
                
                # Fallback if not found by pg_txn_id, try finding by external_ref
                if not txn and external_ref:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id
                        FROM payout_transactions
                        WHERE reference_id = %s AND pg_partner = 'Bridgmoney_Coco'
                    """, (external_ref,))
                    txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for transaction_id: {transaction_id}, external_ref: {external_ref}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # Handle wallet refund for FAILED status (wallet deducted on initiation for merchant payout)
                if mapped_status == 'FAILED':
                    if txn['merchant_id']:
                        print(f"Merchant payout FAILED - checking wallet refund")
                        cursor.execute("""
                            SELECT txn_id FROM merchant_wallet_transactions
                            WHERE reference_id = %s AND txn_type = 'CREDIT'
                            AND description LIKE '%Payout refund%'
                        """, (txn['txn_id'],))
                        wallet_already_refunded = cursor.fetchone()
                        
                        if wallet_already_refunded:
                            print(f"⚠️  Wallet already refunded for this transaction - skipping")
                        else:
                            print(f"Status is FAILED - Refunding merchant settled wallet")
                            cursor.execute("""
                                SELECT amount, net_amount, charge_amount FROM payout_transactions
                                WHERE txn_id = %s
                            """, (txn['txn_id'],))
                            payout_details = cursor.fetchone()
                            
                            total_refund = float(payout_details['amount'])
                            print(f"Refunding to settled wallet - Amount: ₹{total_refund:.2f}")
                            
                            from wallet_service import WalletService
                            wallet_svc = WalletService()
                            credit_result = wallet_svc.credit_merchant_wallet(
                                merchant_id=txn['merchant_id'],
                                amount=total_refund,
                                description=f"Payout refund: ₹{payout_details['net_amount']:.2f} + Charges: ₹{payout_details['charge_amount']:.2f}",
                                reference_id=txn['txn_id']
                            )
                            if credit_result['success']:
                                print(f"✅ WALLET REFUNDED - Balance: ₹{credit_result['balance_before']:.2f} → ₹{credit_result['balance_after']:.2f}")
                            else:
                                print(f"✗ WALLET REFUND FAILED: {credit_result['message']}")
                    elif txn['admin_id']:
                        print(f"Admin personal payout FAILED - no wallet refund needed")
                
                # Update transaction with callback data
                if mapped_status in ['SUCCESS', 'FAILED']:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, 
                            error_message = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, utr, transaction_id, message if mapped_status == 'FAILED' else None, txn['txn_id']))
                else:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, transaction_id, txn['txn_id']))
                
                conn.commit()
                
                # Forward callback to merchant if configured (in exact same format as PayTouch)
                try:
                    if txn['merchant_id']:
                        cursor.execute("""
                            SELECT callback_url FROM payout_transactions
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        txn_callback = cursor.fetchone()
                        callback_url = txn_callback.get('callback_url') if txn_callback else None
                        
                        if not callback_url:
                            cursor.execute("""
                                SELECT payout_callback_url FROM merchant_callbacks
                                WHERE merchant_id = %s AND is_active = TRUE
                            """, (txn['merchant_id'],))
                            merchant_callback = cursor.fetchone()
                            callback_url = merchant_callback.get('payout_callback_url') if merchant_callback else None
                            
                        if callback_url:
                            from callback_forwarder import forward_payout_callback
                            
                            merchant_callback_data = {
                                'txn_id': txn['txn_id'],
                                'reference_id': txn['reference_id'],
                                'status': mapped_status,
                                'utr': utr,
                                'pg_txn_id': transaction_id,
                                'pg_partner': 'Bridgmoney_Coco',
                                'amount': amount,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if txn['merchant_id'] == '9120000001':
                                merchant_callback_data['order_id'] = txn.get('order_id')
                                
                            forward_result = forward_payout_callback(
                                txn_id=txn['txn_id'],
                                merchant_id=txn['merchant_id'],
                                callback_url=callback_url,
                                callback_data=merchant_callback_data
                            )
                            if forward_result['success']:
                                print(f"✅ Callback forwarded successfully to merchant")
                            else:
                                print(f"⚠️  Callback forwarding failed: {forward_result.get('message')}")
                        else:
                            print("No callback URL configured (transaction-specific or merchant-level)")
                except Exception as e:
                    print(f"ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                
                return jsonify({
                    'success': True,
                    'message': 'Payout callback processed successfully',
                    'txn_id': txn['txn_id'],
                    'status': mapped_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"ERROR in Bridgmoney Coco payout callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
