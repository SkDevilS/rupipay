"""
HDFC Paytouch_Barringer Callback Routes
Handles webhook callbacks from HDFC Paytouch_Barringer for payin status updates
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from datetime import datetime
import json

hdfcpaytouch_barringer_callback_bp = Blueprint('hdfcpaytouch_barringer_callback', __name__, url_prefix='/api/callback')

@hdfcpaytouch_barringer_callback_bp.route('/hdfcpaytouch/barringer', methods=['POST', 'GET'])
def hdfcpaytouch_barringer_payin_callback():
    """
    Webhook endpoint for HDFC Paytouch_Barringer payin callbacks
    Handles payment status updates
    
    Dedicated URL: https://api.moneyone.co.in/api/callback/hdfcpaytouch/barringer
    
    This endpoint is flexible and catches ALL parameters sent by HDFC:
    - Supports both POST (JSON/form-data) and GET (query params)
    - Extracts all possible field variations
    - Logs complete callback data for debugging
    """
    try:
        # Get callback data - support ALL methods
        if request.method == 'POST':
            # Try JSON first, then form data
            if request.is_json:
                callback_data = request.json or {}
            else:
                callback_data = request.form.to_dict() or {}
        else:
            # GET request - query parameters
            callback_data = request.args.to_dict() or {}
        
        # Also capture raw data for logging
        raw_data = request.get_data(as_text=True)
        
        print("=" * 80)
        print("HDFC Paytouch_Barringer Payin Callback Received")
        print("=" * 80)
        print(f"Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Raw Data: {raw_data}")
        print(f"Parsed Callback Data: {json.dumps(callback_data, indent=2)}")
        print(f"Query Params: {dict(request.args)}")
        print(f"Form Data: {dict(request.form)}")
        
        # Extract data from callback - try ALL possible field names
        # HDFC may send: apitxnid, request_id, order_id, orderid, etc.
        apitxnid = (
            callback_data.get('apitxnid') or 
            callback_data.get('request_id') or 
            callback_data.get('order_id') or 
            callback_data.get('orderid') or
            callback_data.get('merchant_order_id')
        )
        
        # HDFC may send: transaction_id, txn_id, gateway_txn_id, etc.
        transaction_id = (
            callback_data.get('transaction_id') or 
            callback_data.get('txn_id') or
            callback_data.get('gateway_txn_id') or
            callback_data.get('pg_txn_id') or
            callback_data.get('hdfc_txn_id')
        )
        
        # Status field variations
        status = (
            callback_data.get('status') or 
            callback_data.get('Status') or 
            callback_data.get('payment_status') or
            callback_data.get('txn_status') or
            'PENDING'
        ).upper()
        
        # Amount field variations
        amount = (
            callback_data.get('amount') or 
            callback_data.get('Amount') or
            callback_data.get('txn_amount') or
            callback_data.get('transaction_amount')
        )
        
        # UTR/Bank reference variations
        utr = (
            callback_data.get('utr') or 
            callback_data.get('UTR') or
            callback_data.get('bank_ref_no') or
            callback_data.get('bank_reference') or
            callback_data.get('rrn') or
            callback_data.get('reference_number') or
            callback_data.get('utr_number') or
            callback_data.get('bankRefNo')
        )
        
        # Message/remarks field variations
        message = (
            callback_data.get('message') or 
            callback_data.get('Message') or
            callback_data.get('remarks') or
            callback_data.get('description') or
            callback_data.get('error_message') or
            ''
        )
        
        # Payment mode variations
        payment_mode = (
            callback_data.get('payment_mode') or
            callback_data.get('paymentMode') or
            callback_data.get('mode') or
            'UPI'
        )
        
        print(f"\n📋 EXTRACTED FIELDS:")
        print(f"  API TXN ID (Order ID): {apitxnid}")
        print(f"  Transaction ID (Gateway): {transaction_id}")
        print(f"  Status: {status}")
        print(f"  Amount: {amount}")
        print(f"  UTR: {utr}")
        print(f"  Payment Mode: {payment_mode}")
        print(f"  Message: {message}")
        
        # Validate we have at least one identifier
        if not apitxnid and not transaction_id:
            print("❌ ERROR: No transaction identifier found in callback")
            print(f"Available fields: {list(callback_data.keys())}")
            return jsonify({
                'success': False, 
                'message': 'Missing transaction identifier',
                'received_fields': list(callback_data.keys())
            }), 400
        
        # Map HDFC status to our status
        status_map = {
            'SUCCESS': 'SUCCESS',
            'COMPLETED': 'SUCCESS',
            'PAID': 'SUCCESS',
            'PENDING': 'PENDING',
            'PROCESSING': 'PENDING',
            'INITIATED': 'PENDING',
            'FAILED': 'FAILED',
            'FAILURE': 'FAILED',
            'DECLINED': 'FAILED',
            'REJECTED': 'FAILED',
            'CANCELLED': 'FAILED',
            'EXPIRED': 'FAILED'
        }
        mapped_status = status_map.get(status, 'PENDING')
        
        print(f"✓ Mapped Status: {status} → {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("❌ ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction - try multiple methods
                txn = None
                
                # Method 1: Try by gateway transaction_id
                if transaction_id:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, order_id, net_amount, charge_amount
                        FROM payin_transactions
                        WHERE pg_txn_id = %s AND pg_partner = 'HDFCPaytouch_Barringer'
                    """, (transaction_id,))
                    txn = cursor.fetchone()
                    if txn:
                        print(f"✓ Found transaction by pg_txn_id: {transaction_id}")
                
                # Method 2: Try by order_id (apitxnid)
                if not txn and apitxnid:
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, order_id, net_amount, charge_amount
                        FROM payin_transactions
                        WHERE order_id = %s AND pg_partner = 'HDFCPaytouch_Barringer'
                        ORDER BY created_at DESC LIMIT 1
                    """, (apitxnid,))
                    txn = cursor.fetchone()
                    if txn:
                        print(f"✓ Found transaction by order_id: {apitxnid}")
                
                # Method 3: Try by txn_id pattern (if apitxnid looks like our txn_id)
                if not txn and apitxnid and apitxnid.startswith('HDPT_BAR_'):
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, order_id, net_amount, charge_amount
                        FROM payin_transactions
                        WHERE txn_id = %s AND pg_partner = 'HDFCPaytouch_Barringer'
                    """, (apitxnid,))
                    txn = cursor.fetchone()
                    if txn:
                        print(f"✓ Found transaction by txn_id: {apitxnid}")
                
                if not txn:
                    print(f"❌ ERROR: Transaction not found")
                    print(f"   Searched by transaction_id: {transaction_id}")
                    print(f"   Searched by order_id: {apitxnid}")
                    return jsonify({
                        'success': False, 
                        'message': 'Transaction not found',
                        'searched_transaction_id': transaction_id,
                        'searched_order_id': apitxnid
                    }), 404
                
                print(f"✓ Found Transaction: {txn['txn_id']}")
                print(f"  Current Status: {txn['status']}")
                print(f"  Merchant ID: {txn['merchant_id']}")
                print(f"  Order ID: {txn['order_id']}")
                
                # Handle SUCCESS status - credit wallets
                if mapped_status == 'SUCCESS':
                    print(f"\n💰 Payment SUCCESS - Processing wallet credits")
                    
                    # Check if wallet already credited (idempotency)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn['txn_id'],))
                    
                    wallet_already_credited = cursor.fetchone()['count'] > 0
                    
                    if wallet_already_credited:
                        print(f"⚠️  Wallet already credited for this transaction - skipping")
                    else:
                        # Credit merchant unsettled wallet with net amount (after charges)
                        from wallet_service import wallet_service as wallet_svc
                        wallet_result = wallet_svc.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=float(txn['net_amount']),
                            description=f"PayIn received (HDFC) - {txn['order_id']}",
                            reference_id=txn['txn_id']
                        )
                        
                        if wallet_result['success']:
                            print(f"✅ Merchant unsettled wallet credited: ₹{txn['net_amount']}")
                        else:
                            print(f"✗ Failed to credit merchant unsettled wallet: {wallet_result.get('message')}")
                        
                        # Credit admin unsettled wallet with charge amount
                        admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=float(txn['charge_amount']),
                            description=f"PayIn charge (HDFC) - {txn['order_id']}",
                            reference_id=txn['txn_id']
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✅ Admin unsettled wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"✗ Failed to credit admin unsettled wallet: {admin_wallet_result.get('message')}")
                
                # Update transaction with callback data
                if mapped_status in ['SUCCESS', 'FAILED']:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, bank_ref_no = %s, pg_txn_id = %s, payment_mode = %s,
                            error_message = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, utr, transaction_id, payment_mode, 
                          message if mapped_status == 'FAILED' else None, txn['txn_id']))
                else:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, payment_mode = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, transaction_id, payment_mode, txn['txn_id']))
                
                conn.commit()
                
                # Verify the update
                cursor.execute("""
                    SELECT status, bank_ref_no, pg_txn_id, completed_at
                    FROM payin_transactions
                    WHERE txn_id = %s
                """, (txn['txn_id'],))
                
                updated_txn = cursor.fetchone()
                print(f"\n✓ Transaction Updated:")
                print(f"  Status: {updated_txn['status']}")
                print(f"  UTR: {updated_txn['bank_ref_no']}")
                print(f"  PG TXN ID: {updated_txn['pg_txn_id']}")
                print(f"  Completed: {updated_txn['completed_at']}")
                
                # Forward callback to merchant if configured
                try:
                    # Check for transaction-specific callback URL first
                    cursor.execute("""
                        SELECT callback_url FROM payin_transactions
                        WHERE txn_id = %s
                    """, (txn['txn_id'],))
                    
                    txn_callback = cursor.fetchone()
                    callback_url = txn_callback.get('callback_url') if txn_callback else None
                    
                    # If no transaction-specific callback, check merchant-level callback
                    if not callback_url:
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s AND is_active = TRUE
                        """, (txn['merchant_id'],))
                        
                        merchant_callback = cursor.fetchone()
                        callback_url = merchant_callback.get('payin_callback_url') if merchant_callback else None
                    
                    if callback_url:
                        print(f"\n📤 Forwarding callback to merchant: {callback_url}")
                        
                        from callback_forwarder import forward_payin_callback
                        
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'order_id': txn['order_id'],
                            'status': mapped_status,
                            'utr': utr,
                            'pg_txn_id': transaction_id,
                            'pg_partner': 'HDFCPaytouch_Barringer',
                            'amount': amount,
                            'payment_mode': payment_mode,
                            'message': message,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Forward callback using utility function
                        forward_result = forward_payin_callback(
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
                        print("ℹ️  No callback URL configured (transaction-specific or merchant-level)")
                    
                except Exception as e:
                    print(f"❌ ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                
                print("=" * 80)
                print("✅ Payin callback processed successfully")
                print("=" * 80)
                
                return jsonify({
                    'success': True,
                    'message': 'Payin callback processed successfully',
                    'txn_id': txn['txn_id'],
                    'order_id': txn['order_id'],
                    'status': mapped_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ ERROR in payin callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
