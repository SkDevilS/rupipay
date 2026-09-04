from flask import Blueprint, request, jsonify
import logging
from rang_service import RangService
from database import get_db_connection
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rang_bp = Blueprint('rang', __name__)
rang_service = RangService()

@rang_bp.route('/create-rang-order', methods=['POST'])
def create_rang_order():
    """Create Rang payin order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['merchant_id', 'orderid', 'amount', 'payee_fname', 'payee_email', 'payee_mobile', 'scheme_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Amount must be greater than 0'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid amount format'
            }), 400
        
        # Check if order already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id FROM payin_transactions 
            WHERE merchant_id = %s AND order_id = %s AND pg_partner = 'Rang'
        """, (data['merchant_id'], data['orderid']))
        
        existing_order = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if existing_order:
            return jsonify({
                'success': False,
                'message': 'Order ID already exists'
            }), 400
        
        # Create order with Rang
        result = rang_service.create_payin_order(data['merchant_id'], data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating Rang order: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@rang_bp.route('/check-rang-status/<txn_id>', methods=['GET'])
def check_rang_status(txn_id):
    """Check Rang payment status by transaction ID"""
    try:
        # Get transaction from database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM payin_transactions 
            WHERE txn_id = %s AND pg_partner = 'Rang'
        """, (txn_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Check status with Rang API
        status_result = rang_service.check_payment_status(txn_id)
        
        if status_result['success']:
            # Update transaction status based on response
            # Note: You may need to adjust this based on Rang's actual response format
            status_data = status_result['data']
            
            cursor.execute("""
                UPDATE payin_transactions 
                SET updated_at = NOW()
                WHERE txn_id = %s
            """, (txn_id,))
            
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'transaction': transaction,
            'status_check': status_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking Rang status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@rang_bp.route('/check-rang-status-by-order/<order_id>', methods=['GET'])
def check_rang_status_by_order(order_id):
    """Check Rang payment status by order ID"""
    try:
        # Get transaction from database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM payin_transactions 
            WHERE order_id = %s AND pg_partner = 'Rang'
            ORDER BY created_at DESC LIMIT 1
        """, (order_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Check status with Rang API using txn_id
        status_result = rang_service.check_payment_status(transaction['txn_id'])
        
        if status_result['success']:
            # Update transaction status based on response
            status_data = status_result['data']
            
            cursor.execute("""
                UPDATE payin_transactions 
                SET updated_at = NOW()
                WHERE txn_id = %s
            """, (transaction['txn_id'],))
            
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'transaction': transaction,
            'status_check': status_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking Rang status by order: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500