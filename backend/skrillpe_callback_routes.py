"""
SkrillPe Callback Routes
Handles webhook callbacks from SkrillPe
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
import json
from datetime import datetime

skrillpe_callback_bp = Blueprint('skrillpe_callback', __name__, url_prefix='/api/callback/skrillpe')

@skrillpe_callback_bp.route('/payin', methods=['POST'])
def skrillpe_payin_callback():
    """
    Webhook endpoint for SkrillPe payin status updates
    SkrillPe will call this when payment status changes
    
    Expected callback format:
    {
        "txnId": "893395053",
        "upiTxnId": null,
        "custRef": "808727161206",
        "amount": "200.00",
        "txnStatus": "SUCCESS",
        "payerVpa": "9717736222@axl",
        "payerVerifiedName": "NAMAN BHATIA",
        "payerMobile": "9717736222",
        "payeeVpa": "W_DsnVhmVwQ8ZozQLWkHudM+vHijgPlAkDRcOvCJ6js=",
        "payeeVerifiedName": "SKILLSKRILL INFO SOLUTIONS PRIVATE LIMITED",
        "payeeMobile": null,
        "mrchId": null,
        "aggrId": null,
        "txnDateTime": "2026-03-12 17:36:02",
        "refId": "getp.d.skillskrill.893395053",
        "refUrl": null,
        "sendNotification": "0",
        "riskDescription": null,
        "riskStatus": "0",
        "settlement_status": null,
        "settlement_date": null,
        "settlement_amount": null,
        "remarks": "TTIBZ2026031233081",
        "settlement_account_no": null,
        "piMid": null,
        "pgMid": null,
        "virtualVpa": null,
        "payerAccountType": null
    }
    """
    try:
        print("=" * 80)
        print("SkrillPe Payin Callback Received")
        print("=" * 80)
        
        # Log request details
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        # Get callback data
        callback_data = None
        
        if request.is_json:
            callback_data = request.json
            print("Received as JSON")
        elif request.form:
            callback_data = request.form.to_dict()
            print("Received as Form Data")
        elif request.data:
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
        
        # Extract data from callback
        cust_ref = callback_data.get('custRef')  # This is our transaction ID
        txn_status = callback_data.get('txnStatus')
        amount = callback_data.get('amount')
        payer_vpa = callback_data.get('payerVpa')
        payer_name = callback_data.get('payerVerifiedName')
        payer_mobile = callback_data.get('payerMobile')
        txn_datetime = callback_data.get('txnDateTime')
        remarks = callback_data.get('remarks')
        ref_id = callback_data.get('refId')
        txn_id = callback_data.get('txnId')
        
        if not cust_ref:
            print("ERROR: No custRef in callback")
            return jsonify({'success': False, 'message': 'Missing custRef'}), 400
        
        print(f"Customer Ref (TXN ID): {cust_ref}")
        print(f"Status: {txn_status}")
        print(f"Amount: {amount}")
        print(f"Payer VPA: {payer_vpa}")
        print(f"Payer Name: {payer_name}")
        print(f"Payer Mobile: {payer_mobile}")
        print(f"TXN DateTime: {txn_datetime}")
        print(f"Remarks (UTR): {remarks}")
        print(f"Ref ID: {ref_id}")
        print(f"TXN ID: {txn_id}")
        
        # Map status
        if txn_status and txn_status.upper() == 'SUCCESS':
            mapped_status = 'SUCCESS'
        elif txn_status and txn_status.upper() == 'FAILED':
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
                # Find transaction by txn_id (which is custRef)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount as txn_amount, order_id
                    FROM payin_transactions
                    WHERE txn_id = %s
                """, (cust_ref,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for txn_id: {cust_ref}")
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
                        print(f"⚠ Wallet already credited - skipping duplicate callback")
                        
                        # Just update transaction status if needed
                        if txn['status'] != 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, 
                                    completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (mapped_status, remarks, txn_id, cust_ref))
                            conn.commit()
                            print(f"✓ Updated transaction status to SUCCESS")
                    else:
                        # First time processing SUCCESS - credit unsettled wallet
                        print(f"✓ Processing SUCCESS callback - crediting unsettled wallet")
                        
                        # Update transaction
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, bank_ref_no = %s, pg_txn_id = %s,
                                completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, remarks, txn_id, cust_ref))
                        
                        # Credit merchant unsettled wallet
                        cursor.execute("""
                            UPDATE merchants
                            SET unsettled_wallet_balance = unsettled_wallet_balance + %s,
                                updated_at = NOW()
                            WHERE merchant_id = %s
                        """, (txn['txn_amount'], txn['merchant_id']))
                        
                        # Record wallet transaction
                        cursor.execute("""
                            INSERT INTO merchant_wallet_transactions (
                                merchant_id, txn_type, amount, balance_after,
                                reference_id, description, created_at
                            )
                            SELECT 
                                %s, 'UNSETTLED_CREDIT', %s, unsettled_wallet_balance,
                                %s, %s, NOW()
                            FROM merchants
                            WHERE merchant_id = %s
                        """, (
                            txn['merchant_id'],
                            txn['txn_amount'],
                            txn['txn_id'],
                            f"Payin credit for order {txn['order_id']}",
                            txn['merchant_id']
                        ))
                        
                        conn.commit()
                        print(f"✓ Credited unsettled wallet: ₹{txn['txn_amount']}")
                        
                        # Trigger merchant callback if configured
                        cursor.execute("""
                            SELECT callback_url FROM merchants WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        
                        merchant = cursor.fetchone()
                        if merchant and merchant.get('callback_url'):
                            print(f"📞 Triggering merchant callback: {merchant['callback_url']}")
                            try:
                                import requests
                                callback_payload = {
                                    'txn_id': txn['txn_id'],
                                    'order_id': txn['order_id'],
                                    'amount': str(txn['txn_amount']),
                                    'status': mapped_status,
                                    'utr': remarks,
                                    'pg_txn_id': txn_id,
                                    'timestamp': txn_datetime
                                }
                                
                                requests.post(
                                    merchant['callback_url'],
                                    json=callback_payload,
                                    timeout=10
                                )
                                print(f"✓ Merchant callback sent successfully")
                            except Exception as cb_error:
                                print(f"✗ Merchant callback failed: {cb_error}")
                
                elif mapped_status == 'FAILED':
                    # Update transaction to FAILED
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, cust_ref))
                    
                    conn.commit()
                    print(f"✓ Updated transaction status to FAILED")
                
                else:
                    # INITIATED or other status
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, cust_ref))
                    
                    conn.commit()
                    print(f"✓ Updated transaction status to {mapped_status}")
                
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"SkrillPe callback error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
