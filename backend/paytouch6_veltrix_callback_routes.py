"""
PayTouch6_Veltrix Callback Routes
Handles webhook callbacks from PayTouch6_Veltrix for payout status updates
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
from datetime import datetime
import json

paytouch6_veltrix_callback_bp = Blueprint(
    'paytouch6_veltrix_callback',
    __name__,
    url_prefix='/api/callback'
)


@paytouch6_veltrix_callback_bp.route('/paytouch6/payout', methods=['POST'])
def paytouch6_veltrix_payout_callback():
    """
    Webhook endpoint for PayTouch6_Veltrix payout callbacks
    Handles payout status updates
    """
    try:
        # Get callback data
        callback_data = request.json or request.form.to_dict()

        print("=" * 80)
        print("PayTouch6_Veltrix Payout Callback Received")
        print("=" * 80)
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")

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
            return jsonify({
                'success': False,
                'message': 'Missing transaction identifier'
            }), 400

        print(f"Transaction ID: {transaction_id}")
        print(f"External Ref: {external_ref}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        print(f"Message: {message}")

        # Map gateway status to our internal status
        status_map = {
            'SUCCESS': 'SUCCESS',
            'PENDING': 'QUEUED',
            'FAILED': 'FAILED',
            'PROCESSING': 'INPROCESS'
        }

        mapped_status = status_map.get(status.upper(), 'QUEUED')

        print(f"Mapped Status: {mapped_status}")

        # Database connection
        conn = get_db_connection()

        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500

        try:
            with conn.cursor() as cursor:

                # Find transaction
                if transaction_id:
                    cursor.execute("""
                        SELECT txn_id,
                               status,
                               merchant_id,
                               admin_id,
                               reference_id,
                               order_id
                        FROM payout_transactions
                        WHERE pg_txn_id=%s
                        AND pg_partner='PayTouch6_Veltrix'
                    """, (transaction_id,))
                else:
                    cursor.execute("""
                        SELECT txn_id,
                               status,
                               merchant_id,
                               admin_id,
                               reference_id,
                               order_id
                        FROM payout_transactions
                        WHERE reference_id=%s
                        AND pg_partner='PayTouch6_Veltrix'
                    """, (external_ref,))

                txn = cursor.fetchone()

                if not txn:
                    print(
                        f"ERROR: Transaction not found "
                        f"for transaction_id={transaction_id}, "
                        f"external_ref={external_ref}"
                    )
                    return jsonify({
                        'success': False,
                        'message': 'Transaction not found'
                    }), 404

                print(
                    f"Found Transaction: {txn['txn_id']}, "
                    f"Current Status: {txn['status']}"
                )

                # Refund logic
                if mapped_status == 'FAILED':

                    if txn['merchant_id']:

                        print("Merchant payout FAILED - checking wallet refund")

                        cursor.execute("""
                            SELECT txn_id
                            FROM merchant_wallet_transactions
                            WHERE reference_id=%s
                            AND txn_type='CREDIT'
                            AND description LIKE '%Payout refund%'
                        """, (txn['txn_id'],))

                        wallet_already_refunded = cursor.fetchone()

                        if wallet_already_refunded:
                            print("Wallet already refunded - skipping")

                        else:
                            cursor.execute("""
                                SELECT amount,
                                       net_amount,
                                       charge_amount
                                FROM payout_transactions
                                WHERE txn_id=%s
                            """, (txn['txn_id'],))

                            payout_details = cursor.fetchone()

                            total_refund = float(payout_details['amount'])

                            print(
                                f"Refund Amount: â‚¹{total_refund:.2f}"
                            )

                            from wallet_service import WalletService

                            wallet_svc = WalletService()

                            credit_result = wallet_svc.credit_merchant_wallet(
                                merchant_id=txn['merchant_id'],
                                amount=total_refund,
                                description=(
                                    f"Payout refund: "
                                    f"â‚¹{payout_details['net_amount']:.2f} + "
                                    f"Charges: â‚¹{payout_details['charge_amount']:.2f}"
                                ),
                                reference_id=txn['txn_id']
                            )

                            if credit_result['success']:
                                print(
                                    "Wallet refunded successfully"
                                )
                            else:
                                print(
                                    f"Wallet refund failed: "
                                    f"{credit_result['message']}"
                                )

                    elif txn['admin_id']:
                        print("Admin personal payout FAILED")

                if mapped_status == 'SUCCESS':

                    if txn['merchant_id']:
                        print(
                            "Merchant payout SUCCESS "
                            "- wallet already deducted"
                        )

                    elif txn['admin_id']:
                        print(
                            "Admin personal payout SUCCESS"
                        )

                # Update transaction
                if mapped_status in ['SUCCESS', 'FAILED']:

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET
                            status=%s,
                            utr=%s,
                            pg_txn_id=%s,
                            error_message=%s,
                            completed_at=NOW(),
                            updated_at=NOW()
                        WHERE txn_id=%s
                    """, (
                        mapped_status,
                        utr,
                        transaction_id,
                        message if mapped_status == 'FAILED' else None,
                        txn['txn_id']
                    ))

                else:

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET
                            status=%s,
                            pg_txn_id=%s,
                            updated_at=NOW()
                        WHERE txn_id=%s
                    """, (
                        mapped_status,
                        transaction_id,
                        txn['txn_id']
                    ))

                conn.commit()

                cursor.execute("""
                    SELECT
                        status,
                        utr,
                        pg_txn_id,
                        completed_at
                    FROM payout_transactions
                    WHERE txn_id=%s
                """, (txn['txn_id'],))

                updated_txn = cursor.fetchone()

                print(updated_txn)

                print("=" * 80)
                print("Payout callback processed successfully")
                print("=" * 80)

                # Forward merchant callback
                try:

                    if txn['merchant_id']:

                        cursor.execute("""
                            SELECT callback_url
                            FROM payout_transactions
                            WHERE txn_id=%s
                        """, (txn['txn_id'],))

                        txn_callback = cursor.fetchone()

                        callback_url = (
                            txn_callback.get('callback_url')
                            if txn_callback else None
                        )

                        if not callback_url:

                            cursor.execute("""
                                SELECT payout_callback_url
                                FROM merchant_callbacks
                                WHERE merchant_id=%s
                                AND is_active=TRUE
                            """, (txn['merchant_id'],))

                            merchant_callback = cursor.fetchone()

                            callback_url = (
                                merchant_callback.get('payout_callback_url')
                                if merchant_callback else None
                            )

                        if callback_url:

                            from callback_forwarder import forward_payout_callback

                            merchant_callback_data = {
                                'txn_id': txn['txn_id'],
                                'reference_id': txn['reference_id'],
                                'status': mapped_status,
                                'utr': utr,
                                'pg_txn_id': transaction_id,
                                'pg_partner': 'PayTouch6_Veltrix',
                                'amount': amount,
                                'timestamp': datetime.now().isoformat()
                            }

                            if txn['merchant_id'] == '9120000001':
                                merchant_callback_data['order_id'] = txn.get('order_id')

                            forward_result = forward_payout_callback(
                                txn_id=txn['txn_id'],
                                merchant_id=txn['merchant_id'],
                                callback_url=callback_url,
                                callback_data=merchant_callback_data
                            )

                            if forward_result['success']:
                                print("Callback forwarded successfully")
                            else:
                                print(
                                    f"Callback forwarding failed: "
                                    f"{forward_result.get('message')}"
                                )

                        else:
                            print("No callback URL configured")

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

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500