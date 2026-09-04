from flask import Blueprint, request, jsonify
import logging
from database import get_db_connection
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rang_callback_bp = Blueprint('rang_callback', __name__)

@rang_callback_bp.route('/rang-payin-callback', methods=['POST'])
def rang_payin_callback():
    """Handle Rang payin callback"""
    try:
        # Log raw callback data
        logger.info("=== RANG PAYIN CALLBACK RECEIVED ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.content_type}")
        
        # Handle both form data and JSON (Rang is sending JSON now)
        callback_data = {}
        
        if request.content_type and 'application/json' in request.content_type:
            # JSON format
            callback_data = request.get_json() or {}
            logger.info("Received JSON callback data")
        elif request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            # Form-encoded format
            callback_data = request.form.to_dict()
            logger.info("Received form-encoded callback data")
        else:
            # Try both formats as fallback
            callback_data = request.get_json() or request.form.to_dict() or {}
            logger.info("Using fallback data parsing")
        
        logger.info(f"Callback Data: {callback_data}")
        
        # Extract callback parameters
        status_id = callback_data.get('status_id')
        amount = callback_data.get('amount')
        utr = callback_data.get('utr')
        client_id = callback_data.get('client_id')  # This should be our txn_id
        message = callback_data.get('message')
        
        if not client_id:
            logger.error("Missing client_id in callback")
            logger.error(f"Available fields: {list(callback_data.keys())}")
            return jsonify({'status': 'error', 'message': 'Missing client_id'}), 400
        
        logger.info(f"Processing callback for client_id (RefID): {client_id}")
        
        # Get transaction from database
        # client_id is the RefID we sent to Rang (our txn_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM payin_transactions 
            WHERE txn_id = %s AND pg_partner = 'Rang'
        """, (client_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            logger.error(f"Transaction not found for client_id (RefID): {client_id}")
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Transaction not found'}), 404
        
        # Map Rang status to our status
        # 1: Success, 2: Pending, 3: Failed
        if status_id == '1':
            new_status = 'SUCCESS'
        elif status_id == '2':
            new_status = 'INITIATED'
        elif status_id == '3':
            new_status = 'FAILED'
        else:
            new_status = 'INITIATED'
        
        logger.info(f"Updating transaction {client_id} status from {transaction['status']} to {new_status}")
        
        # Update transaction status (same pattern as Mudrape)
        # Use the actual txn_id from the fetched transaction, not client_id
        txn_id = transaction['txn_id']
        
        if new_status == 'SUCCESS':
            # For SUCCESS status, update with completed_at timestamp
            cursor.execute("""
                UPDATE payin_transactions 
                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                WHERE txn_id = %s
            """, (new_status, utr, client_id, txn_id))
        elif new_status == 'FAILED':
            # For FAILED status, update with completed_at timestamp
            cursor.execute("""
                UPDATE payin_transactions 
                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                WHERE txn_id = %s
            """, (new_status, utr, client_id, txn_id))
        else:
            # For other statuses (INITIATED, etc.), don't set completed_at
            cursor.execute("""
                UPDATE payin_transactions 
                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                WHERE txn_id = %s
            """, (new_status, utr, client_id, txn_id))
        
        # Handle wallet operations for successful payments
        if new_status == 'SUCCESS' and transaction['status'] != 'SUCCESS':
            logger.info(f"Processing successful payment for transaction: {txn_id}")
            
            # Check if wallet has already been credited (idempotency check)
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (txn_id,))
            
            wallet_credit_exists = cursor.fetchone()['count'] > 0
            
            if not wallet_credit_exists:
                # Credit merchant unsettled wallet
                cursor.execute("""
                    SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                """, (transaction['merchant_id'],))
                wallet_result = cursor.fetchone()
                
                if wallet_result:
                    unsettled_before = float(wallet_result['unsettled_balance'])
                    unsettled_after = unsettled_before + float(transaction['net_amount'])
                    
                    cursor.execute("""
                        UPDATE merchant_wallet
                        SET unsettled_balance = %s, last_updated = NOW()
                        WHERE merchant_id = %s
                    """, (unsettled_after, transaction['merchant_id']))
                else:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, 0.00, 0.00, %s)
                    """, (transaction['merchant_id'], transaction['net_amount']))
                    unsettled_before = 0.00
                    unsettled_after = float(transaction['net_amount'])
                
                # Record merchant wallet transaction
                from wallet_service import wallet_service
                wallet_txn_id = wallet_service.generate_txn_id('MWT')
                
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                """, (
                    transaction['merchant_id'], 
                    wallet_txn_id, 
                    transaction['net_amount'],
                    unsettled_before,
                    unsettled_after,
                    f"Rang Payin credited to unsettled wallet - {transaction['order_id']}",
                    txn_id
                ))
                
                logger.info(f"Credited {transaction['net_amount']} to merchant {transaction['merchant_id']} unsettled wallet")
                
                # Credit admin unsettled wallet with charge amount
                cursor.execute("""
                    SELECT unsettled_balance FROM admin_wallet WHERE admin_id = 'admin'
                """, ())
                admin_wallet_result = cursor.fetchone()
                
                if admin_wallet_result:
                    admin_unsettled_before = float(admin_wallet_result['unsettled_balance'])
                    admin_unsettled_after = admin_unsettled_before + float(transaction['charge_amount'])
                    
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
                    """, (transaction['charge_amount'],))
                    admin_unsettled_before = 0.00
                    admin_unsettled_after = float(transaction['charge_amount'])
                
                # Record admin wallet transaction
                admin_wallet_txn_id = wallet_service.generate_txn_id('AWT')
                
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                """, (
                    'admin',
                    admin_wallet_txn_id,
                    transaction['charge_amount'],
                    admin_unsettled_before,
                    admin_unsettled_after,
                    f"Rang Payin charge - {transaction['order_id']}",
                    txn_id
                ))
                
                logger.info(f"Credited {transaction['charge_amount']} to admin unsettled wallet")
            else:
                logger.info(f"Wallet already credited for this transaction - skipping duplicate credit")
        
        conn.commit()
        
        # Send callback to merchant if configured (same logic as Mudrape)
        print("=" * 80)
        print("MERCHANT CALLBACK FORWARDING - Rang")
        print("=" * 80)
        try:
            # First, get the callback URL from the transaction itself (sent in payload)
            cursor.execute("""
                SELECT callback_url FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn_callback = cursor.fetchone()
            callback_url = None
            
            if txn_callback and txn_callback.get('callback_url'):
                callback_url = txn_callback['callback_url'].strip()
                if not callback_url:  # Empty string after strip
                    callback_url = None
            
            print(f"Step 1: Transaction callback_url from DB: {callback_url if callback_url else 'NOT SET'}")
            
            # If no callback URL in transaction, check merchant_callbacks table
            if not callback_url:
                print(f"Step 2: Checking merchant_callbacks table for merchant: {transaction['merchant_id']}")
                cursor.execute("""
                    SELECT payin_callback_url FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (transaction['merchant_id'],))
                
                merchant_callback = cursor.fetchone()
                if merchant_callback and merchant_callback.get('payin_callback_url'):
                    callback_url = merchant_callback['payin_callback_url'].strip()
                    if not callback_url:  # Empty string after strip
                        callback_url = None
                
                print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
            
            if callback_url:
                # DUPLICATE PREVENTION: Check if we already sent a SUCCESS callback for this transaction
                if new_status == 'SUCCESS':
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM callback_logs
                        WHERE merchant_id = %s 
                        AND txn_id = %s 
                        AND response_code BETWEEN 200 AND 299
                        AND request_data LIKE %s
                    """, (transaction['merchant_id'], transaction['txn_id'], '%"status": "SUCCESS"%'))
                    
                    success_callback_sent = cursor.fetchone()['count'] > 0
                    
                    if success_callback_sent:
                        print(f"⚠ SUCCESS callback already sent to merchant - skipping duplicate")
                        print(f"  This is a duplicate callback from Rang")
                        print("=" * 80)
                        
                        return jsonify({
                            'success': True,
                            'message': 'Callback processed (duplicate prevented)',
                            'txn_id': transaction['txn_id'],
                            'status': new_status
                        }), 200
                
                import requests
                
                # Prepare callback payload for merchant (matching Mudrape format)
                # Include PG partner information for merchant to identify source
                merchant_callback_data = {
                    'utr': utr or '',
                    'amount': float(transaction['amount']),
                    'ref_id': transaction['order_id'],
                    'source': 'Rang',  # PG partner name
                    'status': new_status,
                    'txn_id': transaction['txn_id'],  # Our internal txn_id
                    'pg_txn_id': client_id or '',  # Rang's client_id
                    'pg_partner': 'Rang',  # Explicitly include PG partner
                    'payeeVpa': '',
                    'timestamp': datetime.now().isoformat(),
                    'order_id': transaction['order_id']  # Keep for backward compatibility
                }
                
                print(f"Forwarding Rang callback to merchant: {callback_url}")
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
                        transaction['merchant_id'],
                        transaction['txn_id'],
                        callback_url,
                        json.dumps(merchant_callback_data),
                        callback_response.status_code,
                        callback_response.text[:1000]  # Limit response data
                    ))
                    conn.commit()
                    
                    print(f"✓ Rang merchant callback sent successfully and logged")
                    
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: Failed to send Rang merchant callback: {e}")
                    
                    # Log failed callback attempt
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        transaction['merchant_id'],
                        transaction['txn_id'],
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
        
        cursor.close()
        conn.close()
        
        print("=" * 80)
        print("Rang callback processed successfully")
        print("=" * 80)
        
        return jsonify({
            'success': True,
            'message': 'Callback processed successfully',
            'txn_id': transaction['txn_id'],
            'status': new_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing Rang callback: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@rang_callback_bp.route('/test-rang-callback', methods=['POST'])
def test_rang_callback():
    """Test endpoint for Rang callback"""
    try:
        logger.info("=== TEST RANG CALLBACK ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.content_type}")
        
        if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            data = request.form.to_dict()
        else:
            data = request.get_json() or {}
        
        logger.info(f"Test callback data: {data}")
        
        return jsonify({
            'status': 'success',
            'message': 'Test callback received',
            'data': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error in test callback: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500