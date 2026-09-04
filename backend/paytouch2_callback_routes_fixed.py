"""
PayTouch2 Callback Routes (Fixed to handle both PAYOUT and PAYIN)
Handles webhook callbacks from:
1. PayTouch2 - for PAYOUT status updates
2. PayTouchPayin - for PAYIN status updates (QR payments)
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
        "txnid": "4237534069070",
        "apitxnid": "DQR3281774329123961",
        "amount": 200.95,
        "charge": 2,
        "utr": "608373377074",
        "name": "vyapar.173506865983@hdfcbank",
        "mobile": "9123475501",
        "product": "dynamicqrpayin",
        "remark": "Dynamic QR Payin",
        "status_text": "success",
        "created_at": "2026-03-24 10:42:03",
        "updated_at": []
    }
    
    PayTouch2 PAYOUT Callback Format:
    {
        "transaction_id": "...",
        "external_ref": "...",
        "status": "SUCCESS",
        "utr_no": "...",
        "amount": 1000,
        "message": "..."
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
        print(f"Headers: {dict(request.headers)}")
        
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
    
    Callback format:
    {
        "status": "success" | "failed",
        "txnid": "TXN123...",
        "apitxnid": "DQR...",
        "amount": 200.95,
        "charge": 2,
        "utr": "608373377074",
        "name": "vyapar.173506865983@hdfcbank",
        "mobile": "9123475501",
        "product": "dynamicqrpayin",
        "remark": "Dynamic QR Payin",
        "status_text": "success",
        "created_at": "2026-03-24 10:42:03",
        "updated_at": []
    }
    """
    try:
        # Extract callback fields
        status = callback_data.get('status', '').lower()
        txnid = callback_data.get('txnid')
        apitxnid = callback_data.get('apitxnid')
        amount = callback_data.get('amount')
        charge = callback_data.get('charge')
        utr = callback_data.get('utr')
        remark = callback_data.get('remark', '')
        status_text = callback_data.get('status_text', '')
        
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
        print(f"  Remark: {remark}")
        
        # Find transaction in database (check both tables)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First try payin_transactions table (new structure)
        cursor.execute("""
            SELECT id, merchant_id, txn_id, order_id, amount, status, pg_partner
            FROM payin_transactions
            WHERE txn_id = %s AND pg_partner = 'paytouchpayin'
        """, (txnid,))
        
        transaction_row = cursor.fetchone()
        
        # If not found, try payin table (old structure)
        if not transaction_row:
            cursor.execute("""
                SELECT id, merchant_id, txn_id, order_id, amount, status, pg_partner
                FROM payin
                WHERE txn_id = %s AND pg_partner = 'paytouchpayin'
            """, (txnid,))
            transaction_row = cursor.fetchone()
            table_name = 'payin'
        else:
            table_name = 'payin_transactions'
        
        # Convert tuple to dict
        if transaction_row:
            transaction = {
                'id': transaction_row[0],
                'merchant_id': transaction_row[1],
                'txn_id': transaction_row[2],
                'order_id': transaction_row[3],
                'amount': transaction_row[4],
                'status': transaction_row[5],
                'pg_partner': transaction_row[6]
            }
        else:
            transaction = None
        
        if not transaction:
            print(f"❌ Transaction not found: {txnid}")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        merchant_id = transaction['merchant_id']
        current_status = transaction['status']
        
        print(f"✓ Transaction found in {table_name} table")
        print(f"  Merchant: {merchant_id}")
        print(f"  Current Status: {current_status}")
        print(f"  Callback Status: {status}")
        
        # Prevent duplicate processing
        if current_status in ['success', 'failed']:
            print(f"⚠️ Transaction already processed with status: {current_status}")
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        # Map status
        if status == 'success':
            new_status = 'success'
        elif status == 'failed':
            new_status = 'failed'
        else:
            new_status = 'pending'
        
        # Update transaction in the correct table
        cursor.execute(f"""
            UPDATE {table_name}
            SET status = %s, utr = %s, remark = %s, updated_at = NOW()
            WHERE txn_id = %s
        """, (new_status, utr, remark, txnid))
        
        conn.commit()
        
        print(f"✅ Transaction updated: {txnid} -> {new_status}")
        
        # Credit unsettled wallet if success
        if new_status == 'success':
            payin_amount = float(transaction['amount'])
            
            cursor.execute("""
                UPDATE merchants
                SET unsettled_wallet = unsettled_wallet + %s
                WHERE merchant_id = %s
            """, (payin_amount, merchant_id))
            
            conn.commit()
            
            print(f"💰 Credited unsettled wallet: {merchant_id} + ₹{payin_amount}")
            
            # Log transaction
            cursor.execute("""
                INSERT INTO transactions (
                    merchant_id, txn_type, amount, balance_after, 
                    reference_id, description, created_at
                )
                SELECT 
                    %s, 'payin_unsettled_credit', %s, unsettled_wallet,
                    %s, CONCAT('Payin credited (Unsettled) - ', %s), NOW()
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id, payin_amount, txnid, txnid, merchant_id))
            
            conn.commit()
        
        # Forward callback to merchant
        # For PAYIN, callback_url is in merchants table
        cursor.execute("""
            SELECT callback_url
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        merchant_row = cursor.fetchone()
        callback_url = merchant_row[0] if merchant_row else None
        
        if callback_url:
            
            try:
                print(f"🔄 Forwarding callback to merchant: {callback_url}")
                
                # Prepare merchant callback data
                merchant_callback = {
                    'txn_id': txnid,
                    'order_id': transaction.get('order_id', txnid),
                    'amount': amount,
                    'status': new_status,
                    'utr': utr,
                    'pg_txn_id': apitxnid,
                    'remark': remark,
                    'pg_partner': 'paytouchpayin'
                }
                
                print(f"📤 Merchant callback payload: {json.dumps(merchant_callback, indent=2)}")
                
                response = requests.post(
                    callback_url,
                    json=merchant_callback,
                    timeout=10
                )
                
                print(f"✓ Merchant callback response: {response.status_code}")
                print(f"  Response body: {response.text[:200]}")
                
                # Log callback
                try:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txnid,
                        callback_url,
                        json.dumps(merchant_callback),
                        response.status_code,
                        response.text[:1000]
                    ))
                    conn.commit()
                except Exception as log_error:
                    print(f"⚠️ Failed to log callback: {log_error}")
                
            except Exception as e:
                print(f"❌ Error forwarding callback: {str(e)}")
                
                # Log failed callback
                try:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txnid,
                        callback_url,
                        json.dumps(merchant_callback),
                        0,
                        str(e)[:1000]
                    ))
                    conn.commit()
                except Exception as log_error:
                    print(f"⚠️ Failed to log callback error: {log_error}")
        else:
            print(f"ℹ️ No callback URL configured for merchant {merchant_id}")
        
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
    (Original PayTouch2 payout logic)
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
                print(f"ERROR: Transaction not found for transaction_id: {transaction_id}, external_ref: {external_ref}")
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            # Convert to dict
            txn = {
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
            
            # CRITICAL: Handle wallet deduction for SUCCESS status
            if mapped_status == 'SUCCESS':
                if txn['merchant_id']:
                    print(f"Merchant payout SUCCESS - checking wallet deduction")
                    
                    # Check if wallet was already deducted
                    cursor.execute("""
                        SELECT txn_id FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'DEBIT'
                    """, (txn['txn_id'],))
                    
                    wallet_already_deducted = cursor.fetchone()
                    
                    if wallet_already_deducted:
                        print(f"⚠️ Wallet already deducted for this transaction - skipping")
                    else:
                        print(f"Status is SUCCESS - Debiting merchant settled wallet")
                        
                        total_deduction = float(txn['amount'])
                        
                        print(f"Deducting from settled wallet - Amount: ₹{total_deduction:.2f}")
                        
                        # Debit merchant settled wallet
                        from wallet_service import WalletService
                        wallet_svc = WalletService()
                        debit_result = wallet_svc.debit_merchant_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=total_deduction,
                            description=f"Payout: ₹{txn['net_amount']:.2f} + Charges: ₹{txn['charge_amount']:.2f}",
                            reference_id=txn['txn_id']
                        )
                        
                        if debit_result['success']:
                            print(f"✅ WALLET DEBITED - Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                        else:
                            print(f"✗ WALLET DEBIT FAILED: {debit_result['message']}")
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = 'FAILED', error_message = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (f"Wallet debit failed: {debit_result['message']}", txn['txn_id']))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            
                            return jsonify({
                                'success': False,
                                'message': f"Payout succeeded but wallet debit failed: {debit_result['message']}"
                            }), 500
                
                elif txn['admin_id']:
                    print(f"Admin personal payout SUCCESS - no wallet deduction needed")
                    print(f"✅ Admin personal payout completed successfully")
            
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
            
            # Forward callback to merchant if configured
            if txn['merchant_id']:
                cursor.execute("""
                    SELECT payout_callback_url FROM merchant_callbacks
                    WHERE merchant_id = %s AND is_active = TRUE
                """, (txn['merchant_id'],))
                
                merchant_callback_row = cursor.fetchone()
                
                if merchant_callback_row and merchant_callback_row[0]:
                    payout_callback_url = merchant_callback_row[0]
                    
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
                    
                    print(f"🔄 Forwarding callback to merchant: {payout_callback_url}")
                    
                    try:
                        callback_response = requests.post(
                            payout_callback_url,
                            json=merchant_callback_data,
                            headers={'Content-Type': 'application/json'},
                            timeout=10
                        )
                        
                        print(f"✓ Merchant callback response: {callback_response.status_code}")
                        
                        # Log callback attempt
                        try:
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                payout_callback_url,
                                json.dumps(merchant_callback_data),
                                callback_response.status_code,
                                callback_response.text[:1000]
                            ))
                            conn.commit()
                        except Exception as log_error:
                            print(f"⚠️ Failed to log callback: {log_error}")
                        
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Failed to send merchant callback: {e}")
                        
                        # Log failed callback attempt
                        try:
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                payout_callback_url,
                                json.dumps(merchant_callback_data),
                                0,
                                str(e)[:1000]
                            ))
                            conn.commit()
                        except Exception as log_error:
                            print(f"⚠️ Failed to log callback error: {log_error}")
            
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
