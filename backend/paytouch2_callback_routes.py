"""
PayTouch2 Callback Routes
Handles webhook callbacks from PayTouch2 for payout status updates
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from datetime import datetime
import json

paytouch2_callback_bp = Blueprint('paytouch2_callback', __name__, url_prefix='/api/callback')

@paytouch2_callback_bp.route('/paytouch2/payout', methods=['POST'])
def paytouch2_unified_callback():
    """
    Unified webhook endpoint for PayTouch2 payout and PayTouchPayin callbacks
    Handles both payout status updates and payin status updates
    """
    try:
        # Get callback data
        callback_data = request.json or request.form.to_dict()
        
        print("=" * 80)
        print("PayTouch2/PayTouchPayin Unified Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Detect callback type based on data structure
        # Priority: Check for payout-specific fields first
        is_payout_callback = (
            'transaction_id' in callback_data or
            'external_ref' in callback_data or
            'payid' in callback_data
        )
        
        # Only check for payin if it's not a payout
        is_payin_callback = (
            not is_payout_callback and (
                'txnid' in callback_data or 
                'apitxnid' in callback_data or
                'product' in callback_data
            )
        )
        
        if is_payin_callback:
            print("🔍 Detected: PayTouchPayin (Payin) Callback")
            return handle_paytouchpayin_callback(callback_data)
        else:
            print("🔍 Detected: PayTouch2 (Payout) Callback")
            return handle_paytouch2_payout_callback(callback_data)
            
    except Exception as e:
        print(f"ERROR in unified callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


def handle_paytouchpayin_callback(callback_data):
    """
    Handle PayTouchPayin (Payin) callback
    """
    try:
        print("📥 Processing PayTouchPayin Callback")
        
        # Extract PayTouchPayin callback fields
        status = callback_data.get('status', '').lower()
        txnid = callback_data.get('txnid')
        apitxnid = callback_data.get('apitxnid')
        amount = callback_data.get('amount')
        charge = callback_data.get('charge')
        utr = callback_data.get('utr')
        remark = callback_data.get('remark', '')
        status_text = callback_data.get('status_text', '')
        
        if not txnid:
            print(f"❌ Missing txnid in payin callback")
            return jsonify({'success': False, 'error': 'Missing txnid'}), 400
        
        # Find payin transaction in database
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT txn_id, merchant_id, amount, status, order_id
                    FROM payin_transactions
                    WHERE txn_id = %s AND pg_partner = 'paytouchpayin'
                """, (txnid,))
                
                transaction = cursor.fetchone()
                
                if not transaction:
                    print(f"❌ Payin transaction not found: {txnid}")
                    return jsonify({'success': False, 'error': 'Transaction not found'}), 404
                
                merchant_id = transaction['merchant_id']
                current_status = transaction['status']
                
                print(f"✓ Payin transaction found: {txnid}")
                print(f"  Merchant: {merchant_id}")
                print(f"  Current Status: {current_status}")
                print(f"  Callback Status: {status}")
                
                # Prevent duplicate processing
                if current_status in ['SUCCESS', 'FAILED']:
                    print(f"⚠️ Payin transaction already processed with status: {current_status}")
                    print(f"   This is a duplicate callback - will still forward to merchant")
                    
                    # Still forward callback to merchant even if duplicate
                    # (merchant needs to know about the payment)
                    new_status = current_status  # Keep existing status
                    
                    # Skip wallet crediting and status update, but continue to callback forwarding
                    skip_wallet_and_update = True
                else:
                    skip_wallet_and_update = False
                    
                    # Map payin status
                    if status == 'success':
                        new_status = 'SUCCESS'
                    elif status == 'failed':
                        new_status = 'FAILED'
                    else:
                        new_status = 'PENDING'
                
                # Update payin transaction (skip if already processed)
                if not skip_wallet_and_update:
                    if new_status in ['SUCCESS', 'FAILED']:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, bank_ref_no = %s, pg_txn_id = %s, 
                                error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, utr, apitxnid, remark if new_status == 'FAILED' else None, txnid))
                    else:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, apitxnid, txnid))
                    
                    conn.commit()
                    
                    print(f"✅ Payin transaction updated: {txnid} -> {new_status}")
                else:
                    print(f"⏭️  Skipping status update (already processed)")
                
                print("=" * 80)
                print("STARTING MERCHANT CALLBACK FORWARDING")
                print("=" * 80)
                
                # Credit unsettled wallet if success (skip if already processed)
                if new_status == 'SUCCESS' and not skip_wallet_and_update:
                    # Get transaction details
                    cursor.execute("""
                        SELECT amount, charge_amount, net_amount
                        FROM payin_transactions
                        WHERE txn_id = %s
                    """, (txnid,))
                    
                    txn_details = cursor.fetchone()
                    
                    if txn_details:
                        net_amount = float(txn_details['net_amount'])
                        charge_amount = float(txn_details['charge_amount'])
                        
                        # Check if wallet already credited (idempotency)
                        try:
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                            """, (txnid,))
                            
                            wallet_already_credited = cursor.fetchone()['count'] > 0
                        except Exception as e:
                            # Table might not exist, skip idempotency check
                            print(f"⚠️ Could not check wallet credit history: {e}")
                            wallet_already_credited = False
                        
                        if not wallet_already_credited:
                            # Credit merchant unsettled wallet with net amount (direct SQL like mudrape)
                            try:
                                # Get current unsettled balance
                                cursor.execute("""
                                    SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                                """, (merchant_id,))
                                wallet_result = cursor.fetchone()
                                
                                if wallet_result:
                                    unsettled_before = float(wallet_result['unsettled_balance'])
                                    unsettled_after = unsettled_before + net_amount
                                    
                                    cursor.execute("""
                                        UPDATE merchant_wallet
                                        SET unsettled_balance = %s, last_updated = NOW()
                                        WHERE merchant_id = %s
                                    """, (unsettled_after, merchant_id))
                                else:
                                    # Create wallet if doesn't exist
                                    cursor.execute("""
                                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                                        VALUES (%s, 0.00, 0.00, %s)
                                    """, (merchant_id, net_amount))
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
                                    merchant_id, 
                                    wallet_txn_id, 
                                    net_amount,
                                    unsettled_before,
                                    unsettled_after,
                                    f"Paytouchpayin Payin credited to unsettled wallet - {txnid}",
                                    txnid
                                ))
                                
                                print(f"✓ Merchant unsettled wallet credited: ₹{net_amount}")
                                
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
                                    f"Paytouchpayin Payin charge - {txnid}",
                                    txnid
                                ))
                                
                                print(f"✓ Admin unsettled wallet credited: ₹{charge_amount}")
                                
                                conn.commit()
                                print(f"💰 Credited unsettled wallet: {merchant_id} + ₹{net_amount}")
                                
                            except Exception as wallet_error:
                                print(f"❌ Error crediting wallet: {wallet_error}")
                                # Continue to callback forwarding even if wallet credit fails
                        else:
                            print(f"⚠️ Wallet already credited for this transaction - skipping")
                
                # Forward callback to merchant
                cursor.execute("""
                    SELECT callback_url FROM payin_transactions
                    WHERE txn_id = %s
                """, (txnid,))
                
                txn_callback = cursor.fetchone()
                callback_url = None
                
                if txn_callback and txn_callback.get('callback_url'):
                    callback_url = txn_callback['callback_url'].strip()
                    if not callback_url:  # Empty string after strip
                        callback_url = None
                
                print(f"Step 1: Transaction callback_url from DB: {callback_url if callback_url else 'NOT SET'}")
                
                # If no callback URL in transaction, check merchant_callbacks table
                if not callback_url:
                    print(f"Step 2: Checking merchant_callbacks table for merchant: {merchant_id}")
                    cursor.execute("""
                        SELECT payin_callback_url FROM merchant_callbacks
                        WHERE merchant_id = %s
                    """, (merchant_id,))
                    
                    merchant_callback = cursor.fetchone()
                    if merchant_callback and merchant_callback.get('payin_callback_url'):
                        callback_url = merchant_callback['payin_callback_url'].strip()
                        if not callback_url:  # Empty string after strip
                            callback_url = None
                    
                    print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
                
                if callback_url:
                    # DUPLICATE PREVENTION: Check if we already sent a SUCCESS callback
                    if new_status == 'SUCCESS':
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM callback_logs
                            WHERE merchant_id = %s 
                            AND txn_id = %s 
                            AND response_code BETWEEN 200 AND 299
                            AND request_data LIKE %s
                        """, (merchant_id, txnid, '%"status": "SUCCESS"%'))
                        
                        success_callback_sent = cursor.fetchone()['count'] > 0
                        
                        if success_callback_sent:
                            print(f"⚠ SUCCESS callback already sent to merchant - skipping duplicate")
                            
                            return jsonify({
                                'success': True,
                                'message': 'Callback processed (duplicate prevented)',
                                'txn_id': txnid,
                                'status': new_status
                            }), 200
                    
                    import requests
                    
                    merchant_callback_data = {
                        'txn_id': txnid,
                        'order_id': transaction.get('order_id', txnid),
                        'amount': float(amount) if amount else 0,
                        'status': new_status,
                        'utr': utr or '',
                        'pg_txn_id': apitxnid or '',
                        'pg_partner': 'Paytouchpayin',
                        'source': 'Paytouchpayin',
                        'remark': remark,
                        'status_text': status_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    try:
                        print(f"🔄 Forwarding Paytouchpayin callback to merchant: {callback_url}")
                        print(f"📦 Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                        
                        callback_response = requests.post(
                            callback_url,
                            json=merchant_callback_data,
                            headers={'Content-Type': 'application/json'},
                            timeout=10
                        )
                        
                        print(f"✓ Merchant callback response: {callback_response.status_code}")
                        print(f"✓ Merchant callback response body: {callback_response.text[:200]}")
                        
                        # Log callback attempt
                        cursor.execute("""
                            INSERT INTO callback_logs 
                            (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            merchant_id, txnid,
                            callback_url,
                            json.dumps(merchant_callback_data),
                            callback_response.status_code,
                            callback_response.text[:1000]
                        ))
                        conn.commit()
                        
                        print(f"✅ Merchant callback forwarded successfully")
                        
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Error forwarding payin callback: {e}")
                        
                        # Log failed callback
                        cursor.execute("""
                            INSERT INTO callback_logs 
                            (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            merchant_id, txnid,
                            callback_url,
                            json.dumps(merchant_callback_data),
                            0, str(e)[:1000]
                        ))
                        conn.commit()
                else:
                    print(f"ℹ️ No callback URL configured for merchant {merchant_id}")
                    print(f"   - Transaction callback_url: NOT SET")
                    print(f"   - Merchant payin_callback_url: NOT SET")
                
                print("=" * 80)
                print("CALLBACK FORWARDING COMPLETED")
                print("=" * 80)
                
                return jsonify({
                    'success': True,
                    'message': 'Payin callback processed successfully',
                    'txn_id': txnid,
                    'status': new_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"ERROR in payin callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


def handle_paytouch2_payout_callback(callback_data):
    """
    Handle PayTouch2 (Payout) callback - original logic
    """
    try:
        print("📤 Processing PayTouch2 Payout Callback")
        
        # Extract data from callback
        transaction_id = callback_data.get('transaction_id') or callback_data.get('transactionId')
        external_ref = callback_data.get('external_ref') or callback_data.get('request_id')
        status = callback_data.get('status', 'PENDING')
        
        # Extract UTR - check multiple possible field names
        utr = (
            callback_data.get('utr_no') or  # PayTouch2 uses utr_no
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
        
        print(f"Transaction ID: {transaction_id}")
        print(f"External Ref: {external_ref}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        print(f"Message: {message}")
        
        # Map PayTouch2 status to our status
        status_map = {
            'SUCCESS': 'SUCCESS',
            'PENDING': 'QUEUED',
            'FAILED': 'FAILED',
            'PROCESSING': 'INPROCESS'
        }
        mapped_status = status_map.get(status.upper(), 'QUEUED')
        
        print(f"Mapped Status: {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by pg_txn_id or reference_id
                if transaction_id:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id
                        FROM payout_transactions
                        WHERE pg_txn_id = %s AND pg_partner = 'Paytouch2'
                    """, (transaction_id,))
                else:
                    # Try to find by reference_id extracted from external_ref
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id
                        FROM payout_transactions
                        WHERE reference_id = %s AND pg_partner = 'Paytouch2'
                    """, (external_ref,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for transaction_id: {transaction_id}, external_ref: {external_ref}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # NEW FLOW: Handle wallet refund for FAILED status (wallet was already deducted on initiation)
                if mapped_status == 'FAILED':
                    # Check if this is a merchant payout (has merchant_id) or admin personal payout (has admin_id)
                    if txn['merchant_id']:
                        # MERCHANT PAYOUT - Refund wallet
                        print(f"Merchant payout FAILED - checking wallet refund")
                        
                        # Check if wallet was already refunded
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
                            
                            # Refund the total deduction
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
                                print(f"⚠️  WARNING: Payout marked as FAILED but wallet refund failed - manual intervention needed")
                    
                    elif txn['admin_id']:
                        # ADMIN PERSONAL PAYOUT - No wallet refund needed
                        print(f"Admin personal payout FAILED - no wallet refund needed")
                    
                    else:
                        print(f"⚠️  WARNING: Transaction has neither merchant_id nor admin_id")
                
                # For SUCCESS status, no wallet action needed (already deducted on initiation)
                if mapped_status == 'SUCCESS':
                    if txn['merchant_id']:
                        print(f"✅ Merchant payout SUCCESS - Wallet was already deducted on initiation, no action needed")
                    elif txn['admin_id']:
                        print(f"✅ Admin personal payout SUCCESS - completed successfully")
                    else:
                        print(f"⚠️  WARNING: Transaction has neither merchant_id nor admin_id")
                
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
                
                # Verify the update
                cursor.execute("""
                    SELECT status, utr, pg_txn_id, completed_at
                    FROM payout_transactions
                    WHERE txn_id = %s
                """, (txn['txn_id'],))
                
                updated_txn = cursor.fetchone()
                print(f"Verification - Status: {updated_txn['status']}, UTR: {updated_txn['utr']}, PG_TXN_ID: {updated_txn['pg_txn_id']}, Completed: {updated_txn['completed_at']}")
                
                print("=" * 80)
                print("Payout callback processed successfully")
                print("=" * 80)
                
                # Forward callback to merchant if configured
                try:
                    if txn['merchant_id']:
                        # Check for transaction-specific callback URL first
                        cursor.execute("""
                            SELECT callback_url FROM payout_transactions
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        
                        txn_callback = cursor.fetchone()
                        callback_url = txn_callback.get('callback_url') if txn_callback else None
                        
                        # If no transaction-specific callback, check merchant-level callback
                        if not callback_url:
                            cursor.execute("""
                                SELECT payout_callback_url FROM merchant_callbacks
                                WHERE merchant_id = %s AND is_active = TRUE
                            """, (txn['merchant_id'],))
                            
                            merchant_callback = cursor.fetchone()
                            callback_url = merchant_callback.get('payout_callback_url') if merchant_callback else None
                        
                        if callback_url:
                            from callback_forwarder import forward_payout_callback
                            
                            # Prepare callback payload for merchant
                            merchant_callback_data = {
                                'txn_id': txn['txn_id'],
                                'reference_id': txn['reference_id'],
                                'status': mapped_status,
                                'utr': utr,
                                'pg_txn_id': transaction_id,
                                'pg_partner': 'Paytouch2',
                                'amount': amount,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Forward callback using utility function
                            forward_result = forward_payout_callback(
                                txn_id=txn['txn_id'],
                                merchant_id=txn['merchant_id'],
                                callback_url=callback_url,
                                callback_data=merchant_callback_data
                            )
                            
                            if forward_result['success']:
                                print(f"✅ Callback forwarded successfully")
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
        print(f"ERROR in payout callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
