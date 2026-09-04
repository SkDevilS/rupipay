"""
Airpay Grosmart2 V4 Callback Routes
Handles Airpay Grosmart2 IPN (Instant Payment Notification) callbacks with encryption
Uses separate credentials and callback URL from original Airpay
"""

from flask import Blueprint, request, jsonify
from airpay_service import airpay_grosmart2_service
from database import get_db_connection
import json
import os
import requests
from datetime import datetime

airpay_grosmart2_callback_bp = Blueprint('airpay_grosmart2_callback', __name__, url_prefix='/api/callback/airpay/grosmart2')

def log_raw_callback_data(request):
    """Log raw callback data to file for debugging"""
    try:
        log_dir = '/var/www/moneyone/moneyone/backend/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'airpay_grosmart2_callbacks_{datetime.now().strftime("%Y%m%d")}.log')
        
        with open(log_file, 'a') as f:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"METHOD: {request.method}\n")
            f.write(f"URL: {request.url}\n")
            f.write(f"CONTENT-TYPE: {request.content_type}\n")
            f.write("-" * 100 + "\n")
            
            # Headers
            f.write("HEADERS:\n")
            for key, value in request.headers.items():
                f.write(f"  {key}: {value}\n")
            
            # Form data
            if request.form:
                f.write("\nFORM DATA:\n")
                for key, value in request.form.items():
                    f.write(f"  {key}: {value[:200] if len(str(value)) > 200 else value}\n")
            
            # JSON data
            try:
                if request.is_json:
                    json_data = request.get_json()
                    f.write("\nJSON DATA:\n")
                    f.write(json.dumps(json_data, indent=2))
            except:
                pass
            
            # Raw data
            try:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    f.write("\nRAW DATA:\n")
                    f.write(raw_data[:1000])  # First 1000 chars
            except:
                pass
            
            f.write("\n" + "=" * 100 + "\n")
        
        print(f"✓ Callback logged to: {log_file}")
    except Exception as e:
        print(f"Error logging callback: {e}")

@airpay_grosmart2_callback_bp.route('/payin', methods=['POST'])
def airpay_grosmart2_payin_callback():
    """
    Handle Airpay Grosmart2 V4 payin callback (IPN)
    According to documentation, Airpay sends encrypted JSON data
    """
    try:
        # Log everything to file for debugging
        log_raw_callback_data(request)
        
        print("=" * 80)
        print("Airpay Grosmart2 V4 Payin Callback Received")
        print("=" * 80)
        print(f"Headers: {dict(request.headers)}")
        print(f"Content-Type: {request.content_type}")
        print(f"Method: {request.method}")
        
        # Get callback data
        if request.content_type == 'application/json' or request.is_json:
            callback_data = request.get_json()
        else:
            callback_data = request.form.to_dict()
        
        print(f"Raw callback data: {json.dumps(callback_data, indent=2)}")
        
        if not callback_data:
            print("ERROR: No callback data received")
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        # Check if callback is encrypted (has 'response' field with encrypted data)
        if 'response' in callback_data and 'merchant_id' in callback_data:
            print(f"Callback is ENCRYPTED - decrypting...")
            encrypted_response = callback_data.get('response')
            
            # Decrypt the response using Grosmart2 service
            decrypted_data = airpay_grosmart2_service.decrypt_data(encrypted_response)
            
            if not decrypted_data:
                print("ERROR: Failed to decrypt callback data")
                return jsonify({'success': False, 'message': 'Decryption failed'}), 400
            
            print(f"Decrypted callback data: {json.dumps(decrypted_data, indent=2)}")
            
            # Extract the actual callback data from decrypted response
            if 'data' in decrypted_data and isinstance(decrypted_data['data'], dict):
                callback_data = decrypted_data['data']
                print(f"✓ Extracted transaction data from 'data' field")
            else:
                callback_data = decrypted_data
                print(f"✓ Using decrypted data directly (no nested 'data' field)")
        
        # Extract key fields from callback according to IPN documentation
        merchant_id = callback_data.get('merchant_id')
        ap_transactionid = callback_data.get('ap_transactionid')
        amount = callback_data.get('amount')
        transaction_status = callback_data.get('transaction_status')
        orderid = callback_data.get('orderid')
        message = callback_data.get('message', '')
        
        # Multiple possible field names for RRN/UTR
        rrn = (callback_data.get('rrn') or 
               callback_data.get('utr_no') or 
               callback_data.get('bank_ref_no'))
        
        # Payment channel
        chmod = callback_data.get('chmod', 'upi')
        
        # Custom variables
        customvar = callback_data.get('customvar', '')
        
        # Additional fields from IPN callback
        customer_vpa = callback_data.get('customer_vpa', '')
        transaction_payment_status = callback_data.get('transaction_payment_status', '')
        transaction_time = callback_data.get('transaction_time', '')
        
        print(f"Parsed Callback:")
        print(f"  Merchant ID: {merchant_id}")
        print(f"  Order ID: {orderid}")
        print(f"  Airpay Txn ID: {ap_transactionid}")
        print(f"  Transaction Status: {transaction_status}")
        print(f"  Payment Status: {transaction_payment_status}")
        print(f"  Amount: ₹{amount}")
        print(f"  RRN/UTR: {rrn}")
        print(f"  Payment Channel: {chmod}")
        print(f"  Customer VPA: {customer_vpa}")
        print(f"  Custom Var: {customvar}")
        
        if not orderid:
            print("ERROR: Missing order_id in callback")
            return jsonify({'success': False, 'message': 'Missing order_id'}), 400
        
        # Find transaction in database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Try to extract txn_id from customvar first (more reliable)
                txn_id_from_customvar = None
                if customvar and 'txn_id=' in customvar:
                    try:
                        parts = customvar.split('|')
                        for part in parts:
                            if part.startswith('txn_id='):
                                txn_id_from_customvar = part.split('txn_id=', 1)[1]
                                print(f"✓ Extracted txn_id from customvar: {txn_id_from_customvar}")
                                break
                    except Exception as e:
                        print(f"ERROR parsing txn_id from customvar: {e}")
                
                # Find transaction by txn_id (from customvar) or order_id (with LIKE for partial match)
                if txn_id_from_customvar:
                    cursor.execute("""
                        SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status
                        FROM payin_transactions
                        WHERE txn_id = %s AND pg_partner = 'Airpay_Grosmart2'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (txn_id_from_customvar,))
                else:
                    # Fallback: Try exact match first, then partial match
                    cursor.execute("""
                        SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status
                        FROM payin_transactions
                        WHERE (order_id = %s OR order_id LIKE %s) AND pg_partner = 'Airpay_Grosmart2'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (orderid, f"{orderid}%"))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for order_id: {orderid}")
                    if txn_id_from_customvar:
                        print(f"  Also tried txn_id: {txn_id_from_customvar}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # Map Airpay status to our status
                # According to documentation:
                # 200 - Transaction is success
                # 211 - Transaction is processing
                # 400 - Transaction is failed
                # 401 - Transaction will not register properly
                # 402 - Payment that has not yet been processed
                # 403 - Not received any call back from bank
                # 405 - Transaction has bounced
                # 503 - No records found
                if transaction_status == 200:
                    new_status = 'SUCCESS'
                elif transaction_status == 211:
                    new_status = 'PROCESSING'
                elif transaction_status in [400, 401, 402, 403, 405]:
                    new_status = 'FAILED'
                elif transaction_status == 503:
                    new_status = 'NOT_FOUND'
                else:
                    new_status = 'INITIATED'
                
                print(f"Mapped Status: {transaction_status} -> {new_status}")
                
                # Extract payment mode
                payment_mode = chmod.upper() if chmod else 'UPI'
                
                # Update transaction
                if new_status in ['SUCCESS', 'FAILED']:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s,
                            pg_txn_id = %s,
                            bank_ref_no = %s,
                            payment_mode = %s,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
                else:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s,
                            pg_txn_id = %s,
                            bank_ref_no = %s,
                            payment_mode = %s,
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
                
                print(f"✓ Updated transaction status to {new_status}")
                
                # If successful, credit wallets
                if new_status == 'SUCCESS':
                    # Check if wallet already credited (idempotency)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn['txn_id'],))
                    
                    wallet_already_credited = cursor.fetchone()['count'] > 0
                    
                    if not wallet_already_credited:
                        print(f"Crediting wallets for successful payment")
                        
                        # Credit merchant unsettled wallet
                        from wallet_service import wallet_service as wallet_svc
                        wallet_result = wallet_svc.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=float(txn['net_amount']),
                            description=f"Airpay Grosmart2 Payin credited to unsettled wallet - {orderid}",
                            reference_id=txn['txn_id']
                        )
                        
                        if wallet_result['success']:
                            print(f"✓ Merchant unsettled wallet credited: ₹{txn['net_amount']}")
                        else:
                            print(f"✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                        
                        # Credit admin unsettled wallet
                        admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=float(txn['charge_amount']),
                            description=f"Airpay Grosmart2 Payin charge - {orderid}",
                            reference_id=txn['txn_id']
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✓ Admin unsettled wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"⚠ Wallet already credited for this transaction - skipping")
                
                conn.commit()
                
                # Forward callback to merchant
                # Extract callback URL from customvar field
                merchant_callback_url = None
                
                if customvar and 'callback_url=' in customvar:
                    try:
                        # customvar format: "merchant_id=XXX|txn_id=YYY|callback_url=https://..."
                        parts = customvar.split('|')
                        for part in parts:
                            if part.startswith('callback_url='):
                                merchant_callback_url = part.split('callback_url=', 1)[1]
                                print(f"✓ Extracted callback URL from customvar: {merchant_callback_url}")
                                break
                    except Exception as e:
                        print(f"ERROR parsing customvar: {e}")
                
                # If not in customvar, no callback URL available
                if not merchant_callback_url:
                    print(f"⚠ No callback URL found in customvar field")
                
                if merchant_callback_url:
                    try:
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'order_id': orderid,
                            'status': new_status,
                            'amount': str(txn['amount']),
                            'net_amount': str(txn['net_amount']),
                            'charge_amount': str(txn['charge_amount']),
                            'utr': rrn,
                            'pg_txn_id': ap_transactionid,
                            'payment_mode': payment_mode,
                            'pg_partner': 'Airpay_Grosmart2',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(f"Forwarding callback to merchant: {merchant_callback_url}")
                        print(f"Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                        
                        try:
                            callback_response = requests.post(
                                merchant_callback_url,
                                json=merchant_callback_data,
                                headers={'Content-Type': 'application/json'},
                                timeout=10
                            )
                            
                            print(f"Merchant callback response: {callback_response.status_code}")
                            
                            # Log callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                merchant_callback_url,
                                json.dumps(merchant_callback_data),
                                callback_response.status_code,
                                callback_response.text[:1000]
                            ))
                            conn.commit()
                            
                            print(f"✓ Merchant callback sent successfully")
                            
                        except requests.exceptions.RequestException as e:
                            print(f"ERROR: Failed to send merchant callback: {e}")
                            
                            # Log failed callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                merchant_callback_url,
                                json.dumps(merchant_callback_data),
                                0,
                                str(e)[:1000]
                            ))
                            conn.commit()
                    except Exception as e:
                        print(f"ERROR in merchant callback forwarding: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("⚠ No merchant callback URL found (not in customvar or merchant_callbacks table)")
                
                print("=" * 80)
                print("Callback processed successfully")
                print("=" * 80)
                
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully',
                    'txn_id': txn['txn_id'],
                    'status': new_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"ERROR in callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@airpay_grosmart2_callback_bp.route('/test', methods=['GET', 'POST'])
def test_airpay_grosmart2_callback():
    """Test endpoint for Airpay Grosmart2 callback"""
    try:
        print(f"=== Airpay Grosmart2 Test Callback ===")
        print(f"Method: {request.method}")
        print(f"Headers: {dict(request.headers)}")
        
        if request.method == 'POST':
            if request.content_type == 'application/json':
                data = request.get_json()
            else:
                data = request.form.to_dict()
            print(f"Data: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Test callback received',
            'method': request.method,
            'headers': dict(request.headers),
            'data': data if request.method == 'POST' else None
        }), 200
        
    except Exception as e:
        print(f"Test callback error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
