"""
Upilnk Coco Webhook/Callback Routes
Handles incoming payin webhooks
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
import json
import requests
from config import Config

upilnk_coco_callback_bp = Blueprint('upilnk_coco_callback', __name__)

@upilnk_coco_callback_bp.route('/api/callback/upilnk-coco', methods=['POST'])
def handle_upilnk_coco_callback():
    """Handle incoming webhook from Upilnk Coco"""
    try:
        data = request.get_json()
        if not data:
            data = request.form.to_dict()
            
        print(f"📥 Upilnk Coco Webhook Received: {json.dumps(data)}")
        
        # Payload format:
        # {
        #     "order_id": "your-order-id",
        #     "status": "paid",
        #     "tr_id": "unique_id"
        # }
        
        order_id = data.get('order_id')
        status = str(data.get('status', '')).lower()
        tr_id = data.get('tr_id')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing order_id'}), 400
            
        if status in ['paid', 'success', 'successful']:
            txn_status = 'success'
        elif status in ['failed', 'failure']:
            txn_status = 'failed'
        else:
            txn_status = 'pending'
            
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
            
        try:
            with conn.cursor() as cursor:
                # Find transaction
                cursor.execute("""
                    SELECT id, merchant_id, txn_id, order_id, amount, net_amount, charge_amount, callback_url, status, pg_partner
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'Upilnk_Coco'
                """, (order_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Upilnk Coco Webhook: Transaction not found for order {order_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                    
                txn_id = txn['txn_id']
                current_status = txn['status']
                merchant_id = txn['merchant_id']
                amount = float(txn['amount'])
                
                print(f"ℹ️ Transaction {txn_id} current status: {current_status}")
                
                if current_status in ['success', 'SUCCESS', 'failed', 'FAILED']:
                    print(f"⚠️ Transaction {txn_id} already marked as {current_status}")
                    return jsonify({'success': True, 'message': 'Already processed'}), 200
                    
                # Update status
                cursor.execute("""
                    UPDATE payin_transactions 
                    SET status = %s,
                        bank_ref_no = %s,
                        pg_txn_id = COALESCE(pg_txn_id, %s),
                        updated_at = NOW()
                    WHERE txn_id = %s
                """, (txn_status.upper(), tr_id, tr_id, txn_id))
                
                if txn_status == 'success':
                    # Credit merchant unsettled wallet
                    from wallet_service import wallet_service
                    wallet_service.credit_unsettled_wallet(
                        merchant_id=merchant_id,
                        amount=amount,
                        description=f"Payin credited (Unsettled) - {txn_id}",
                        reference_id=txn_id
                    )
                    
                conn.commit()
                print(f"✅ Upilnk Coco Webhook: Transaction {txn_id} updated to {txn_status.upper()}")
                
                # Forward callback to merchant if configured
                print(f"\n{'='*80}")
                print(f"MERCHANT CALLBACK FORWARDING - Upilnk_Coco")
                print(f"{'='*80}")
                
                try:
                    callback_url = txn.get('callback_url')
                    if callback_url:
                        callback_url = callback_url.strip() or None
                    
                    print(f"Step 1: Transaction callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    if not callback_url:
                        print(f"Step 2: Checking merchant_callbacks table")
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s
                        """, (merchant_id,))
                        merchant_callback_fallback = cursor.fetchone()
                        if merchant_callback_fallback and merchant_callback_fallback.get('payin_callback_url'):
                            callback_url = merchant_callback_fallback['payin_callback_url'].strip() or None
                        print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    if callback_url:
                        if 'api.moneyone.co.in/api/callback/' in callback_url or 'admin.moneyone.co.in/api/callback/' in callback_url:
                            print(f"⚠ Skipping callback forward - merchant callback URL is our own callback endpoint")
                        else:
                            merchant_callback_data = {
                                'txn_id': txn_id,
                                'order_id': order_id,
                                'status': txn_status.upper(),
                                'amount': str(amount),
                                'net_amount': str(txn.get('net_amount', amount)),
                                'charge_amount': str(txn.get('charge_amount', '0')),
                                'utr': tr_id or '',
                                'pg_txn_id': tr_id or '',
                                'payment_mode': 'UPI',
                                'pg_partner': 'Upilnk_Coco',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            print(f"Forwarding callback to merchant: {callback_url}")
                            
                            try:
                                callback_response = requests.post(
                                    callback_url,
                                    json=merchant_callback_data,
                                    headers={'Content-Type': 'application/json'},
                                    timeout=10
                                )
                                print(f"Merchant callback response: {callback_response.status_code}")
                                
                                cursor.execute("""
                                    INSERT INTO callback_logs 
                                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                """, (
                                    merchant_id, txn_id, callback_url, json.dumps(merchant_callback_data),
                                    callback_response.status_code, callback_response.text[:1000]
                                ))
                                conn.commit()
                                print(f"✓ Merchant callback sent successfully")
                            except requests.exceptions.RequestException as e:
                                print(f"ERROR: Failed to send merchant callback: {e}")
                                cursor.execute("""
                                    INSERT INTO callback_logs 
                                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                """, (
                                    merchant_id, txn_id, callback_url, json.dumps(merchant_callback_data),
                                    0, str(e)[:1000]
                                ))
                                conn.commit()
                    else:
                        print("No merchant callback URL configured")
                except Exception as e:
                    print(f"ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                        
                return jsonify({'success': True, 'message': 'Webhook processed successfully'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Upilnk Coco Webhook error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
