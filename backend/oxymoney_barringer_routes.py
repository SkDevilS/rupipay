"""
Oxymoney_Barringer Payin Routes
Handles payin transaction creation and status check
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from oxymoney_barringer_service import oxymoney_barringer_service
from database import get_db_connection

oxymoney_barringer_bp = Blueprint('oxymoney_barringer', __name__, url_prefix='/api/oxymoney-barringer')

@oxymoney_barringer_bp.route('/payin/create', methods=['POST'])
@jwt_required()
def create_payin():
    """
    Create payin order via Oxymoney_Barringer
    
    Request body:
    {
        "amount": 100.00,
        "orderid": "ORDER123",
        "payee_fname": "John",
        "payee_lname": "Doe",
        "payee_email": "john@example.com",
        "payee_mobile": "9876543210",
        "note": "Payment for order",
        "expiryValue": 1,
        "callback_url": "https://merchant.com/callback"
    }
    """
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'orderid', 'payee_fname', 'payee_email', 'payee_mobile']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Create payin order
        result = oxymoney_barringer_service.create_payin_order(current_merchant, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Create payin error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@oxymoney_barringer_bp.route('/payin/status', methods=['POST'])
@jwt_required()
def check_payin_status():
    """
    Check payin transaction status
    
    Request body:
    {
        "client_ref_id": "OXBAR_20260501123456_MERCHANT123"
        OR
        "txn_id": "OXY_BAR_MERCHANT123_ORDER123_20260501123456"
    }
    """
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        client_ref_id = data.get('client_ref_id')
        txn_id = data.get('txn_id')
        
        if not client_ref_id and not txn_id:
            return jsonify({'success': False, 'message': 'Either client_ref_id or txn_id is required'}), 400
        
        # If txn_id provided, get the Oxymoney txn_id from database
        if txn_id:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Database connection failed'}), 500
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT pg_txn_id FROM payin_transactions
                        WHERE txn_id = %s AND merchant_id = %s AND pg_partner = 'Oxymoney_Barringer'
                    """, (txn_id, current_merchant))
                    
                    txn = cursor.fetchone()
                    
                    if not txn:
                        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                    
                    ox_txn_id = txn['pg_txn_id']
            finally:
                conn.close()
        else:
            ox_txn_id = None
        
        # Check status
        result = oxymoney_barringer_service.check_transaction_status(
            client_ref_id=client_ref_id,
            txn_id=ox_txn_id
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Check status error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@oxymoney_barringer_bp.route('/vpa/usage', methods=['GET'])
@jwt_required()
def get_vpa_usage():
    """
    Get VPA usage statistics (Admin only)
    
    Returns usage stats for all 5 VPAs and total usage information
    """
    try:
        current_user = get_jwt_identity()
        
        # Verify admin access
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if user is admin
                cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = %s", (current_user,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Unauthorized - Admin access required'}), 403
        finally:
            conn.close()
        
        # Get VPA usage stats
        stats_data = oxymoney_barringer_service.get_vpa_usage_stats()
        
        return jsonify({
            'success': True,
            'vpa_stats': stats_data.get('vpa_stats', []),
            'total_usage': stats_data.get('total_usage', 0),
            'total_daily_limit': stats_data.get('total_daily_limit', 4950000),
            'total_max_threshold': stats_data.get('total_max_threshold', 4500000),
            'total_remaining': stats_data.get('total_remaining', 0),
            'total_usage_percentage': stats_data.get('total_usage_percentage', 0),
            'approaching_limit': stats_data.get('approaching_limit', False),
            'limit_status': stats_data.get('limit_status', 'AVAILABLE'),
            'daily_limit': oxymoney_barringer_service.vpa_daily_limit,
            'safety_threshold': oxymoney_barringer_service.vpa_safety_threshold
        }), 200
            
    except Exception as e:
        print(f"Get VPA usage error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
