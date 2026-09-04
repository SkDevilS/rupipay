"""
Vega Callback Routes
Handles callbacks from Vega payment gateway and forwards them to merchants
"""

from flask import Blueprint, request, jsonify
import json
import requests
from database import get_db_connection
from datetime import datetime

vega_callback_bp = Blueprint('vega_callback', __name__, url_prefix='/api/callback')

@vega_callback_bp.route('/vega/payin', methods=['POST'])
def vega_payin_callback():
    """
    Webhook endpoint for Vega payin status updates
    Vega will call this when payin status changes
    """
    try:
        print("=" * 80)
        print("Vega Payin Callback Received")
        print("=" * 80)
        
        # Log request details
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        # Get callback data - support both JSON and form-data
        callback_data = None
        
        if request.is_json:
            # JSON payload
            callback_data = request.json
            print("Received as JSON")
        elif request.form:
            # Form data
            callback_data = request.form.to_dict()
            print("Received as Form Data")
        elif request.data:
            # Raw data - try to parse as JSON
            try:
                callback_data = json.loads(request.data.decode('utf-8'))
                print("Received as Raw Data (parsed as JSON)")
            except:
                print(f"Raw Data (could not parse): {request.data}")
                return jsonify({'success': False, 'message': 'Invalid data format'}), 400
        else:
            print("ERROR: No data received")
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        print(f"Callback Data: {json.dumps(callback_data, indent=2)}")
        
        # Extract data from Vega callback
        # Vega uses similar format to Mudrape since it's founded by Mudrape team
        track_id = (callback_data.get('trackID') or 
                   callback_data.get('track_id') or
                   callback_data.get('ref_id') or 
                   callback_data.get('refId'))
        txn_id = (callback_data.get('txn_id') or 
                  callback_data.get('txnId') or
                  callback_data.get('orderId'))
        status = callback_data.get('status')
        utr = (callback_data.get('utr') or 
               callback_data.get('UTR') or
               callback_data.get('bankRefNo') or
               callback_data.get('bank_ref_no'))
        amount = callback_data.get('amount')
        currency = callback_data.get('currency', 'INR')
        timestamp = callback_data.get('timestamp', '')
        
        if not track_id:
            print("ERROR: No trackID/track_id/ref_id in callback")
            return jsonify({'success': False, 'message': 'Missing trackID/track_id/ref_id'}), 400
        
        print(f"Track ID: {track_id}")
        print(f"TXN ID: {txn_id}")
        print(f"Status: {status}")
        print(f"UTR: {utr}")
        print(f"Amount: {amount}")
        print(f"Currency: {currency}")
        print(f"Timestamp: {timestamp}")
        
        # Map status
        if status and status.upper() == 'SUCCESS':
            mapped_status = 'SUCCESS'
        elif status and status.upper() == 'FAILED':
            mapped_status = 'FAILED'
        else:
            mapped_status = 'INITIATED'
        
        print(f"Mapped Status: {mapped_status}")
        
        # Update database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by order_id (which is the track_id for Vega)
                cursor.execute("""
                    SELECT txn_id, status, merchant_id, amount as txn_amount, net_amount, charge_amount, callback_url
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'Vega'
                """, (track_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Vega transaction not found for track_id: {track_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # Update transaction
                if mapped_status == 'SUCCESS':
                    # Check if wallet has already been credited (idempotency check)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn['txn_id'],))
                    
                    wallet_credit_exists = cursor.fetchone()['count'] > 0
                    
                    if wallet_credit_exists:
                        print(f"⚠ Wallet already credited for this transaction - skipping wallet credit")
                        print(f"  This is a duplicate callback from Vega")
                        
                        # Just update transaction status and UTR if needed
                        if txn['status'] != 'SUCCESS':
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = %s, bank_ref_no = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE order_id = %s
                            """, (mapped_status, utr, txn_id, track_id))
                            conn.commit()
                            print(f"✓ Updated transaction status to SUCCESS")
                        elif utr and utr != txn.get('bank_ref_no'):
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE order_id = %s
                            """, (utr, txn_id, track_id))
                            conn.commit()
                            print(f"✓ Updated UTR: {utr}")
                    else:
                        # First time processing SUCCESS - credit unsettled wallet
                        print(f"Processing SUCCESS callback - crediting unsettled wallet")
                        
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = %s, pg_txn_id = %s, bank_ref_no = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE order_id = %s
                        """, (mapped_status, txn_id, utr, track_id))
                        
                        # Get net amount and charge amount
                        net_amount = float(txn['net_amount']) if txn['net_amount'] else float(txn['txn_amount'])
                        charge_amount = float(txn['charge_amount']) if txn['charge_amount'] else 0.00
                        
                        # Get current unsettled balance
                        cursor.execute("""
                            SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        wallet_result = cursor.fetchone()
                        
                        if wallet_result:
                            unsettled_before = float(wallet_result['unsettled_balance'])
                            unsettled_after = unsettled_before + net_amount
                            
                            cursor.execute("""
                                UPDATE merchant_wallet
                                SET unsettled_balance = %s, last_updated = NOW()
                                WHERE merchant_id = %s
                            """, (unsettled_after, txn['merchant_id']))
                        else:
                            # Create wallet if doesn't exist
                            cursor.execute("""
                                INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                                VALUES (%s, 0.00, 0.00, %s)
                            """, (txn['merchant_id'], net_amount))
                            unsettled_before = 0.00
                            unsettled_after = net_amount
                        
                        # Record merchant wallet transaction
                        from wallet_service import wallet_service
                        wallet_txn_id = wallet_service.generate_txn_id('MWT')
                        cursor.execute("""
                            INSERT INTO merchant_wallet_transactions
                            (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                            VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                        """, (
                            txn['merchant_id'], 
                            wallet_txn_id, 
                            net_amount,
                            unsettled_before,
                            unsettled_after,
                            f"Vega Payin credited to unsettled wallet - {track_id}",
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Merchant unsettled wallet credited: {net_amount}")
                        
                        # Credit admin unsettled wallet with charge amount
                        cursor.execute("""
                            SELECT unsettled_balance FROM admin_wallet WHERE admin_id = 'admin'
                        """, ())
                        admin_wallet_result = cursor.fetchone()
                        
                        if admin_wallet_result:
                            admin_unsettled_before = float(admin_wallet_result['unsettled_balance'])
                            admin_unsettled_after = admin_unsettled_before + charge_amount
                            
                            cursor.execute("""
                                UPDATE admin_wallet
                                SET unsettled_balance = %s, last_updated = NOW()
                                WHERE admin_id = 'admin'
                            """, (admin_unsettled_after,))
                        else:
                            # Create admin wallet if doesn't exist
                            cursor.execute("""
                                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                                VALUES ('admin', 0.00, %s)
                            """, (charge_amount,))
                            admin_unsettled_before = 0.00
                            admin_unsettled_after = charge_amount
                        
                        # Record admin wallet transaction
                        admin_wallet_txn_id = wallet_service.generate_txn_id('AWT')
                        cursor.execute("""
                            INSERT INTO admin_wallet_transactions
                            (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                            VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                        """, (
                            'admin',
                            admin_wallet_txn_id,
                            charge_amount,
                            admin_unsettled_before,
                            admin_unsettled_after,
                            f"Vega Payin charge - {track_id}",
                            txn['txn_id']
                        ))
                        
                        print(f"✓ Admin unsettled wallet credited: {charge_amount}")
                        
                        conn.commit()
                else:
                    # FAILED or other status - just update transaction
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, bank_ref_no = %s, updated_at = NOW()
                        WHERE order_id = %s
                    """, (mapped_status, txn_id, utr, track_id))
                    
                    conn.commit()
                
                print("=" * 80)
                print("Vega callback processed successfully")
                print("=" * 80)
                
                # Forward callback to merchant
                forward_callback_to_merchant(cursor, txn, callback_data, mapped_status, track_id, utr, txn_id)
                
                return jsonify({'success': True, 'message': 'Callback processed successfully'})
                
        except Exception as e:
            print(f"ERROR processing callback: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"ERROR in Vega callback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


def forward_callback_to_merchant(cursor, txn, original_callback_data, status, track_id, utr, txn_id):
    """
    Forward callback to merchant's callback URL
    """
    print("=" * 80)
    print("MERCHANT CALLBACK FORWARDING - VEGA")
    print("=" * 80)
    
    try:
        callback_url = None
        
        # Get callback URL from transaction
        if txn.get('callback_url'):
            callback_url = txn['callback_url'].strip()
            if not callback_url:  # Empty string after strip
                callback_url = None
        
        print(f"Step 1: Transaction callback_url from DB: {callback_url if callback_url else 'NOT SET'}")
        
        # If no callback URL in transaction, check merchant_callbacks table
        if not callback_url:
            print(f"Step 2: Checking merchant_callbacks table for merchant: {txn['merchant_id']}")
            cursor.execute("""
                SELECT payin_callback_url FROM merchant_callbacks
                WHERE merchant_id = %s
            """, (txn['merchant_id'],))
            
            merchant_callback = cursor.fetchone()
            
            if merchant_callback and merchant_callback.get('payin_callback_url'):
                callback_url = merchant_callback['payin_callback_url'].strip()
                if not callback_url:  # Empty string after strip
                    callback_url = None
                print(f"Found merchant callback URL: {callback_url}")
            else:
                print("No callback URL found in merchant_callbacks table")
        
        if not callback_url:
            print("❌ No callback URL configured - skipping merchant callback")
            return
        
        print(f"✓ Using callback URL: {callback_url}")
        
        # Prepare callback payload for merchant
        # Use standard format that merchants expect
        merchant_callback_data = {
            'status': status,
            'txnid': track_id,  # Use track_id as txnid (this is what merchant sent as orderid)
            'amount': str(txn['txn_amount']),
            'productinfo': 'Payment',
            'firstname': '',  # We don't store this separately
            'email': '',      # We don't store this separately
            'phone': '',      # We don't store this separately
            'utr': utr or '',
            'pg_txn_id': txn_id or '',
            'pg_partner': 'Vega',
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Merchant callback payload: {json.dumps(merchant_callback_data, indent=2)}")
        
        # Send callback to merchant
        print(f"Sending callback to: {callback_url}")
        
        response = requests.post(
            callback_url,
            json=merchant_callback_data,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Merchant callback response status: {response.status_code}")
        print(f"Merchant callback response: {response.text}")
        
        # Log callback attempt
        cursor.execute("""
            INSERT INTO callback_logs (
                txn_id, merchant_id, callback_url, callback_data, 
                response_status, response_data, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            txn['txn_id'],
            txn['merchant_id'],
            callback_url,
            json.dumps(merchant_callback_data),
            response.status_code,
            response.text[:1000]  # Limit response data length
        ))
        
        if response.status_code == 200:
            print("✅ Merchant callback sent successfully")
        else:
            print(f"⚠ Merchant callback failed with status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ Merchant callback timeout")
        # Log timeout
        cursor.execute("""
            INSERT INTO callback_logs (
                txn_id, merchant_id, callback_url, callback_data, 
                response_status, response_data, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            txn['txn_id'],
            txn['merchant_id'],
            callback_url,
            json.dumps(merchant_callback_data),
            0,
            'TIMEOUT'
        ))
    except Exception as e:
        print(f"❌ Merchant callback error: {e}")
        # Log error
        cursor.execute("""
            INSERT INTO callback_logs (
                txn_id, merchant_id, callback_url, callback_data, 
                response_status, response_data, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            txn['txn_id'],
            txn['merchant_id'],
            callback_url,
            json.dumps(merchant_callback_data),
            -1,
            str(e)[:1000]
        ))