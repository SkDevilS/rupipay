from flask import Blueprint, request, jsonify
from database import get_db_connection
from payu_payout_service import payu_payout_service
import json
from datetime import datetime

payu_webhook_bp = Blueprint('payu_webhook', __name__)

# PayU IP addresses for webhook validation
PAYU_IPS = [
    '180.179.168.225',
    '13.71.57.148',
    '52.140.8.68',
    '180.179.174.1',
    '180.179.165.250',
    '13.235.110.253'
]

def validate_payu_ip():
    """Validate if request is from PayU IP"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    # In development, allow all IPs
    # In production, uncomment the following lines
    # if client_ip not in PAYU_IPS:
    #     return False
    return True

def log_webhook(event_type, merchant_ref_id, payu_ref_id, payload, status='RECEIVED', error_message=None):
    """Log webhook data"""
    try:
        connection = get_db_connection()
        if not connection:
            return
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO payu_webhook_logs 
                (event_type, merchant_ref_id, payu_ref_id, payload, status, error_message, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                event_type,
                merchant_ref_id,
                payu_ref_id,
                json.dumps(payload),
                status,
                error_message,
                datetime.now() if status == 'PROCESSED' else None
            ))
            connection.commit()
    except Exception as e:
        print(f"Error logging webhook: {e}")
    finally:
        if connection:
            connection.close()

@payu_webhook_bp.route('/payu/webhook/payout', methods=['POST'])
def payu_payout_webhook():
    """Handle PayU payout webhooks"""
    try:
        # Validate IP
        if not validate_payu_ip():
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized IP address'
            }), 403
        
        # Get webhook data
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({
                'status': 'error',
                'message': 'No data received'
            }), 400
        
        event = webhook_data.get('event')
        merchant_ref_id = webhook_data.get('merchantReferenceId')
        payu_ref_id = webhook_data.get('payuRefId')
        
        # Log webhook receipt
        log_webhook(event, merchant_ref_id, payu_ref_id, webhook_data, 'RECEIVED')
        
        # Process webhook based on event type
        if event in ['TRANSFER_SUCCESS', 'TRANSFER_FAILED', 'TRANSFER_REVERSED', 'REQUEST_PROCESSING_FAILED']:
            result = payu_payout_service.update_transaction_from_webhook(webhook_data)
            
            if result['success']:
                log_webhook(event, merchant_ref_id, payu_ref_id, webhook_data, 'PROCESSED')
                
                # Send callback to merchant if configured
                send_merchant_callback(merchant_ref_id, webhook_data)
                
                return jsonify({
                    'status': 'success',
                    'message': 'Webhook processed successfully'
                }), 200
            else:
                log_webhook(event, merchant_ref_id, payu_ref_id, webhook_data, 'FAILED', result.get('error'))
                return jsonify({
                    'status': 'error',
                    'message': result.get('error')
                }), 500
        
        elif event == 'DEPOSIT_SUCCESS':
            # Handle deposit success
            handle_deposit_webhook(webhook_data)
            log_webhook(event, None, None, webhook_data, 'PROCESSED')
            return jsonify({'status': 'success'}), 200
        
        elif event == 'LOW_BALANCE_ALERT':
            # Handle low balance alert
            handle_low_balance_webhook(webhook_data)
            log_webhook(event, None, None, webhook_data, 'PROCESSED')
            return jsonify({'status': 'success'}), 200
        
        elif event == 'SMART_SEND_DETAIL_SUBMITTED':
            # Handle smart send detail submission
            log_webhook(event, merchant_ref_id, None, webhook_data, 'PROCESSED')
            return jsonify({'status': 'success'}), 200
        
        elif event in ['SMART_SEND_EXPIRED', 'SMART_SEND_CANCELLED', 'SMART_SEND_REJECTED']:
            # Handle smart send status changes
            log_webhook(event, merchant_ref_id, None, webhook_data, 'PROCESSED')
            return jsonify({'status': 'success'}), 200
        
        elif event == 'BULK_SMART_SEND_FILE_PROCESSED':
            # Handle bulk smart send file processing
            log_webhook(event, None, None, webhook_data, 'PROCESSED')
            return jsonify({'status': 'success'}), 200
        
        else:
            log_webhook(event, merchant_ref_id, payu_ref_id, webhook_data, 'PROCESSED')
            return jsonify({
                'status': 'success',
                'message': 'Webhook received'
            }), 200
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def send_merchant_callback(merchant_ref_id, webhook_data):
    """Send callback to merchant"""
    try:
        connection = get_db_connection()
        if not connection:
            return
        
        with connection.cursor() as cursor:
            # Get transaction and merchant details
            cursor.execute("""
                SELECT pt.merchant_id, pt.txn_id, mc.payout_callback_url
                FROM payout_transactions pt
                LEFT JOIN merchant_callbacks mc ON pt.merchant_id = mc.merchant_id
                WHERE pt.reference_id = %s
            """, (merchant_ref_id,))
            
            result = cursor.fetchone()
            
            if result and result['payout_callback_url']:
                import requests
                
                callback_data = {
                    'txn_id': result['txn_id'],
                    'reference_id': merchant_ref_id,
                    'status': webhook_data.get('event'),
                    'payu_ref_id': webhook_data.get('payuRefId'),
                    'bank_ref_no': webhook_data.get('bankReferenceId'),
                    'message': webhook_data.get('msg'),
                    'timestamp': datetime.now().isoformat()
                }
                
                try:
                    response = requests.post(
                        result['payout_callback_url'],
                        json=callback_data,
                        timeout=10
                    )
                    
                    # Log callback
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        result['merchant_id'],
                        result['txn_id'],
                        result['payout_callback_url'],
                        json.dumps(callback_data),
                        response.status_code,
                        response.text
                    ))
                    connection.commit()
                except Exception as e:
                    print(f"Callback error: {e}")
    except Exception as e:
        print(f"Error sending merchant callback: {e}")
    finally:
        if connection:
            connection.close()

def handle_deposit_webhook(webhook_data):
    """Handle deposit success webhook"""
    try:
        connection = get_db_connection()
        if not connection:
            return
        
        with connection.cursor() as cursor:
            # Log deposit in admin wallet
            amount = float(webhook_data.get('amount', 0))
            transfer_id = webhook_data.get('transferId')
            
            # Update admin wallet main balance
            cursor.execute("""
                UPDATE admin_wallet 
                SET main_balance = main_balance + %s
                WHERE admin_id = 'admin'
            """, (amount,))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO admin_wallet_transactions 
                (admin_id, txn_id, wallet_type, txn_type, amount, balance_before, balance_after, description)
                SELECT 'admin', %s, 'MAIN', 'CREDIT', %s, 
                       main_balance - %s, main_balance, 
                       CONCAT('PayU Deposit - ', %s)
                FROM admin_wallet WHERE admin_id = 'admin'
            """, (transfer_id, amount, amount, transfer_id))
            
            connection.commit()
    except Exception as e:
        print(f"Error handling deposit webhook: {e}")
    finally:
        if connection:
            connection.close()

def handle_low_balance_webhook(webhook_data):
    """Handle low balance alert webhook"""
    try:
        # You can implement notification logic here
        # For example, send email/SMS to admin
        print(f"Low balance alert: {webhook_data.get('msg')}")
        print(f"Current balance: {webhook_data.get('currentBalance')}")
    except Exception as e:
        print(f"Error handling low balance webhook: {e}")

@payu_webhook_bp.route('/payu/webhook/config', methods=['GET'])
def get_webhook_config():
    """Get webhook configuration"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM payu_webhook_config WHERE is_active = TRUE")
            configs = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': configs
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@payu_webhook_bp.route('/payu/webhook/config', methods=['POST'])
def set_webhook_config():
    """Set webhook configuration"""
    try:
        data = request.get_json()
        event_type = data.get('event_type')
        webhook_url = data.get('webhook_url')
        
        if not event_type or not webhook_url:
            return jsonify({
                'success': False,
                'error': 'event_type and webhook_url are required'
            }), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO payu_webhook_config (event_type, webhook_url)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE webhook_url = %s, updated_at = NOW()
            """, (event_type, webhook_url, webhook_url))
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Webhook configuration saved'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@payu_webhook_bp.route('/payu/webhook/logs', methods=['GET'])
def get_webhook_logs():
    """Get webhook logs"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        event_type = request.args.get('event_type')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with connection.cursor() as cursor:
            query = "SELECT * FROM payu_webhook_logs"
            params = []
            
            if event_type:
                query += " WHERE event_type = %s"
                params.append(event_type)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM payu_webhook_logs"
            if event_type:
                count_query += " WHERE event_type = %s"
                cursor.execute(count_query, [event_type])
            else:
                cursor.execute(count_query)
            
            total = cursor.fetchone()['total']
            
            return jsonify({
                'success': True,
                'data': logs,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()
