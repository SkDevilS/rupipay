"""
RMS_HAMSTER Callback Routes
Handles webhook callbacks from RMS_HAMSTER payment gateway
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
import json

rmshamster_callback_bp = Blueprint('rmshamster_callback', __name__, url_prefix='/api/callback')

@rmshamster_callback_bp.route('/rmshamster/payin', methods=['POST', 'GET'])
def rmshamster_payin_callback():
    """
    Webhook endpoint for RMS_HAMSTER payin status updates
    RMS_HAMSTER will call this when payin status changes

    Expected callback format (as query parameters):
    https://www.yourdomain.com/callback?payid=1234&client_id=2121&operator_ref=1234567&status=success/failure

    Parameters:
    - payid: RMS_HAMSTER payment ID
    - client_id: unique identifier of the client (our order_id)
    - operator_ref: UTR/operator reference number
    - status: "success" or "failure"
    """
    try:
        print("=" * 80)
        print("RMS_HAMSTER Payin Callback Received")
        print("=" * 80)

        # Log request details
        print(f"Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Query String: {request.query_string.decode('utf-8')}")

        # Get callback data from query parameters (GET) or body (POST)
        callback_data = None

        if request.method == 'GET' or request.args:
            # Query parameters (most likely format based on sample)
            callback_data = request.args.to_dict()
            print("Received as Query Parameters (GET)")
        elif request.is_json:
            # JSON payload
            callback_data = request.json
            print("Received as JSON")
        elif request.form:
            # Form data
            callback_data = request.form.to_dict()
            print("Received as Form Data")
        elif request.data:
            # Raw data - try to parse as JSON
            try:
                callback_data = json.loads(request.data.decode('utf-8'))
                print("Received as Raw Data (parsed as JSON)")
            except:
                print(f"Raw Data (could not parse): {request.data}")
                return jsonify({'success': False, 'message': 'Invalid data format'}), 400
        else:
            print("ERROR: No data received")
            return jsonify({'success': False, 'message': 'No data received'}), 400

        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")

        # Extract data from callback (RMS_HAMSTER actual format)
        payid = callback_data.get('payid', '')                    # RMS_HAMSTER payment ID (optional)
        order_id_from_rmsjss = callback_data.get('order_id', '')  # RMS_HAMSTER's order ID (e.g., 378112)
        client_id = callback_data.get('client_id', '')            # Our order_id
        operator_ref = callback_data.get('operator_ref', '')      # UTR
        utr = callback_data.get('utr', '')                        # Alternative UTR field
        status = callback_data.get('status', '')                  # "credit" or "debit" or "success"/"failure"

        # Use whichever UTR field is populated
        if not operator_ref and utr:
            operator_ref = utr

        # Use order_id from RMS_HAMSTER as payid if payid is not provided
        if not payid and order_id_from_rmsjss:
            payid = order_id_from_rmsjss

        if not client_id:
            print("ERROR: No client_id in callback")
            return jsonify({'success': False, 'message': 'Missing client_id'}), 400

        print(f"Pay ID: {payid}")
        print(f"RMS_HAMSTER Order ID: {order_id_from_rmsjss}")
        print(f"Client ID (Our Order ID): {client_id}")
        print(f"Operator Ref (UTR): {operator_ref}")
        print(f"Status: {status}")

        # Map RMS_HAMSTER status to our status
        # RMS_HAMSTER sends: "credit" for success, "debit" for failure
        # Also support: "success" and "failure" for backward compatibility
        if status.lower() in ['success', 'credit']:
            mapped_status = 'SUCCESS'
        elif status.lower() in ['failure', 'debit']:
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
                # Find transaction by order_id (which is the client_id)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount, net_amount, charge_amount, callback_url
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'RMS_HAMSTER'
                """, (client_id,))

                txn = cursor.fetchone()

                if not txn:
                    print(f"ERROR: Transaction not found for order_id: {client_id}")
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
                        print(f"  This is a duplicate callback from RMS_HAMSTER")

                        # Just update transaction status and UTR if needed
                        if txn['status'] != 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE order_id = %s
                            """, (mapped_status, utr, payid, client_id))
                            conn.commit()
                            print(f"✓ Updated transaction status to SUCCESS")
                    else:
                        # First time processing SUCCESS - credit unsettled wallet
                        print(f"Processing SUCCESS callback - crediting unsettled wallet")

                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, pg_txn_id = %s, bank_ref_no = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE order_id = %s
                        """, (mapped_status, payid, utr, client_id))

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
                            f"RMS_HAMSTER Payin credited to unsettled wallet - {client_id}",
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
                            f"RMS_HAMSTER Payin charge - {client_id}",
                            txn['txn_id']
                        ))

                        print(f"✓ Admin unsettled wallet credited: {charge_amount}")

                        conn.commit()
                        print(f"✓ Transaction updated to SUCCESS and wallets credited")

                elif mapped_status == 'FAILED':
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE order_id = %s
                    """, (mapped_status, payid, client_id))
                    conn.commit()
                    print(f"✓ Transaction updated to FAILED")

                # Verify the update
                cursor.execute("""
                    SELECT status, bank_ref_no, pg_txn_id, completed_at
                    FROM payin_transactions
                    WHERE order_id = %s
                """, (client_id,))

                updated_txn = cursor.fetchone()
                print(f"Verification - Status: {updated_txn['status']}, UTR: {updated_txn['bank_ref_no']}, PG_TXN_ID: {updated_txn['pg_txn_id']}, Completed: {updated_txn['completed_at']}")

                print("=" * 80)
                print("Callback processed successfully")
                print("=" * 80)

                # Forward callback to merchant if configured
                print(f"\n{'='*80}")
                print(f"MERCHANT CALLBACK FORWARDING - RMS_HAMSTER")
                print(f"{'='*80}")
                
                try:
                    # Step 1: Get callback URL from payin_transactions (merchant sends this in payin request)
                    cursor.execute("""
                        SELECT callback_url
                        FROM payin_transactions
                        WHERE order_id = %s
                    """, (client_id,))

                    merchant_callback = cursor.fetchone()
                    callback_url = None

                    if merchant_callback and merchant_callback.get('callback_url'):
                        callback_url = merchant_callback['callback_url'].strip()
                        if not callback_url:
                            callback_url = None
                    
                    print(f"Step 1: Transaction callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    # Step 2: If no callback URL in transaction, check merchant_callbacks table as fallback
                    if not callback_url:
                        print(f"Step 2: Checking merchant_callbacks table")
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        
                        merchant_callback_fallback = cursor.fetchone()
                        if merchant_callback_fallback and merchant_callback_fallback.get('payin_callback_url'):
                            callback_url = merchant_callback_fallback['payin_callback_url'].strip()
                            if not callback_url:
                                callback_url = None
                        
                        print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    if callback_url:
                        # IMPORTANT: Don't forward to our own callback URL (prevent loop)
                        if 'api.moneyone.co.in/api/callback/rmshamster' in callback_url or \
                           'admin.moneyone.co.in/api/callback/rmshamster' in callback_url:
                            print(f"⚠ Skipping callback forward - merchant callback URL is our own callback endpoint")
                            print(f"  Merchant callback URL: {callback_url}")
                        else:
                            import requests

                            # Prepare callback payload for merchant (matching Oxymoney_Barringer format)
                            merchant_callback_data = {
                                'txn_id': txn['txn_id'],
                                'order_id': client_id,
                                'status': mapped_status,
                                'amount': str(txn['amount']),
                                'net_amount': str(txn['net_amount']),
                                'charge_amount': str(txn['charge_amount']),
                                'utr': operator_ref or '',
                                'pg_txn_id': payid or order_id_from_rmsjss or '',
                                'payment_mode': 'UPI',
                                'pg_partner': 'RMS_HAMSTER',
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
                                    callback_response.text[:1000]
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
                        print("No merchant callback URL configured")

                except Exception as e:
                    print(f"ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                
                print(f"{'='*80}\n")

                return jsonify({
                    'status': 'success',
                    'message': 'Callback received and processed successfully.'
                }), 200

        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR in callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'Failed to process callback data.'
        }), 500