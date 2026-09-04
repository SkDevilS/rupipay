"""
Oxymoney_Barringer Callback Routes
Handles TransXT API callbacks for payin transactions
"""

from flask import Blueprint, request, jsonify
from oxymoney_barringer_service import oxymoney_barringer_service
from database import get_db_connection
import json
import requests
from datetime import datetime

oxymoney_barringer_callback_bp = Blueprint('oxymoney_barringer_callback', __name__, url_prefix='/api/callback/oxy-barringer')

@oxymoney_barringer_callback_bp.route('/payin', methods=['POST'])
def oxymoney_barringer_payin_callback():
    """
    Handle Oxymoney_Barringer payin callback
    
    Callback format (from documentation):
    {
        "rrn": "247340973172",
        "note": "Payment",
        "refId": "X2604301144251324189192222",
        "txnId": "SUR8CB36E39D0204DC6891179939F30BA37",
        "amount": "100.00",
        "errorCode": "00",
        "errorMsg": "",
        "status": "SUCCESS",
        "tpRespCode": "",
        "clientRefId": "OXBAR2CDF01E1E3D3EDC",
        "txnDate": "2026-04-30T11:44:37+05:30",
        "payerDtls": {
            "mobileNo": "918975891441",
            "vpa": "8975891441@axl",
            "acNo": "438802120024524",
            "ifsc": "UBIN0543888",
            "name": "SHEKH GAFFAR SHEKH JAMAL",
            "mccCode": "0000"
        },
        "merchantDtls": {
            "merchantVpa": "barringer@suryoday",
            "name": "Dyma Infotech Private Limited",
            "mccCode": "5641",
            "mId": "31326"
        }
    }
    """
    try:
        print("=" * 80)
        print("Oxymoney_Barringer Payin Callback Received")
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
        
        # Extract key fields from callback
        client_ref_id = callback_data.get('clientRefId')
        ox_txn_id = callback_data.get('txnId')
        status = callback_data.get('status', '').upper()
        amount = callback_data.get('amount')
        rrn = callback_data.get('rrn', '')
        error_code = callback_data.get('errorCode', '')
        error_msg = callback_data.get('errorMsg', '')
        txn_date = callback_data.get('txnDate', '')
        
        # Payer details
        payer_dtls = callback_data.get('payerDtls', {})
        customer_vpa = payer_dtls.get('vpa', '')
        customer_name = payer_dtls.get('name', '')
        customer_mobile = payer_dtls.get('mobileNo', '')
        
        # Merchant details
        merchant_dtls = callback_data.get('merchantDtls', {})
        merchant_vpa = merchant_dtls.get('merchantVpa', '')
        
        print(f"Parsed Callback:")
        print(f"  Client Ref ID: {client_ref_id}")
        print(f"  Oxymoney Txn ID: {ox_txn_id}")
        print(f"  Status: {status}")
        print(f"  Amount: ₹{amount}")
        print(f"  RRN/UTR: {rrn}")
        print(f"  Error Code: {error_code}")
        print(f"  Customer VPA: {customer_vpa}")
        print(f"  Merchant VPA: {merchant_vpa}")
        
        if not client_ref_id and not ox_txn_id:
            print("ERROR: Missing both client_ref_id and txn_id in callback")
            return jsonify({'success': False, 'message': 'Missing transaction identifiers'}), 400
        
        # Find transaction in database
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by pg_txn_id (Oxymoney txn_id)
                # Include payment_url to extract VPA later
                if ox_txn_id:
                    cursor.execute("""
                        SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status, payment_url
                        FROM payin_transactions
                        WHERE pg_txn_id = %s AND pg_partner = 'Oxymoney_Barringer'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (ox_txn_id,))
                    
                    txn = cursor.fetchone()
                
                # If not found, try by client_ref_id in payment_url or other fields
                if not txn and client_ref_id:
                    cursor.execute("""
                        SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status, payment_url
                        FROM payin_transactions
                        WHERE payment_url LIKE %s AND pg_partner = 'Oxymoney_Barringer'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (f"%{client_ref_id}%",))
                    
                    txn = cursor.fetchone()
                
                if not txn:
                    print(f"ERROR: Transaction not found for client_ref_id: {client_ref_id}, ox_txn_id: {ox_txn_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"Found Transaction: {txn['txn_id']}, Current Status: {txn['status']}")
                
                # Map Oxymoney status to our status
                if status == 'SUCCESS':
                    new_status = 'SUCCESS'
                elif status == 'FAILED':
                    new_status = 'FAILED'
                elif status in ['PENDING', 'PROCESSING']:
                    new_status = 'PENDING'
                else:
                    new_status = 'INITIATED'
                
                print(f"Mapped Status: {status} -> {new_status}")
                
                # Update transaction
                if new_status in ['SUCCESS', 'FAILED']:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s,
                            bank_ref_no = %s,
                            payment_mode = 'UPI',
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, rrn, txn['txn_id']))
                else:
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s,
                            bank_ref_no = %s,
                            payment_mode = 'UPI',
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, rrn, txn['txn_id']))
                
                print(f"✓ Updated transaction status to {new_status}")
                
                # If successful, credit wallets and record VPA usage
                if new_status == 'SUCCESS':
                    # Extract VPA from payment_url (stored as "intent_url|VPA:vpa_value")
                    payment_url = txn.get('payment_url', '')
                    vpa_used = None
                    
                    if '|VPA:' in payment_url:
                        vpa_used = payment_url.split('|VPA:')[1].split('|')[0]
                        print(f"✓ Extracted VPA from transaction: {vpa_used}")
                    else:
                        print(f"⚠️  WARNING: VPA not found in payment_url")
                        print(f"   Payment URL: {payment_url}")
                    
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
                            description=f"Oxymoney_Barringer Payin credited to unsettled wallet - {txn['order_id']}",
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
                            description=f"Oxymoney_Barringer Payin charge - {txn['order_id']}",
                            reference_id=txn['txn_id']
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✓ Admin unsettled wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"⚠ Wallet already credited for this transaction - skipping")
                    
                    # Record VPA usage on SUCCESS (only if VPA was extracted)
                    if vpa_used:
                        # Check if VPA usage already recorded (idempotency)
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM oxymoney_barringer_vpa_usage
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        
                        vpa_already_recorded = cursor.fetchone()['count'] > 0
                        
                        if not vpa_already_recorded:
                            cursor.execute("""
                                INSERT INTO oxymoney_barringer_vpa_usage (
                                    vpa, amount, txn_id, merchant_id, created_at
                                ) VALUES (%s, %s, %s, %s, NOW())
                            """, (vpa_used, txn['amount'], txn['txn_id'], txn['merchant_id']))
                            
                            print(f"✅ VPA usage recorded: {vpa_used} - ₹{txn['amount']}")
                            print(f"   This VPA's limit has been updated and will be reflected in next order creation")
                        else:
                            print(f"⚠ VPA usage already recorded for this transaction - skipping")
                    else:
                        print(f"❌ Cannot record VPA usage - VPA not found in transaction data")
                
                conn.commit()
                
                # Forward callback to merchant
                # Get callback URL from transaction
                cursor.execute("""
                    SELECT callback_url FROM payin_transactions
                    WHERE txn_id = %s
                """, (txn['txn_id'],))
                
                txn_data = cursor.fetchone()
                merchant_callback_url = txn_data.get('callback_url') if txn_data else None
                
                if merchant_callback_url:
                    try:
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'order_id': txn['order_id'],
                            'status': new_status,
                            'amount': str(txn['amount']),
                            'net_amount': str(txn['net_amount']),
                            'charge_amount': str(txn['charge_amount']),
                            'utr': rrn,
                            'pg_txn_id': ox_txn_id,
                            'payment_mode': 'UPI',
                            'pg_partner': 'Oxymoney_Barringer',
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
                    print("⚠ No merchant callback URL found")
                
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

@oxymoney_barringer_callback_bp.route('/test', methods=['GET', 'POST'])
def test_oxymoney_barringer_callback():
    """Test endpoint for Oxymoney_Barringer callback"""
    try:
        print(f"=== Oxymoney_Barringer Test Callback ===")
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
