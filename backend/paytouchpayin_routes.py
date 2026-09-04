"""
Paytouchpayin Payment Gateway Routes
Handles QR generation and status check
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from paytouchpayin_service import PaytouchpayinService
from database_pooled import get_db_connection
import json

paytouchpayin_bp = Blueprint('paytouchpayin', __name__)
paytouchpayin_service = PaytouchpayinService()

@paytouchpayin_bp.route('/api/paytouchpayin/create-order', methods=['POST'])
@jwt_required()
def create_paytouchpayin_order():
    """
    Create Paytouchpayin Dynamic QR order
    
    Request Body:
    {
        "amount": 100,
        "order_id": "ORDER123",
        "customer_name": "John Doe",
        "customer_mobile": "9876543210",
        "customer_email": "john@example.com"
    }
    """
    try:
        merchant_id = get_jwt_identity()
        data = request.get_json()
        
        print(f"📥 Paytouchpayin order request from merchant: {merchant_id}")
        print(f"📦 Request data: {json.dumps(data, indent=2)}")
        
        # Validate required fields
        if not data.get('amount'):
            return jsonify({
                'success': False,
                'error': 'Amount is required'
            }), 400
        
        # Create order
        result = paytouchpayin_service.create_payin_order(merchant_id, data)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Error in create_paytouchpayin_order: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paytouchpayin_bp.route('/api/paytouchpayin/check-status/<txn_id>', methods=['GET'])
@jwt_required()
def check_paytouchpayin_status(txn_id):
    """
    Check Paytouchpayin transaction status
    Note: Paytouchpayin uses instant callback, so status is updated automatically
    This endpoint just returns the current status from database
    """
    try:
        merchant_id = get_jwt_identity()
        
        print(f"🔍 Checking Paytouchpayin status for txn_id: {txn_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                txn_id, pg_txn_id, order_id, amount, charge, final_amount,
                status, utr, customer_name, customer_mobile, customer_email,
                remark, created_at, updated_at
            FROM payin
            WHERE txn_id = %s AND merchant_id = %s AND pg_partner = 'paytouchpayin'
        """, (txn_id, merchant_id))
        
        transaction = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': transaction
        }), 200
        
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paytouchpayin_bp.route('/api/paytouchpayin/check-status-by-order/<order_id>', methods=['GET'])
@jwt_required()
def check_paytouchpayin_status_by_order(order_id):
    """
    Check Paytouchpayin transaction status by order_id
    """
    try:
        merchant_id = get_jwt_identity()
        
        print(f"🔍 Checking Paytouchpayin status for order_id: {order_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                txn_id, pg_txn_id, order_id, amount, charge, final_amount,
                status, utr, customer_name, customer_mobile, customer_email,
                remark, created_at, updated_at
            FROM payin
            WHERE order_id = %s AND merchant_id = %s AND pg_partner = 'paytouchpayin'
            ORDER BY created_at DESC
            LIMIT 1
        """, (order_id, merchant_id))
        
        transaction = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': transaction
        }), 200
        
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
