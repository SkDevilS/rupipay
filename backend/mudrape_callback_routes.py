from flask import Blueprint, request, jsonify
from database import get_db_connection
from timezone_utils import parse_mudrape_timestamp
from datetime import datetime
import json
import requests

mudrape_callback_bp = Blueprint('mudrape_callback', __name__, url_prefix='/api/callback')

@mudrape_callback_bp.route('/mudrape/payout', methods=['POST'])
def mudrape_payout_callback():
    """
    Webhook endpoint for Mudrape payout status updates
    Mudrape will call this when payout status changes
    """
    try:
        # Get callback data from Mudrape
        callback_data = request.json
        
        print("=" * 80)
        print("Mudrape Payout Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Extract data from callback - check multiple possible field names
        client_txn_id = (callback_data.get('clientTxnId') or 
                        callback_data.get('apiTxnId') or
                        callback_data.get('data', {}).get('clientTxnId') or
                        callback_data.get('data', {}).get('clientTransactionId'))
        
        status_code = callback_data.get('statusCode') or callback_data.get('statuscode')
        payout_status = callback_data.get('payoutStatus')
        
        # Extract UTR from multiple possible locations
        utr = (callback_data.get('utr') or 
               callback_data.get('uniqueId') or
               callback_data.get('data', {}).get('txnId') or
               callback_data.get('data', {}).get('bankRefNo'))
        
        # Extract bank reference number
        bank_ref_num = callback_data.get('data', {}).get('bank_ref_num') or callback_data.get('data', {}).get('bankRefNo')
        
        # Extract Mudrape transaction ID
        mudrape_txn_id = (callback_data.get('data', {}).get('txnId') or
                         callback_data.get('transactionId') or
                         callback_data.get('apiTxnId'))
        
        # Extract completion timestamp
        processed_at = None
        if callback_data.get('data'):
            processed_at = (callback_data['data'].get('processedAt') or 
                          callback_data['data'].get('transactionDate'))
        
        if not client_txn_id:
            print("ERROR: No clientTxnId in callback")
            return jsonify({'success': False, 'message': 'Missing clientTxnId'}), 400
        
        print(f"Client TXN ID: {client_txn_id}")
        print(f"Status Code: {status_code}")
        print(f"Payout Status: {payout_status}")
        print(f"UTR: {utr}")
        print(f"Bank Ref Num: {bank_ref_num}")
        print(f"Mudrape TXN ID: {mudrape_txn_id}")
        print(f"Processed At: {processed_at}")
        
        # Map Mudrape status to our status
        # Database ENUM: INITIATED, QUEUED, INPROCESS, SUCCESS, FAILED, REVERSED
        if status_code == 10000 or (payout_status and payout_status.upper() == 'SUCCESS'):
            status = 'SUCCESS'
        elif status_code == 10003 or (payout_status and payout_status.upper() == 'FAILED'):
            status = 'FAILED'
        elif payout_status and payout_status.upper() == 'PENDING':
            status = 'INITIATED'
        else:
            status = 'INITIATED'
        
        print(f"Mapped Status: {status}")
        
        # Convert processed_at to IST if available
        completed_at = None
        if processed_at and status in ['SUCCESS', 'FAILED']:
            completed_at = parse_mudrape_timestamp(processed_at)
            if completed_at:
                print(f"Completed At (IST): {completed_at}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by reference_id (which is the client_txn_id)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, reference_id
                    FROM payout_transactions
                    WHERE reference_id = %s
                """, (client_txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for reference_id: {client_txn_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # NEW FLOW: Refund wallet when status is FAILED (wallet was already deducted on initiation)
                if status == 'FAILED' and txn['merchant_id']:
                    # Check if wallet was already refunded to prevent duplicate refunds
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
                        
                        # Get transaction details for wallet refund
                        cursor.execute("""
                            SELECT amount, net_amount, charge_amount FROM payout_transactions
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        payout_details = cursor.fetchone()
                        
                        # Refund the total deduction (amount + charges)
                        total_refund = float(payout_details['amount'])
                        
                        print(f"Refunding to settled wallet - Amount: ₹{total_refund:.2f} (Net: ₹{payout_details['net_amount']:.2f} + Charges: ₹{payout_details['charge_amount']:.2f})")
                        
                        # Credit merchant settled wallet (refund)
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
                            # Log the error but don't fail the callback
                            print(f"⚠️  WARNING: Payout marked as FAILED but wallet refund failed - manual intervention needed")
                
                # For SUCCESS status, no wallet action needed (already deducted on initiation)
                if status == 'SUCCESS' and txn['merchant_id']:
                    print(f"✅ Payout SUCCESS - Wallet was already deducted on initiation, no action needed")
                
                # Prepare UTR value - use bank_ref_num if available, otherwise utr
                final_utr = bank_ref_num if bank_ref_num else utr
                
                # Update transaction with callback data
                if status in ['SUCCESS', 'FAILED']:
                    if completed_at:
                        # Use timestamp from Mudrape
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, pg_txn_id = %s, completed_at = %s, updated_at = NOW()
                            WHERE reference_id = %s
                        """, (status, final_utr, mudrape_txn_id, completed_at, client_txn_id))
                        print(f"✓ Updated with completed_at from Mudrape: {completed_at}")
                    else:
                        # Fallback to NOW() if no timestamp
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (status, final_utr, mudrape_txn_id, client_txn_id))
                        print(f"✓ Updated with completed_at = NOW()")
                else:
                    # Status is still pending/initiated
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE reference_id = %s
                    """, (status, final_utr, mudrape_txn_id, client_txn_id))
                    print(f"✓ Updated status to {status}")
                
                conn.commit()
                
                # Verify the update
                cursor.execute("""
                    SELECT status, utr, pg_txn_id, completed_at
                    FROM payout_transactions
                    WHERE reference_id = %s
                """, (client_txn_id,))
                
                updated_txn = cursor.fetchone()
                print(f"Verification - Status: {updated_txn['status']}, UTR: {updated_txn['utr']}, PG_TXN_ID: {updated_txn['pg_txn_id']}, Completed: {updated_txn['completed_at']}")
                
                print("=" * 80)
                print("Callback processed successfully")
                print("=" * 80)
                
                # Forward callback to merchant if configured
                try:
                    cursor.execute("""
                        SELECT callback_url FROM merchant_callbacks
                        WHERE merchant_id = %s AND is_active = TRUE
                    """, (txn['merchant_id'],))
                    
                    merchant_callback = cursor.fetchone()
                    
                    if merchant_callback and merchant_callback['callback_url']:
                        import requests
                        
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'reference_id': client_txn_id,
                            'status': status,
                            'utr': final_utr,
                            'pg_txn_id': mudrape_txn_id,
                            'pg_partner': 'Mudrape',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(f"Forwarding callback to merchant: {merchant_callback['callback_url']}")
                        print(f"Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                        
                        try:
                            callback_response = requests.post(
                                merchant_callback['callback_url'],
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
                                merchant_callback['callback_url'],
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
                                merchant_callback['callback_url'],
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
                
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully',
                    'txn_id': txn['txn_id'],
                    'status': status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"ERROR in callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@mudrape_callback_bp.route('/mudrape/payin', methods=['POST'])
def mudrape_payin_callback():
    """
    Webhook endpoint for Mudrape payin status updates
    Mudrape will call this when payin status changes
    """
    try:
        print("=" * 80)
        print("Mudrape Payin Callback Received")
        print("=" * 80)
        
        # Log request details
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        # Get callback data - support both JSON and form-data
        callback_data = None
        
        if request.is_json:
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
        
        # Extract data from callback - Support both Mudrape and Vega formats
        # Mudrape format: {"utr": "", "amount": , "ref_id": "", "source": "Mudrape", 
        #                  "status": "SUCCESS", "txn_id": "", "payeeVpa": "", "timestamp": ""}
        # Vega format: {"referenceId": "", "orderId": "", "status": "SUCCESS", "amount": 1, 
        #               "message": "Payment successful", "timestamp": "2026-03-10T09:25:44.418Z"}
        
        # Check if this is Vega format (has referenceId and orderId)
        is_vega_format = 'referenceId' in callback_data and 'orderId' in callback_data
        
        if is_vega_format:
            print("🔍 VEGA CALLBACK FORMAT DETECTED")
            # Vega callback format mapping
            ref_id = callback_data.get('referenceId') or callback_data.get('orderId')
            txn_id = callback_data.get('orderId', '')
            status = callback_data.get('status')
            utr = ''  # Vega doesn't provide UTR in callback
            amount = callback_data.get('amount')
            source = 'Vega'
            payee_vpa = ''
            timestamp = callback_data.get('timestamp', '')
            message = callback_data.get('message', '')
            
            print(f"Vega Callback - Reference ID: {ref_id}, Order ID: {txn_id}, Message: {message}")
        else:
            print("🔍 MUDRAPE CALLBACK FORMAT DETECTED")
            # Mudrape callback format mapping
            ref_id = (callback_data.get('ref_id') or 
                      callback_data.get('refId') or 
                      callback_data.get('RefID'))
            txn_id = (callback_data.get('txn_id') or 
                      callback_data.get('txnId'))
            status = callback_data.get('status')
            utr = (callback_data.get('utr') or 
                   callback_data.get('UTR') or
                   callback_data.get('bankRefNo') or
                   callback_data.get('bank_ref_no'))
            amount = callback_data.get('amount')
            source = callback_data.get('source', 'Mudrape')
            payee_vpa = callback_data.get('payeeVpa', '')
            timestamp = callback_data.get('timestamp', '')
        
        if not ref_id:
            if is_vega_format:
                print("ERROR: No referenceId/orderId in Vega callback")
                return jsonify({'success': False, 'message': 'Missing referenceId/orderId in Vega callback'}), 400
            else:
                print("ERROR: No ref_id/refId in Mudrape callback")
                return jsonify({'success': False, 'message': 'Missing ref_id/refId in Mudrape callback'}), 400
        
        print(f"Callback Format: {'VEGA' if is_vega_format else 'MUDRAPE'}")
        print(f"Ref ID: {ref_id}")
        print(f"TXN ID: {txn_id}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        print(f"Source: {source}")
        if is_vega_format:
            print(f"Message: {callback_data.get('message', '')}")
        else:
            print(f"Payee VPA: {payee_vpa}")
        print(f"Timestamp: {timestamp}")
        
        # Map status
        if status and status.upper() == 'SUCCESS':
            mapped_status = 'SUCCESS'
        elif status and status.upper() == 'FAILED':
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
                # Find transaction by order_id (which is the ref_id)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount as txn_amount, pg_partner
                    FROM payin_transactions
                    WHERE order_id = %s
                """, (ref_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for order_id: {ref_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                # Detect if this is a Vega transaction
                is_vega_transaction = txn.get('pg_partner') == 'Vega'
                pg_partner_name = txn.get('pg_partner', 'Mudrape')
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}, PG Partner: {pg_partner_name}")
                
                if is_vega_transaction:
                    print("🔍 VEGA TRANSACTION DETECTED - Processing via Mudrape callback system")
                    print(f"   Vega is using Mudrape's callback URL as configured")
                
                # If UTR is missing in callback but status is SUCCESS, fetch it from Mudrape
                # Note: Vega doesn't provide UTR in callback, so skip UTR fetching for Vega
                if mapped_status == 'SUCCESS' and not utr and not is_vega_format:
                    print("⚠ UTR missing in Mudrape callback, fetching from Mudrape status API...")
                    from mudrape_service import MudrapeService
                    mudrape_service = MudrapeService()
                    status_result = mudrape_service.check_payment_status(ref_id)
                    
                    if status_result.get('success'):
                        utr = status_result.get('utr')
                        if not txn_id:
                            txn_id = status_result.get('txnId')
                        print(f"✓ Fetched UTR from status API: {utr}")
                        print(f"✓ Fetched TXN ID from status API: {txn_id}")
                    else:
                        print(f"✗ Failed to fetch UTR from status API: {status_result.get('message')}")
                elif is_vega_format and mapped_status == 'SUCCESS':
                    print("ℹ Vega callback - UTR not provided in callback (normal for Vega)")
                
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
                        print(f"  This is a duplicate callback from Mudrape")
                        
                        # Just update transaction status and UTR if needed
                        if txn['status'] != 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE order_id = %s
                            """, (mapped_status, utr, txn_id, ref_id))
                            conn.commit()
                            print(f"✓ Updated transaction status to SUCCESS")
                        elif utr and utr != txn.get('bank_ref_no'):
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE order_id = %s
                            """, (utr, txn_id, ref_id))
                            conn.commit()
                            print(f"✓ Updated UTR: {utr}")
                    else:
                        # First time processing SUCCESS - credit unsettled wallet
                        print(f"Processing SUCCESS callback - crediting unsettled wallet")
                        
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, pg_txn_id = %s, bank_ref_no = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE order_id = %s
                        """, (mapped_status, txn_id, utr, ref_id))
                        
                        # Get net amount and charge amount
                        cursor.execute("""
                            SELECT net_amount, charge_amount FROM payin_transactions WHERE order_id = %s
                        """, (ref_id,))
                        payin_data = cursor.fetchone()
                        net_amount = float(payin_data['net_amount']) if payin_data else float(txn['txn_amount'])
                        charge_amount = float(payin_data['charge_amount']) if payin_data else 0.00
                        
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
                        
                        # Use appropriate description based on PG partner
                        wallet_description = f"{pg_partner_name} Payin credited to unsettled wallet - {ref_id}"
                        
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
                            wallet_description,
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Merchant unsettled wallet credited: {net_amount} ({pg_partner_name})")
                        
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
                        admin_wallet_description = f"{pg_partner_name} Payin charge - {ref_id}"
                        
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
                            admin_wallet_description,
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Admin unsettled wallet credited: {charge_amount} ({pg_partner_name})")
                        
                        conn.commit()
                else:
                    # FAILED or other status - just update transaction
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, bank_ref_no = %s, updated_at = NOW()
                        WHERE order_id = %s
                    """, (mapped_status, txn_id, utr, ref_id))
                    
                    conn.commit()
                
                print("=" * 80)
                print(f"{pg_partner_name} Payin callback processed successfully")
                print("=" * 80)
                
                # Forward callback to merchant if configured
                print("=" * 80)
                print(f"MERCHANT CALLBACK FORWARDING - {pg_partner_name}")
                print("=" * 80)
                try:
                    # First, get the callback URL from the transaction itself (sent in payload)
                    cursor.execute("""
                        SELECT callback_url FROM payin_transactions
                        WHERE order_id = %s
                    """, (ref_id,))
                    
                    txn_callback = cursor.fetchone()
                    callback_url = None
                    
                    if txn_callback and txn_callback.get('callback_url'):
                        callback_url = txn_callback['callback_url'].strip()
                        if not callback_url:  # Empty string after strip
                            callback_url = None
                    
                    print(f"Step 1: Transaction callback_url from DB: {callback_url if callback_url else 'NOT SET'}")
                    
                    # If no callback URL in transaction, check merchant_callbacks table
                    if not callback_url:
                        print(f"Step 2: Checking merchant_callbacks table for merchant: {txn['merchant_id']}")
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        
                        merchant_callback = cursor.fetchone()
                        if merchant_callback and merchant_callback.get('payin_callback_url'):
                            callback_url = merchant_callback['payin_callback_url'].strip()
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
                            """, (txn['merchant_id'], txn['txn_id'], '%"status": "SUCCESS"%'))
                            
                            success_callback_sent = cursor.fetchone()['count'] > 0
                            
                            if success_callback_sent:
                                print(f"⚠ SUCCESS callback already sent to merchant - skipping duplicate")
                                print(f"  This is a duplicate callback from Mudrape")
                                print("=" * 80)
                                
                                return jsonify({
                                    'success': True,
                                    'message': 'Callback processed (duplicate prevented)',
                                    'txn_id': txn['txn_id'],
                                    'status': mapped_status
                                }), 200
                        import requests
                        
                        # Prepare callback payload for merchant (matching standard format)
                        # Include PG partner information for merchant to identify source
                        merchant_callback_data = {
                            'utr': utr or '',
                            'amount': float(txn['txn_amount']),
                            'ref_id': ref_id,
                            'source': pg_partner_name,  # Use actual PG partner name
                            'status': mapped_status,
                            'txn_id': txn['txn_id'],  # Our internal txn_id
                            'pg_txn_id': txn_id or '',  # PG's txn_id
                            'pg_partner': pg_partner_name,  # Explicitly include PG partner
                            'payeeVpa': payee_vpa,
                            'timestamp': timestamp or datetime.now().isoformat(),
                            'order_id': ref_id  # Keep for backward compatibility
                        }
                        
                        print(f"Forwarding {pg_partner_name} callback to merchant: {callback_url}")
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
                                txn['merchant_id'],
                                txn['txn_id'],
                                callback_url,
                                json.dumps(merchant_callback_data),
                                callback_response.status_code,
                                callback_response.text[:1000]  # Limit response data
                            ))
                            conn.commit()
                            
                            print(f"✓ {pg_partner_name} merchant callback sent successfully and logged")
                            
                        except requests.exceptions.RequestException as e:
                            print(f"ERROR: Failed to send {pg_partner_name} merchant callback: {e}")
                            
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
