"""
Mudrape Payout API Routes
Handles merchant payout operations through Mudrape (UPI & IMPS)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from mudrape_service import mudrape_service
from database import get_db_connection
from utils import decrypt_aes, encrypt_aes
import json

mudrape_payout_bp = Blueprint('mudrape_payout', __name__, url_prefix='/api/mudrape/payout')

@mudrape_payout_bp.route('/upi/create', methods=['POST'])
@jwt_required()
def create_upi_payout():
    """
    Create Mudrape UPI payout (for merchant dashboard)
    
    Expects encrypted payload with:
    - upi_id
    - amount
    - beneficiary_name
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
                
                payout_data = json.loads(decrypted_data)
                
                # Validate required fields
                required_fields = ['upi_id', 'amount', 'beneficiary_name']
                for field in required_fields:
                    if not payout_data.get(field):
                        return jsonify({'success': False, 'message': f'{field} is required'}), 400
                
                # Create Mudrape UPI payout
                result = mudrape_service.create_upi_payout(current_merchant, payout_data)
                
                if not result.get('success'):
                    return jsonify(result), 400
                
                # Encrypt response
                response_data = {
                    'txn_id': result['txn_id'],
                    'amount': result['amount'],
                    'charge_amount': result['charge_amount'],
                    'total_deduction': result['total_deduction'],
                    'status': result['status'],
                    'mudrape_txn_id': result.get('mudrape_txn_id'),
                    'message': result['message']
                }
                
                encrypted_response = encrypt_aes(
                    json.dumps(response_data),
                    merchant['aes_key'],
                    merchant['aes_iv']
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Payout initiated successfully',
                    'data': encrypted_response
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create UPI payout error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@mudrape_payout_bp.route('/imps/create', methods=['POST'])
@jwt_required()
def create_imps_payout():
    """
    Create Mudrape IMPS payout (for merchant dashboard)
    
    Expects encrypted payload with:
    - account_number
    - ifsc_code
    - amount
    - beneficiary_name
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
                
                payout_data = json.loads(decrypted_data)
                
                # Validate required fields
                required_fields = ['account_number', 'ifsc_code', 'amount', 'beneficiary_name']
                for field in required_fields:
                    if not payout_data.get(field):
                        return jsonify({'success': False, 'message': f'{field} is required'}), 400
                
                # Create Mudrape IMPS payout
                result = mudrape_service.create_imps_payout(current_merchant, payout_data)
                
                if not result.get('success'):
                    return jsonify(result), 400
                
                # Encrypt response
                response_data = {
                    'txn_id': result['txn_id'],
                    'amount': result['amount'],
                    'charge_amount': result['charge_amount'],
                    'total_deduction': result['total_deduction'],
                    'status': result['status'],
                    'mudrape_txn_id': result.get('mudrape_txn_id'),
                    'message': result['message']
                }
                
                encrypted_response = encrypt_aes(
                    json.dumps(response_data),
                    merchant['aes_key'],
                    merchant['aes_iv']
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Payout initiated successfully',
                    'data': encrypted_response
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create IMPS payout error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@mudrape_payout_bp.route('/status/<txn_id>', methods=['GET'])
@jwt_required()
def check_payout_status(txn_id):
    """Check Mudrape payout status"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get transaction details
                cursor.execute("""
                    SELECT * FROM payout_transactions
                    WHERE txn_id = %s AND merchant_id = %s AND pg_partner = 'Mudrape'
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
                            'amount': float(txn['amount']),
                            'charge_amount': float(txn['charge_amount']),
                            'total_deduction': float(txn['total_deduction']),
                            'status': txn['status'],
                            'pg_txn_id': txn.get('pg_txn_id'),
                            'utr': txn.get('utr'),
                            'created_at': txn['created_at'].isoformat() if txn.get('created_at') else None,
                            'completed_at': txn['completed_at'].isoformat() if txn.get('completed_at') else None
                        }
                    }), 200
                
                # Check status from Mudrape
                status_result = mudrape_service.check_payout_status(txn_id)
                
                if not status_result.get('success'):
                    return jsonify(status_result), 400
                
                # Update transaction status if changed
                mudrape_status = status_result.get('status', 'INITIATED')
                
                if mudrape_status != txn['status']:
                    mudrape_service.update_payout_status(
                        txn_id,
                        mudrape_status,
                        status_result.get('txnId'),
                        status_result.get('utr')
                    )
                
                # Get updated transaction
                cursor.execute("""
                    SELECT * FROM payout_transactions WHERE txn_id = %s
                """, (txn_id,))
                
                updated_txn = cursor.fetchone()
                
                return jsonify({
                    'success': True,
                    'status': updated_txn['status'],
                    'transaction': {
                        'txn_id': updated_txn['txn_id'],
                        'amount': float(updated_txn['amount']),
                        'charge_amount': float(updated_txn['charge_amount']),
                        'total_deduction': float(updated_txn['total_deduction']),
                        'status': updated_txn['status'],
                        'pg_txn_id': updated_txn.get('pg_txn_id'),
                        'utr': updated_txn.get('utr'),
                        'created_at': updated_txn['created_at'].isoformat() if updated_txn.get('created_at') else None,
                        'completed_at': updated_txn['completed_at'].isoformat() if updated_txn.get('completed_at') else None
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check payout status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@mudrape_payout_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_payout_transactions():
    """Get all payout transactions for merchant"""
    try:
        current_merchant = get_jwt_identity()
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status')
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Build query
                query = """
                    SELECT txn_id, amount, charge_amount, total_deduction,
                           status, payout_mode, beneficiary_name, beneficiary_account,
                           created_at, completed_at, utr
                    FROM payout_transactions
                    WHERE merchant_id = %s AND pg_partner = 'Mudrape'
                """
                params = [current_merchant]
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                transactions = cursor.fetchall()
                
                # Get total count
                count_query = "SELECT COUNT(*) as total FROM payout_transactions WHERE merchant_id = %s AND pg_partner = 'Mudrape'"
                count_params = [current_merchant]
                
                if status:
                    count_query += " AND status = %s"
                    count_params.append(status)
                
                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['total']
                
                # Format dates and decimals
                for txn in transactions:
                    if txn.get('created_at'):
                        txn['created_at'] = txn['created_at'].isoformat()
                    if txn.get('completed_at'):
                        txn['completed_at'] = txn['completed_at'].isoformat()
                    txn['amount'] = float(txn['amount'])
                    txn['charge_amount'] = float(txn['charge_amount'])
                    txn['total_deduction'] = float(txn['total_deduction'])
                
                return jsonify({
                    'success': True,
                    'transactions': transactions,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get payout transactions error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
