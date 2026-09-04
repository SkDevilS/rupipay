"""
Tourquest Callback Routes
Handles webhook callbacks from Tourquest payment gateway
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
import json
import requests

tourquest_callback_bp = Blueprint('tourquest_callback', __name__, url_prefix='/api/callback')

@tourquest_callback_bp.route('/tourquest/payin', methods=['POST'])
def tourquest_payin_callback():
    """
    Webhook endpoint for Tourquest payin status updates
    Tourquest will call this when payin status changes
    """
    try:
        # Get callback data from Tourquest
        callback_data = request.json
        
        print("=" * 80)
        print("Tourquest Payin Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Extract data from callback
        clientrefno = callback_data.get('clientrefno')
        txn_id = callback_data.get('txnid')
        status = callback_data.get('status', '').upper()
        utr = callback_data.get('utr')
        amount = callback_data.get('amount')
        
        if not clientrefno:
            print("ERROR: No clientrefno in callback")
            return jsonify({'success': False, 'message': 'Missing clientrefno'}), 400
        
        print(f"Client Ref No: {clientrefno}")
        print(f"TXN ID: {txn_id}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        
        # Map status
        if status == 'SUCCESS':
            mapped_status = 'SUCCESS'
        elif status == 'FAILED':
            mapped_status = 'FAILED'
        else:
            mapped_status = 'INITIATED'
        
        print(f"Mapped Status: {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by pg_txn_id (which is the clientrefno)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount as txn_amount, order_id, net_amount, charge_amount
                    FROM payin_transactions
                    WHERE pg_txn_id = %s AND pg_partner = 'Tourquest'
                """, (clientrefno,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for clientrefno: {clientrefno}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # Update transaction
                if mapped_status == 'SUCCESS':
                    # Check if wallet has already been credited (idempotency check)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn['txn_id'],))
                    
                    wallet_credit_exists = cursor.fetchone()['count'] > 0
                    
                    if wallet_credit_exists:
                        print(f"⚠ Wallet already credited for this transaction - skipping wallet credit")
                        print(f"  This is a duplicate callback from Tourquest")
                        
                        # Just update transaction status if needed
                        if txn['status'] != 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = %s, bank_ref_no = %s, payment_mode = 'UPI',
                                    completed_at = NOW(), updated_at = NOW()
                                WHERE pg_txn_id = %s
                            """, (mapped_status, utr, clientrefno))
                            conn.commit()
                            print(f"✓ Updated transaction status to SUCCESS")
                        elif utr and utr != txn.get('bank_ref_no'):
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET bank_ref_no = %s, updated_at = NOW()
                                WHERE pg_txn_id = %s
                            """, (utr, clientrefno))
                            conn.commit()
                            print(f"✓ Updated UTR: {utr}")
                    else:
                        # First time processing SUCCESS - credit unsettled wallet
                        print(f"Processing SUCCESS callback - crediting unsettled wallet")
                        
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, bank_ref_no = %s, payment_mode = 'UPI',
                                completed_at = NOW(), updated_at = NOW()
                            WHERE pg_txn_id = %s
                        """, (mapped_status, utr, clientrefno))
                        
                        # Credit merchant unsettled wallet (net amount after charges)
                        net_amount = float(txn['net_amount'])
                        charge_amount = float(txn['charge_amount'])
                        
                        # Get current unsettled balance
                        cursor.execute("""
                            SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        wallet_result = cursor.fetchone()
                        
                        if wallet_result:
                            unsettled_before = float(wallet_result['unsettled_balance'])
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
                        txn_id = wallet_service.generate_txn_id('MWT')
                        cursor.execute("""
                            INSERT INTO merchant_wallet_transactions
                            (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                            VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                        """, (
                            txn['merchant_id'], 
                            txn_id, 
                            net_amount,
                            unsettled_before,
                            unsettled_after,
                            f"Payin credited to unsettled wallet via Tourquest - {txn['order_id']}",
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Merchant unsettled wallet credited: {net_amount}")
                        
                        # Credit admin unsettled wallet with charge amount
                        cursor.execute("""
                            SELECT unsettled_balance FROM admin_wallet WHERE admin_id = 'admin'
                        """, ())
                        admin_wallet_result = cursor.fetchone()
                        
                        if admin_wallet_result:
                            admin_unsettled_before = float(admin_wallet_result['unsettled_balance'])
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
                        admin_txn_id = wallet_service.generate_txn_id('AWT')
                        cursor.execute("""
                            INSERT INTO admin_wallet_transactions
                            (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                            VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                        """, (
                            'admin',
                            admin_txn_id,
                            charge_amount,
                            admin_unsettled_before,
                            admin_unsettled_after,
                            f"Payin charge via Tourquest - {txn['order_id']}",
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Admin unsettled wallet credited: {charge_amount}")
                        
                        conn.commit()
                else:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, bank_ref_no = %s, updated_at = NOW()
                        WHERE pg_txn_id = %s
                    """, (mapped_status, utr, clientrefno))
                
                conn.commit()
                
                print("=" * 80)
                print("Payin callback processed successfully")
                print("=" * 80)
                
                # Forward callback to merchant if configured
                try:
                    # First, get the callback URL from the transaction itself (sent in payload)
                    cursor.execute("""
                        SELECT callback_url FROM payin_transactions
                        WHERE pg_txn_id = %s
                    """, (clientrefno,))
                    
                    txn_callback = cursor.fetchone()
                    callback_url = txn_callback.get('callback_url') if txn_callback else None
                    
                    # If no callback URL in transaction, check merchant_callbacks table
                    if not callback_url:
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        
                        merchant_callback = cursor.fetchone()
                        if merchant_callback and merchant_callback.get('payin_callback_url'):
                            callback_url = merchant_callback['payin_callback_url'].strip()
                            if not callback_url:  # Empty string after strip
                                callback_url = None
                    
                    if callback_url:
                        print(f"Merchant callback_url: {callback_url}")
                        import requests
                        
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'order_id': txn['order_id'],
                            'status': mapped_status,
                            'amount': float(txn['txn_amount']),
                            'utr': utr,
                            'pg_txn_id': clientrefno,
                            'pg_partner': 'Tourquest',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(f"Forwarding callback to merchant: {callback_url}")
                        print(f"Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                        
                        try:
                            callback_response = requests.post(
                                callback_url,
                                json=merchant_callback_data,
                                headers={'Content-Type': 'application/json'},
                                timeout=10
                            )
                            
                            print(f"Merchant callback response: {callback_response.status_code}")
                            
                            # Log callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                callback_url,
                                json.dumps(merchant_callback_data),
                                callback_response.status_code,
                                callback_response.text[:1000]  # Limit response data
                            ))
                            conn.commit()
                            
                            print(f"✓ Merchant callback sent successfully")
                            
                        except requests.exceptions.RequestException as e:
                            print(f"ERROR: Failed to send merchant callback: {e}")
                            
                            # Log failed callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                callback_url,
                                json.dumps(merchant_callback_data),
                                0,
                                str(e)[:1000]
                            ))
                            conn.commit()
                    else:
                        print("No merchant callback URL configured (neither in transaction nor merchant_callbacks table)")
                        
                except Exception as e:
                    print(f"ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully',
                    'txn_id': txn['txn_id'],
                    'status': mapped_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"ERROR in payin callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
