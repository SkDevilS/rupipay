"""
Airpay V4 Callback Routes
Handles Airpay IPN (Instant Payment Notification) callbacks with encryption
"""

from flask import Blueprint, request, jsonify
from airpay_service_v4 import airpay_service_v4
from database import get_db_connection
import json
from datetime import datetime

airpay_callback_v4_bp = Blueprint('airpay_callback_v4', __name__, url_prefix='/api/callback/airpay/v4')

@airpay_callback_v4_bp.route('/payin', methods=['POST'])
def airpay_payin_callback_v4():
    """
    Handle Airpay V4 payin callback (IPN)
    According to documentation, Airpay sends encrypted JSON data
    """
    try:
        print(f"=== Airpay V4 Payin Callback Received ===")
        print(f"Headers: {dict(request.headers)}")
        print(f"Content-Type: {request.content_type}")
        
        # Get callback data
        if request.content_type == 'application/json':
            callback_data = request.get_json()
        else:
            callback_data = request.form.to_dict()
        
        print(f"Raw callback data: {callback_data}")
        
        if not callback_data:
            print("No callback data received")
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        # Check if data is encrypted
        if 'data' in callback_data and 'encryptionkey' in callback_data:
            # Decrypt the callback data
            encrypted_data = callback_data.get('data')
            decrypted_data = airpay_service_v4.decrypt_data(encrypted_data)
            
            if not decrypted_data:
                print("Failed to decrypt callback data")
                return jsonify({'success': False, 'message': 'Failed to decrypt callback'}), 400
            
            callback_data = decrypted_data
            print(f"Decrypted callback data: {callback_data}")
        
        # Extract key fields from callback
        merchant_id = callback_data.get('merchant_id')
        ap_transactionid = callback_data.get('ap_transactionid')
        amount = callback_data.get('amount')
        transaction_status = callback_data.get('transaction_status')
        orderid = callback_data.get('orderid')
        message = callback_data.get('message', '')
        
        print(f"Parsed callback:")
        print(f"  Merchant ID: {merchant_id}")
        print(f"  Order ID: {orderid}")
        print(f"  Airpay Txn ID: {ap_transactionid}")
        print(f"  Status: {transaction_status}")
        print(f"  Amount: {amount}")
        print(f"  Message: {message}")
        
        if not orderid or not ap_transactionid:
            print("Missing required callback fields")
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Find transaction in database
        conn = get_db_connection()
        if not conn:
            print("Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by order_id
                cursor.execute("""
                    SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status, callback_url
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'Airpay'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (orderid,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"Transaction not found for order_id: {orderid}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found transaction: {txn['txn_id']}")
                
                # Map Airpay status to our status
                if transaction_status == 200:
                    new_status = 'SUCCESS'
                elif transaction_status in [400, 401, 402, 403, 405]:
                    new_status = 'FAILED'
                elif transaction_status == 211:
                    new_status = 'PROCESSING'
                else:
                    new_status = 'PENDING'
                
                print(f"Status mapping: {transaction_status} -> {new_status}")
                
                # Only update if status changed
                if txn['status'] != new_status:
                    print(f"Updating transaction status from {txn['status']} to {new_status}")
                    
                    # Extract additional fields
                    rrn = callback_data.get('rrn') or callback_data.get('utr_no')
                    payment_mode = callback_data.get('chmod', 'UPI').upper()
                    
                    # Update transaction
                    if new_status in ['SUCCESS', 'FAILED']:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s,
                                pg_txn_id = %s,
                                bank_ref_no = %s,
                                payment_mode = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
                    else:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s,
                                pg_txn_id = %s,
                                bank_ref_no = %s,
                                payment_mode = %s,
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
                    
                    # If successful, credit wallets
                    if new_status == 'SUCCESS':
                        # Check if wallet already credited (idempotency)
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM merchant_wallet_transactions
                            WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                        """, (txn['txn_id'],))
                        
                        wallet_already_credited = cursor.fetchone()['count'] > 0
                        
                        if not wallet_already_credited:
                            print(f"Crediting wallets for successful payment")
                            
                            from wallet_service import wallet_service as wallet_svc
                            
                            wallet_result = wallet_svc.credit_unsettled_wallet(
                                merchant_id=txn['merchant_id'],
                                amount=float(txn['net_amount']),
                                description=f"PayIn received (Airpay V4 callback) - {orderid}",
                                reference_id=txn['txn_id']
                            )
                            
                            if wallet_result['success']:
                                print(f"✓ Merchant wallet credited: ₹{txn['net_amount']}")
                            else:
                                print(f"✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                            
                            admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                                admin_id='admin',
                                amount=float(txn['charge_amount']),
                                description=f"PayIn charge (Airpay V4 callback) - {orderid}",
                                reference_id=txn['txn_id']
                            )
                            
                            if admin_wallet_result['success']:
                                print(f"✓ Admin wallet credited: ₹{txn['charge_amount']}")
                            else:
                                print(f"✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                        else:
                            print(f"⚠ Wallet already credited for this transaction - skipping")
                    
                    conn.commit()
                    print(f"✓ Transaction updated successfully")
                    
                    # Send callback to merchant if callback URL exists
                    if txn.get('callback_url'):
                        print(f"Sending callback to merchant: {txn['callback_url']}")
                        send_merchant_callback(txn, callback_data, new_status)
                else:
                    print(f"Status unchanged ({txn['status']}), no update needed")
                
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Airpay V4 callback error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


def send_merchant_callback(txn, airpay_callback_data, status):
    """Send callback notification to merchant"""
    try:
        import requests
        
        callback_url = txn.get('callback_url')
        if not callback_url:
            print("No callback URL configured")
            return
        
        # Prepare merchant callback data
        merchant_callback_data = {
            'txn_id': txn['txn_id'],
            'order_id': txn['order_id'],
            'merchant_id': txn['merchant_id'],
            'amount': str(txn['amount']),
            'net_amount': str(txn['net_amount']),
            'charge_amount': str(txn['charge_amount']),
            'status': status,
            'payment_mode': airpay_callback_data.get('chmod', 'UPI'),
            'pg_txn_id': airpay_callback_data.get('ap_transactionid'),
            'bank_ref_no': airpay_callback_data.get('rrn') or airpay_callback_data.get('utr_no'),
            'message': airpay_callback_data.get('message', ''),
            'pg_partner': 'Airpay',
            'callback_time': datetime.now().isoformat()
        }
        
        print(f"Sending merchant callback to: {callback_url}")
        print(f"Callback data: {merchant_callback_data}")
        
        response = requests.post(
            callback_url,
            json=merchant_callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Merchant callback response: {response.status_code} - {response.text}")
        
        # Log callback attempt
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs (
                            txn_id, callback_url, callback_data, response_status, 
                            response_data, created_at
                        ) VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (
                        txn['txn_id'],
                        callback_url,
                        json.dumps(merchant_callback_data),
                        response.status_code,
                        response.text[:1000]
                    ))
                    conn.commit()
            finally:
                conn.close()
        
    except Exception as e:
        print(f"Merchant callback error: {e}")
        import traceback
        traceback.print_exc()
