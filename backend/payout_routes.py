from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
import jwt
import bcrypt
from datetime import datetime
from database import get_db_connection
from config import Config
import payout_service
import payu_payout_service
import wallet_service
import uuid
import json
import csv
import io
from mudrape_service import mudrape_service
from paytouch_service import paytouch_service
from paytouch2_service import paytouch2_service
from paytouch3_service import paytouch3_service

payout_bp = Blueprint('payout', __name__, url_prefix='/api/payout')

# Get service instances
payout_svc = payout_service.payout_service
payu_payout_svc = payu_payout_service.payu_payout_service
wallet_svc = wallet_service.wallet_service


# Admin Personal Payout
@payout_bp.route('/admin/personal-payout', methods=['POST'])
@jwt_required()
def admin_personal_payout():
    """
    Admin Personal Payout - Direct Mudrape API call
    NO wallet balance check or deduction
    """
    try:
        data = request.json
        admin_id = get_jwt_identity()
        
        # Validate required fields
        required_fields = ['bank_id', 'amount', 'tpin', 'pg_partner']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
            
            # Check payout limit - maximum 500,000 per transaction
            if amount > 500000:
                return jsonify({'success': False, 'message': 'Transaction out of limit. Maximum payout amount is â‚¹5,00,000 per transaction'}), 400
                
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid amount format'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify TPIN
                cursor.execute("SELECT pin_hash FROM admin_users WHERE admin_id = %s", (admin_id,))
                admin = cursor.fetchone()
                
                if not admin or not admin['pin_hash']:
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400
                
                # Get bank details
                cursor.execute("""
                    SELECT * FROM admin_banks 
                    WHERE id = %s AND admin_id = %s AND is_active = TRUE
                """, (data['bank_id'], admin_id))
                bank = cursor.fetchone()
                
                if not bank:
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # NO WALLET BALANCE CHECK - Admin personal payouts go directly through selected gateway

                # PayStorePe requires beneficiary mobile/email. Admin personal payout
                # forms do not ask for these fields, so generate synthetic but valid
                # contact values for gateway validation. These are not presented as
                # the admin's real contact details.
                import random
                bene_mobile = str(data.get('bene_mobile', ''))
                if not bene_mobile or len(bene_mobile) != 10 or not bene_mobile.isdigit():
                    bene_mobile = f"9{random.randint(100000000, 999999999)}"
                
                bene_email = str(data.get('bene_email', ''))
                if not bene_email or '@' not in bene_email:
                    bene_email = f"admin.payout.{random.randint(100000, 999999)}@paysetu.shop"

                # Create payout transaction record (using admin_id field for admin payouts)
                reference_id = f"ADMIN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                
                # Generate transaction ID based on selected gateway
                pg_partner_upper = data['pg_partner'].upper()
                if pg_partner_upper in ['PAYTOUCH3_TRENDORA', 'PAYTOUCH_TRENDORA']:
                    txn_id = f"PT3_TREN_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH4_BARRINGER', 'PAYTOUCH_BARRINGER']:
                    txn_id = f"PT4_BAR_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH5_COCO', 'PAYTOUCH_COCO']:
                    txn_id = f"PT5_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH6_VELTRIX', 'PAYTOUCH_VELTRIX']:
                    txn_id = f"PT6_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_VELTRIX', 'PAYSTOREPE_VELTRIX']:
                    txn_id = f"PSP_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_COCO', 'PAYSTOREPE_COCO']:
                    txn_id = f"PSP_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    txn_id = f"BM_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH2', 'PAYTOUCH_GROSMART']:
                    txn_id = f"PT2_GROS_TXN{uuid.uuid4().hex[:12].upper()}"
                else:
                    # Default for other gateways (PAYU, MUDRAPE, etc.)
                    txn_id = f"TXN{uuid.uuid4().hex[:16].upper()}"
                
                # Auto-generate order_id for admin payouts
                order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute("""
                    INSERT INTO payout_transactions 
                    (txn_id, reference_id, order_id, merchant_id, admin_id, amount, charge_amount, charge_type, net_amount,
                     bene_name, bene_email, bene_mobile, bene_bank, account_no, ifsc_code, payment_type, pg_partner, status, created_at)
                    VALUES (%s, %s, %s, NULL, %s, %s, 0.00, 'FIXED', %s, %s, %s, %s, %s, %s, %s, 'IMPS', %s, 'INITIATED', NOW())
                """, (txn_id, reference_id, order_id, admin_id, data['amount'], data['amount'],
                      bank['account_holder_name'], bene_email, bene_mobile, bank['bank_name'],
                      bank['account_number'], bank['ifsc_code'], data['pg_partner']))
                
                conn.commit()
                
                # Process payout based on pg_partner (already defined above)
                
                if pg_partner_upper == 'PAYU':
                    # Use PayU for payout - Direct API call, NO wallet deduction
                    transfer_data = [{
                        'bene_name': bank['account_holder_name'],
                        'bene_email': '',
                        'bene_mobile': '',
                        'purpose': 'Admin Personal Payout',
                        'amount': float(data['amount']),
                        'batch_id': '',
                        'reference_id': reference_id,
                        'payment_type': 'IMPS',
                        'account_no': bank['account_number'],
                        'ifsc_code': bank['ifsc_code'],
                        'retry': False
                    }]
                    
                    result = payu_payout_svc.initiate_transfer(transfer_data)
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayU
                        # Update status to QUEUED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'QUEUED', updated_at = NOW()
                            WHERE reference_id = %s
                        """, (reference_id,))
                        conn.commit()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('error', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('error', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper == 'MUDRAPE':
                    # Use Mudrape for payout (IMPS) - Direct API call, NO wallet deduction
                    result = mudrape_service.call_imps_payout_api(
                        account_number=bank['account_number'],
                        ifsc_code=bank['ifsc_code'],
                        client_txn_id=reference_id,
                        amount=float(data['amount']),
                        beneficiary_name=bank['account_holder_name']
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through Mudrape
                        # Update transaction with Mudrape response
                        status = result.get('status', 'INITIATED')
                        mudrape_txn_id = result.get('mudrape_txn_id', '')
                        
                        print(f"DEBUG: result dict = {result}")
                        print(f"DEBUG: status variable = '{status}' (type: {type(status)})")
                        print(f"DEBUG: mudrape_txn_id = '{mudrape_txn_id}'")
                        print(f"Mudrape payout initiated - Status: {status}, TxnID: {mudrape_txn_id}")
                        
                        # Set completed_at if status is final
                        if status in ['SUCCESS', 'FAILED']:
                            update_query = """
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE reference_id = %s
                            """
                            update_params = (status, mudrape_txn_id, reference_id)
                            print(f"DEBUG: Executing UPDATE with status='{status}', pg_txn_id='{mudrape_txn_id}', ref='{reference_id}'")
                            cursor.execute(update_query, update_params)
                        else:
                            update_query = """
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE reference_id = %s
                            """
                            update_params = (status, mudrape_txn_id, reference_id)
                            print(f"DEBUG: Executing UPDATE with status='{status}', pg_txn_id='{mudrape_txn_id}', ref='{reference_id}'")
                            cursor.execute(update_query, update_params)
                        
                        conn.commit()
                        print(f"DEBUG: UPDATE committed, rows affected: {cursor.rowcount}")
                        
                        # If status is still INITIATED (pending), check status from Mudrape API
                        if status == 'INITIATED':
                            print(f"Checking status from Mudrape for reference_id: {reference_id}")
                            import time
                            time.sleep(2)  # Wait 2 seconds before checking
                            
                            status_result = mudrape_service.check_payout_status(reference_id)
                            print(f"DEBUG: status_result = {status_result}")
                            if status_result.get('success'):
                                updated_status = status_result.get('status', 'INITIATED')
                                utr = status_result.get('utr')
                                completed_at_from_api = status_result.get('completed_at')
                                
                                print(f"Mudrape status check result - Status: {updated_status}, UTR: {utr}, Completed: {completed_at_from_api}")
                                print(f"DEBUG: About to UPDATE with status='{updated_status}'")
                                
                                # Update with latest status
                                if updated_status in ['SUCCESS', 'FAILED']:
                                    if completed_at_from_api:
                                        # Use the timestamp from Mudrape
                                        update_query2 = """
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = %s, updated_at = NOW()
                                            WHERE reference_id = %s
                                        """
                                        update_params2 = (updated_status, utr, completed_at_from_api, reference_id)
                                    else:
                                        # Fallback to NOW() if no timestamp from Mudrape
                                        update_query2 = """
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                            WHERE reference_id = %s
                                        """
                                        update_params2 = (updated_status, utr, reference_id)
                                    print(f"DEBUG: Executing final UPDATE: status='{updated_status}', utr='{utr}', completed_at='{completed_at_from_api}', ref='{reference_id}'")
                                    cursor.execute(update_query2, update_params2)
                                else:
                                    update_query2 = """
                                        UPDATE payout_transactions 
                                        SET status = %s, utr = %s, updated_at = NOW()
                                        WHERE reference_id = %s
                                    """
                                    update_params2 = (updated_status, utr, reference_id)
                                    print(f"DEBUG: Executing final UPDATE: status='{updated_status}', utr='{utr}', ref='{reference_id}'")
                                    cursor.execute(update_query2, update_params2)
                                
                                conn.commit()
                                print(f"DEBUG: Final UPDATE committed, rows affected: {cursor.rowcount}")
                                status = updated_status
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': status
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper in ['PAYTOUCH', 'PAYTOUCH_TRUAXIS']:
                    # Use PayTouch for payout - Direct API call, NO wallet deduction
                    # PayTouch requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service
                    
                    result = paytouch_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch
                        print(f"PayTouch payout initiated - Status: {result.get('status')}, TxnID: {result.get('paytouch_txn_id')}")
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper in ['PAYTOUCH2', 'PAYTOUCH_GROSMART']:
                    # Use PayTouch2 for payout - Direct API call, NO wallet deduction
                    # PayTouch2 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service
                    
                    result = paytouch2_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch2
                        print(f"PayTouch2 payout initiated - Status: {result.get('status')}, TxnID: {result.get('paytouch2_txn_id')}")
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper in ['PAYTOUCH3_TRENDORA', 'PAYTOUCH_TRENDORA']:
                    # Use PayTouch3_Trendora for payout - Direct API call, NO wallet deduction
                    # PayTouch3 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service
                    
                    result = paytouch3_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch3_Trendora
                        print(f"PayTouch3_Trendora payout initiated - Status: {result.get('status')}, TxnID: {result.get('paytouch3_txn_id')}")
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper in ['PAYTOUCH4_BARRINGER', 'PAYTOUCH_BARRINGER']:
                    # Use PayTouch4_Barringer for payout - Direct API call, NO wallet deduction
                    # PayTouch4 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    from paytouch4_service import paytouch4_service
                    
                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service
                    
                    result = paytouch4_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch4_Barringer
                        print(f"PayTouch4_Barringer payout initiated - Status: {result.get('status')}, TxnID: {result.get('paytouch4_txn_id')}")
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400
                
                elif pg_partner_upper in ['PAYTOUCH5_COCO', 'PAYTOUCH_COCO']:
                    # Use PayTouch5_Coco for payout - Direct API call, NO wallet deduction
                    from paytouch5_coco_service import paytouch5_service
                    
                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service
                    
                    result = paytouch5_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )
                    
                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch5_Coco
                        print(f"PayTouch5_Coco payout initiated - Status: {result.get('status')}, TxnID: {result.get('paytouch5_txn_id')}")
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))
                        conn.commit()
                        
                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400

                elif pg_partner_upper in ['PAYTOUCH6_VELTRIX', 'PAYTOUCH_VELTRIX']:
                    # Use PayTouch6_Veltrix for payout - Direct API call, NO wallet deduction
                    from paytouch6_veltrix_service import paytouch6_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }
                    # payment_mode, narration, bank_branch are hardcoded in service

                    result = paytouch6_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )

                    if result['success']:
                        # NO WALLET DEDUCTION - Admin personal payouts go directly through PayTouch6_Veltrix
                        print(
                            f"PayTouch6_Veltrix payout initiated - "
                            f"Status: {result.get('status')}, "
                            f"TxnID: {result.get('paytouch6_txn_id')}"
                        )

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200

                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))

                        conn.commit()

                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400

                elif pg_partner_upper == 'PAYSTOREPE_VELTRIX':
                    # PayStorePe payout
                    from paystorepe_veltrix_service import paystorepe_veltrix_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount,
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': 'IMPS',
                        'callback_url': f"{request.host_url.rstrip('/')}/api/callback/paystorepe_veltrix/payout".replace("http://", "https://"),
                        'remarks': 'Admin Payout'
                    }

                    paystorepe_result = paystorepe_veltrix_service.initiate_payout(
                        merchant_id=None,
                        payout_data=payout_data,
                        admin_id=admin_id
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    # NO WALLET DEDUCTION - Admin personal payouts go directly through PayStorePe
                    print(f"PayStorePe_Veltrix payout initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))
                    conn.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Payout initiated successfully',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'status': status
                    }), 200

                elif pg_partner_upper == 'PAYSTOREPE_COCO':
                    # PayStorePe payout
                    from paystorepe_coco_service import paystorepe_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount,
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': 'IMPS',
                        'callback_url': f"{request.host_url.rstrip('/')}/api/callback/paystorepe_coco/payout".replace("http://", "https://"),
                        'remarks': 'Admin Payout'
                    }

                    paystorepe_result = paystorepe_coco_service.initiate_payout(
                        merchant_id=None,
                        payout_data=payout_data,
                        admin_id=admin_id
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    # NO WALLET DEDUCTION - Admin personal payouts go directly through PayStorePe
                    print(f"PayStorePe_Coco payout initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))
                    conn.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Payout initiated successfully',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'status': status
                    }), 200

                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    # Use Bridgmoney_Coco for payout - Direct API call, NO wallet deduction
                    from bridgmoney_coco_service import bridgmoney_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': float(data['amount']),
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email
                    }

                    result = bridgmoney_coco_service.initiate_payout(
                        merchant_id=None,  # No merchant for admin payouts
                        payout_data=payout_data,
                        admin_id=admin_id
                    )

                    if result['success']:
                        print(
                            f"Bridgmoney_Coco payout initiated - "
                            f"Status: {result.get('status')}, "
                            f"TxnID: {result.get('bridgmoney_coco_txn_id')}"
                        )

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': result.get('status', 'QUEUED')
                        }), 200

                    else:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE reference_id = %s
                        """, (result.get('message', 'Payout failed'), reference_id))

                        conn.commit()

                        return jsonify({
                            'success': False,
                            'message': result.get('message', 'Payout failed')
                        }), 400

                else:
                    return jsonify({
                        'success': False,
                        'message': f'Payment gateway {data["pg_partner"]} not supported'
                    }), 400
                    
        finally:
            conn.close()
                
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Fund Request - Client creates request
@payout_bp.route('/client/fund-request', methods=['POST'])
@jwt_required()
def create_fund_request():
    try:
        data = request.json
        merchant_id = get_jwt_identity()
        
        if 'amount' not in data or float(data['amount']) <= 0:
            return jsonify({'success': False, 'message': 'Valid amount is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            request_id = f"FR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
            
            cursor.execute("""
                INSERT INTO fund_requests (request_id, merchant_id, amount, request_type, remarks)
                VALUES (%s, %s, %s, %s, %s)
            """, (request_id, merchant_id, data['amount'], 'SETTLEMENT', data.get('remarks', '')))
            
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'message': 'Fund request submitted', 'request_id': request_id}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get Fund Requests - Admin view
@payout_bp.route('/admin/fund-requests', methods=['GET'])
@jwt_required()
def get_fund_requests():
    try:
        status = request.args.get('status', 'PENDING')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT fr.*, m.full_name, m.mobile, m.email
                FROM fund_requests fr
                JOIN merchants m ON fr.merchant_id = m.merchant_id
                WHERE fr.status = %s
                ORDER BY fr.requested_at DESC
            """, (status,))
            
            requests_list = cursor.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'data': requests_list}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Approve/Reject Fund Request
@payout_bp.route('/admin/fund-request/<request_id>', methods=['PUT'])
@jwt_required()
def process_fund_request(request_id):
    conn = None
    try:
        data = request.json
        admin_id = get_jwt_identity()
        action = data.get('action')  # 'APPROVE' or 'REJECT'
        
        if action not in ['APPROVE', 'REJECT']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get fund request
            cursor.execute("""
                SELECT * FROM fund_requests WHERE request_id = %s AND status = 'PENDING'
            """, (request_id,))
            fund_request = cursor.fetchone()
            
            if not fund_request:
                conn.close()
                return jsonify({'success': False, 'message': 'Request not found'}), 404
            
            if action == 'APPROVE':
                # CRITICAL FIX: Pass the connection to ensure atomic transaction
                # This prevents admin wallet debit if merchant credit fails
                admin_debit = wallet_svc.debit_admin_wallet(
                    admin_id,
                    float(fund_request['amount']),
                    f"Fund request approved for {fund_request['merchant_id']} - {request_id}",
                    reference_id=request_id,
                    conn=conn  # Pass existing connection for atomic transaction
                )
                
                if not admin_debit['success']:
                    conn.close()
                    return jsonify(admin_debit), 400
                
                # CRITICAL FIX: Credit SETTLED wallet, not unsettled wallet
                # Fund requests/topups should go to settled balance (ready for payout)
                # NOT to unsettled balance (which is for PayIN that needs settlement)
                
                # Get current settled balance
                cursor.execute("""
                    SELECT settled_balance FROM merchant_wallet WHERE merchant_id = %s
                """, (fund_request['merchant_id'],))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, %s, %s, 0.00)
                    """, (fund_request['merchant_id'], fund_request['amount'], fund_request['amount']))
                    settled_before = 0.00
                else:
                    settled_before = float(wallet['settled_balance'])
                
                settled_after = settled_before + float(fund_request['amount'])
                
                # Update settled balance
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET settled_balance = %s, balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (settled_after, settled_after, fund_request['merchant_id']))
                
                # Record transaction in merchant_wallet_transactions
                txn_id = f"MWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s)
                """, (
                    fund_request['merchant_id'], txn_id, fund_request['amount'],
                    settled_before, settled_after,
                    f"Fund topup approved - {request_id}",
                    request_id
                ))
            
            # Update request status
            cursor.execute("""
                UPDATE fund_requests 
                SET status = %s, processed_at = NOW(), processed_by = %s, remarks = %s
                WHERE request_id = %s
            """, ('APPROVED' if action == 'APPROVE' else 'REJECTED', admin_id, data.get('remarks', ''), request_id))
            
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'message': f'Request {action.lower()}d successfully'}), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# Admin Topup Fund
@payout_bp.route('/admin/topup-fund', methods=['POST'])
@jwt_required()
def admin_topup_fund():
    try:
        data = request.json
        admin_id = get_jwt_identity()
        
        required_fields = ['merchant_id', 'amount', 'tpin']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin TPIN
                cursor.execute("SELECT pin_hash FROM admin_users WHERE admin_id = %s", (admin_id,))
                admin = cursor.fetchone()
                
                if not admin or not admin['pin_hash']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400
                
                # Lock admin wallet row to prevent concurrent topups (race condition fix)
                cursor.execute("""
                    SELECT admin_id FROM admin_wallet 
                    WHERE admin_id = %s 
                    FOR UPDATE
                """, (admin_id,))
                
                # Check for duplicate topup in last minute (idempotency check)
                cursor.execute("""
                    SELECT COUNT(*) as count, MAX(processed_at) as last_topup
                    FROM fund_requests
                    WHERE merchant_id = %s 
                    AND amount = %s
                    AND processed_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
                    AND status = 'APPROVED'
                """, (data['merchant_id'], data['amount']))
                
                duplicate_check = cursor.fetchone()
                if duplicate_check and duplicate_check['count'] > 0:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Duplicate topup detected. Last topup of â‚¹{data["amount"]} was processed at {duplicate_check["last_topup"]}. Please wait before retrying.'
                    }), 400
                
                # Check available balance in admin wallet
                # Admin Wallet = PayIN + Fetch - Topups + Manual Adjustments
                # (Payouts are deducted from merchant wallets, not admin wallet)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                """)
                total_payin = float(cursor.fetchone()['total_payin'])
                
                # Get total approved fund requests (topups already given to merchants)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                """)
                total_topup = float(cursor.fetchone()['total_topup'])
                
                # Get total fetch from merchants (money returned to admin)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetch
                    FROM merchant_wallet_transactions
                    WHERE txn_type = 'DEBIT' 
                    AND description LIKE '%fetched by admin%'
                """)
                total_fetch = float(cursor.fetchone()['total_fetch'])
                
                # Get manual adjustments from admin_wallet_transactions
                cursor.execute("""
                    SELECT COALESCE(SUM(
                        CASE 
                            WHEN txn_type = 'CREDIT' THEN amount
                            WHEN txn_type = 'DEBIT' THEN -amount
                            ELSE 0
                        END
                    ), 0) as total_adjustments
                    FROM admin_wallet_transactions
                    WHERE description LIKE '%Manual balance%'
                    OR description LIKE '%Balance adjustment%'
                    OR description LIKE '%Initial capital%'
                """)
                total_adjustments = float(cursor.fetchone()['total_adjustments'])
                
                # Admin available balance = PayIN + Fetch - Topups + Manual Adjustments
                # Topups transfer money FROM admin TO merchants
                # Payouts are paid from merchant wallets, not admin wallet
                available_balance = total_payin + total_fetch - total_topup + total_adjustments
                
                # Log for debugging
                print(f"=== TOPUP VALIDATION ===")
                print(f"Merchant: {data['merchant_id']}")
                print(f"Amount: {data['amount']}")
                print(f"Available Balance: {available_balance}")
                print(f"PayIN: {total_payin}, Fetch: {total_fetch}, Topups: {total_topup}, Adjustments: {total_adjustments}")
                
                if float(data['amount']) > available_balance:
                    print(f"âŒ VALIDATION FAILED: {data['amount']} > {available_balance}")
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'message': f'Insufficient balance in wallet, remaining balance in wallet: â‚¹{available_balance:.2f}'
                    }), 400
                
                print(f"âœ“ VALIDATION PASSED: {data['amount']} <= {available_balance}")
                
                # Create fund request entry (auto-approved by admin)
                request_id = f"FR{uuid.uuid4().hex[:12].upper()}"
                remarks = data.get('remarks', 'Manual topup by admin')
                
                cursor.execute("""
                    INSERT INTO fund_requests 
                    (request_id, merchant_id, amount, status, remarks, processed_by, processed_at)
                    VALUES (%s, %s, %s, 'APPROVED', %s, %s, NOW())
                """, (request_id, data['merchant_id'], data['amount'], remarks, admin_id))
                
                # CRITICAL FIX: Record admin wallet debit in same transaction
                # Calculate balance for admin wallet transaction
                balance_before = available_balance
                balance_after = available_balance - float(data['amount'])
                
                awt_id = f"AWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s)
                """, (admin_id, awt_id, data['amount'], balance_before, balance_after,
                      f"Manual topup for {data['merchant_id']} - {request_id}", request_id))
                
                # CRITICAL FIX: Credit merchant's SETTLED wallet in same transaction
                # Get current settled balance
                cursor.execute("""
                    SELECT settled_balance FROM merchant_wallet WHERE merchant_id = %s
                """, (data['merchant_id'],))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, %s, %s, 0.00)
                    """, (data['merchant_id'], data['amount'], data['amount']))
                    settled_before = 0.00
                else:
                    settled_before = float(wallet['settled_balance'])
                
                settled_after = settled_before + float(data['amount'])
                
                # Update settled balance
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET settled_balance = %s, balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (settled_after, settled_after, data['merchant_id']))
                
                # Record transaction in merchant_wallet_transactions
                txn_id = f"MWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s)
                """, (
                    data['merchant_id'], txn_id, data['amount'],
                    settled_before, settled_after,
                    f"Topup approved - {request_id}",
                    request_id
                ))
                
                print(f"âœ“ Credited merchant settled wallet: â‚¹{data['amount']}")
                
                conn.commit()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Topup successful',
                'request_id': request_id
            }), 200
            
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            raise e
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Client Settle Fund (Disburse to bank)
@payout_bp.route('/client/settle-fund', methods=['POST'])
@jwt_required()
def client_settle_fund():
    try:
        data = request.json
        merchant_id = get_jwt_identity()
        
        # IP SECURITY CHECK - Validate merchant IP for settle fund operations
        from ip_security_routes import validate_merchant_ip
        is_valid, message = validate_merchant_ip(merchant_id, '/api/payout/client/settle-fund')
        if not is_valid:
            return jsonify({'success': False, 'message': message}), 403
        
        required_fields = ['bank_id', 'amount', 'tpin']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify merchant TPIN
                cursor.execute("SELECT pin_hash, scheme_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant or not merchant['pin_hash']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400
                
                # Get bank details
                cursor.execute("""
                    SELECT * FROM merchant_banks 
                    WHERE id = %s AND merchant_id = %s AND is_active = TRUE
                """, (data['bank_id'], merchant_id))
                bank = cursor.fetchone()
                
                if not bank:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # Calculate payout charges based on merchant scheme
                charges = payout_svc.calculate_charges(
                    float(data['amount']),
                    merchant['scheme_id'],
                    'PAYOUT'
                )
                
                if not charges:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Unable to calculate payout charges'}), 400
                
                # NEW LOGIC: User receives full amount, charges deducted from wallet
                # Amount to send to bank = requested amount (full amount)
                amount_to_bank = float(data['amount'])
                # Total deduction from wallet = amount + charges
                total_wallet_deduction = amount_to_bank + charges['charge_amount']
                
                if amount_to_bank <= 0:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid settlement amount'}), 400
                
                # Get settled balance from merchant_wallet (this is the withdrawable amount)
                cursor.execute("""
                    SELECT COALESCE(settled_balance, 0) as available_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                wallet_result = cursor.fetchone()
                available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00
                
                # Check if settled balance is sufficient (amount + charges)
                if total_wallet_deduction > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'message': f'Insufficient balance in wallet, remaining balance in wallet: â‚¹{available_balance:.2f}'
                    }), 400
                
                # Get PG partner from service routing for PAYOUT
                # First try to get merchant-specific routing
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE service_type = 'PAYOUT' 
                    AND routing_type = 'SINGLE_USER'
                    AND merchant_id = %s
                    AND is_active = TRUE
                    ORDER BY priority ASC
                    LIMIT 1
                """, (merchant_id,))
                routing = cursor.fetchone()
                
                # If no merchant-specific routing, get ALL_USERS routing
                if not routing:
                    cursor.execute("""
                        SELECT pg_partner FROM service_routing
                        WHERE service_type = 'PAYOUT' 
                        AND routing_type = 'ALL_USERS'
                        AND is_active = TRUE
                        ORDER BY priority ASC
                        LIMIT 1
                    """)
                    routing = cursor.fetchone()
                
                if not routing:
                    conn.close()
                    return jsonify({'success': False, 'message': 'No payout gateway configured'}), 400
                
                pg_partner = routing['pg_partner']
                
                print(f"DEBUG: Merchant {merchant_id} payout - pg_partner from DB: '{pg_partner}'")
                
                # Create payout transaction record with charges
                # Store total_wallet_deduction as amount (what's deducted from wallet)
                reference_id = f"SF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                
                # Generate transaction ID based on gateway
                pg_partner_upper = pg_partner.upper()
                if pg_partner_upper in ['PAYTOUCH3_TRENDORA', 'PAYTOUCH_TRENDORA']:
                    txn_id = f"PT3_TREN_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH4_BARRINGER', 'PAYTOUCH_BARRINGER']:
                    txn_id = f"PT4_BAR_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH5_COCO', 'PAYTOUCH_COCO']:
                    txn_id = f"PT5_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH6_VELTRIX', 'PAYTOUCH_VELTRIX']:
                    txn_id = f"PT6_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_VELTRIX', 'PAYSTOREPE_VELTRIX']:
                    txn_id = f"PSP_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_COCO', 'PAYSTOREPE_COCO']:
                    txn_id = f"PSP_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    txn_id = f"BM_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH2', 'PAYTOUCH_GROSMART']:
                    txn_id = f"PT2_GROS_TXN{uuid.uuid4().hex[:12].upper()}"
                else:
                    # Default for other gateways
                    txn_id = f"TXN{uuid.uuid4().hex[:16].upper()}"
                
                order_id = f"SF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                
                # DO NOT debit wallet yet - only debit when payout is SUCCESS
                cursor.execute("""
                    INSERT INTO payout_transactions 
                    (txn_id, reference_id, order_id, merchant_id, amount, charge_amount, charge_type, 
                     net_amount, bene_name, bene_bank, account_no, ifsc_code, 
                     pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())
                """, (txn_id, reference_id, order_id, merchant_id, total_wallet_deduction, 
                      charges['charge_amount'], charges['charge_type'], amount_to_bank,
                      bank['account_holder_name'], bank['bank_name'], 
                      bank['account_number'], bank['ifsc_code'], pg_partner))
                
                conn.commit()
                
                # Process through payment gateway (pg_partner_upper already defined above)
                
                print(f"DEBUG: pg_partner_upper: '{pg_partner_upper}'")
                
                if pg_partner_upper == 'PAYU':
                    transfer_data = [{
                        'reference_id': reference_id,
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_email': '',
                        'bene_mobile': '',
                        'account_no': bank['account_number'],
                        'ifsc_code': bank['ifsc_code'],
                        'payment_type': 'IMPS',
                        'purpose': 'Fund Settlement'
                    }]
                    
                    payu_result = payu_payout_svc.initiate_transfer(transfer_data)
                    
                    if payu_result['success']:
                        # Update status to QUEUED (wallet will be deducted when status becomes SUCCESS)
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'QUEUED', pg_response = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (json.dumps(payu_result['data']), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': 'QUEUED'
                        }), 200
                    else:
                        # Update status to FAILED (no wallet deduction happened, so no refund needed)
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (payu_result.get('error', 'PayU transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': payu_result.get('error')
                        }), 400
                
                elif pg_partner_upper == 'MUDRAPE':
                    # Use Mudrape for payout (IMPS)
                    mudrape_result = mudrape_service.call_imps_payout_api(
                        account_number=bank['account_number'],
                        ifsc_code=bank['ifsc_code'],
                        client_txn_id=reference_id,
                        amount=amount_to_bank,  # Send full requested amount to user
                        beneficiary_name=bank['account_holder_name']
                    )
                    
                    if mudrape_result['success']:
                        # Update transaction with Mudrape response
                        status = mudrape_result.get('status', 'INITIATED')
                        mudrape_txn_id = mudrape_result.get('mudrape_txn_id', '')
                        
                        print(f"Mudrape settlement initiated - Status: {status}, TxnID: {mudrape_txn_id}")
                        
                        # Deduct wallet ONLY if status is SUCCESS
                        if status == 'SUCCESS':
                            debit_result = wallet_svc.debit_merchant_wallet(
                                merchant_id=merchant_id,
                                amount=total_wallet_deduction,
                                description=f"Settlement: â‚¹{amount_to_bank:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                                reference_id=txn_id
                            )
                            
                            if not debit_result['success']:
                                # This shouldn't happen as we already checked balance, but handle it
                                cursor.execute("""
                                    UPDATE payout_transactions 
                                    SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                                    WHERE txn_id = %s
                                """, (f"Wallet deduction failed: {debit_result['message']}", txn_id))
                                conn.commit()
                                conn.close()
                                return jsonify({
                                    'success': False,
                                    'message': f"Payout succeeded but wallet deduction failed: {debit_result['message']}",
                                    'txn_id': txn_id
                                }), 500
                            
                            print(f"âœ… WALLET DEBITED - Balance: â‚¹{debit_result['balance_before']:.2f} â†’ â‚¹{debit_result['balance_after']:.2f}")
                            
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        elif status == 'FAILED':
                            # No wallet deduction for failed transactions
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        else:
                            # PENDING/INITIATED - wallet will be deducted later when status becomes SUCCESS
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        
                        conn.commit()
                        
                        # If status is still INITIATED (pending), check status from Mudrape API
                        if status == 'INITIATED':
                            print(f"Checking status from Mudrape for reference_id: {reference_id}")
                            import time
                            time.sleep(2)  # Wait 2 seconds before checking
                            
                            status_result = mudrape_service.check_payout_status(reference_id)
                            if status_result.get('success'):
                                updated_status = status_result.get('status', 'INITIATED')
                                utr = status_result.get('utr')
                                completed_at_from_api = status_result.get('completed_at')
                                
                                print(f"Mudrape status check result - Status: {updated_status}, UTR: {utr}, Completed: {completed_at_from_api}")
                                
                                # Deduct wallet if status changed to SUCCESS
                                if updated_status == 'SUCCESS' and status != 'SUCCESS':
                                    debit_result = wallet_svc.debit_merchant_wallet(
                                        merchant_id=merchant_id,
                                        amount=total_wallet_deduction,
                                        description=f"Settlement: â‚¹{amount_to_bank:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                                        reference_id=txn_id
                                    )
                                    
                                    if debit_result['success']:
                                        print(f"âœ… WALLET DEBITED - Balance: â‚¹{debit_result['balance_before']:.2f} â†’ â‚¹{debit_result['balance_after']:.2f}")
                                
                                # Update with latest status
                                if updated_status in ['SUCCESS', 'FAILED']:
                                    if completed_at_from_api:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = %s, updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, completed_at_from_api, txn_id))
                                    else:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, txn_id))
                                else:
                                    cursor.execute("""
                                        UPDATE payout_transactions 
                                        SET status = %s, utr = %s, updated_at = NOW()
                                        WHERE txn_id = %s
                                    """, (updated_status, utr, txn_id))
                                
                                conn.commit()
                                status = updated_status
                        
                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully' if status != 'SUCCESS' else 'Settlement completed successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.' if status not in ['SUCCESS', 'FAILED'] else None
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mudrape_result.get('message', 'Mudrape transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': mudrape_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH':
                    # Use PayTouch for payout
                    # PayTouch requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch_result = paytouch_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch_result['success']:
                        status = paytouch_result.get('status', 'QUEUED')
                        paytouch_txn_id = paytouch_result.get('paytouch_txn_id', '')
                        
                        print(f"PayTouch settlement initiated - Status: {status}, TxnID: {paytouch_txn_id}")
                        
                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch response
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch_result.get('message', 'PayTouch transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH2':
                    # Use PayTouch2 for payout
                    # PayTouch2 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch2_result = paytouch2_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch2_result['success']:
                        status = paytouch2_result.get('status', 'QUEUED')
                        paytouch2_txn_id = paytouch2_result.get('paytouch2_txn_id', '')
                        
                        print(f"PayTouch2 settlement initiated - Status: {status}, TxnID: {paytouch2_txn_id}")
                        
                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch2 response
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch2_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch2_result.get('message', 'PayTouch2 transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch2_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH3_TRENDORA':
                    # Use PayTouch3_Trendora for payout
                    # PayTouch3 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch3_result = paytouch3_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch3_result['success']:
                        status = paytouch3_result.get('status', 'QUEUED')
                        paytouch3_txn_id = paytouch3_result.get('paytouch3_txn_id', '')
                        
                        print(f"PayTouch3_Trendora settlement initiated - Status: {status}, TxnID: {paytouch3_txn_id}")
                        
                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch3 response
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch3_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch3_result.get('message', 'PayTouch3_Trendora transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch3_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH4_BARRINGER':
                    # Use PayTouch4_Barringer for payout
                    # PayTouch4 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    from paytouch4_service import paytouch4_service
                    
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch4_result = paytouch4_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch4_result['success']:
                        status = paytouch4_result.get('status', 'QUEUED')
                        paytouch4_txn_id = paytouch4_result.get('paytouch4_txn_id', '')
                        
                        print(f"PayTouch4_Barringer settlement initiated - Status: {status}, TxnID: {paytouch4_txn_id}")
                        
                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch4 response
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch4_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch4_result.get('message', 'PayTouch4_Barringer transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch4_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH5_COCO':
                    # Use PayTouch5_Coco for payout
                    from paytouch5_coco_service import paytouch5_service
                    
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,  # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch5_result = paytouch5_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch5_result['success']:
                        status = paytouch5_result.get('status', 'QUEUED')
                        paytouch5_txn_id = paytouch5_result.get('paytouch5_txn_id', '')
                        
                        print(f"PayTouch5_Coco settlement initiated - Status: {status}, TxnID: {paytouch5_txn_id}")
                        
                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch5 response
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch5_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200
                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch5_result.get('message', 'PayTouch5_Coco transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch5_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH6_VELTRIX':
                    # Use PayTouch6_Veltrix for payout
                    from paytouch6_veltrix_service import paytouch6_service

                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount_to_bank,      # Send full requested amount to user
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }

                    paytouch6_result = paytouch6_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if paytouch6_result['success']:
                        status = paytouch6_result.get('status', 'QUEUED')
                        paytouch6_txn_id = paytouch6_result.get('paytouch6_txn_id', '')

                        print(
                            f"PayTouch6_Veltrix settlement initiated - "
                            f"Status: {status}, TxnID: {paytouch6_txn_id}"
                        )

                        # Wallet will be deducted via callback when status becomes SUCCESS
                        # Update transaction with PayTouch6 response
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch6_txn_id, txn_id))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200

                    else:
                        # No wallet deduction for failed transactions
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paytouch6_result.get('message', 'PayTouch6_Veltrix transfer failed'),
                            txn_id
                        ))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': paytouch6_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYSTOREPE_VELTRIX':
                    # PayStorePe payout
                    from paystorepe_veltrix_service import paystorepe_veltrix_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount_to_bank,
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': payment_type,
                        'callback_url': callback_url,
                        'remarks': purpose
                    }

                    paystorepe_result = paystorepe_veltrix_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    print(f"PayStorePe_Veltrix settlement initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    # Wallet will be deducted via callback when status becomes SUCCESS
                    # Update transaction with PayStorePe_Veltrix response
                    cursor.execute("""
                        UPDATE payout_transactions 
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))

                    conn.commit()
                    conn.close()

                    return jsonify({
                        'success': True,
                        'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'requested_amount': amount_to_bank,
                        'charges': charges['charge_amount'],
                        'total_to_deduct': total_wallet_deduction,
                        'status': status
                    }), 200

                elif pg_partner_upper == 'PAYSTOREPE_COCO':
                    # PayStorePe payout
                    from paystorepe_coco_service import paystorepe_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount_to_bank,
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name'],
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': payment_type,
                        'callback_url': callback_url,
                        'remarks': purpose
                    }

                    paystorepe_result = paystorepe_coco_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    print(f"PayStorePe_Coco settlement initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    # Wallet will be deducted via callback when status becomes SUCCESS
                    # Update transaction with PayStorePe_Coco response
                    cursor.execute("""
                        UPDATE payout_transactions 
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))

                    conn.commit()
                    conn.close()

                    return jsonify({
                        'success': True,
                        'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'requested_amount': amount_to_bank,
                        'charges': charges['charge_amount'],
                        'total_to_deduct': total_wallet_deduction,
                        'status': status
                    }), 200

                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    # Use Bridgmoney_Coco for payout
                    from bridgmoney_coco_service import bridgmoney_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount_to_bank,
                        'bene_name': bank['account_holder_name'],
                        'bene_account': bank['account_number'],
                        'bene_ifsc': bank['ifsc_code'],
                        'bank_name': bank['bank_name']
                    }

                    bm_result = bridgmoney_coco_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if bm_result['success']:
                        status = bm_result.get('status', 'QUEUED')
                        bm_txn_id = bm_result.get('bridgmoney_coco_txn_id', '')

                        print(f"Bridgmoney_Coco settlement initiated - Status: {status}, TxnID: {bm_txn_id}")

                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, bm_txn_id, txn_id))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully. Wallet has been deducted immediately. Will be refunded if payout fails..',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.'
                        }), 200

                    else:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (bm_result.get('message', 'Bridgmoney_Coco transfer failed'), txn_id))
                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': 'Settlement failed',
                            'txn_id': txn_id,
                            'error': bm_result.get('message')
                        }), 400

                else:
                    # For other gateways, keep as PENDING
                    conn.close()
                    return jsonify({
                        'success': True,
                        'message': 'Settlement request created',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'requested_amount': amount_to_bank,
                        'charges': charges['charge_amount'],
                        'total_deducted': total_wallet_deduction,
                        'amount_to_bank': amount_to_bank,
                        'status': 'PENDING'
                    }), 200
                    
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Admin Fetch Fund
@payout_bp.route('/admin/fetch-fund', methods=['POST'])
@jwt_required()
def admin_fetch_fund():
    """
    Admin fetches funds from merchant wallet.
    This reduces merchant's settled balance and increases admin's balance.
    """
    try:
        data = request.json
        admin_id = get_jwt_identity()
        
        required_fields = ['merchant_id', 'amount', 'tpin', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': '{} is required'.format(field)}), 400
        
        # Validate amount
        try:
            fetch_amount = float(data['amount'])
            if fetch_amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount format'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin TPIN
                cursor.execute("SELECT pin_hash FROM admin_users WHERE admin_id = %s", (admin_id,))
                admin = cursor.fetchone()
                
                if not admin or not admin['pin_hash']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400
                
                merchant_id = data['merchant_id']
                reason = data['reason']
                
                # Get settled balance from merchant_wallet
                cursor.execute("""
                    SELECT COALESCE(settled_balance, 0) as available_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                wallet_result = cursor.fetchone()
                available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00
                
                print("=== FETCH FUND DEBUG ===")
                print("Merchant ID: {}".format(merchant_id))
                print("Settled Balance (Available): â‚¹{:.2f}".format(available_balance))
                print("Fetch Amount: â‚¹{:.2f}".format(fetch_amount))
                
                # Check if sufficient balance
                if fetch_amount > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient balance in wallet, remaining balance in wallet: â‚¹{:.2f}'.format(available_balance)
                    }), 400
            
            conn.close()
            
            # Debit merchant wallet using wallet service
            debit_result = wallet_svc.debit_merchant_wallet(
                merchant_id=merchant_id,
                amount=fetch_amount,
                description="Fund fetched by admin - {}".format(reason),
                reference_id=reason
            )
            
            if not debit_result['success']:
                return jsonify({
                    'success': False,
                    'message': debit_result['message']
                }), 400
            
            print("âœ… WALLET DEBITED - Balance Before: â‚¹{:.2f}, Balance After: â‚¹{:.2f}".format(
                debit_result['balance_before'], debit_result['balance_after']))
            
            # Credit admin wallet
            admin_credit = wallet_svc.credit_admin_wallet(
                admin_id=admin_id,
                amount=fetch_amount,
                description="Fund fetched from {} - {}".format(merchant_id, reason),
                reference_id=debit_result['txn_id']
            )
            
            if admin_credit['success']:
                print("âœ… ADMIN WALLET CREDITED - â‚¹{:.2f}".format(fetch_amount))
            
            return jsonify({
                'success': True,
                'message': 'Fund fetched successfully',
                'txn_id': debit_result['txn_id'],
                'amount': fetch_amount,
                'balance_before': debit_result['balance_before'],
                'balance_after': debit_result['balance_after']
            }), 200
            
        except Exception as e:
            print("Error in admin_fetch_fund: {}".format(str(e)))
            if conn:
                conn.rollback()
                conn.close()
            raise e
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
# Client Direct Payout (with bank details in request)
@payout_bp.route('/client/direct-payout', methods=['POST'])
@jwt_required()
def client_direct_payout():
    """
    Process payout with bank details provided directly in the request.
    No need to pre-register bank account.
    """
    try:
        data = request.json
        merchant_id = get_jwt_identity()

        # IP SECURITY CHECK - Validate merchant IP for payout operations
        from ip_security_routes import validate_merchant_ip
        is_valid, message = validate_merchant_ip(merchant_id, '/api/payout/client/direct-payout')
        if not is_valid:
            return jsonify({'success': False, 'message': message}), 403

        # Required fields for direct payout
        required_fields = ['amount', 'tpin', 'account_holder_name', 'account_number', 'ifsc_code', 'bank_name', 'order_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400

        # Optional fields
        payment_type = data.get('payment_type', 'IMPS')  # IMPS, NEFT, RTGS
        purpose = data.get('purpose', 'Payout')
        bene_email = data.get('bene_email', '')
        bene_mobile = data.get('bene_mobile', '')
        callback_url = data.get('callback_url', None)  # Optional callback URL for this transaction

        # Validate payment type
        if payment_type not in ['IMPS', 'NEFT', 'RTGS']:
            return jsonify({'success': False, 'message': 'Invalid payment_type. Must be IMPS, NEFT, or RTGS'}), 400

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
            
            # Check payout limit - maximum 500,000 per transaction
            if amount > 500000:
                return jsonify({'success': False, 'message': 'Transaction out of limit. Maximum payout amount is â‚¹5,00,000 per transaction'}), 400
                
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid amount format'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        try:
            with conn.cursor() as cursor:
                # Check for duplicate order_id for this merchant
                cursor.execute("""
                    SELECT txn_id, status FROM payout_transactions
                    WHERE merchant_id = %s AND order_id = %s
                """, (merchant_id, data['order_id']))
                existing_payout = cursor.fetchone()
                
                if existing_payout:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Payout failed: Duplicate order_id. A payout with order_id {data["order_id"]} already exists',
                        'existing_txn_id': existing_payout['txn_id'],
                        'existing_status': existing_payout['status']
                    }), 400
                
                # Verify merchant TPIN
                cursor.execute("SELECT pin_hash, scheme_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                merchant = cursor.fetchone()

                if not merchant or not merchant['pin_hash']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400

                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400

                # Calculate payout charges based on merchant scheme
                charges = payout_svc.calculate_charges(
                    amount,
                    merchant['scheme_id'],
                    'PAYOUT'
                )

                if not charges:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Unable to calculate payout charges'}), 400

                # Send full requested amount to bank, deduct charges from wallet separately
                net_amount_to_bank = amount  # Full requested amount goes to beneficiary
                total_deduction = amount + charges['charge_amount']  # Total to deduct from wallet

                # Get settled balance from merchant_wallet (this is the withdrawable amount)
                cursor.execute("""
                    SELECT COALESCE(settled_balance, 0) as available_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                wallet_result = cursor.fetchone()
                available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00

                # DEBUG LOGGING
                print(f"=== PAYOUT VALIDATION DEBUG ===")
                print(f"Merchant ID: {merchant_id}")
                print(f"Requested Amount: â‚¹{amount:.2f}")
                print(f"Charges: â‚¹{charges['charge_amount']:.2f}")
                print(f"Total Deduction: â‚¹{total_deduction:.2f}")
                print(f"Settled Balance (Available): â‚¹{available_balance:.2f}")
                print(f"Validation Check: {total_deduction} > {available_balance} = {total_deduction > available_balance}")
                print(f"===============================")

                # Check if settled balance is sufficient (amount + charges)
                if total_deduction > available_balance:
                    print(f"âŒ VALIDATION FAILED - Rejecting payout")
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient balance in wallet, remaining balance in wallet: â‚¹{available_balance:.2f}'
                    }), 400
                
                print(f"âœ… VALIDATION PASSED - Processing payout")
                
                # Get PG partner from service routing for PAYOUT
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE service_type = 'PAYOUT'
                    AND routing_type = 'SINGLE_USER'
                    AND merchant_id = %s
                    AND is_active = TRUE
                    ORDER BY priority ASC
                    LIMIT 1
                """, (merchant_id,))
                routing = cursor.fetchone()

                # If no merchant-specific routing, get ALL_USERS routing
                if not routing:
                    cursor.execute("""
                        SELECT pg_partner FROM service_routing
                        WHERE service_type = 'PAYOUT'
                        AND routing_type = 'ALL_USERS'
                        AND is_active = TRUE
                        ORDER BY priority ASC
                        LIMIT 1
                    """)
                    routing = cursor.fetchone()

                if not routing:
                    conn.close()
                    return jsonify({'success': False, 'message': 'No payout gateway configured'}), 400

                pg_partner = routing['pg_partner']

                # Create payout transaction record
                reference_id = f"DP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                
                # Generate transaction ID based on gateway
                pg_partner_upper = pg_partner.upper()
                if pg_partner_upper in ['PAYTOUCH3_TRENDORA', 'PAYTOUCH_TRENDORA']:
                    txn_id = f"PT3_TREN_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH4_BARRINGER', 'PAYTOUCH_BARRINGER']:
                    txn_id = f"PT4_BAR_TXN{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH5_COCO', 'PAYTOUCH_COCO']:
                    txn_id = f"PT5_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH6_VELTRIX', 'PAYTOUCH_VELTRIX']:
                    txn_id = f"PT6_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_VELTRIX', 'PAYSTOREPE_VELTRIX']:
                    txn_id = f"PSP_VE_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYSTOREPE_COCO', 'PAYSTOREPE_COCO']:
                    txn_id = f"PSP_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    txn_id = f"BM_CO_TXN_{uuid.uuid4().hex[:12].upper()}"
                elif pg_partner_upper in ['PAYTOUCH2', 'PAYTOUCH_GROSMART']:
                    txn_id = f"PT2_GROS_TXN{uuid.uuid4().hex[:12].upper()}"
                else:
                    # Default for other gateways
                    txn_id = f"TXN{uuid.uuid4().hex[:16].upper()}"

                cursor.execute("""
                    INSERT INTO payout_transactions
                    (txn_id, reference_id, order_id, merchant_id, amount, charge_amount, charge_type,
                     net_amount, bene_name, bene_email, bene_mobile, bene_bank, account_no,
                     ifsc_code, payment_type, purpose, callback_url, pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'INITIATED', NOW())
                """, (txn_id, reference_id, data['order_id'], merchant_id, total_deduction,
                      charges['charge_amount'], charges['charge_type'], net_amount_to_bank,
                      data['account_holder_name'], bene_email, bene_mobile, data['bank_name'],
                      data['account_number'], data['ifsc_code'], payment_type, purpose, callback_url, pg_partner))

                conn.commit()

                # DEDUCT WALLET IMMEDIATELY - after transaction created, before calling gateway API
                # Wallet will be refunded if payout fails via callback
                debit_result = wallet_svc.debit_merchant_wallet(
                    merchant_id=merchant_id,
                    amount=total_deduction,
                    description=f"Payout: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                    reference_id=txn_id
                )
                
                if not debit_result['success']:
                    # Rollback transaction record if wallet deduction fails
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED', error_message = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (f"Wallet deduction failed: {debit_result['message']}", txn_id))
                    conn.commit()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': debit_result['message']
                    }), 400
                
                print(f"âœ… WALLET DEBITED IMMEDIATELY - Balance: â‚¹{debit_result['balance_before']:.2f} â†’ â‚¹{debit_result['balance_after']:.2f}")
                wallet_balance_after_deduction = debit_result['balance_after']

                # Process through payment gateway (pg_partner_upper already defined above)

                if pg_partner_upper == 'PAYU':
                    transfer_data = [{
                        'reference_id': reference_id,
                        'amount': net_amount_to_bank,
                        'bene_name': data['account_holder_name'],
                        'bene_email': bene_email,
                        'bene_mobile': bene_mobile,
                        'account_no': data['account_number'],
                        'ifsc_code': data['ifsc_code'],
                        'payment_type': payment_type,
                        'purpose': purpose
                    }]

                    payu_result = payu_payout_svc.initiate_transfer(transfer_data)

                    if payu_result['success']:
                        # Update status to QUEUED (wallet already deducted)
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'QUEUED', updated_at = NOW()
                            WHERE txn_id = %s
                        """, (txn_id,))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': 'QUEUED',
                            'wallet_balance': wallet_balance_after_deduction,  # Balance after deduction
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (payu_result.get('error', 'PayU transfer failed'), txn_id))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': payu_result.get('error')
                        }), 400

                elif pg_partner_upper == 'MUDRAPE':
                    mudrape_result = mudrape_service.call_imps_payout_api(
                        account_number=data['account_number'],
                        ifsc_code=data['ifsc_code'],
                        client_txn_id=reference_id,
                        amount=net_amount_to_bank,
                        beneficiary_name=data['account_holder_name']
                    )

                    if mudrape_result['success']:
                        status = mudrape_result.get('status', 'INITIATED')
                        mudrape_txn_id = mudrape_result.get('mudrape_txn_id', '')

                        print(f"Mudrape payout initiated - Status: {status}, TxnID: {mudrape_txn_id}")

                        # Wallet already deducted - just update transaction status
                        if status == 'SUCCESS':
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        elif status == 'FAILED':
                            # Refund wallet for failed transactions
                            refund_result = wallet_svc.credit_merchant_wallet(
                                merchant_id=merchant_id,
                                amount=total_deduction,
                                description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                                reference_id=txn_id
                            )
                            
                            if refund_result['success']:
                                print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                            
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        else:
                            # PENDING/INITIATED - wallet already deducted, will be refunded if it fails later
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))

                        conn.commit()
                        
                        # If status is still INITIATED (pending), check status from Mudrape API
                        if status == 'INITIATED':
                            print(f"Checking status from Mudrape for reference_id: {reference_id}")
                            import time
                            time.sleep(2)  # Wait 2 seconds before checking
                            
                            status_result = mudrape_service.check_payout_status(reference_id)
                            if status_result.get('success'):
                                updated_status = status_result.get('status', 'INITIATED')
                                utr = status_result.get('utr')
                                completed_at_from_api = status_result.get('completed_at')
                                
                                print(f"Mudrape status check result - Status: {updated_status}, UTR: {utr}, Completed: {completed_at_from_api}")
                                
                                # Refund wallet if status changed to FAILED
                                if updated_status == 'FAILED' and status != 'FAILED':
                                    refund_result = wallet_svc.credit_merchant_wallet(
                                        merchant_id=merchant_id,
                                        amount=total_deduction,
                                        description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                                        reference_id=txn_id
                                    )
                                    
                                    if refund_result['success']:
                                        print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                                
                                # Update with latest status
                                if updated_status in ['SUCCESS', 'FAILED']:
                                    if completed_at_from_api:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = %s, updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, completed_at_from_api, txn_id))
                                    else:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, txn_id))
                                else:
                                    cursor.execute("""
                                        UPDATE payout_transactions 
                                        SET status = %s, utr = %s, updated_at = NOW()
                                        WHERE txn_id = %s
                                    """, (updated_status, utr, txn_id))
                                
                                conn.commit()
                                status = updated_status
                        
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.' if status != 'SUCCESS' else 'Payout completed successfully. Wallet has been deducted.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': status,
                            'wallet_balance': wallet_balance_after_deduction,  # Balance after deduction
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.' if status not in ['SUCCESS', 'FAILED'] else None,
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mudrape_result.get('message', 'Mudrape transfer failed'), txn_id))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': mudrape_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH':
                    # Use PayTouch for payout
                    # PayTouch requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': net_amount_to_bank,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch_result = paytouch_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch_result['success']:
                        status = paytouch_result.get('status', 'QUEUED')
                        paytouch_txn_id = paytouch_result.get('paytouch_txn_id', '')
                        
                        # Wallet already deducted - just update transaction
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': status,
                            'wallet_balance': wallet_balance_after_deduction,  # Balance after deduction
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch_result.get('message', 'PayTouch transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH2':
                    # Use PayTouch2 for payout
                    # PayTouch2 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': net_amount_to_bank,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch2_result = paytouch2_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch2_result['success']:
                        status = paytouch2_result.get('status', 'QUEUED')
                        paytouch2_txn_id = paytouch2_result.get('paytouch2_txn_id', '')
                        
                        # Wallet already deducted - just update transaction
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch2_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': status,
                            'wallet_balance': wallet_balance_after_deduction,  # Balance after deduction
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch2_result.get('message', 'PayTouch2 transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch2_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH3_TRENDORA':
                    # Use PayTouch3_Trendora for payout
                    # PayTouch3 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': net_amount_to_bank,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data['bank_name']
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch3_result = paytouch3_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch3_result['success']:
                        status = paytouch3_result.get('status', 'QUEUED')
                        paytouch3_txn_id = paytouch3_result.get('paytouch3_txn_id', '')
                        
                        # Wallet already deducted - just update transaction
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch3_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_to_deduct': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': status,
                            'wallet_balance': wallet_balance_after_deduction,  # Balance after deduction
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch3_result.get('message', 'PayTouch3_Trendora transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch3_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH4_BARRINGER':
                    # Use PayTouch4_Barringer for payout
                    # PayTouch4 requirements: request_id=order_id, currency=INR, narration=Truaxis, payment_mode=IMPS, bank_branch=oooo
                    from paytouch4_service import paytouch4_service
                    
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount,  # Changed from amount_to_bank to amount
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', '')
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch4_result = paytouch4_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch4_result['success']:
                        status = paytouch4_result.get('status', 'QUEUED')
                        paytouch4_txn_id = paytouch4_result.get('paytouch4_txn_id', '')
                        
                        # Wallet already deducted - just update transaction
                        print(f"PayTouch4_Barringer settlement initiated - Status: {status}, TxnID: {paytouch4_txn_id}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch4_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch4_result.get('message', 'PayTouch4_Barringer transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch4_result.get('message')
                        }), 400
                
                elif pg_partner_upper == 'PAYTOUCH5_COCO':
                    # Use PayTouch5_Coco for payout
                    from paytouch5_coco_service import paytouch5_service
                    
                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount,  # Changed from amount_to_bank to amount
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', '')
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }
                    
                    paytouch5_result = paytouch5_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )
                    
                    if paytouch5_result['success']:
                        status = paytouch5_result.get('status', 'QUEUED')
                        paytouch5_txn_id = paytouch5_result.get('paytouch5_txn_id', '')
                        
                        # Wallet already deducted - just update transaction
                        print(f"PayTouch5_Coco settlement initiated - Status: {status}, TxnID: {paytouch5_txn_id}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch5_txn_id, txn_id))
                        
                        conn.commit()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )
                        
                        if refund_result['success']:
                            print(f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (paytouch5_result.get('message', 'PayTouch5_Coco transfer failed'), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch5_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYTOUCH6_VELTRIX':
                    # Use PayTouch6_Veltrix for payout
                    from paytouch6_veltrix_service import paytouch6_service

                    payout_data = {
                        'reference_id': reference_id,  # This will be used as request_id
                        'amount': amount,  # Changed from amount_to_bank to amount
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', '')
                        # payment_mode, narration, bank_branch are hardcoded in service
                    }

                    paytouch6_result = paytouch6_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if paytouch6_result['success']:
                        status = paytouch6_result.get('status', 'QUEUED')
                        paytouch6_txn_id = paytouch6_result.get('paytouch6_txn_id', '')

                        # Wallet already deducted - just update transaction
                        print(
                            f"PayTouch6_Veltrix settlement initiated - "
                            f"Status: {status}, TxnID: {paytouch6_txn_id}"
                        )

                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, paytouch6_txn_id, txn_id))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200

                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: â‚¹{amount:.2f} + Charges: â‚¹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )

                        if refund_result['success']:
                            print(
                                f"âœ… WALLET REFUNDED - Balance: â‚¹{refund_result['balance_before']:.2f} â†’ â‚¹{refund_result['balance_after']:.2f}"
                            )

                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paytouch6_result.get('message', 'PayTouch6_Veltrix transfer failed'),
                            txn_id
                        ))

                        conn.commit()

                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': paytouch6_result.get('message')
                        }), 400

                elif pg_partner_upper == 'PAYSTOREPE_VELTRIX':
                    # PayStorePe payout
                    from paystorepe_veltrix_service import paystorepe_veltrix_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', ''),
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': payment_type,
                        'callback_url': callback_url,
                        'remarks': purpose
                    }

                    paystorepe_result = paystorepe_veltrix_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    # Wallet already deducted - just update transaction
                    print(f"PayStorePe_Veltrix settlement initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    cursor.execute("""
                        UPDATE payout_transactions 
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))

                    conn.commit()
                    conn.close()

                    return jsonify({
                        'success': True,
                        'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'amount': amount,
                        'charges': charges['charge_amount'],
                        'total_deducted': total_deduction,
                        'status': status,
                        'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                        'beneficiary': {
                            'name': data['account_holder_name'],
                            'account': data['account_number'],
                            'bank': data.get('bank_name', 'Bank Account')
                        }
                    }), 200

                elif pg_partner_upper == 'PAYSTOREPE_COCO':
                    # PayStorePe payout
                    from paystorepe_coco_service import paystorepe_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', ''),
                        'bene_mobile': bene_mobile,
                        'bene_email': bene_email,
                        'payment_mode': payment_type,
                        'callback_url': callback_url,
                        'remarks': purpose
                    }

                    paystorepe_result = paystorepe_coco_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if not paystorepe_result.get('success'):
                        # Gateway rejected the payout before merchant wallet debit.
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'FAILED',
                                pg_txn_id = %s,
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            paystorepe_result.get('paystorepe_txn_id'),
                            paystorepe_result.get('message', 'PayStorePe payout failed'),
                            txn_id
                        ))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': paystorepe_result.get(
                                'message',
                                'PayStorePe payout failed'
                            ),
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'status': 'FAILED'
                        }), 400

                    status = paystorepe_result.get('status', 'QUEUED')
                    paystorepe_txn_id = paystorepe_result.get('paystorepe_txn_id', '')

                    # Wallet already deducted - just update transaction
                    print(f"PayStorePe_Coco settlement initiated - Status: {status}, TxnID: {paystorepe_txn_id}")

                    cursor.execute("""
                        UPDATE payout_transactions 
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, paystorepe_txn_id, txn_id))

                    conn.commit()
                    conn.close()

                    return jsonify({
                        'success': True,
                        'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'amount': amount,
                        'charges': charges['charge_amount'],
                        'total_deducted': total_deduction,
                        'status': status,
                        'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                        'beneficiary': {
                            'name': data['account_holder_name'],
                            'account': data['account_number'],
                            'bank': data.get('bank_name', 'Bank Account')
                        }
                    }), 200

                elif pg_partner_upper in ['BRIDGMONEY_COCO', 'BRIDGMONEY_COCO_PAYOUT', 'BRIDGMONEY']:
                    # Use Bridgmoney_Coco for payout
                    from bridgmoney_coco_service import bridgmoney_coco_service

                    payout_data = {
                        'reference_id': reference_id,
                        'amount': amount,
                        'bene_name': data['account_holder_name'],
                        'bene_account': data['account_number'],
                        'bene_ifsc': data['ifsc_code'],
                        'bank_name': data.get('bank_name', '')
                    }

                    bm_result = bridgmoney_coco_service.initiate_payout(
                        merchant_id=merchant_id,
                        payout_data=payout_data,
                        admin_id=None
                    )

                    if bm_result['success']:
                        status = bm_result.get('status', 'QUEUED')
                        bm_txn_id = bm_result.get('bridgmoney_coco_txn_id', '')

                        print(f"Bridgmoney_Coco settlement initiated - Status: {status}, TxnID: {bm_txn_id}")

                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = %s, pg_txn_id = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (status, bm_txn_id, txn_id))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully. Wallet has been deducted immediately.',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'status': status,
                            'note': 'Wallet has been deducted immediately. Will be refunded if payout fails.',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200

                    else:
                        # Payout failed - refund the wallet
                        refund_result = wallet_svc.credit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=total_deduction,
                            description=f"Payout refund: ₹{amount:.2f} + Charges: ₹{charges['charge_amount']:.2f}",
                            reference_id=txn_id
                        )

                        if refund_result['success']:
                            print(
                                f"✅ WALLET REFUNDED - Balance: ₹{refund_result['balance_before']:.2f} → ₹{refund_result['balance_after']:.2f}"
                            )

                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                completed_at = NOW(),
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (bm_result.get('message', 'Bridgmoney_Coco transfer failed'), txn_id))
                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': False,
                            'message': 'Payout failed. Wallet has been refunded.',
                            'txn_id': txn_id,
                            'error': bm_result.get('message')
                        }), 400

                else:
                    conn.close()
                    return jsonify({
                        'success': True,
                        'message': 'Payout request created',
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'order_id': data['order_id'],
                        'requested_amount': amount,
                        'charges': charges['charge_amount'],
                        'total_deducted': total_deduction,
                        'amount_to_beneficiary': net_amount_to_bank,
                        'status': 'INITIATED',
                        'beneficiary': {
                            'name': data['account_holder_name'],
                            'account_number': data['account_number'],
                            'ifsc_code': data['ifsc_code'],
                            'bank_name': data['bank_name']
                        }
                    }), 200

        except Exception as e:
            # DO NOT ROLLBACK - the INSERT was already committed at line 1247
            # Rolling back here would delete the payout record but wallet was already debited
            print(f"âŒ Error in client_direct_payout after INSERT: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.close()
            # Return error but don't rollback the transaction
            return jsonify({'success': False, 'message': f'Payout processing error: {str(e)}'}), 500

    except Exception as e:
        print(f"âŒ Error in client_direct_payout: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



# Get Payout Report - Admin
@payout_bp.route('/admin/payout-report', methods=['GET'])
@jwt_required()
def get_admin_payout_report():
    """Get payout report with pagination (admin only)"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        # Get filter parameters
        merchant_id = request.args.get('merchant_id')
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        search = request.args.get('search')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Build main query with pagination
                query = """
                    SELECT 
                        pt.id,
                        pt.txn_id,
                        pt.merchant_id,
                        pt.reference_id,
                        pt.order_id,
                        pt.batch_id,
                        pt.amount,
                        pt.charge_amount,
                        pt.charge_type,
                        pt.net_amount,
                        pt.bene_name,
                        pt.bene_email,
                        pt.bene_mobile,
                        pt.bene_bank,
                        pt.ifsc_code,
                        pt.account_no,
                        pt.vpa,
                        pt.payment_type,
                        pt.purpose,
                        pt.status,
                        pt.pg_partner,
                        pt.pg_txn_id,
                        pt.bank_ref_no,
                        pt.utr,
                        pt.name_with_bank,
                        pt.name_match_score,
                        pt.error_message,
                        pt.remarks,
                        pt.callback_url,
                        pt.created_at,
                        pt.updated_at,
                        pt.completed_at,
                        m.full_name,
                        m.mobile,
                        m.full_name as payer_name
                    FROM payout_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE 1=1
                """
                params = []
                
                if merchant_id:
                    query += " AND pt.merchant_id = %s"
                    params.append(merchant_id)
                
                if status:
                    query += " AND pt.status = %s"
                    params.append(status)
                
                # Add search filter
                if search:
                    query += """ AND (
                        pt.txn_id LIKE %s OR 
                        pt.reference_id LIKE %s OR 
                        pt.order_id LIKE %s OR
                        pt.merchant_id LIKE %s OR 
                        m.full_name LIKE %s OR
                        pt.bene_name LIKE %s OR
                        pt.account_no LIKE %s OR
                        pt.ifsc_code LIKE %s OR
                        pt.utr LIKE %s OR
                        pt.bank_ref_no LIKE %s
                    )"""
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern] * 10)
                
                if from_date:
                    query += " AND DATE(pt.created_at) >= %s"
                    params.append(from_date)
                
                if to_date:
                    query += " AND DATE(pt.created_at) <= %s"
                    params.append(to_date)
                
                query += " ORDER BY pt.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                payouts = cursor.fetchall()
                
                # Get total count with same filters
                count_query = """
                    SELECT COUNT(*) as total 
                    FROM payout_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE 1=1
                """
                count_params = []
                
                if merchant_id:
                    count_query += " AND pt.merchant_id = %s"
                    count_params.append(merchant_id)
                
                if status:
                    count_query += " AND pt.status = %s"
                    count_params.append(status)
                
                if search:
                    count_query += """ AND (
                        pt.txn_id LIKE %s OR 
                        pt.reference_id LIKE %s OR 
                        pt.order_id LIKE %s OR
                        pt.merchant_id LIKE %s OR 
                        m.full_name LIKE %s OR
                        pt.bene_name LIKE %s OR
                        pt.account_no LIKE %s OR
                        pt.ifsc_code LIKE %s OR
                        pt.utr LIKE %s OR
                        pt.bank_ref_no LIKE %s
                    )"""
                    search_pattern = f"%{search}%"
                    count_params.extend([search_pattern] * 10)
                
                if from_date:
                    count_query += " AND DATE(pt.created_at) >= %s"
                    count_params.append(from_date)
                
                if to_date:
                    count_query += " AND DATE(pt.created_at) <= %s"
                    count_params.append(to_date)
                
                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['total']
                
                # Format the data properly
                formatted_payouts = []
                for payout in payouts:
                    formatted_payout = {
                        'id': payout['id'],
                        'txn_id': payout['txn_id'],
                        'merchant_id': payout['merchant_id'],
                        'reference_id': payout['reference_id'],
                        'order_id': payout.get('order_id'),
                        'batch_id': payout['batch_id'],
                        'amount': float(payout['amount']) if payout['amount'] else 0.0,
                        'charge_amount': float(payout['charge_amount']) if payout['charge_amount'] else 0.0,
                        'charge_type': payout['charge_type'],
                        'net_amount': float(payout['net_amount']) if payout['net_amount'] else 0.0,
                        'bene_name': payout['bene_name'],
                        'bene_email': payout['bene_email'],
                        'bene_mobile': payout['bene_mobile'],
                        'bene_bank': payout['bene_bank'],
                        'ifsc_code': payout['ifsc_code'],
                        'account_no': payout['account_no'],
                        'vpa': payout['vpa'],
                        'payment_type': payout['payment_type'],
                        'purpose': payout['purpose'],
                        'status': payout['status'],
                        'pg_partner': payout['pg_partner'],
                        'pg_txn_id': payout['pg_txn_id'],
                        'bank_ref_no': payout['bank_ref_no'],
                        'utr': payout['utr'],
                        'name_with_bank': payout['name_with_bank'],
                        'name_match_score': payout['name_match_score'],
                        'error_message': payout['error_message'],
                        'remarks': payout['remarks'],
                        'callback_url': payout['callback_url'],
                        'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['created_at'] else None,
                        'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['updated_at'] else None,
                        'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['completed_at'] else None,
                        'full_name': payout['full_name'],
                        'mobile': payout['mobile'],
                        'payer_name': payout['payer_name']
                    }
                    formatted_payouts.append(formatted_payout)
            
                return jsonify({
                    'success': True, 
                    'data': formatted_payouts,
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
        print(f"Error in get_admin_payout_report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/admin/payout-report/all', methods=['GET'])
@jwt_required()
def get_admin_payout_report_all():
    """Get ALL payout transactions (admin only) with filters - for download - OPTIMIZED with batch processing"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get filter parameters
            status = request.args.get('status')
            search = request.args.get('search')
            from_date = request.args.get('from_date')
            to_date = request.args.get('to_date')
            
            # OPTIMIZATION 1: First get total count to show progress
            count_query = """
                SELECT COUNT(*) as total
                FROM payout_transactions pt
                WHERE 1=1
            """
            count_params = []
            
            if status:
                count_query += " AND pt.status = %s"
                count_params.append(status)
            
            if search:
                count_query += """ AND (
                    pt.txn_id LIKE %s OR
                    pt.reference_id LIKE %s OR
                    pt.order_id LIKE %s OR
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s
                )"""
                search_pattern = f"%{search}%"
                count_params.extend([search_pattern] * 6)
            
            if from_date:
                count_query += " AND DATE(pt.created_at) >= %s"
                count_params.append(from_date)
            
            if to_date:
                count_query += " AND DATE(pt.created_at) <= %s"
                count_params.append(to_date)
            
            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()['total']
            
            print(f"Fetching {total_count} payout records for download...")
            
            # OPTIMIZATION 2: Fetch in batches to prevent timeout
            batch_size = 5000  # Process 5000 records at a time
            all_payouts = []
            offset = 0
            
            while offset < total_count:
                # Build query with LIMIT and OFFSET
                query = """
                    SELECT 
                        pt.id,
                        pt.txn_id,
                        pt.merchant_id,
                        pt.admin_id,
                        pt.reference_id,
                        pt.order_id,
                        pt.batch_id,
                        pt.amount,
                        pt.charge_amount,
                        pt.charge_type,
                        pt.net_amount,
                        pt.bene_name,
                        pt.bene_email,
                        pt.bene_mobile,
                        pt.bene_bank,
                        pt.ifsc_code,
                        pt.account_no,
                        pt.vpa,
                        pt.payment_type,
                        pt.purpose,
                        pt.status,
                        pt.pg_partner,
                        pt.pg_txn_id,
                        pt.bank_ref_no,
                        pt.utr,
                        pt.name_with_bank,
                        pt.name_match_score,
                        pt.error_message,
                        pt.remarks,
                        pt.callback_url,
                        pt.created_at,
                        pt.updated_at,
                        pt.completed_at,
                        m.full_name,
                        m.mobile
                    FROM payout_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE 1=1
                """
                params = []
                
                if status:
                    query += " AND pt.status = %s"
                    params.append(status)
                
                if search:
                    query += """ AND (
                        pt.txn_id LIKE %s OR
                        pt.reference_id LIKE %s OR
                        pt.order_id LIKE %s OR
                        pt.bene_name LIKE %s OR
                        pt.account_no LIKE %s OR
                        pt.ifsc_code LIKE %s OR
                        m.full_name LIKE %s
                    )"""
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern] * 7)
                
                if from_date:
                    query += " AND DATE(pt.created_at) >= %s"
                    params.append(from_date)
                
                if to_date:
                    query += " AND DATE(pt.created_at) <= %s"
                    params.append(to_date)
                
                query += " ORDER BY pt.created_at DESC LIMIT %s OFFSET %s"
                params.extend([batch_size, offset])
                
                # Execute batch query
                cursor.execute(query, params)
                batch_payouts = cursor.fetchall()
                
                if not batch_payouts:
                    break
                
                # Format the batch data
                for payout in batch_payouts:
                    formatted_payout = {
                        'id': payout.get('id'),
                        'txn_id': payout.get('txn_id'),
                        'merchant_id': payout.get('merchant_id'),
                        'admin_id': payout.get('admin_id'),
                        'reference_id': payout.get('reference_id'),
                        'order_id': payout.get('order_id'),
                        'batch_id': payout.get('batch_id'),
                        'amount': float(payout['amount']) if payout.get('amount') else 0.0,
                        'charge_amount': float(payout['charge_amount']) if payout.get('charge_amount') else 0.0,
                        'charge_type': payout.get('charge_type'),
                        'net_amount': float(payout['net_amount']) if payout.get('net_amount') else 0.0,
                        'bene_name': payout.get('bene_name'),
                        'bene_email': payout.get('bene_email'),
                        'bene_mobile': payout.get('bene_mobile'),
                        'bene_bank': payout.get('bene_bank'),
                        'ifsc_code': payout.get('ifsc_code'),
                        'account_no': payout.get('account_no'),
                        'vpa': payout.get('vpa'),
                        'payment_type': payout.get('payment_type'),
                        'purpose': payout.get('purpose'),
                        'status': payout.get('status'),
                        'pg_partner': payout.get('pg_partner'),
                        'pg_txn_id': payout.get('pg_txn_id'),
                        'bank_ref_no': payout.get('bank_ref_no'),
                        'utr': payout.get('utr') or payout.get('bank_ref_no'),
                        'name_with_bank': payout.get('name_with_bank'),
                        'name_match_score': payout.get('name_match_score'),
                        'error_message': payout.get('error_message'),
                        'remarks': payout.get('remarks'),
                        'callback_url': payout.get('callback_url'),
                        'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout.get('created_at') else None,
                        'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout.get('updated_at') else None,
                        'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout.get('completed_at') else None,
                        'full_name': payout.get('full_name'),
                        'mobile': payout.get('mobile'),
                        'payer_name': payout.get('full_name') or 'Admin Payout'
                    }
                    all_payouts.append(formatted_payout)
                
                offset += batch_size
                print(f"Processed {len(all_payouts)}/{total_count} records...")
        
        conn.close()
        print(f"âœ“ Successfully fetched {len(all_payouts)} payout records")
        return jsonify({'success': True, 'data': all_payouts, 'count': len(all_payouts)}), 200
    
    except Exception as e:
        print(f"Error in get_admin_payout_report_all: {e}")
        import traceback
        error_details = traceback.format_exc()
        print(f"Full traceback: {error_details}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@payout_bp.route('/admin/payout-report/download-csv', methods=['GET'])
@jwt_required()
def download_admin_payout_report_csv():
    """Download payout report as CSV file - optimized for large datasets (streaming)"""
    try:
        # Get filter parameters
        status = request.args.get('status')
        search = request.args.get('search')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        def generate_csv():
            """Generator function to stream CSV data"""
            conn = get_db_connection()
            if not conn:
                yield "error,Database connection failed\n"
                return
            
            try:
                with conn.cursor() as cursor:
                    # Build query
                    query = """
                        SELECT 
                            pt.txn_id,
                            pt.merchant_id,
                            pt.admin_id,
                            pt.reference_id,
                            pt.order_id,
                            pt.amount,
                            pt.charge_amount,
                            pt.net_amount,
                            pt.bene_name,
                            pt.bene_mobile,
                            pt.bene_bank,
                            pt.ifsc_code,
                            pt.account_no,
                            pt.payment_type,
                            pt.status,
                            pt.pg_partner,
                            pt.utr,
                            pt.created_at,
                            pt.completed_at,
                            m.full_name as merchant_name
                        FROM payout_transactions pt
                        LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                        WHERE 1=1
                    """
                    params = []
                    
                    if status:
                        query += " AND pt.status = %s"
                        params.append(status)
                    
                    if search:
                        query += """ AND (
                            pt.txn_id LIKE %s OR
                            pt.reference_id LIKE %s OR
                            pt.order_id LIKE %s OR
                            pt.bene_name LIKE %s OR
                            pt.account_no LIKE %s OR
                            pt.ifsc_code LIKE %s OR
                            m.full_name LIKE %s
                        )"""
                        search_pattern = f"%{search}%"
                        params.extend([search_pattern] * 7)
                    
                    if from_date:
                        query += " AND DATE(pt.created_at) >= %s"
                        params.append(from_date)
                    
                    if to_date:
                        query += " AND DATE(pt.created_at) <= %s"
                        params.append(to_date)
                    
                    query += " ORDER BY pt.created_at DESC"
                    
                    # Write CSV header
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow([
                        'Transaction ID', 'Merchant ID', 'Admin ID', 'Reference ID', 'Order ID',
                        'Amount', 'Charge', 'Net Amount', 'Beneficiary Name', 'Mobile',
                        'Bank', 'IFSC', 'Account Number', 'Payment Type', 'Status',
                        'Gateway', 'UTR', 'Created Date', 'Created Time', 'Completed Date', 'Completed Time', 'Merchant Name'
                    ])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                    
                    # Execute query and stream results
                    cursor.execute(query, params)
                    
                    # Fetch and write in batches
                    batch_size = 1000
                    while True:
                        rows = cursor.fetchmany(batch_size)
                        if not rows:
                            break
                        
                        for row in rows:
                            # Split created_at into date and time
                            created_date = ''
                            created_time = ''
                            if row.get('created_at'):
                                created_dt = row['created_at']
                                created_date = created_dt.strftime('%Y-%m-%d')
                                created_time = created_dt.strftime('%H:%M:%S')
                            
                            # Split completed_at into date and time
                            completed_date = ''
                            completed_time = ''
                            if row.get('completed_at'):
                                completed_dt = row['completed_at']
                                completed_date = completed_dt.strftime('%Y-%m-%d')
                                completed_time = completed_dt.strftime('%H:%M:%S')
                            
                            writer.writerow([
                                row.get('txn_id', ''),
                                row.get('merchant_id', ''),
                                row.get('admin_id', ''),
                                row.get('reference_id', ''),
                                row.get('order_id', ''),
                                row.get('amount', 0),
                                row.get('charge_amount', 0),
                                row.get('net_amount', 0),
                                row.get('bene_name', ''),
                                row.get('bene_mobile', ''),
                                row.get('bene_bank', ''),
                                row.get('ifsc_code', ''),
                                row.get('account_no', ''),
                                row.get('payment_type', ''),
                                row.get('status', ''),
                                row.get('pg_partner', ''),
                                row.get('utr', ''),
                                created_date,
                                created_time,
                                completed_date,
                                completed_time,
                                row.get('merchant_name', '')
                            ])
                        
                        yield output.getvalue()
                        output.seek(0)
                        output.truncate(0)
                
            finally:
                conn.close()
        
        # Generate filename with timestamp
        filename = f"payout_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Return streaming response
        return Response(
            stream_with_context(generate_csv()),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        print(f"Error in download_admin_payout_report_csv: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/admin/payout-report/today', methods=['GET'])
@jwt_required()
def get_admin_payout_report_today():
    """Get ALL payout transactions for today (admin only) - for report download"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    pt.*,
                    m.full_name,
                    m.mobile,
                    m.full_name as payer_name
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE DATE(pt.created_at) = CURDATE()
                ORDER BY pt.created_at DESC
            """
            
            cursor.execute(query)
            payouts = cursor.fetchall()
            
            # Format the data properly
            formatted_payouts = []
            for payout in payouts:
                formatted_payout = {
                    'id': payout['id'],
                    'txn_id': payout['txn_id'],
                    'merchant_id': payout['merchant_id'],
                    'reference_id': payout['reference_id'],
                    'order_id': payout.get('order_id'),
                    'batch_id': payout['batch_id'],
                    'amount': float(payout['amount']) if payout['amount'] else 0.0,
                    'charge_amount': float(payout['charge_amount']) if payout['charge_amount'] else 0.0,
                    'charge_type': payout['charge_type'],
                    'net_amount': float(payout['net_amount']) if payout['net_amount'] else 0.0,
                    'bene_name': payout['bene_name'],
                    'bene_email': payout['bene_email'],
                    'bene_mobile': payout['bene_mobile'],
                    'bene_bank': payout['bene_bank'],
                    'ifsc_code': payout['ifsc_code'],
                    'account_no': payout['account_no'],
                    'vpa': payout['vpa'],
                    'payment_type': payout['payment_type'],
                    'purpose': payout['purpose'],
                    'status': payout['status'],
                    'pg_partner': payout['pg_partner'],
                    'pg_txn_id': payout['pg_txn_id'],
                    'bank_ref_no': payout['bank_ref_no'],
                    'utr': payout['utr'],
                    'name_with_bank': payout['name_with_bank'],
                    'name_match_score': payout['name_match_score'],
                    'error_message': payout['error_message'],
                    'remarks': payout['remarks'],
                    'callback_url': payout['callback_url'],
                    'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['created_at'] else None,
                    'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['updated_at'] else None,
                    'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['completed_at'] else None,
                    'full_name': payout['full_name'],
                    'mobile': payout['mobile'],
                    'payer_name': payout['payer_name']
                }
                formatted_payouts.append(formatted_payout)
        
        conn.close()
        return jsonify({'success': True, 'data': formatted_payouts, 'count': len(formatted_payouts)}), 200
        
    except Exception as e:
        print(f"Error in get_admin_payout_report_today: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# Get Pending Payouts - Admin
@payout_bp.route('/admin/pending-payouts', methods=['GET'])
@jwt_required()
def get_pending_payouts():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT pt.*, m.full_name, m.mobile
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.status IN ('FAILED', 'INITIATED', 'INPROCESS')
                ORDER BY pt.created_at DESC
            """)
            payouts = cursor.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'data': payouts}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get Admin Wallet Overview
@payout_bp.route('/admin/wallet-overview', methods=['GET'])
@jwt_required()
def get_admin_wallet_overview():
    try:
        admin_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM admin_wallet WHERE admin_id = %s
            """, (admin_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                wallet = {'main_balance': 0, 'unsettled_balance': 0}
        
        conn.close()
        return jsonify({'success': True, 'data': wallet}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get Admin Wallet Statement
@payout_bp.route('/admin/wallet-statement', methods=['GET'])
@jwt_required()
def get_admin_wallet_statement():
    try:
        admin_id = get_jwt_identity()
        wallet_type = request.args.get('wallet_type', 'MAIN')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            query = """
                SELECT * FROM admin_wallet_transactions
                WHERE admin_id = %s AND wallet_type = %s
            """
            params = [admin_id, wallet_type]
            
            if from_date:
                query += " AND DATE(created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(created_at) <= %s"
                params.append(to_date)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'data': transactions}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get Client Wallet Statement (Unsettled)
@payout_bp.route('/client/wallet-statement', methods=['GET'])
@jwt_required()
def get_client_wallet_statement():
    try:
        merchant_id = get_jwt_identity()
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            query = """
                SELECT * FROM wallet_transactions
                WHERE merchant_id = %s
            """
            params = [merchant_id]
            
            if from_date:
                query += " AND DATE(created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(created_at) <= %s"
                params.append(to_date)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'data': transactions}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Get Fund Requests - Client view
@payout_bp.route('/client/fund-requests', methods=['GET'])
@jwt_required()
def get_client_fund_requests():
    try:
        merchant_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM fund_requests
                WHERE merchant_id = %s
                ORDER BY requested_at DESC
            """, (merchant_id,))
            
            requests_list = cursor.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'data': requests_list}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get Unsettled Wallet Balance - Client
@payout_bp.route('/client/unsettled-wallet', methods=['GET'])
@jwt_required()
def get_unsettled_wallet():
    try:
        merchant_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT balance FROM merchant_unsettled_wallet WHERE merchant_id = %s
            """, (merchant_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                wallet = {'balance': 0}
        
        conn.close()
        return jsonify({'success': True, 'data': wallet}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Get Payout Report - Client
@payout_bp.route('/client/report', methods=['GET'])
@jwt_required()
def get_client_payout_report():
    """Get payout report for merchant with search and date filters"""
    try:
        merchant_id = get_jwt_identity()
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        search = request.args.get('search')  # New: search parameter

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        with conn.cursor() as cursor:
            query = """
                SELECT
                    pt.id,
                    pt.txn_id,
                    pt.merchant_id,
                    pt.reference_id,
                    pt.order_id,
                    pt.batch_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.charge_type,
                    pt.net_amount,
                    pt.bene_name,
                    pt.bene_email,
                    pt.bene_mobile,
                    pt.bene_bank,
                    pt.ifsc_code,
                    pt.account_no,
                    pt.vpa,
                    pt.payment_type,
                    pt.purpose,
                    pt.status,
                    pt.pg_partner,
                    pt.pg_txn_id,
                    pt.bank_ref_no,
                    pt.utr,
                    pt.name_with_bank,
                    pt.name_match_score,
                    pt.error_message,
                    pt.remarks,
                    pt.callback_url,
                    pt.created_at,
                    pt.updated_at,
                    pt.completed_at,
                    m.full_name,
                    m.mobile
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id = %s
            """
            params = [merchant_id]

            if status:
                query += " AND pt.status = %s"
                params.append(status)

            # Add search filter (searches across multiple fields)
            if search:
                query += """ AND (
                    pt.txn_id LIKE %s OR
                    pt.reference_id LIKE %s OR
                    pt.order_id LIKE %s OR
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    pt.utr LIKE %s OR
                    pt.bank_ref_no LIKE %s
                )"""
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 8)

            if from_date:
                query += " AND DATE(pt.created_at) >= %s"
                params.append(from_date)

            if to_date:
                query += " AND DATE(pt.created_at) <= %s"
                params.append(to_date)

            query += " ORDER BY pt.created_at DESC LIMIT 100"

            cursor.execute(query, params)
            payouts = cursor.fetchall()

            # Format the data properly
            formatted_payouts = []
            for payout in payouts:
                formatted_payout = {
                    'id': payout['id'],
                    'txn_id': payout['txn_id'],
                    'merchant_id': payout['merchant_id'],
                    'reference_id': payout['reference_id'],
                    'order_id': payout.get('order_id'),
                    'batch_id': payout['batch_id'],
                    'amount': float(payout['amount']) if payout['amount'] else 0.0,
                    'charge_amount': float(payout['charge_amount']) if payout['charge_amount'] else 0.0,
                    'charge_type': payout['charge_type'],
                    'net_amount': float(payout['net_amount']) if payout['net_amount'] else 0.0,
                    'bene_name': payout['bene_name'],
                    'bene_email': payout['bene_email'],
                    'bene_mobile': payout['bene_mobile'],
                    'bene_bank': payout['bene_bank'],
                    'ifsc_code': payout['ifsc_code'],
                    'account_no': payout['account_no'],
                    'vpa': payout['vpa'],
                    'payment_type': payout['payment_type'],
                    'purpose': payout['purpose'],
                    'status': payout['status'],
                    'pg_partner': payout['pg_partner'],
                    'pg_txn_id': payout['pg_txn_id'],
                    'bank_ref_no': payout['bank_ref_no'],
                    'utr': payout['utr'],
                    'name_with_bank': payout['name_with_bank'],
                    'name_match_score': payout['name_match_score'],
                    'error_message': payout['error_message'],
                    'remarks': payout['remarks'],
                    'callback_url': payout['callback_url'],
                    'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['created_at'] else None,
                    'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['updated_at'] else None,
                    'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['completed_at'] else None,
                    'full_name': payout['full_name'],
                    'mobile': payout['mobile']
                }
                formatted_payouts.append(formatted_payout)

        conn.close()
        return jsonify({'success': True, 'data': formatted_payouts}), 200

    except Exception as e:
        print(f"Error in get_client_payout_report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/client/report/all', methods=['GET'])
@jwt_required()
def get_client_payout_report_all():
    """Get ALL payout report for merchant (for download) with filters - OPTIMIZED with batch processing"""
    try:
        merchant_id = get_jwt_identity()
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        search = request.args.get('search')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        with conn.cursor() as cursor:
            # OPTIMIZATION 1: First get total count
            count_query = """
                SELECT COUNT(*) as total
                FROM payout_transactions pt
                WHERE pt.merchant_id = %s
            """
            count_params = [merchant_id]

            if status:
                count_query += " AND pt.status = %s"
                count_params.append(status)

            if search:
                count_query += """ AND (
                    pt.txn_id LIKE %s OR
                    pt.reference_id LIKE %s OR
                    pt.order_id LIKE %s OR
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    pt.utr LIKE %s OR
                    pt.bank_ref_no LIKE %s
                )"""
                search_pattern = f"%{search}%"
                count_params.extend([search_pattern] * 8)

            if from_date:
                count_query += " AND DATE(pt.created_at) >= %s"
                count_params.append(from_date)

            if to_date:
                count_query += " AND DATE(pt.created_at) <= %s"
                count_params.append(to_date)

            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()['total']
            
            print(f"Fetching {total_count} payout records for merchant {merchant_id}...")

            # OPTIMIZATION 2: Fetch in batches
            batch_size = 5000
            all_payouts = []
            offset = 0

            while offset < total_count:
                query = """
                    SELECT
                        pt.id,
                        pt.txn_id,
                        pt.merchant_id,
                        pt.reference_id,
                        pt.order_id,
                        pt.batch_id,
                        pt.amount,
                        pt.charge_amount,
                        pt.charge_type,
                        pt.net_amount,
                        pt.bene_name,
                        pt.bene_email,
                        pt.bene_mobile,
                        pt.bene_bank,
                        pt.ifsc_code,
                        pt.account_no,
                        pt.vpa,
                        pt.payment_type,
                        pt.purpose,
                        pt.status,
                        pt.pg_partner,
                        pt.pg_txn_id,
                        pt.bank_ref_no,
                        pt.utr,
                        pt.name_with_bank,
                        pt.name_match_score,
                        pt.error_message,
                        pt.remarks,
                        pt.callback_url,
                        pt.created_at,
                        pt.updated_at,
                        pt.completed_at,
                        m.full_name,
                        m.mobile
                    FROM payout_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE pt.merchant_id = %s
                """
                params = [merchant_id]

                if status:
                    query += " AND pt.status = %s"
                    params.append(status)

                if search:
                    query += """ AND (
                        pt.txn_id LIKE %s OR
                        pt.reference_id LIKE %s OR
                        pt.order_id LIKE %s OR
                        pt.bene_name LIKE %s OR
                        pt.account_no LIKE %s OR
                        pt.ifsc_code LIKE %s OR
                        pt.utr LIKE %s OR
                        pt.bank_ref_no LIKE %s
                    )"""
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern] * 8)

                if from_date:
                    query += " AND DATE(pt.created_at) >= %s"
                    params.append(from_date)

                if to_date:
                    query += " AND DATE(pt.created_at) <= %s"
                    params.append(to_date)

                query += " ORDER BY pt.created_at DESC LIMIT %s OFFSET %s"
                params.extend([batch_size, offset])

                cursor.execute(query, params)
                batch_payouts = cursor.fetchall()

                if not batch_payouts:
                    break

                # Format the batch data
                for payout in batch_payouts:
                    formatted_payout = {
                        'id': payout['id'],
                        'txn_id': payout['txn_id'],
                        'merchant_id': payout['merchant_id'],
                        'reference_id': payout['reference_id'],
                        'order_id': payout.get('order_id'),
                        'batch_id': payout['batch_id'],
                        'amount': float(payout['amount']) if payout['amount'] else 0.0,
                        'charge_amount': float(payout['charge_amount']) if payout['charge_amount'] else 0.0,
                        'charge_type': payout['charge_type'],
                        'net_amount': float(payout['net_amount']) if payout['net_amount'] else 0.0,
                        'bene_name': payout['bene_name'],
                        'bene_email': payout['bene_email'],
                        'bene_mobile': payout['bene_mobile'],
                        'bene_bank': payout['bene_bank'],
                        'ifsc_code': payout['ifsc_code'],
                        'account_no': payout['account_no'],
                        'vpa': payout['vpa'],
                        'payment_type': payout['payment_type'],
                        'purpose': payout['purpose'],
                        'status': payout['status'],
                        'pg_partner': payout['pg_partner'],
                        'pg_txn_id': payout['pg_txn_id'],
                        'bank_ref_no': payout['bank_ref_no'],
                        'utr': payout['utr'],
                        'name_with_bank': payout['name_with_bank'],
                        'name_match_score': payout['name_match_score'],
                        'error_message': payout['error_message'],
                        'remarks': payout['remarks'],
                        'callback_url': payout['callback_url'],
                        'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['created_at'] else None,
                        'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['updated_at'] else None,
                        'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['completed_at'] else None,
                        'full_name': payout['full_name'],
                        'mobile': payout['mobile']
                    }
                    all_payouts.append(formatted_payout)

                offset += batch_size
                print(f"Processed {len(all_payouts)}/{total_count} records...")

        conn.close()
        print(f"âœ“ Successfully fetched {len(all_payouts)} payout records")
        return jsonify({'success': True, 'data': all_payouts, 'count': len(all_payouts)}), 200

    except Exception as e:
        print(f"Error in get_client_payout_report_all: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/client/report/download-csv', methods=['GET'])
@jwt_required()
def download_client_payout_report_csv():
    """Download merchant payout report as CSV file - optimized for large datasets (streaming)"""
    try:
        merchant_id = get_jwt_identity()
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        search = request.args.get('search')
        
        def generate_csv():
            """Generator function to stream CSV data"""
            conn = get_db_connection()
            if not conn:
                yield "error,Database connection failed\n"
                return
            
            try:
                with conn.cursor() as cursor:
                    # Build query
                    query = """
                        SELECT 
                            pt.txn_id,
                            pt.reference_id,
                            pt.order_id,
                            pt.amount,
                            pt.charge_amount,
                            pt.net_amount,
                            pt.bene_name,
                            pt.bene_mobile,
                            pt.bene_bank,
                            pt.ifsc_code,
                            pt.account_no,
                            pt.payment_type,
                            pt.status,
                            pt.pg_partner,
                            pt.utr,
                            pt.created_at,
                            pt.completed_at
                        FROM payout_transactions pt
                        WHERE pt.merchant_id = %s
                    """
                    params = [merchant_id]
                    
                    if status:
                        query += " AND pt.status = %s"
                        params.append(status)
                    
                    if search:
                        query += """ AND (
                            pt.txn_id LIKE %s OR
                            pt.reference_id LIKE %s OR
                            pt.order_id LIKE %s OR
                            pt.bene_name LIKE %s OR
                            pt.account_no LIKE %s OR
                            pt.ifsc_code LIKE %s OR
                            pt.utr LIKE %s
                        )"""
                        search_pattern = f"%{search}%"
                        params.extend([search_pattern] * 7)
                    
                    if from_date:
                        query += " AND DATE(pt.created_at) >= %s"
                        params.append(from_date)
                    
                    if to_date:
                        query += " AND DATE(pt.created_at) <= %s"
                        params.append(to_date)
                    
                    query += " ORDER BY pt.created_at DESC"
                    
                    # Write CSV header
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow([
                        'Transaction ID', 'Reference ID', 'Order ID',
                        'Amount', 'Charge', 'Net Amount', 'Beneficiary Name', 'Mobile',
                        'Bank', 'IFSC', 'Account Number', 'Payment Type', 'Status',
                        'Gateway', 'UTR', 'Created At', 'Completed At'
                    ])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                    
                    # Execute query and stream results
                    cursor.execute(query, params)
                    
                    # Fetch and write in batches
                    batch_size = 1000
                    while True:
                        rows = cursor.fetchmany(batch_size)
                        if not rows:
                            break
                        
                        for row in rows:
                            writer.writerow([
                                row.get('txn_id', ''),
                                row.get('reference_id', ''),
                                row.get('order_id', ''),
                                row.get('amount', 0),
                                row.get('charge_amount', 0),
                                row.get('net_amount', 0),
                                row.get('bene_name', ''),
                                row.get('bene_mobile', ''),
                                row.get('bene_bank', ''),
                                row.get('ifsc_code', ''),
                                row.get('account_no', ''),
                                row.get('payment_type', ''),
                                row.get('status', ''),
                                row.get('pg_partner', ''),
                                row.get('utr', ''),
                                row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row.get('created_at') else '',
                                row['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if row.get('completed_at') else ''
                            ])
                        
                        yield output.getvalue()
                        output.seek(0)
                        output.truncate(0)
                
            finally:
                conn.close()
        
        # Generate filename with timestamp
        filename = f"payout_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Return streaming response
        return Response(
            stream_with_context(generate_csv()),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        print(f"Error in download_client_payout_report_csv: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/client/report/today', methods=['GET'])
@jwt_required()
def get_client_payout_report_today():
    """Get today's payout report for merchant (for download)"""
    try:
        merchant_id = get_jwt_identity()

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        with conn.cursor() as cursor:
            query = """
                SELECT
                    pt.id,
                    pt.txn_id,
                    pt.merchant_id,
                    pt.reference_id,
                    pt.order_id,
                    pt.batch_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.charge_type,
                    pt.net_amount,
                    pt.bene_name,
                    pt.bene_email,
                    pt.bene_mobile,
                    pt.bene_bank,
                    pt.ifsc_code,
                    pt.account_no,
                    pt.vpa,
                    pt.payment_type,
                    pt.purpose,
                    pt.status,
                    pt.pg_partner,
                    pt.pg_txn_id,
                    pt.bank_ref_no,
                    pt.utr,
                    pt.name_with_bank,
                    pt.name_match_score,
                    pt.error_message,
                    pt.remarks,
                    pt.callback_url,
                    pt.created_at,
                    pt.updated_at,
                    pt.completed_at,
                    m.full_name,
                    m.mobile
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id = %s AND DATE(pt.created_at) = CURDATE()
                ORDER BY pt.created_at DESC
            """

            cursor.execute(query, [merchant_id])
            payouts = cursor.fetchall()

            formatted_payouts = []
            for payout in payouts:
                formatted_payout = {
                    'id': payout['id'],
                    'txn_id': payout['txn_id'],
                    'merchant_id': payout['merchant_id'],
                    'reference_id': payout['reference_id'],
                    'order_id': payout.get('order_id'),
                    'batch_id': payout['batch_id'],
                    'amount': float(payout['amount']) if payout['amount'] else 0.0,
                    'charge_amount': float(payout['charge_amount']) if payout['charge_amount'] else 0.0,
                    'charge_type': payout['charge_type'],
                    'net_amount': float(payout['net_amount']) if payout['net_amount'] else 0.0,
                    'bene_name': payout['bene_name'],
                    'bene_email': payout['bene_email'],
                    'bene_mobile': payout['bene_mobile'],
                    'bene_bank': payout['bene_bank'],
                    'ifsc_code': payout['ifsc_code'],
                    'account_no': payout['account_no'],
                    'vpa': payout['vpa'],
                    'payment_type': payout['payment_type'],
                    'purpose': payout['purpose'],
                    'status': payout['status'],
                    'pg_partner': payout['pg_partner'],
                    'pg_txn_id': payout['pg_txn_id'],
                    'bank_ref_no': payout['bank_ref_no'],
                    'utr': payout['utr'],
                    'name_with_bank': payout['name_with_bank'],
                    'name_match_score': payout['name_match_score'],
                    'error_message': payout['error_message'],
                    'remarks': payout['remarks'],
                    'callback_url': payout['callback_url'],
                    'created_at': payout['created_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['created_at'] else None,
                    'updated_at': payout['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['updated_at'] else None,
                    'completed_at': payout['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if payout['completed_at'] else None,
                    'full_name': payout['full_name'],
                    'mobile': payout['mobile']
                }
                formatted_payouts.append(formatted_payout)

        conn.close()
        return jsonify({'success': True, 'data': formatted_payouts, 'count': len(formatted_payouts)}), 200

    except Exception as e:
        print(f"Error in get_client_payout_report_today: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



# Client/Merchant Status Check - Check payout status from Mudrape
@payout_bp.route('/client/check-status/<txn_id>', methods=['POST'])
@jwt_required()
def client_check_payout_status(txn_id):
    """
    Check payout status from any PG partner and update database automatically.
    This endpoint is for merchants to check their own payout transactions.
    Supports: Mudrape, PayTouch, TourQuest (with database updates)
    PayTouch2: Read-only status check (no database updates - handled by cron job)
    """
    try:
        merchant_id = get_jwt_identity()

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        with conn.cursor() as cursor:
            # Get transaction details - ensure it belongs to the merchant
            cursor.execute("""
                SELECT txn_id, reference_id, pg_partner, status, merchant_id, pg_txn_id, 
                       amount, utr, created_at, completed_at
                FROM payout_transactions
                WHERE txn_id = %s AND merchant_id = %s
            """, (txn_id, merchant_id))

            txn = cursor.fetchone()

            if not txn:
                conn.close()
                return jsonify({'success': False, 'message': 'Transaction not found or unauthorized'}), 404

            print(f"Merchant {merchant_id} checking status for {txn['txn_id']} - {txn['reference_id']} via {txn['pg_partner']}")

            # Check status based on PG partner
            if txn['pg_partner'] == 'Mudrape':
                status_result = mudrape_service.check_payout_status(txn['reference_id'])
            elif txn['pg_partner'] == 'PayTouch':
                status_result = paytouch_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )
            elif txn['pg_partner'] == 'Paytouch2':
                # PayTouch2 status check - READ ONLY (don't update database)
                status_result = paytouch2_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )
                
                if not status_result.get('success'):
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': status_result.get('message', 'Failed to check status from PayTouch2')
                    }), 400

                # For PayTouch2, return status without updating database
                paytouch2_status = status_result.get('status', 'PENDING')
                paytouch2_utr = status_result.get('utr')
                paytouch2_txn_id = status_result.get('transaction_id') or txn['pg_txn_id']

                print(f"PayTouch2 Status Check (READ ONLY): Status={paytouch2_status}, UTR={paytouch2_utr}, PG_TXN_ID={paytouch2_txn_id}")

                conn.close()
                return jsonify({
                    'success': True,
                    'message': 'PayTouch2 status retrieved successfully (read-only)',
                    'data': {
                        'txn_id': txn['txn_id'],
                        'reference_id': txn['reference_id'],
                        'amount': float(txn['amount']) if txn['amount'] else 0.0,
                        'status': txn['status'],  # Current database status
                        'paytouch2_status': paytouch2_status,  # Live PayTouch2 status
                        'utr': txn['utr'],  # Current database UTR
                        'paytouch2_utr': paytouch2_utr,  # Live PayTouch2 UTR
                        'pg_txn_id': txn['pg_txn_id'],
                        'paytouch2_txn_id': paytouch2_txn_id,  # Live PayTouch2 transaction ID
                        'pg_partner': txn['pg_partner'],
                        'created_at': txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                        'completed_at': txn['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['completed_at'] else None,
                        'note': 'PayTouch2 status is read-only. Database updates happen via callback or cron job.'
                    }
                }), 200
                
            elif txn['pg_partner'] == 'TourQuest':
                status_result = tourquest_service.check_payout_status(txn['reference_id'])
            else:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Status check not supported for {txn["pg_partner"]}'
                }), 400

            if not status_result.get('success'):
                conn.close()
                return jsonify({
                    'success': False,
                    'message': status_result.get('message', f'Failed to check status from {txn["pg_partner"]}')
                }), 400

            new_status = status_result.get('status', 'INITIATED')
            utr = status_result.get('utr')
            completed_at_from_api = status_result.get('completed_at')
            created_at_from_api = status_result.get('created_at')
            pg_txn_id = status_result.get('transaction_id') or status_result.get('pg_txn_id') or txn['pg_txn_id']

            print(f"{txn['pg_partner']} returned: Status={new_status}, UTR={utr}, PG_TXN_ID={pg_txn_id}, Created={created_at_from_api}, Completed={completed_at_from_api}")

            # Update transaction with timestamps from PG partner
            if new_status in ['SUCCESS', 'FAILED']:
                if completed_at_from_api and created_at_from_api:
                    # Update both created_at and completed_at from API
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, created_at = %s, completed_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, pg_txn_id, created_at_from_api, completed_at_from_api, txn_id))
                elif completed_at_from_api:
                    # Update only completed_at
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, completed_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, pg_txn_id, completed_at_from_api, txn_id))
                else:
                    # Fallback to NOW()
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, pg_txn_id, txn_id))
            else:
                # Status is still pending/initiated
                if created_at_from_api:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, created_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, pg_txn_id, created_at_from_api, txn_id))
                else:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, pg_txn_id, txn_id))

            conn.commit()

            # Get updated transaction
            cursor.execute("""
                SELECT * FROM payout_transactions WHERE txn_id = %s
            """, (txn_id,))

            updated_txn = cursor.fetchone()

            conn.close()

            print(f"âœ“ Transaction {txn_id} checked successfully - Status: {new_status}, UTR: {utr}")

            return jsonify({
                'success': True,
                'message': 'Status checked and updated successfully',
                'data': {
                    'txn_id': updated_txn['txn_id'],
                    'reference_id': updated_txn['reference_id'],
                    'amount': float(updated_txn['amount']),
                    'status': updated_txn['status'],
                    'utr': updated_txn['utr'],
                    'pg_txn_id': updated_txn['pg_txn_id'],
                    'pg_partner': updated_txn['pg_partner'],
                    'created_at': updated_txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if updated_txn['created_at'] else None,
                    'completed_at': updated_txn['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if updated_txn['completed_at'] else None
                }
            }), 200

    except Exception as e:
        print(f"Error in client_check_payout_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500




# Manual Status Sync - Check single transaction status from Mudrape (Admin)
@payout_bp.route('/sync-status/<txn_id>', methods=['POST'])
@jwt_required()
def sync_transaction_status(txn_id):
    """Manually sync transaction status from Mudrape"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT txn_id, reference_id, pg_partner, status
                FROM payout_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                conn.close()
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
            if txn['pg_partner'] != 'Mudrape':
                conn.close()
                return jsonify({'success': False, 'message': 'Only Mudrape transactions can be synced'}), 400
            
            print(f"Manual sync requested for {txn['txn_id']} - {txn['reference_id']}")
            
            # Check status from Mudrape
            status_result = mudrape_service.check_payout_status(txn['reference_id'])
            
            if not status_result.get('success'):
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': status_result.get('message', 'Failed to check status from Mudrape')
                }), 400
            
            new_status = status_result.get('status', 'INITIATED')
            utr = status_result.get('utr')
            completed_at_from_api = status_result.get('completed_at')
            created_at_from_api = status_result.get('created_at')
            
            print(f"Mudrape returned: Status={new_status}, UTR={utr}, Created={created_at_from_api}, Completed={completed_at_from_api}")
            
            # Update transaction with timestamps from Mudrape
            if new_status in ['SUCCESS', 'FAILED']:
                if completed_at_from_api and created_at_from_api:
                    # Update both created_at and completed_at from Mudrape
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, created_at = %s, completed_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, created_at_from_api, completed_at_from_api, txn_id))
                elif completed_at_from_api:
                    # Update only completed_at
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, completed_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, completed_at_from_api, txn_id))
                else:
                    # Fallback to NOW()
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, txn_id))
            else:
                # Status is still pending/initiated
                if created_at_from_api:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, created_at = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, created_at_from_api, txn_id))
                else:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (new_status, utr, txn_id))
            
            conn.commit()
            
            # Get updated transaction
            cursor.execute("""
                SELECT * FROM payout_transactions WHERE txn_id = %s
            """, (txn_id,))
            
            updated_txn = cursor.fetchone()
            
            conn.close()
            
            print(f"âœ“ Transaction {txn_id} synced successfully - Status: {new_status}, Created: {created_at_from_api}, Completed: {completed_at_from_api}")
            
            return jsonify({
                'success': True,
                'message': 'Status synced successfully',
                'data': updated_txn
            }), 200
            
    except Exception as e:
        print(f"Error in sync_transaction_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# Get Payout Stats - Client
@payout_bp.route('/client/stats', methods=['GET'])
@jwt_required()
def get_client_payout_stats():
    """Get payout statistics for merchant with date ranges"""
    try:
        merchant_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get stats by status
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM payout_transactions
                WHERE merchant_id = %s
                GROUP BY status
            """, (merchant_id,))
            
            stats_by_status = cursor.fetchall()
            
            # Initialize stats
            stats = {
                'success': {'count': 0, 'amount': 0},
                'pending': {'count': 0, 'amount': 0},
                'failed': {'count': 0, 'amount': 0},
                'queued': {'count': 0, 'amount': 0}
            }
            
            # Map database results to stats
            for stat in stats_by_status:
                status = stat['status'].upper()  # Convert to uppercase for consistency
                if status == 'SUCCESS':
                    stats['success'] = {'count': stat['count'], 'amount': float(stat['total_amount'])}
                elif status in ['INITIATED', 'INPROCESS']:
                    stats['pending']['count'] += stat['count']
                    stats['pending']['amount'] += float(stat['total_amount'])
                elif status in ['FAILED', 'REVERSED']:
                    stats['failed']['count'] += stat['count']
                    stats['failed']['amount'] += float(stat['total_amount'])
                elif status == 'QUEUED':
                    stats['queued'] = {'count': stat['count'], 'amount': float(stat['total_amount'])}
            
            # Get today's stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE merchant_id = %s AND DATE(created_at) = CURDATE()
            """, (merchant_id,))
            today = cursor.fetchone()
            
            # Get yesterday's stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE merchant_id = %s AND DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
            """, (merchant_id,))
            yesterday = cursor.fetchone()
            
            # Get last 7 days stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE merchant_id = %s AND DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, (merchant_id,))
            last7days = cursor.fetchone()
            
            # Get last 30 days stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE merchant_id = %s AND DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """, (merchant_id,))
            last30days = cursor.fetchone()
        
        conn.close()
        return jsonify({
            'success': True, 
            'stats': stats,
            'timeRanges': {
                'today': {
                    'payout': float(today['payout']),
                    'net_payout': float(today['net_payout'])
                },
                'yesterday': {
                    'payout': float(yesterday['payout']),
                    'net_payout': float(yesterday['net_payout'])
                },
                'last7days': {
                    'payout': float(last7days['payout']),
                    'net_payout': float(last7days['net_payout'])
                },
                'last30days': {
                    'payout': float(last30days['payout']),
                    'net_payout': float(last30days['net_payout'])
                }
            }
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# Get Payout Stats - Admin
@payout_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
def get_admin_payout_stats():
    """Get payout statistics for admin with date ranges"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get stats by status
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN charge_amount ELSE 0 END), 0) as total_payout_charges
                FROM payout_transactions
                GROUP BY status
            """)
            
            stats_by_status = cursor.fetchall()
            
            # Get total payout charges
            total_payout_charges = sum(float(stat.get('total_payout_charges', 0)) for stat in stats_by_status)
            
            # Initialize stats
            stats = {
                'success': {'count': 0, 'amount': 0},
                'pending': {'count': 0, 'amount': 0},
                'failed': {'count': 0, 'amount': 0},
                'queued': {'count': 0, 'amount': 0}
            }
            
            # Map database results to stats
            for stat in stats_by_status:
                status = stat['status'].upper()  # Convert to uppercase for consistency
                if status == 'SUCCESS':
                    stats['success'] = {'count': stat['count'], 'amount': float(stat['total_amount'])}
                elif status in ['INITIATED', 'INPROCESS']:
                    stats['pending']['count'] += stat['count']
                    stats['pending']['amount'] += float(stat['total_amount'])
                elif status in ['FAILED', 'REVERSED']:
                    stats['failed']['count'] += stat['count']
                    stats['failed']['amount'] += float(stat['total_amount'])
                elif status == 'QUEUED':
                    stats['queued'] = {'count': stat['count'], 'amount': float(stat['total_amount'])}
            
            # Get today's stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE DATE(created_at) = CURDATE()
            """)
            today = cursor.fetchone()
            
            # Get yesterday's stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
            """)
            yesterday = cursor.fetchone()
            
            # Get last 7 days stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """)
            last7days = cursor.fetchone()
            
            # Get last 30 days stats
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as payout,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN net_amount ELSE 0 END), 0) as net_payout
                FROM payout_transactions
                WHERE DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            last30days = cursor.fetchone()
        
        conn.close()
        return jsonify({
            'success': True, 
            'stats': stats,
            'totals': {
                'total_payout_charges': float(total_payout_charges)
            },
            'timeRanges': {
                'today': {
                    'payout': float(today['payout']),
                    'net_payout': float(today['net_payout'])
                },
                'yesterday': {
                    'payout': float(yesterday['payout']),
                    'net_payout': float(yesterday['net_payout'])
                },
                'last7days': {
                    'payout': float(last7days['payout']),
                    'net_payout': float(last7days['net_payout'])
                },
                'last30days': {
                    'payout': float(last30days['payout']),
                    'net_payout': float(last30days['net_payout'])
                }
            }
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
        return jsonify({'success': False, 'message': str(e)}), 500


# PayU Payout Token and Account Management APIs

@payout_bp.route('/admin/payu/token/generate', methods=['POST'])
@jwt_required()
def generate_payu_token():
    """Generate PayU payout access token"""
    try:
        result = payu_payout_svc.generate_access_token()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Token generated successfully',
                'data': {
                    'access_token': result['access_token'][:20] + '...',  # Masked for security
                    'token_type': result.get('token_type'),
                    'expires_in': result.get('expires_in'),
                    'user_uuid': result.get('user_uuid')
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Token generation failed')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payout_bp.route('/admin/payu/token/refresh', methods=['POST'])
@jwt_required()
def refresh_payu_token():
    """Refresh PayU payout access token"""
    try:
        result = payu_payout_svc.refresh_access_token()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Token refreshed successfully',
                'data': {
                    'access_token': result['access_token'][:20] + '...'  # Masked for security
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Token refresh failed')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payout_bp.route('/admin/payu/account/details', methods=['GET'])
@jwt_required()
def get_payu_account_details():
    """Get PayU payout account details"""
    try:
        result = payu_payout_svc.get_account_details()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Failed to get account details')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Client/Merchant Status Check by Order ID - Check payout status using client order_id
@payout_bp.route('/client/check-status-by-order-id/<order_id>', methods=['GET'])
@jwt_required()
def client_check_payout_status_by_order_id(order_id):
    """
    Check payout status using client order_id (similar to MoneyStake API).
    This endpoint allows merchants to check their payout transactions using the order_id they provided.
    
    Example:
    GET /api/payout/client/check-status-by-order-id/ORDER12345
    Authorization: Bearer <token>
    
    Response:
    {
        "success": true,
        "message": "Payout status retrieved successfully",
        "data": {
            "order_id": "ORDER12345",
            "txn_id": "TXN5074C9A5A1B5",
            "reference_id": "DP2026040221520368FF8E",
            "amount": 2015.0,
            "status": "SUCCESS",
            "utr": "609221495505",
            "pg_partner": "Mudrape",
            "created_at": "2026-04-02 21:52:03",
            "completed_at": "2026-04-02 21:57:23"
        }
    }
    """
    try:
        merchant_id = get_jwt_identity()

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        with conn.cursor() as cursor:
            # Get transaction details by order_id - ensure it belongs to the merchant
            cursor.execute("""
                SELECT txn_id, reference_id, order_id, pg_partner, status, merchant_id, pg_txn_id, 
                       amount, charge_amount, net_amount, utr, created_at, completed_at,
                       bene_name, account_no, ifsc_code, payment_type
                FROM payout_transactions
                WHERE order_id = %s AND merchant_id = %s
            """, (order_id, merchant_id))

            txn = cursor.fetchone()

            if not txn:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': 'Transaction not found or unauthorized'
                }), 404

            print(f"Merchant {merchant_id} checking status for order_id={order_id}, txn_id={txn['txn_id']}, pg_partner={txn['pg_partner']}")

            # Return the current transaction status from database
            response_data = {
                'order_id': txn['order_id'],
                'txn_id': txn['txn_id'],
                'reference_id': txn['reference_id'],
                'amount': float(txn['amount']) if txn['amount'] else 0.0,
                'charge_amount': float(txn['charge_amount']) if txn['charge_amount'] else 0.0,
                'net_amount': float(txn['net_amount']) if txn['net_amount'] else 0.0,
                'status': txn['status'],
                'utr': txn['utr'],
                'pg_partner': txn['pg_partner'],
                'pg_txn_id': txn['pg_txn_id'],
                'bene_name': txn['bene_name'],
                'account_no': txn['account_no'],
                'ifsc_code': txn['ifsc_code'],
                'payment_type': txn['payment_type'],
                'created_at': txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                'completed_at': txn['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['completed_at'] else None
            }

            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Payout status retrieved successfully',
                'data': response_data
            }), 200

    except Exception as e:
        print(f"Error checking payout status by order_id: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@payout_bp.route('/admin/payu/transfer/status/<reference_id>', methods=['GET'])
@jwt_required()
def check_payu_transfer_status(reference_id):
    """Check PayU transfer status"""
    try:
        result = payout_svc.get_transaction_status(reference_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Failed to check status')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payout_bp.route('/admin/payu/transfer/list', methods=['POST'])
@jwt_required()
def list_payu_transfers():
    """List PayU transfers with filters"""
    try:
        data = request.get_json()
        
        result = payu_payout_svc.check_transfer_status(
            merchant_ref_id=data.get('merchant_ref_id'),
            batch_id=data.get('batch_id'),
            transfer_status=data.get('transfer_status'),
            from_date=data.get('from_date'),
            to_date=data.get('to_date'),
            page=data.get('page', 1),
            page_size=data.get('page_size', 100)
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Failed to list transfers')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Client Direct Payout (with bank details in request)


@payout_bp.route('/admin/advanced-search', methods=['POST'])
@jwt_required()
def admin_advanced_search_payout():
    """
    Advanced search for merchant payout analytics
    Supports single day and date range (day-wise) search
    """
    try:
        # Get admin identity
        admin_id = get_jwt_identity()
        
        # Verify admin role
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT role FROM admin_users WHERE admin_id = %s", (admin_id,))
                admin = cursor.fetchone()
                
                if not admin or admin['role'] not in ['admin', 'superadmin']:
                    return jsonify({'success': False, 'message': 'Unauthorized'}), 403
                
                # Get request data
                data = request.get_json()
                merchant_id = data.get('merchant_id')
                mode = data.get('mode')  # 'single' or 'range'
                
                if not merchant_id:
                    return jsonify({'success': False, 'message': 'Merchant ID is required'}), 400
                
                if mode not in ['single', 'range']:
                    return jsonify({'success': False, 'message': 'Invalid mode. Use "single" or "range"'}), 400
                
                # Get merchant name
                cursor.execute("SELECT full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                merchant_name = merchant['full_name']
                
                if mode == 'single':
                    # Single day search
                    date = data.get('date')
                    if not date:
                        return jsonify({'success': False, 'message': 'Date is required for single day search'}), 400
                    
                    # Query for single day
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_transactions,
                            COALESCE(SUM(amount), 0) as total_amount,
                            COALESCE(SUM(charge_amount), 0) as total_charges,
                            COALESCE(SUM(net_amount), 0) as net_amount
                        FROM payout_transactions
                        WHERE merchant_id = %s 
                        AND DATE(created_at) = %s
                        AND status = 'SUCCESS'
                    """, (merchant_id, date))
                    
                    result = cursor.fetchone()
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'merchant_id': merchant_id,
                            'merchant_name': merchant_name,
                            'date': date,
                            'total_transactions': result['total_transactions'],
                            'total_amount': float(result['total_amount']),
                            'total_charges': float(result['total_charges']),
                            'net_amount': float(result['net_amount'])
                        }
                    })
                
                else:  # mode == 'range'
                    # Date range search with day-wise breakdown
                    from_date = data.get('from_date')
                    to_date = data.get('to_date')
                    
                    if not from_date or not to_date:
                        return jsonify({'success': False, 'message': 'Both from_date and to_date are required for range search'}), 400
                    
                    # Query for day-wise data
                    cursor.execute("""
                        SELECT 
                            DATE(created_at) as date,
                            COUNT(*) as total_transactions,
                            COALESCE(SUM(amount), 0) as total_amount,
                            COALESCE(SUM(charge_amount), 0) as total_charges,
                            COALESCE(SUM(net_amount), 0) as net_amount
                        FROM payout_transactions
                        WHERE merchant_id = %s 
                        AND DATE(created_at) BETWEEN %s AND %s
                        AND status = 'SUCCESS'
                        GROUP BY DATE(created_at)
                        ORDER BY DATE(created_at)
                    """, (merchant_id, from_date, to_date))
                    
                    daily_data = cursor.fetchall()
                    
                    # Calculate summary
                    total_transactions = sum(day['total_transactions'] for day in daily_data)
                    total_amount = sum(float(day['total_amount']) for day in daily_data)
                    total_charges = sum(float(day['total_charges']) for day in daily_data)
                    net_amount = sum(float(day['net_amount']) for day in daily_data)
                    
                    # Format daily data
                    formatted_daily_data = [
                        {
                            'date': str(day['date']),
                            'total_transactions': day['total_transactions'],
                            'total_amount': float(day['total_amount']),
                            'total_charges': float(day['total_charges']),
                            'net_amount': float(day['net_amount'])
                        }
                        for day in daily_data
                    ]
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'merchant_id': merchant_id,
                            'merchant_name': merchant_name,
                            'from_date': from_date,
                            'to_date': to_date,
                            'daily_data': formatted_daily_data,
                            'summary': {
                                'total_transactions': total_transactions,
                                'total_amount': total_amount,
                                'total_charges': total_charges,
                                'net_amount': net_amount
                            }
                        }
                    })
        
        finally:
            conn.close()
    
    except Exception as e:
        print(f"Advanced search error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
