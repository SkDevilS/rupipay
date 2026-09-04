"""
Tourquest Payin API Routes
Handles merchant payin operations through Tourquest
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from tourquest_service import tourquest_service
from database import get_db_connection
from utils import decrypt_aes, encrypt_aes
import json

tourquest_bp = Blueprint('tourquest', __name__, url_prefix='/api/tourquest')

@tourquest_bp.route('/order/create', methods=['POST'])
@jwt_required()
def create_tourquest_order():
    """
    Create Tourquest payin order (for merchant dashboard)
    
    Expects encrypted payload with:
    - amount
    - orderid
    - payee_fname
    - payee_lname (optional)
    - payee_mobile
    - payee_email
    """
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        encrypted_data = data.get('data')
        if not encrypted_data:
            return jsonify({'success': False, 'message': 'Encrypted data required'}), 400
        
        # Get merchant AES credentials from database
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT aes_key, aes_iv FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                
                merchant = cursor.fetchone()
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Decrypt payload
                decrypted_data = decrypt_aes(encrypted_data, merchant['aes_key'], merchant['aes_iv'])
                if not decrypted_data:
                    return jsonify({'success': False, 'message': 'Failed to decrypt data'}), 400
                
                order_data = json.loads(decrypted_data)
                
                # Validate required fields
                required_fields = ['amount', 'orderid', 'payee_fname', 'payee_mobile', 'payee_email']
                for field in required_fields:
                    if not order_data.get(field):
                        return jsonify({'success': False, 'message': f'{field} is required'}), 400
                
                # Create Tourquest payin order
                result = tourquest_service.create_payin_order(current_merchant, order_data)
                
                if not result.get('success'):
                    return jsonify(result), 400
                
                # Encrypt response
                response_data = {
                    'txn_id': result['txn_id'],
                    'order_id': result['order_id'],
                    'amount': result['amount'],
                    'charge_amount': result['charge_amount'],
                    'net_amount': result['net_amount'],
                    'qr_string': result['qr_string'],
                    'upi_link': result['upi_link'],
                    'tourquest_txn_id': result['tourquest_txn_id'],
                    'clientrefno': result['clientrefno']
                }
                
                encrypted_response = encrypt_aes(
                    json.dumps(response_data),
                    merchant['aes_key'],
                    merchant['aes_iv']
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Order created successfully',
                    'data': encrypted_response
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create Tourquest order error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@tourquest_bp.route('/status/<txn_id>', methods=['GET'])
@jwt_required()
def check_tourquest_status(txn_id):
    """Check Tourquest payment status by transaction ID"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get transaction details
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE txn_id = %s AND merchant_id = %s AND pg_partner = 'Tourquest'
                """, (txn_id, current_merchant))
                
                txn = cursor.fetchone()
                
                if not txn:
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                # If transaction is already completed, return status
                if txn['status'] in ['SUCCESS', 'FAILED', 'CANCELLED']:
                    return jsonify({
                        'success': True,
                        'status': txn['status'],
                        'transaction': {
                            'txn_id': txn['txn_id'],
                            'order_id': txn['order_id'],
                            'amount': float(txn['amount']),
                            'charge_amount': float(txn['charge_amount']),
                            'net_amount': float(txn['net_amount']),
                            'status': txn['status'],
                            'pg_txn_id': txn.get('pg_txn_id'),
                            'bank_ref_no': txn.get('bank_ref_no'),
                            'created_at': txn['created_at'].isoformat() if txn.get('created_at') else None,
                            'completed_at': txn['completed_at'].isoformat() if txn.get('completed_at') else None
                        }
                    }), 200
                
                # Check status from Tourquest using pg_txn_id (clientrefno)
                clientrefno = txn.get('pg_txn_id')
                if not clientrefno:
                    return jsonify({
                        'success': True,
                        'status': txn['status'],
                        'message': 'Payment pending'
                    }), 200
                
                status_result = tourquest_service.check_payment_status(clientrefno)
                
                if not status_result.get('success'):
                    return jsonify(status_result), 400
                
                # Update transaction status if changed
                tourquest_status = status_result.get('status', '').upper()
                
                if tourquest_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
                    # Update to SUCCESS
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'SUCCESS',
                            bank_ref_no = %s,
                            payment_mode = 'UPI',
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status_result.get('utr'), txn_id))
                    
                    # Credit merchant unsettled wallet with net amount
                    from wallet_service import wallet_service as wallet_svc
                    net_amount = float(txn['net_amount'])
                    charge_amount = float(txn['charge_amount'])
                    
                    wallet_result = wallet_svc.credit_unsettled_wallet(
                        merchant_id=current_merchant,
                        amount=net_amount,
                        description=f"PayIn received (Tourquest) - {txn['order_id']}",
                        reference_id=txn_id
                    )
                    
                    if wallet_result['success']:
                        print(f"✓ Merchant unsettled wallet credited: ₹{net_amount}")
                    else:
                        print(f"✗ Failed to credit merchant unsettled wallet: {wallet_result.get('message')}")
                    
                    # Credit admin unsettled wallet with charge amount
                    admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                        admin_id='admin',
                        amount=charge_amount,
                        description=f"PayIn charge (Tourquest) - {txn['order_id']}",
                        reference_id=txn_id
                    )
                    
                    if admin_wallet_result['success']:
                        print(f"✓ Admin unsettled wallet credited: ₹{charge_amount}")
                    else:
                        print(f"✗ Failed to credit admin unsettled wallet: {admin_wallet_result.get('message')}")
                    
                    conn.commit()
                    
                    return jsonify({
                        'success': True,
                        'status': 'SUCCESS',
                        'message': 'Payment successful',
                        'transaction': {
                            'txn_id': txn_id,
                            'order_id': txn['order_id'],
                            'amount': float(txn['amount']),
                            'status': 'SUCCESS',
                            'utr': status_result.get('utr')
                        }
                    }), 200
                
                elif tourquest_status in ['FAILED', 'EXPIRED'] and txn['status'] not in ['FAILED', 'CANCELLED']:
                    # Update to FAILED
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED',
                            error_message = %s,
                            updated_at = NOW(),
                            completed_at = NOW()
                        WHERE txn_id = %s
                    """, (status_result.get('message', 'Payment failed'), txn_id))
                    
                    conn.commit()
                    
                    return jsonify({
                        'success': True,
                        'status': 'FAILED',
                        'message': 'Payment failed',
                        'transaction': {
                            'txn_id': txn_id,
                            'order_id': txn['order_id'],
                            'status': 'FAILED'
                        }
                    }), 200
                
                # Return current status
                return jsonify({
                    'success': True,
                    'status': txn['status'],
                    'message': 'Payment pending',
                    'transaction': {
                        'txn_id': txn_id,
                        'order_id': txn['order_id'],
                        'amount': float(txn['amount']),
                        'status': txn['status']
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check Tourquest status error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
