"""
VIYONAPAY Payin Routes
Handles VIYONAPAY payment order creation and status checking
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection
from viyonapay_service import ViyonapayService

viyonapay_bp = Blueprint('viyonapay', __name__, url_prefix='/api/viyonapay')
viyonapay_service = ViyonapayService()

@viyonapay_bp.route('/create-order', methods=['POST'])
@jwt_required()
def create_viyonapay_order():
    """Create a new VIYONAPAY payment order"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'customer_name', 'customer_email', 'customer_mobile']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Create order
        result = viyonapay_service.create_payin_order(current_merchant, data)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Create VIYONAPAY order error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@viyonapay_bp.route('/status/<txn_id>', methods=['GET'])
@jwt_required()
def check_viyonapay_status(txn_id):
    """Check VIYONAPAY payment status by transaction ID"""
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
                    WHERE txn_id = %s AND merchant_id = %s AND pg_partner = 'VIYONAPAY'
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
                
                # Check status from VIYONAPAY using order_id
                order_id = txn.get('order_id')
                if not order_id:
                    return jsonify({
                        'success': True,
                        'status': txn['status'],
                        'message': 'Payment pending'
                    }), 200
                
                status_result = viyonapay_service.check_payment_status(order_id)
                
                if not status_result.get('success'):
                    return jsonify(status_result), 400
                
                # Update transaction status if changed
                viyonapay_status = status_result.get('status', '').upper()
                
                if viyonapay_status == 'SUCCESS' and txn['status'] != 'SUCCESS':
                    # Update to SUCCESS
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'SUCCESS',
                            pg_txn_id = %s,
                            bank_ref_no = %s,
                            payment_mode = %s,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (
                        status_result.get('transaction_id'),
                        status_result.get('bank_reference_number'),
                        status_result.get('payment_mode', 'UPI'),
                        txn_id
                    ))
                    
                    # Credit merchant unsettled wallet with net amount
                    from wallet_service import wallet_service as wallet_svc
                    net_amount = float(txn['net_amount'])
                    charge_amount = float(txn['charge_amount'])
                    
                    wallet_result = wallet_svc.credit_unsettled_wallet(
                        merchant_id=current_merchant,
                        amount=net_amount,
                        description=f"PayIn received (VIYONAPAY) - {order_id}",
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
                        description=f"PayIn charge (VIYONAPAY) - {order_id}",
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
                            'order_id': order_id,
                            'amount': float(txn['amount']),
                            'status': 'SUCCESS',
                            'pg_txn_id': status_result.get('transaction_id'),
                            'bank_ref_no': status_result.get('bank_reference_number')
                        }
                    }), 200
                
                elif viyonapay_status in ['FAILED', 'EXPIRED'] and txn['status'] not in ['FAILED', 'CANCELLED']:
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
                            'order_id': order_id,
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
                        'order_id': order_id,
                        'amount': float(txn['amount']),
                        'status': txn['status']
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check VIYONAPAY status error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@viyonapay_bp.route('/status/order/<order_id>', methods=['GET'])
@jwt_required()
def check_viyonapay_status_by_order(order_id):
    """Check VIYONAPAY payment status by order ID"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get transaction details by order_id
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE order_id = %s AND merchant_id = %s AND pg_partner = 'VIYONAPAY'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order_id, current_merchant))
                
                txn = cursor.fetchone()
                
                if not txn:
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                # Use the txn_id to check status
                return check_viyonapay_status(txn['txn_id'])
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check VIYONAPAY status by order error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
