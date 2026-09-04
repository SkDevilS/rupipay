"""
RMS_Coco Callback Routes
Handles webhook callbacks from RMS_Coco payment gateway
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
import json

rmscoco_callback_bp = Blueprint('rmscoco_callback', __name__, url_prefix='/api/callback')

@rmscoco_callback_bp.route('/rmscoco/payin', methods=['POST', 'GET'])
def rmscoco_payin_callback():
    """
    Webhook endpoint for RMS_Coco payin status updates
    RMS_Coco will call this when payin status changes

    Expected callback format (as query parameters):
    https://www.yourdomain.com/callback?payid=1234&client_id=2121&operator_ref=1234567&status=success/failure

    Parameters:
    - payid: RMS_Coco payment ID
    - client_id: unique identifier of the client (our order_id)
    - operator_ref: UTR/operator reference number
    - status: "success" or "failure"
    """
    try:
        print("=" * 80)
        print("RMS_Coco Payin Callback Received")
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

        # Extract data from callback (RMS_Coco actual format)
        payid = callback_data.get('payid', '')                    # RMS_Coco payment ID (optional)
        order_id_from_rmscoco = callback_data.get('order_id', '')  # RMS_Coco's order ID (e.g., 378112)
        client_id = callback_data.get('client_id', '')            # Our order_id
        operator_ref = callback_data.get('operator_ref', '')      # UTR
        utr = callback_data.get('utr', '')                        # Alternative UTR field
        status = callback_data.get('status', '')                  # "credit" or "debit" or "success"/"failure"

        # Use whichever UTR field is populated
        if not operator_ref and utr:
            operator_ref = utr

        # Use order_id from RMS_Coco as payid if payid is not provided
        if not payid and order_id_from_rmscoco:
            payid = order_id_from_rmscoco

        if not client_id:
            print("ERROR: No client_id in callback")
            return jsonify({'success': False, 'message': 'Missing client_id'}), 400

        print(f"Pay ID: {payid}")
        print(f"RMS_Coco Order ID: {order_id_from_rmscoco}")
        print(f"Client ID (Our Order ID): {client_id}")
        print(f"Operator Ref (UTR): {operator_ref}")
        print(f"Status: {status}")

        # Map RMS_Coco status to our status
        # RMS_Coco sends: "credit" for success, "debit" for failure
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
                    WHERE order_id = %s AND pg_partner = 'RMS_COCO'
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
                        print(f"  This is a duplicate callback from RMS_Coco")

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

                        conn.commit()  # commit transaction status update first

                        net_amount = float(txn['net_amount'])
                        charge_amount = float(txn['charge_amount'])

                        # Use wallet_service to credit merchant unsettled wallet safely
                        from wallet_service import wallet_service

                        merchant_wallet_result = wallet_service.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=net_amount,
                            description=f"RMS_Coco Payin credited - {client_id}",
                            reference_id=txn['txn_id']
                        )

                        if merchant_wallet_result.get('success'):
                            print(f"✓ Merchant unsettled wallet credited: {net_amount}")
                        else:
                            print(f"✗ Failed to credit merchant unsettled wallet: {merchant_wallet_result.get('message')}")

                        # Use wallet_service to credit admin unsettled wallet safely
                        # (avoids FK constraint error if admin_wallet row doesn't exist)
                        admin_wallet_result = wallet_service.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=charge_amount,
                            description=f"RMS_Coco Payin charge - {client_id}",
                            reference_id=txn['txn_id']
                        )

                        if admin_wallet_result.get('success'):
                            print(f"✓ Admin unsettled wallet credited: {charge_amount}")
                        else:
                            print(f"✗ Failed to credit admin unsettled wallet: {admin_wallet_result.get('message')}")

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
                print(f"MERCHANT CALLBACK FORWARDING - RMS_Coco")
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
                        if 'api.rupipay.shop/api/callback/rmscoco' in callback_url or \
                           'admin.rupipay.shop/api/callback/rmscoco' in callback_url:
                            print(f"⚠ Skipping callback forward - merchant callback URL is our own callback endpoint")
                            print(f"  Merchant callback URL: {callback_url}")
                        else:
                            import requests

                            # Prepare callback payload for merchant (matching standard format)
                            merchant_callback_data = {
                                'txn_id': txn['txn_id'],
                                'order_id': client_id,
                                'status': mapped_status,
                                'amount': str(txn['amount']),
                                'net_amount': str(txn['net_amount']),
                                'charge_amount': str(txn['charge_amount']),
                                'utr': operator_ref or '',
                                'pg_txn_id': payid or order_id_from_rmscoco or '',
                                'payment_mode': 'UPI',
                                'pg_partner': 'RMS_COCO',
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
