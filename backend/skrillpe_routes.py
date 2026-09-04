"""
SkrillPe API Routes
Handles SkrillPe payin operations
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from skrillpe_service import skrillpe_service
from database import get_db_connection
import json

skrillpe_bp = Blueprint('skrillpe', __name__, url_prefix='/api/skrillpe')

@skrillpe_bp.route('/order/create', methods=['POST'])
@jwt_required()
def create_skrillpe_order():
    """Create SkrillPe payin order"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'orderid', 'payee_fname', 'payee_mobile']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Create order
        result = skrillpe_service.create_payin_order(current_merchant, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Create SkrillPe order error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@skrillpe_bp.route('/status/<txn_id>', methods=['GET'])
@jwt_required()
def check_skrillpe_status(txn_id):
    """Check SkrillPe payment status"""
    try:
        current_merchant = get_jwt_identity()
        
        # Verify transaction belongs to merchant
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT txn_id, merchant_id, order_id, amount, status, 
                           pg_txn_id, bank_ref_no, qr_code_url
                    FROM payin_transactions
                    WHERE txn_id = %s AND merchant_id = %s
                """, (txn_id, current_merchant))
                
                txn = cursor.fetchone()
                
                if not txn:
                    return jsonify({
                        'success': False,
                        'message': 'Transaction not found'
                    }), 404
                
                # Check status from SkrillPe
                status_result = skrillpe_service.check_payment_status(txn_id)
                
                if status_result['success']:
                    # Update database if status changed
                    new_status = status_result['status']
                    
                    if new_status != txn['status']:
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, bank_ref_no = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            new_status,
                            status_result.get('rrn'),
                            txn_id
                        ))
                        
                        if new_status == 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET completed_at = NOW()
                                WHERE txn_id = %s
                            """, (txn_id,))
                        
                        conn.commit()
                    
                    return jsonify({
                        'success': True,
                        'txn_id': txn_id,
                        'order_id': txn['order_id'],
                        'amount': float(txn['amount']),
                        'status': new_status,
                        'rrn': status_result.get('rrn'),
                        'payer_vpa': status_result.get('payer_vpa'),
                        'payer_name': status_result.get('payer_name'),
                        'message': status_result.get('message')
                    }), 200
                else:
                    return jsonify(status_result), 400
                    
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check SkrillPe status error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
