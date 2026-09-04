"""
Paytouchpayin Callback Handler
Receives instant callbacks for payment success/failure
"""

from flask import Blueprint, request, jsonify
from database_pooled import get_db_connection
import json
from datetime import datetime
import requests

paytouchpayin_callback_bp = Blueprint('paytouchpayin_callback', __name__)

def log_callback_data(request, callback_data):
    """Log callback data for debugging"""
    try:
        print(f"\n{'='*80}")
        print(f"📥 PAYTOUCHPAYIN CALLBACK RECEIVED")
        print(f"{'='*80}")
        print(f"⏰ Timestamp: {datetime.now()}")
        print(f"🌐 IP Address: {request.remote_addr}")
        print(f"📋 Headers: {dict(request.headers)}")
        print(f"📦 Callback Data: {json.dumps(callback_data, indent=2)}")
        print(f"{'='*80}\n")
    except Exception as e:
        print(f"❌ Error logging callback: {str(e)}")


@paytouchpayin_callback_bp.route('/api/paytouchpayin/callback', methods=['POST'])
def paytouchpayin_callback():
    """
    Handle Paytouchpayin instant callback
    
    Success Callback:
    {
        "status": "success",
        "txnid": "4237534069070",
        "apitxnid": "DQR3281774329123961",
        "amount": 200.95,
        "charge": 2,
        "utr": "608373377074",
        "name": "vyapar.173506865983@hdfcbank",
        "mobile": "9123475501",
        "product": "dynamicqrpayin",
        "remark": "Dynamic QR Payin",
        "status_text": "success",
        "created_at": "2026-03-24 10:42:03",
        "updated_at": []
    }
    
    Failed Callback:
    {
        "status": "failed",
        "txnid": "QRSTC20260328M03491820",
        "apitxnid": "DQR3281774323420213",
        "amount": 105.14,
        "charge": 1.05,
        "utr": null,
        "name": "vyapar.173506865983@hdfcbank",
        "mobile": "9123475501",
        "product": "dynamicqrpayin",
        "remark": "QR Expired Automatically",
        "status_text": "failed",
        "created_at": "2026-03-24 09:07:00",
        "updated_at": []
    }
    """
    try:
        # Get callback data
        callback_data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Log callback
        log_callback_data(request, callback_data)
        
        # Extract callback fields
        status = callback_data.get('status', '').lower()
        txnid = callback_data.get('txnid')
        apitxnid = callback_data.get('apitxnid')
        amount = callback_data.get('amount')
        charge = callback_data.get('charge')
        utr = callback_data.get('utr')
        remark = callback_data.get('remark', '')
        status_text = callback_data.get('status_text', '')
        
        if not txnid:
            print(f"❌ Missing txnid in callback")
            return jsonify({'success': False, 'error': 'Missing txnid'}), 400
        
        # Find transaction in database (check both tables)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First try payin_transactions table (new structure)
        cursor.execute("""
            SELECT id, merchant_id, txn_id, order_id, amount, status, pg_partner
            FROM payin_transactions
            WHERE txn_id = %s AND pg_partner = 'paytouchpayin'
        """, (txnid,))
        
        transaction_row = cursor.fetchone()
        
        # If not found, try payin table (old structure)
        if not transaction_row:
            cursor.execute("""
                SELECT id, merchant_id, txn_id, order_id, amount, status, pg_partner
                FROM payin
                WHERE txn_id = %s AND pg_partner = 'paytouchpayin'
            """, (txnid,))
            transaction_row = cursor.fetchone()
            table_name = 'payin'
        else:
            table_name = 'payin_transactions'
        
        # Convert tuple to dict
        if transaction_row:
            transaction = {
                'id': transaction_row[0],
                'merchant_id': transaction_row[1],
                'txn_id': transaction_row[2],
                'order_id': transaction_row[3],
                'amount': transaction_row[4],
                'status': transaction_row[5],
                'pg_partner': transaction_row[6]
            }
        else:
            transaction = None
        
        if not transaction:
            print(f"❌ Transaction not found: {txnid}")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        merchant_id = transaction['merchant_id']
        current_status = transaction['status']
        
        print(f"✓ Transaction found: {txnid}")
        print(f"  Merchant: {merchant_id}")
        print(f"  Current Status: {current_status}")
        print(f"  Callback Status: {status}")
        
        # Prevent duplicate processing
        if current_status in ['success', 'failed']:
            print(f"⚠️ Transaction already processed with status: {current_status}")
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        # Map status
        if status == 'success':
            new_status = 'success'
        elif status == 'failed':
            new_status = 'failed'
        else:
            new_status = 'pending'
        
        # Update transaction
        cursor.execute("""
            UPDATE payin
            SET status = %s, utr = %s, remark = %s, updated_at = NOW()
            WHERE txn_id = %s
        """, (new_status, utr, remark, txnid))
        
        conn.commit()
        
        print(f"✅ Transaction updated: {txnid} -> {new_status}")
        
        # Credit unsettled wallet if success
        if new_status == 'success':
            payin_amount = float(transaction['amount'])
            
            cursor.execute("""
                UPDATE merchants
                SET unsettled_wallet = unsettled_wallet + %s
                WHERE merchant_id = %s
            """, (payin_amount, merchant_id))
            
            conn.commit()
            
            print(f"💰 Credited unsettled wallet: {merchant_id} + {payin_amount}")
            
            # Log transaction
            cursor.execute("""
                INSERT INTO transactions (
                    merchant_id, txn_type, amount, balance_after, 
                    reference_id, description, created_at
                )
                SELECT 
                    %s, 'payin_unsettled_credit', %s, unsettled_wallet,
                    %s, CONCAT('Payin credited (Unsettled) - ', %s), NOW()
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id, payin_amount, txnid, txnid, merchant_id))
            
            conn.commit()
        
        # Forward callback to merchant
        cursor.execute("""
            SELECT callback_url
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        merchant = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if merchant and merchant.get('callback_url'):
            callback_url = merchant['callback_url']
            
            try:
                print(f"🔄 Forwarding callback to merchant: {callback_url}")
                
                # Prepare merchant callback data
                merchant_callback = {
                    'txn_id': txnid,
                    'order_id': transaction.get('order_id', txnid),
                    'amount': amount,
                    'status': new_status,
                    'utr': utr,
                    'pg_txn_id': apitxnid,
                    'remark': remark
                }
                
                response = requests.post(
                    callback_url,
                    json=merchant_callback,
                    timeout=10
                )
                
                print(f"✓ Merchant callback response: {response.status_code}")
                
            except Exception as e:
                print(f"❌ Error forwarding callback: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Callback processed successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing callback: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@paytouchpayin_callback_bp.route('/api/paytouchpayin/test-callback', methods=['POST'])
def test_paytouchpayin_callback():
    """Test endpoint to simulate callback"""
    try:
        data = request.get_json()
        print(f"🧪 Test callback received: {json.dumps(data, indent=2)}")
        
        return jsonify({
            'success': True,
            'message': 'Test callback received',
            'data': data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
