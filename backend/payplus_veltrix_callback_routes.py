"""
Payplus_Veltrix Callback Routes
Handles webhook callbacks from Payplus_Veltrix with HMAC SHA256 signature verification
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from config import Config
import json
import hmac
import hashlib
from datetime import datetime

payplus_veltrix_callback_bp = Blueprint('payplus_veltrix_callback', __name__, url_prefix='/api/callback/payplus-veltrix')

@payplus_veltrix_callback_bp.route('/webhook', methods=['POST'])
@payplus_veltrix_callback_bp.route('/payin', methods=['POST'])
def payplus_veltrix_webhook():
    """
    Webhook endpoint for Payplus_Veltrix real-time updates
    Signature Header: x-payplus-signature (HMAC SHA256 of raw body)
    Payload:
    - event: payin.success or payout.success
    - status: processing or success
    - orderId / payoutId: Payplus transaction id
    - merchantOrderId: merchant deposit id
    - timestamp: ISO date string
    """
    try:
        print("=" * 80)
        print("Payplus_Veltrix Webhook Callback Received")
        print("=" * 80)
        
        signature = request.headers.get("x-payplus-signature")
        raw_body = request.get_data()
        
        # Verify HMAC SHA256 signature if secret is configured
        webhook_secret = Config.PAYPLUS_VELTRIX_WEBHOOK_SECRET
        if webhook_secret:
            expected_sig = hmac.new(
                webhook_secret.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = signature and hmac.compare_digest(signature, expected_sig)
            if not is_valid:
                print(f"❌ Invalid webhook signature! Received: {signature}")
                return jsonify({"success": False, "message": "Invalid signature"}), 401
            else:
                print("✅ Webhook signature verified successfully")
        else:
            print("⚠ PAYPLUS_VELTRIX_WEBHOOK_SECRET not configured, skipping signature verification")
        
        # Parse payload
        callback_data = None
        if request.is_json:
            callback_data = request.get_json(silent=True)
        if not callback_data and raw_body:
            try:
                callback_data = json.loads(raw_body.decode('utf-8'))
            except Exception:
                pass
        
        if not callback_data:
            print("❌ No valid JSON data in webhook callback")
            return jsonify({"success": False, "message": "No data received"}), 400
            
        print(f"📦 Callback Data: {json.dumps(callback_data, indent=2)}")
        
        event = callback_data.get('event', '')
        status = str(callback_data.get('status', '')).lower()
        merchant_order_id = callback_data.get('merchantOrderId')
        order_id = callback_data.get('orderId')
        utr = callback_data.get('utr', '')
        
        if not merchant_order_id:
            print("❌ Missing merchantOrderId in callback")
            return jsonify({"success": False, "message": "Missing merchantOrderId"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Database error"}), 500
            
        cursor = conn.cursor()
        
        # Find transaction
        cursor.execute("""
            SELECT * FROM payin_transactions
            WHERE txn_id = %s OR order_id = %s
            ORDER BY created_at DESC LIMIT 1
        """, (merchant_order_id, merchant_order_id))
        
        txn = cursor.fetchone()
        if not txn:
            cursor.close()
            conn.close()
            print(f"❌ Transaction not found for merchantOrderId: {merchant_order_id}")
            return jsonify({"success": True, "message": "Transaction not found"}), 200
            
        # Wallet Credit Rule: credit player wallet only once after valid payin.success
        if event == 'payin.success' or status == 'success':
            if txn['status'] == 'SUCCESS':
                print(f"✓ Transaction {merchant_order_id} already marked as SUCCESS (idempotent)")
                cursor.close()
                conn.close()
                return jsonify({"success": True, "message": "Already processed"}), 200
                
            print(f"💰 Processing PAYIN SUCCESS for txn: {txn['txn_id']}")
            
            # Update payin transaction status
            cursor.execute("""
                UPDATE payin_transactions
                SET status = 'SUCCESS', bank_ref_no = %s, pg_txn_id = %s,
                    completed_at = NOW(), updated_at = NOW()
                WHERE txn_id = %s
            """, (utr, order_id or txn.get('pg_txn_id'), txn['txn_id']))
            
            # Check if wallet was already credited
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (txn['txn_id'],))
            
            wallet_already_credited = cursor.fetchone()['count'] > 0
            
            if not wallet_already_credited:
                from wallet_service import wallet_service
                wallet_result = wallet_service.credit_unsettled_wallet(
                    merchant_id=txn['merchant_id'],
                    amount=float(txn['net_amount']),
                    description=f"PayIn received (Payplus_Veltrix) - {txn['order_id']}",
                    reference_id=txn['txn_id']
                )
                if wallet_result.get('success'):
                    print(f"✅ Credited ₹{txn['net_amount']} to merchant {txn['merchant_id']} unsettled wallet")
                else:
                    print(f"❌ Wallet credit error: {wallet_result.get('message')}")
            else:
                print(f"✓ Wallet already credited for {txn['txn_id']}")
                
            conn.commit()
            
        elif status in ['failed', 'rejected', 'cancelled']:
            if txn['status'] not in ['SUCCESS', 'FAILED']:
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = 'FAILED', remark = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (f"Webhook status: {status}", txn['txn_id']))
                conn.commit()
                print(f"⚠ Marked transaction {txn['txn_id']} as FAILED")
                
        cursor.close()
        conn.close()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        print(f"❌ Error in payplus_veltrix_webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
