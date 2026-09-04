"""
Transaction Logs Routes
Provides API response details for payin and payout transactions
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database_pooled import get_db_connection
import json
from datetime import datetime

transaction_logs_bp = Blueprint('transaction_logs', __name__)


@transaction_logs_bp.route('/api/admin/transaction-logs/payin/<txn_id>', methods=['GET'])
@jwt_required()
def get_payin_transaction_logs(txn_id):
    """
    Get complete API logs for a payin transaction
    Returns merchant request, gateway request/response, callback data
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute("""
            SELECT 
                pt.*,
                m.full_name as merchant_name,
                m.merchant_id
            FROM payin_transactions pt
            LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
            WHERE pt.txn_id = %s
        """, (txn_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Parse JSON fields safely
        def safe_parse_json(data):
            if not data:
                return None
            if isinstance(data, dict):
                return data
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except:
                    return {'raw': data}
            return None
        
        merchant_request = safe_parse_json(transaction.get('request_payload'))
        gateway_request = safe_parse_json(transaction.get('pg_request'))
        gateway_response = safe_parse_json(transaction.get('pg_response'))
        callback_request = safe_parse_json(transaction.get('callback_data'))
        callback_response = safe_parse_json(transaction.get('callback_response'))
        
        # Check if callback was forwarded
        callback_forwarded = bool(transaction.get('callback_forwarded_at'))
        
        # Build response
        logs = {
            'transaction_id': txn_id,
            'merchant_id': transaction.get('merchant_id'),
            'merchant_name': transaction.get('merchant_name'),
            'status': transaction.get('status'),
            'amount': float(transaction.get('amount', 0)),
            'service_name': transaction.get('pg_partner', 'Unknown'),
            'created_at': transaction.get('created_at').isoformat() if transaction.get('created_at') else None,
            
            # Merchant Request (what merchant sent to us)
            'merchant_request': merchant_request or {
                'amount': transaction.get('amount'),
                'order_id': transaction.get('order_id'),
                'payee_name': transaction.get('payee_name'),
                'payee_mobile': transaction.get('payee_mobile'),
                'payee_email': transaction.get('payee_email')
            },
            
            # Gateway Request (what we sent to payment gateway)
            'gateway_request': gateway_request,
            
            # Gateway Response (what payment gateway sent back)
            'gateway_response': gateway_response,
            
            # Callback from Gateway (webhook from payment gateway)
            'callback_from_gateway': callback_request,
            
            # Callback to Merchant
            'callback_to_merchant': {
                'forwarded': callback_forwarded,
                'forwarded_at': transaction.get('callback_forwarded_at').isoformat() if transaction.get('callback_forwarded_at') else None,
                'merchant_callback_url': transaction.get('callback_url'),
                'response': callback_response,
                'payload_sent': {
                    'txn_id': txn_id,
                    'order_id': transaction.get('order_id'),
                    'status': transaction.get('status'),
                    'amount': transaction.get('amount'),
                    'utr': transaction.get('utr') or transaction.get('bank_ref_no'),
                    'pg_txn_id': transaction.get('pg_txn_id')
                }
            },
            
            # Additional Info
            'additional_info': {
                'pg_txn_id': transaction.get('pg_txn_id'),
                'utr': transaction.get('utr'),
                'bank_ref_no': transaction.get('bank_ref_no'),
                'payment_mode': transaction.get('payment_mode'),
                'error_message': transaction.get('error_message'),
                'remarks': transaction.get('remarks')
            },
            
            # Data availability status
            'data_status': {
                'has_request_payload': bool(merchant_request),
                'has_gateway_request': bool(gateway_request),
                'has_gateway_response': bool(gateway_response),
                'has_callback_data': bool(callback_request),
                'has_callback_response': bool(callback_response)
            }
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs
        })
        
    except Exception as e:
        print(f"Error fetching payin logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching logs: {str(e)}'
        }), 500


@transaction_logs_bp.route('/api/admin/transaction-logs/payout/<txn_id>', methods=['GET'])
@jwt_required()
def get_payout_transaction_logs(txn_id):
    """
    Get complete API logs for a payout transaction
    Returns request, gateway request/response, callback data
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get transaction details
        cursor.execute("""
            SELECT 
                pt.*,
                m.full_name as merchant_name,
                m.merchant_id
            FROM payout_transactions pt
            LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
            WHERE pt.txn_id = %s
        """, (txn_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Parse JSON fields safely
        def safe_parse_json(data):
            if not data:
                return None
            if isinstance(data, dict):
                return data
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except:
                    return {'raw': data}
            return None
        
        request_payload = safe_parse_json(transaction.get('request_payload'))
        gateway_request = safe_parse_json(transaction.get('pg_request'))
        gateway_response = safe_parse_json(transaction.get('pg_response'))
        callback_request = safe_parse_json(transaction.get('callback_data'))
        callback_response = safe_parse_json(transaction.get('callback_response'))
        
        # Check if callback was forwarded
        callback_forwarded = bool(transaction.get('callback_forwarded_at'))
        
        # Determine payer
        if transaction.get('merchant_id'):
            payer_name = transaction.get('merchant_name', 'Unknown Merchant')
            payer_id = transaction.get('merchant_id')
            payer_type = 'merchant'
        else:
            payer_name = f"Admin ({transaction.get('admin_id', 'Unknown')})"
            payer_id = transaction.get('admin_id')
            payer_type = 'admin'
        
        # Build response
        logs = {
            'transaction_id': txn_id,
            'payer_id': payer_id,
            'payer_name': payer_name,
            'payer_type': payer_type,
            'status': transaction.get('status'),
            'amount': float(transaction.get('amount', 0)),
            'pg_partner': transaction.get('pg_partner', 'Unknown'),
            'created_at': transaction.get('created_at').isoformat() if transaction.get('created_at') else None,
            
            # Request Payload (what was sent to us)
            'request_payload': request_payload or {
                'amount': transaction.get('amount'),
                'order_id': transaction.get('order_id'),
                'bene_name': transaction.get('bene_name'),
                'bene_mobile': transaction.get('bene_mobile'),
                'account_no': transaction.get('account_no'),
                'ifsc_code': transaction.get('ifsc_code'),
                'vpa': transaction.get('vpa'),
                'payment_type': transaction.get('payment_type')
            },
            
            # Gateway Request (what we sent to payment gateway)
            'gateway_request': gateway_request,
            
            # Gateway Response (what payment gateway sent back)
            'gateway_response': gateway_response,
            
            # Callback from Gateway (webhook from payment gateway)
            'callback_from_gateway': callback_request,
            
            # Callback to Merchant (if merchant payout)
            'callback_to_merchant': {
                'forwarded': callback_forwarded,
                'forwarded_at': transaction.get('callback_forwarded_at').isoformat() if transaction.get('callback_forwarded_at') else None,
                'merchant_callback_url': transaction.get('callback_url'),
                'response': callback_response,
                'payload_sent': {
                    'txn_id': txn_id,
                    'order_id': transaction.get('order_id'),
                    'status': transaction.get('status'),
                    'amount': transaction.get('amount'),
                    'utr': transaction.get('utr') or transaction.get('bank_ref_no'),
                    'reference_id': transaction.get('reference_id')
                } if transaction.get('merchant_id') else None
            },
            
            # Additional Info
            'additional_info': {
                'reference_id': transaction.get('reference_id'),
                'pg_txn_id': transaction.get('pg_txn_id'),
                'utr': transaction.get('utr'),
                'bank_ref_no': transaction.get('bank_ref_no'),
                'payment_type': transaction.get('payment_type'),
                'error_message': transaction.get('error_message'),
                'remarks': transaction.get('remarks'),
                'name_with_bank': transaction.get('name_with_bank'),
                'name_match_score': transaction.get('name_match_score')
            },
            
            # Data availability status
            'data_status': {
                'has_request_payload': bool(request_payload),
                'has_gateway_request': bool(gateway_request),
                'has_gateway_response': bool(gateway_response),
                'has_callback_data': bool(callback_request),
                'has_callback_response': bool(callback_response)
            }
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs
        })
        
    except Exception as e:
        print(f"Error fetching payout logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching logs: {str(e)}'
        }), 500
