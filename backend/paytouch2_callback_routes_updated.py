"""
PayTouch2 Callback Routes (Updated with Mudrape/Airpay Pattern)
Handles webhook callbacks from:
1. PayTouch2 - for PAYOUT status updates
2. PayTouchPayin - for PAYIN status updates (QR payments)

CALLBACK FORWARDING PATTERN (Following Mudrape/Airpay):
1. Check payin_transactions.callback_url first (from transaction payload)
2. Then check merchant_callbacks.payin_callback_url as fallback
3. Prevent duplicate SUCCESS callbacks using callback_logs
4. Credit unsettled wallet for PAYIN SUCCESS
5. Log all callback attempts in callback_logs table
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from datetime import datetime
import json
import requests

paytouch2_callback_bp = Blueprint('paytouch2_callback', __name__, url_prefix='/api/callback')

@paytouch2_callback_bp.route('/paytouch2/payout', methods=['POST'])
def paytouch2_combined_callback():
    """
    Webhook endpoint for both PayTouch2 PAYOUT and PayTouchPayin PAYIN callbacks
    
    PayTouchPayin PAYIN Callback Format:
    {
        "status": "success",
        "txnid": "PTPIN...",
        "apitxnid": "DQR...",
        "amount": 200.95,
        "charge": 2,
        "utr": "608373377074",
        "product": "dynamicqrpayin"
    }
    
    PayTouch2 PAYOUT Callback Format:
    {
        "transaction_id": "...",
        "external_ref": "...",
        "status": "SUCCESS",
        "utr_no": "...",
        "amount": 1000
    }
    """
    try:
        # Get callback data
        callback_data = request.get_json() if request.is_json else request.form.to_dict()
        
        print("=" * 80)
        print("PayTouch Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        print(f"IP Address: {request.remote_addr}")
        
        # Detect callback type based on fields
        is_payin = 'txnid' in callback_data and 'product' in callback_data
        is_payout = 'transaction_id' in callback_data or 'external_ref' in callback_data
        
        if is_payin:
            print("🔍 Detected: PayTouchPayin PAYIN callback")
            return handle_paytouchpayin_callback(callback_data)
        elif is_payout:
            print("🔍 Detected: PayTouch2 PAYOUT callback")
            return handle_paytouch2_payout_callback(callback_data)
        else:
            print("❌ ERROR: Unknown callback format")
            return jsonify({'success': False, 'message': 'Unknown callback format'}), 400
            
    except Exception as e:
        print(f"❌ ERROR in callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


def handle_paytouchpayin_callback(callback_data):
    """
    Handle PayTouchPayin PAYIN callback
    Following Mudrape/Airpay callback forwarding pattern
    """
    try:
        # Extract callback fields
        status = callback_data.get('status', '').lower()
        txnid = callback_data.get('txnid')
        apitxnid = callback_data.get('apitxnid')
        amount = callback_data.get('amount')
        charge = callback_data.get('charge')
        utr = callback_data.get('utr', '')
        product = callback_data.get('product', '')
        
        if not txnid:
            print(f"❌ Missing txnid in callback")
            return jsonify({'success': False, 'error': 'Missing txnid'}), 400
        
        print(f"📋 PayTouchPayin Callback Details:")
        print(f"  TXN ID: {txnid}")
        print(f"  API TXN ID: {apitxnid}")
        print(f"  Status: {status}")
        print(f"  Amount: {amount}")
        print(f"  Charge: {charge}")
        print(f"  UTR: {utr}")
        print(f"  Product: {product}")
        
        # Map status
        status_map = {
            'success': 'SUCCESS',
            'failed': 'FAILED',
            'pending': 'INITIATED'
        }
        mapped_status = status_map.get(status, 'INITIATED')
        print(f"  Mapped Status: {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Find transaction by txn_id
            cursor.execute("""
                SELECT txn_id, status, merchant_id, amount, net_amount, charge_amount, order_id, callback_url
                FROM payin_transactions
                WHERE txn_id = %s AND pg_partner = 'PayTouchPayin'
            """, (txnid,))
            
            txn_row = cursor.fetchone()
            
            if not txn_row:
                print(f"❌ Transaction not found: {txnid}")
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Transaction not found'}), 404
            
            # Convert to dict (DictCursor returns dict)
            txn = txn_row if isinstance(txn_row, dict) else {
                'txn_id': txn_row[0],
                'status': txn_row[1],
                'merchant_id': txn_row[2],
                'amount': txn_row[3],
                'net_amount': txn_row[4],
                'charge_amount': txn_row[5],
                'order_id': txn_row[6],
                'callback_url': txn_row[7]
            }
            
            print(f"✓ Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
            
            # Update transaction status
            if mapped_status == 'SUCCESS':
                # Check if wallet has already been credited (idempotency check)
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (txn['txn_id'],))
                
                wallet_check = cursor.fetchone()
                wallet_credit_exists = (wallet_check['count'] if isinstance(wallet_check, dict) else wallet_check[0]) > 0
                
                if wallet_credit_exists:
                    print(f"⚠️ Wallet already credited - skipping duplicate")
                    
                    # Just update transaction status and UTR if needed
                    if txn['status'] != 'SUCCESS':
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, utr, apitxnid, txn['txn_id']))
                        conn.commit()
                        print(f"✓ Updated transaction status to SUCCESS")
                    elif utr:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (utr, apitxnid, txn['txn_id']))
                        conn.commit()
                        print(f"✓ Updated UTR: {utr}")
                else:
                    # First time processing SUCCESS - credit unsettled wallet
                    print(f"Processing SUCCESS callback - crediting unsettled wallet")
                    
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, utr, apitxnid, txn['txn_id']))
                    
                    net_amount = float(txn['net_amount'])
                    charge_amount = float(txn['charge_amount'])
                    
                    # Get current unsettled balance
                    cursor.execute("""
                        SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                    """, (txn['merchant_id'],))
                    wallet_result = cursor.fetchone()
                    
                    if wallet_result:
                        unsettled_before = float(wallet_result['unsettled_balance'] if isinstance(wallet_result, dict) else wallet_result[0])
                        unsettled_after = unsettled_before + net_amount
                        
                        cursor.execute("""
                            UPDATE merchant_wallet
                            SET unsettled_balance = %s, last_updated = NOW()
                            WHERE merchant_id = %s
                        """, (unsettled_after, txn['merchant_id']))
                    else:
                        # Create wallet if doesn't exist
                        cursor.execute("""
                            INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                            VALUES (%s, 0.00, 0.00, %s)
                        """, (txn['merchant_id'], net_amount))
                        unsettled_before = 0.00
                        unsettled_after = net_amount
                    
                    # Record merchant wallet transaction
                    from wallet_service import wallet_service
                    wallet_txn_id = wallet_service.generate_txn_id('MWT')
                    
                    cursor.execute("""
                        INSERT INTO merchant_wallet_transactions
                        (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                        VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                    """, (
                        txn['merchant_id'], 
                        wallet_txn_id, 
                        net_amount,
                        unsettled_before,
                        unsettled_after,
                        f"PayTouchPayin Payin credited to unsettled wallet - {txn['order_id']}",
                        txn['txn_id']
                    ))
                    
                    print(f"✓ Merchant unsettled wallet credited: {net_amount}")
                    
                    # Credit admin unsettled wallet with charge amount
                    cursor.execute("""
                        SELECT unsettled_balance FROM admin_wallet WHERE admin_id = 'admin'
                    """, ())
                    admin_wallet_result = cursor.fetchone()
                    
                    if admin_wallet_result:
                        admin_unsettled_before = float(admin_wallet_result['unsettled_balance'] if isinstance(admin_wallet_result, dict) else admin_wallet_result[0])
                        admin_unsettled_after = admin_unsettled_before + charge_amount
                        
                        cursor.execute("""
                            UPDATE admin_wallet
                            SET unsettled_balance = %s, last_updated = NOW()
                            WHERE admin_id = 'admin'
                        """, (admin_unsettled_after,))
                    else:
                        # Create admin wallet if doesn't exist
                        cursor.execute("""
                            INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                            VALUES ('admin', 0.00, %s)
                        """, (charge_amount,))
                        admin_unsettled_before = 0.00
                        admin_unsettled_after = charge_amount
                    
                    # Record admin wallet transaction
                    admin_wallet_txn_id = wallet_service.generate_txn_id('AWT')
                    
                    cursor.execute("""
                        INSERT INTO admin_wallet_transactions
                        (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                        VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                    """, (
                        'admin',
                        admin_wallet_txn_id,
                        charge_amount,
                        admin_unsettled_before,
                        admin_unsettled_after,
                        f"PayTouchPayin Payin charge - {txn['order_id']}",
                        txn['txn_id']
                    ))
                    
                    print(f"✓ Admin unsettled wallet credited: {charge_amount}")
                    
                    conn.commit()
            else:
                # FAILED or other status - just update transaction
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = %s, bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, utr, apitxnid, txn['txn_id']))
                
                conn.commit()
            
            print(f"✅ Transaction updated successfully")
            
            # ========================================================================
            # MERCHANT CALLBACK FORWARDING (Following Mudrape/Airpay Pattern)
            # ========================================================================
            print("=" * 80)
            print("MERCHANT CALLBACK FORWARDING - PayTouchPayin")
            print("=" * 80)
            
            merchant_id = txn['merchant_id']
            callback_url = None
            
            # Step 1: Check transaction callback_url first (from payin request payload)
            if txn.get('callback_url'):
                callback_url = txn['callback_url'].strip()
                if not callback_url:  # Empty string after strip
                    callback_url = None
            
            print(f"Step 1: Transaction callback_url from DB: {callback_url if callback_url else 'NOT SET'}")
            
            # Step 2: If no callback URL in transaction, check merchant_callbacks table
            if not callback_url:
                print(f"Step 2: Checking merchant_callbacks table for merchant: {merchant_id}")
                cursor.execute("""
                    SELECT payin_callback_url FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                merchant_callback_row = cursor.fetchone()
                if merchant_callback_row:
                    cb_url = merchant_callback_row['payin_callback_url'] if isinstance(merchant_callback_row, dict) else merchant_callback_row[0]
                    if cb_url:
                        callback_url = cb_url.strip()
                        if not callback_url:  # Empty string after strip
                            callback_url = None
                
                print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
            
            if callback_url:
                # DUPLICATE PREVENTION: Check if we already sent a SUCCESS callback for this transaction
                if mapped_status == 'SUCCESS':
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM callback_logs
                        WHERE merchant_id = %s 
                        AND txn_id = %s 
                        AND response_code BETWEEN 200 AND 299
                        AND request_data LIKE %s
                    """, (merchant_id, txn['txn_id'], '%"status": "SUCCESS"%'))
                    
                    callback_result = cursor.fetchone()
                    success_callback_sent = (callback_result['count'] if isinstance(callback_result, dict) else callback_result[0]) > 0
                    
                    if success_callback_sent:
                        print(f"⚠ SUCCESS callback already sent to merchant - skipping duplicate")
                        print("=" * 80)
                        
                        cursor.close()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Callback processed (duplicate prevented)',
                            'txn_id': txn['txn_id'],
                            'status': mapped_status
                        }), 200
                
                # Prepare callback payload for merchant (matching standard format)
                merchant_callback_data = {
                    'txn_id': txn['txn_id'],
                    'order_id': txn['order_id'],
                    'status': mapped_status,
                    'utr': utr or '',
                    'pg_partner': 'PayTouchPayin',
                    'pg_txn_id': apitxnid or '',
                    'amount': float(txn['amount']),
                    'net_amount': float(txn['net_amount']),
                    'charge_amount': float(txn['charge_amount']),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"Forwarding PayTouchPayin callback to merchant: {callback_url}")
                print(f"Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                
                try:
                    callback_response = requests.post(
                        callback_url,
                        json=merchant_callback_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    
                    print(f"Merchant callback response: {callback_response.status_code}")
                    print(f"Merchant callback response body: {callback_response.text[:200]}")
                    
                    # Log callback attempt
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn['txn_id'],
                        callback_url,
                        json.dumps(merchant_callback_data),
                        callback_response.status_code,
                        callback_response.text[:1000]
                    ))
                    conn.commit()
                    
                    print(f"✓ PayTouchPayin merchant callback sent successfully and logged")
                    
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: Failed to send PayTouchPayin merchant callback: {e}")
                    
                    # Log failed callback attempt
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn['txn_id'],
                        callback_url,
                        json.dumps(merchant_callback_data),
                        0,
                        str(e)[:1000]
                    ))
                    conn.commit()
            else:
                print(f"⚠ No callback URL configured for merchant {merchant_id}")
                print(f"  Checked: 1) payin_transactions.callback_url, 2) merchant_callbacks.payin_callback_url")
            
            cursor.close()
            conn.close()
            
            print("=" * 80)
            print("✅ PayTouchPayin callback processed successfully")
            print("=" * 80)
            
            return jsonify({
                'success': True,
                'message': 'Callback processed successfully'
            }), 200
            
        except Exception as e:
            if conn:
                conn.close()
            raise e
            
    except Exception as e:
        print(f"❌ Error processing PayTouchPayin callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



def handle_paytouch2_payout_callback(callback_data):
    """
    Handle PayTouch2 PAYOUT callback
    (Original PayTouch2 payout logic - unchanged)
    """
    try:
        # Extract data from callback
        transaction_id = callback_data.get('transaction_id') or callback_data.get('transactionId')
        external_ref = callback_data.get('external_ref') or callback_data.get('request_id')
        status = callback_data.get('status', 'PENDING')
        
        # Extract UTR - check multiple possible field names
        utr = (
            callback_data.get('utr_no') or
            callback_data.get('utr') or
            callback_data.get('bank_ref_no') or
            callback_data.get('bankRefNo') or
            callback_data.get('bank_reference_number') or
            callback_data.get('rrn') or
            callback_data.get('reference_number') or
            callback_data.get('utr_number')
        )
        
        amount = callback_data.get('amount')
        message = callback_data.get('message', '')
        
        if not transaction_id and not external_ref:
            print("ERROR: No transaction_id or external_ref in callback")
            return jsonify({'success': False, 'message': 'Missing transaction identifier'}), 400
        
        print(f"📋 PayTouch2 Payout Callback Details:")
        print(f"  Transaction ID: {transaction_id}")
        print(f"  External Ref: {external_ref}")
        print(f"  Status: {status}")
        print(f"  UTR: {utr}")
        print(f"  Amount: {amount}")
        print(f"  Message: {message}")
        
        # Map PayTouch2 status to our status
        status_map = {
            'SUCCESS': 'SUCCESS',
            'PENDING': 'QUEUED',
            'FAILED': 'FAILED',
            'PROCESSING': 'INPROCESS'
        }
        mapped_status = status_map.get(status.upper(), 'QUEUED')
        
        print(f"  Mapped Status: {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Find transaction by pg_txn_id or reference_id
            if transaction_id:
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, admin_id, reference_id, amount, net_amount, charge_amount
                    FROM payout_transactions
                    WHERE pg_txn_id = %s AND pg_partner = 'Paytouch2'
                """, (transaction_id,))
            else:
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, admin_id, reference_id, amount, net_amount, charge_amount
                    FROM payout_transactions
                    WHERE reference_id = %s AND pg_partner = 'Paytouch2'
                """, (external_ref,))
            
            txn_row = cursor.fetchone()
            
            if not txn_row:
                print(f"ERROR: Transaction not found")
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            # Convert to dict
            txn = txn_row if isinstance(txn_row, dict) else {
                'txn_id': txn_row[0],
                'status': txn_row[1],
                'merchant_id': txn_row[2],
                'admin_id': txn_row[3],
                'reference_id': txn_row[4],
                'amount': txn_row[5],
                'net_amount': txn_row[6],
                'charge_amount': txn_row[7]
            }
            
            print(f"✓ Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
            
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
            print(f"✅ Transaction updated successfully")
            
            cursor.close()
            conn.close()
            
            print("=" * 80)
            print("✅ PayTouch2 payout callback processed successfully")
            print("=" * 80)
            
            return jsonify({
                'success': True,
                'message': 'Callback processed successfully',
                'txn_id': txn['txn_id'],
                'status': mapped_status
            }), 200
            
        except Exception as e:
            if conn:
                conn.close()
            raise e
            
    except Exception as e:
        print(f"❌ Error processing PayTouch2 payout callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
