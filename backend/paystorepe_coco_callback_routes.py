"""
PayStorePe_Coco Callback Routes
Handles webhook callbacks from PayStorePe_Coco for payout status updates
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from datetime import datetime
import json

paystorepe_coco_callback_bp = Blueprint('paystorepe_coco_callback', __name__, url_prefix='/api/callback')

@paystorepe_coco_callback_bp.route('/paystorepe_coco/payout', methods=['POST'])
def paystorepe_coco_payout_callback():
    """
    Webhook endpoint for PayStorePe_Coco payout callbacks
    Handles payout status updates
    """
    try:
        # Get callback data
        callback_data = request.json or request.form.to_dict()
        
        print("=" * 80)
        print("PayStorePe_Coco Payout Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Extract data from callback
        transaction_id = callback_data.get('txn_id')
        external_ref = callback_data.get('client_id')
        status = callback_data.get('status', 'PENDING')
        utr = callback_data.get('utr')
        message = callback_data.get('message', '')
        amount = callback_data.get('amount')
        
        if not transaction_id and not external_ref:
            print("ERROR: No transaction_id or external_ref in callback")
            return jsonify({'success': False, 'message': 'Missing transaction identifier'}), 400
        
        print(f"Transaction ID: {transaction_id}")
        print(f"External Ref: {external_ref}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Message: {message}")
        
        # Map PayStorePe status to our status
        status_upper = status.upper()
        if status_upper == 'SUCCESS':
            mapped_status = 'SUCCESS'
        elif status_upper in ['FAILED', 'FAILURE']:
            mapped_status = 'FAILED'
        elif status_upper in ['PENDING', 'QUEUED', 'INITIATED']:
            mapped_status = 'QUEUED'
        elif status_upper == 'PROCESSING':
            mapped_status = 'INPROCESS'
        else:
            mapped_status = 'QUEUED'
            
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
                        SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id, amount
                        FROM payout_transactions
                        WHERE pg_txn_id = %s AND UPPER(pg_partner) = 'PAYSTOREPE_COCO'
                    """, (transaction_id,))
                else:
                    # Try to find by reference_id extracted from external_ref
                    cursor.execute("""
                        SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id, amount
                        FROM payout_transactions
                        WHERE reference_id = %s AND UPPER(pg_partner) = 'PAYSTOREPE_COCO'
                    """, (external_ref,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    # Fallback without pg_partner check
                    if transaction_id:
                        cursor.execute("""
                            SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id, amount
                            FROM payout_transactions
                            WHERE pg_txn_id = %s
                        """, (transaction_id,))
                        txn = cursor.fetchone()
                    
                    if not txn and external_ref:
                        cursor.execute("""
                            SELECT txn_id, status, merchant_id, admin_id, reference_id, order_id, amount
                            FROM payout_transactions
                            WHERE reference_id = %s
                        """, (external_ref,))
                        txn = cursor.fetchone()

                if not txn:
                    print(f"ERROR: Transaction not found for transaction_id: {transaction_id}, external_ref: {external_ref}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # NEW FLOW: Handle wallet refund for FAILED status (wallet was already deducted on initiation)
                if mapped_status == 'FAILED':
                    # Check if this is a merchant payout (has merchant_id) or admin personal payout (has admin_id)
                    if txn.get('merchant_id'):
                        # MERCHANT PAYOUT - Refund wallet
                        print(f"Merchant payout FAILED - checking wallet refund")
                        
                        # Check if wallet was already refunded
                        cursor.execute("""
                            SELECT txn_id FROM merchant_wallet_transactions
                            WHERE reference_id = %s AND txn_type = 'CREDIT'
                            AND description LIKE '%%Payout refund%%'
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
                            
                            if payout_details:
                                # Refund the total deduction
                                total_refund = float(payout_details['amount'])
                                
                                print(f"Refunding to settled wallet - Amount: ₹{total_refund:.2f} (Net: ₹{payout_details['net_amount']:.2f} + Charges: ₹{payout_details['charge_amount']:.2f})")
                                
                                # Credit merchant settled wallet (refund)
                                from wallet_service import WalletService
                                wallet_svc = WalletService()
                                credit_result = wallet_svc.credit_merchant_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=total_refund,
                                    description=f"Payout refund: ₹{float(payout_details['net_amount']):.2f} + Charges: ₹{float(payout_details['charge_amount']):.2f}",
                                    reference_id=txn['txn_id']
                                )
                                
                                if credit_result.get('success'):
                                    print(f"✅ WALLET REFUNDED - Balance: ₹{credit_result.get('balance_before', 0):.2f} → ₹{credit_result.get('balance_after', 0):.2f}")
                                else:
                                    print(f"✗ WALLET REFUND FAILED: {credit_result.get('message')}")
                                    print(f"⚠️  WARNING: Payout marked as FAILED but wallet refund failed - manual intervention needed")
                    
                    elif txn.get('admin_id'):
                        # ADMIN PERSONAL PAYOUT - No wallet refund needed
                        print(f"Admin personal payout FAILED - no wallet refund needed")
                    
                    else:
                        print(f"⚠️  WARNING: Transaction has neither merchant_id nor admin_id")
                
                # For SUCCESS status, no wallet action needed (already deducted on initiation)
                if mapped_status == 'SUCCESS':
                    if txn.get('merchant_id'):
                        print(f"✅ Merchant payout SUCCESS - Wallet was already deducted on initiation, no action needed")
                    elif txn.get('admin_id'):
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
                    if txn.get('merchant_id'):
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
                                'pg_partner': 'PayStorePe_Coco',
                                'amount': float(amount) if amount else float(txn.get('amount') or 0),
                                'message': message,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Specifically forward order_id for MID 9120000001
                            if txn['merchant_id'] == '9120000001':
                                merchant_callback_data['order_id'] = txn.get('order_id')
                            
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
                            print(f"ℹ️  No callback URL configured for merchant {txn['merchant_id']}")
                    else:
                        print(f"ℹ️  Admin payout - no merchant callback to forward")
                        
                except Exception as e:
                    print(f"ERROR forwarding callback: {e}")
                    import traceback
                    traceback.print_exc()
                
                # PaystorePe needs HTTP 200 response
                response_data = {
                    "success": True,
                    "message": "Callback processed successfully",
                    "txn_id": transaction_id,
                    "client_id": external_ref,
                    "status": mapped_status
                }
                return jsonify(response_data), 200
                
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"ERROR processing callback: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
            
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"CRITICAL ERROR in callback route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
