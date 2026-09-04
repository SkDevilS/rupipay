from flask import Blueprint, request, jsonify
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
from mudrape_service import mudrape_service

payout_bp = Blueprint('payout', __name__, url_prefix='/api/payout')

# Get service instances
payout_svc = payout_service.payout_service
payu_payout_svc = payu_payout_service.payu_payout_service
wallet_svc = wallet_service.wallet_service


# Admin Personal Payout
@payout_bp.route('/admin/personal-payout', methods=['POST'])
@jwt_required()
def admin_personal_payout():
    try:
        data = request.json
        admin_id = get_jwt_identity()
        
        # Validate required fields
        required_fields = ['bank_id', 'amount', 'tpin', 'pg_partner']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify TPIN
                cursor.execute("SELECT pin_hash FROM admin_users WHERE admin_id = %s", (admin_id,))
                admin = cursor.fetchone()
                
                if not admin or not admin['pin_hash']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    conn.close()
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 400
                
                # Get bank details
                cursor.execute("""
                    SELECT * FROM admin_banks 
                    WHERE id = %s AND admin_id = %s AND is_active = TRUE
                """, (data['bank_id'], admin_id))
                bank = cursor.fetchone()
                
                if not bank:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # Check admin balance
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                """)
                total_payin = float(cursor.fetchone()['total_payin'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                """)
                total_topup = float(cursor.fetchone()['total_topup'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetch
                    FROM merchant_wallet_transactions
                    WHERE txn_type = 'DEBIT' 
                    AND description LIKE '%fetched by admin%'
                """)
                total_fetch = float(cursor.fetchone()['total_fetch'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payout
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED')
                """)
                total_payout = float(cursor.fetchone()['total_payout'])
                
                available_balance = total_payin + total_fetch - total_topup - total_payout
                
                if float(data['amount']) > available_balance:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
                
                # Create payout transaction record (using admin_id as merchant_id for admin payouts)
                reference_id = f"ADMIN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                txn_id = f"TXN{uuid.uuid4().hex[:12].upper()}"
                # Auto-generate order_id for admin payouts
                order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute("""
                    INSERT INTO payout_transactions 
                    (txn_id, reference_id, order_id, merchant_id, amount, charge_amount, charge_type, net_amount,
                     bene_name, bene_bank, account_no, ifsc_code, payment_type, pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, 0.00, 'FIXED', %s, %s, %s, %s, %s, 'IMPS', %s, 'INITIATED', NOW())
                """, (txn_id, reference_id, order_id, admin_id, data['amount'], data['amount'],
                      bank['account_holder_name'], bank['bank_name'],
                      bank['account_number'], bank['ifsc_code'], data['pg_partner']))
                
                conn.commit()
                
                # Process payout based on pg_partner
                pg_partner_upper = data['pg_partner'].upper()
                
                if pg_partner_upper == 'PAYU':
                    # Use PayU for payout
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
                    # Use Mudrape for payout (IMPS)
                    result = mudrape_service.call_imps_payout_api(
                        account_number=bank['account_number'],
                        ifsc_code=bank['ifsc_code'],
                        client_txn_id=reference_id,
                        amount=float(data['amount']),
                        beneficiary_name=bank['account_holder_name']
                    )
                    
                    if result['success']:
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
                # Debit from admin wallet using wallet service
                admin_debit = wallet_svc.debit_admin_wallet(
                    admin_id,
                    float(fund_request['amount']),
                    f"Fund request approved for {fund_request['merchant_id']} - {request_id}",
                    reference_id=request_id
                )
                
                if not admin_debit['success']:
                    conn.close()
                    return jsonify(admin_debit), 400
                
                # Add to merchant unsettled wallet
                cursor.execute("""
                    INSERT INTO merchant_unsettled_wallet (merchant_id, balance)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE balance = balance + %s
                """, (fund_request['merchant_id'], fund_request['amount'], fund_request['amount']))
                
                # Record wallet transaction
                cursor.execute("""
                    SELECT balance FROM merchant_unsettled_wallet WHERE merchant_id = %s
                """, (fund_request['merchant_id'],))
                wallet = cursor.fetchone()
                
                txn_id = f"FT{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                    INSERT INTO wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description)
                    VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s)
                """, (
                    fund_request['merchant_id'], txn_id, fund_request['amount'],
                    wallet['balance'] - fund_request['amount'], wallet['balance'],
                    f"Fund topup approved - {request_id}"
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
                
                # Check available balance (from PayIN + Fetch)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                """)
                total_payin = float(cursor.fetchone()['total_payin'])
                
                # Get total approved fund requests (wallet balance)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                """)
                total_topup = float(cursor.fetchone()['total_topup'])
                
                # Get total fetch from merchants
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetch
                    FROM merchant_wallet_transactions
                    WHERE txn_type = 'DEBIT' 
                    AND description LIKE '%fetched by admin%'
                """)
                total_fetch = float(cursor.fetchone()['total_fetch'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payout
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED')
                """)
                total_payout = float(cursor.fetchone()['total_payout'])
                
                available_balance = total_payin + total_fetch - total_topup - total_payout
                
                if float(data['amount']) > available_balance:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
                
                # Create fund request entry (auto-approved by admin)
                request_id = f"FR{uuid.uuid4().hex[:12].upper()}"
                remarks = data.get('remarks', 'Manual topup by admin')
                
                cursor.execute("""
                    INSERT INTO fund_requests 
                    (request_id, merchant_id, amount, status, remarks, processed_by, processed_at)
                    VALUES (%s, %s, %s, 'APPROVED', %s, %s, NOW())
                """, (request_id, data['merchant_id'], data['amount'], remarks, admin_id))
                
                conn.commit()
            
            conn.close()
            
            # Debit from admin wallet using wallet service
            admin_debit = wallet_svc.debit_admin_wallet(
                admin_id,
                float(data['amount']),
                f"Manual topup for {data['merchant_id']} - {request_id}",
                reference_id=request_id
            )
            
            if not admin_debit['success']:
                return jsonify(admin_debit), 400
            
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
                
                # Get wallet balance from approved fund requests
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as wallet_balance
                    FROM fund_requests
                    WHERE merchant_id = %s AND status = 'APPROVED'
                """, (merchant_id,))
                wallet_balance = float(cursor.fetchone()['wallet_balance'])
                
                # Get total settlements already made
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_settlements
                    FROM payout_transactions
                    WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
                """, (merchant_id,))
                total_settlements = float(cursor.fetchone()['total_settlements'])
                
                # Get total fetched by admin
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetched
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                    AND txn_type = 'DEBIT'
                    AND description LIKE '%fetched by admin%'
                """, (merchant_id,))
                total_fetched = float(cursor.fetchone()['total_fetched'])
                
                # Available balance = Approved funds - Settlements - Fetched
                available_balance = wallet_balance - total_settlements - total_fetched
                
                # Check if available balance is sufficient (amount + charges)
                if total_wallet_deduction > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'message': f'Insufficient balance. Required: ₹{total_wallet_deduction:.2f} (Amount: ₹{amount_to_bank:.2f} + Charges: ₹{charges["charge_amount"]:.2f}), Available: ₹{available_balance:.2f}'
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
                txn_id = f"TXN{uuid.uuid4().hex[:12].upper()}"
                
                cursor.execute("""
                    INSERT INTO payout_transactions 
                    (txn_id, reference_id, merchant_id, amount, charge_amount, charge_type, 
                     net_amount, bene_name, bene_bank, account_no, ifsc_code, 
                     pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())
                """, (txn_id, reference_id, merchant_id, total_wallet_deduction, 
                      charges['charge_amount'], charges['charge_type'], amount_to_bank,
                      bank['account_holder_name'], bank['bank_name'], 
                      bank['account_number'], bank['ifsc_code'], pg_partner))
                
                conn.commit()
                
                # Process through PayU if configured
                pg_partner_upper = pg_partner.upper()
                
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
                        # Update status to QUEUED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'QUEUED', pg_response = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (json.dumps(payu_result['data']), txn_id))
                        conn.commit()
                        
                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': 'Settlement initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': 'QUEUED'
                        }), 200
                    else:
                        # Update status to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions 
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
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
                        
                        # Set completed_at if status is final
                        if status in ['SUCCESS', 'FAILED']:
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        else:
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
                            'message': 'Settlement initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'requested_amount': amount_to_bank,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_wallet_deduction,
                            'amount_to_bank': amount_to_bank,
                            'status': status
                        }), 200
                    else:
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
    This reduces merchant's available balance and increases admin's balance.
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
                
                # Calculate merchant's available balance
                # Step 1: Get wallet balance from approved fund requests
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as wallet_balance
                    FROM fund_requests
                    WHERE merchant_id = %s AND status = 'APPROVED'
                """, (merchant_id,))
                result = cursor.fetchone()
                wallet_balance = float(result['wallet_balance']) if result else 0.0
                
                # Step 2: Get total settlements already made
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_settlements
                    FROM payout_transactions
                    WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
                """, (merchant_id,))
                result = cursor.fetchone()
                total_settlements = float(result['total_settlements']) if result else 0.0
                
                # Step 3: Get total fetched by admin (previous fetches)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetched
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                    AND txn_type = 'DEBIT'
                    AND description LIKE %s
                """, (merchant_id, '%fetched by admin%'))
                result = cursor.fetchone()
                total_fetched = float(result['total_fetched']) if result else 0.0
                
                # Calculate available balance
                available_balance = wallet_balance - total_settlements - total_fetched
                
                print("=== FETCH FUND DEBUG ===")
                print("Merchant ID: {}".format(merchant_id))
                print("Wallet Balance (Approved): {}".format(wallet_balance))
                print("Total Settlements: {}".format(total_settlements))
                print("Total Fetched: {}".format(total_fetched))
                print("Available Balance: {}".format(available_balance))
                print("Fetch Amount: {}".format(fetch_amount))
                
                # Check if sufficient balance
                if fetch_amount > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient balance. Available: Rs.{:.2f}, Requested: Rs.{:.2f}'.format(available_balance, fetch_amount)
                    }), 400
                
                # Generate transaction ID
                txn_id = wallet_svc.generate_txn_id('MWT')
                
                # Calculate new balance
                balance_after = available_balance - fetch_amount
                
                # Create description (avoid % in f-string for SQL)
                description = "Fund fetched by admin - {}".format(reason)
                
                # Record the fetch transaction in merchant_wallet_transactions
                insert_query = """
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after,
                     description, reference_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                insert_values = (
                    merchant_id,
                    txn_id,
                    'DEBIT',
                    fetch_amount,
                    available_balance,
                    balance_after,
                    description,
                    reason
                )
                
                print("Executing INSERT with values:")
                print("  merchant_id: {}".format(merchant_id))
                print("  txn_id: {}".format(txn_id))
                print("  amount: {}".format(fetch_amount))
                print("  balance_before: {}".format(available_balance))
                print("  balance_after: {}".format(balance_after))
                print("  description: {}".format(description))
                
                cursor.execute(insert_query, insert_values)
                conn.commit()
                
                print("Fetch fund transaction recorded successfully")
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Fund fetched successfully',
                'txn_id': txn_id,
                'amount': fetch_amount,
                'balance_before': available_balance,
                'balance_after': balance_after
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

        # Validate payment type
        if payment_type not in ['IMPS', 'NEFT', 'RTGS']:
            return jsonify({'success': False, 'message': 'Invalid payment_type. Must be IMPS, NEFT, or RTGS'}), 400

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
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

                # Get wallet balance from approved fund requests
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as wallet_balance
                    FROM fund_requests
                    WHERE merchant_id = %s AND status = 'APPROVED'
                """, (merchant_id,))
                wallet_balance = float(cursor.fetchone()['wallet_balance'])

                # Get total payouts already made
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payouts
                    FROM payout_transactions
                    WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
                """, (merchant_id,))
                total_payouts = float(cursor.fetchone()['total_payouts'])

                available_balance = wallet_balance - total_payouts

                # Check if available balance is sufficient (amount + charges)
                if total_deduction > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient balance. Required: ₹{total_deduction} (Amount: ₹{amount} + Charges: ₹{charges["charge_amount"]}), Available: ₹{available_balance}'
                    }), 400

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
                txn_id = f"TXN{uuid.uuid4().hex[:12].upper()}"

                cursor.execute("""
                    INSERT INTO payout_transactions
                    (txn_id, reference_id, order_id, merchant_id, amount, charge_amount, charge_type,
                     net_amount, bene_name, bene_email, bene_mobile, bene_bank, account_no,
                     ifsc_code, payment_type, purpose, pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'INITIATED', NOW())
                """, (txn_id, reference_id, data['order_id'], merchant_id, total_deduction,
                      charges['charge_amount'], charges['charge_type'], net_amount_to_bank,
                      data['account_holder_name'], bene_email, bene_mobile, data['bank_name'],
                      data['account_number'], data['ifsc_code'], payment_type, purpose, pg_partner))

                conn.commit()

                # Process through payment gateway
                pg_partner_upper = pg_partner.upper()

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
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'QUEUED', updated_at = NOW()
                            WHERE txn_id = %s
                        """, (txn_id,))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': 'QUEUED',
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (payu_result.get('error', 'PayU transfer failed'), txn_id))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed',
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

                        if status in ['SUCCESS', 'FAILED']:
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))
                        else:
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (status, mudrape_txn_id, txn_id))

                        conn.commit()
                        conn.close()

                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'order_id': data['order_id'],
                            'requested_amount': amount,
                            'charges': charges['charge_amount'],
                            'total_deducted': total_deduction,
                            'amount_to_beneficiary': net_amount_to_bank,
                            'status': status,
                            'beneficiary': {
                                'name': data['account_holder_name'],
                                'account_number': data['account_number'],
                                'ifsc_code': data['ifsc_code'],
                                'bank_name': data['bank_name']
                            }
                        }), 200
                    else:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mudrape_result.get('message', 'Mudrape transfer failed'), txn_id))
                        conn.commit()

                        conn.close()
                        return jsonify({
                            'success': False,
                            'message': 'Payout failed',
                            'txn_id': txn_id,
                            'error': mudrape_result.get('message')
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
            if conn:
                conn.rollback()
                conn.close()
            raise e

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



# Get Payout Report - Admin
@payout_bp.route('/admin/payout-report', methods=['GET'])
@jwt_required()
def get_admin_payout_report():
    try:
        merchant_id = request.args.get('merchant_id')
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
                    pt.merchant_id LIKE %s OR 
                    m.full_name LIKE %s OR
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    pt.utr LIKE %s OR
                    pt.bank_ref_no LIKE %s
                )"""
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 9)
            
            if from_date:
                query += " AND DATE(pt.created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(pt.created_at) <= %s"
                params.append(to_date)
            
            query += " ORDER BY pt.created_at DESC"
            
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
        return jsonify({'success': True, 'data': formatted_payouts}), 200
        
    except Exception as e:
        print(f"Error in get_admin_payout_report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@payout_bp.route('/admin/payout-report/all', methods=['GET'])
@jwt_required()
def get_admin_payout_report_all():
    """Get ALL payout transactions (admin only) with filters - for download"""
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
            
            query = """
                SELECT 
                    pt.id,
                    pt.txn_id,
                    pt.merchant_id,
                    pt.admin_id,
                    pt.reference_id,
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
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    m.full_name LIKE %s
                )"""
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 6)
            
            if from_date:
                query += " AND DATE(pt.created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(pt.created_at) <= %s"
                params.append(to_date)
            
            query += " ORDER BY pt.created_at DESC"
            
            cursor.execute(query, params)
            payouts = cursor.fetchall()
            
            # Format the data
            formatted_payouts = []
            for payout in payouts:
                formatted_payout = {
                    'id': payout.get('id'),
                    'txn_id': payout.get('txn_id'),
                    'merchant_id': payout.get('merchant_id'),
                    'admin_id': payout.get('admin_id'),
                    'reference_id': payout.get('reference_id'),
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
                formatted_payouts.append(formatted_payout)
        
        conn.close()
        return jsonify({'success': True, 'data': formatted_payouts, 'count': len(formatted_payouts)}), 200
    
    except Exception as e:
        print(f"Error in get_admin_payout_report_all: {e}")
        import traceback
        error_details = traceback.format_exc()
        print(f"Full traceback: {error_details}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


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
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    pt.utr LIKE %s OR
                    pt.bank_ref_no LIKE %s
                )"""
                search_pattern = f"%{search}%"
                params.extend([search_pattern] * 7)

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
    """Get ALL payout report for merchant (for download) with filters"""
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
            query = """
                SELECT
                    pt.id,
                    pt.txn_id,
                    pt.merchant_id,
                    pt.reference_id,
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
                    pt.bene_name LIKE %s OR
                    pt.account_no LIKE %s OR
                    pt.ifsc_code LIKE %s OR
                    pt.utr LIKE %s OR
                    pt.bank_ref_no LIKE %s
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

            cursor.execute(query, params)
            payouts = cursor.fetchall()

            formatted_payouts = []
            for payout in payouts:
                formatted_payout = {
                    'id': payout['id'],
                    'txn_id': payout['txn_id'],
                    'merchant_id': payout['merchant_id'],
                    'reference_id': payout['reference_id'],
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
        print(f"Error in get_client_payout_report_all: {e}")
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
    Check payout status from Mudrape and update database automatically.
    This endpoint is for merchants to check their own payout transactions.
    """
    try:
        merchant_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            # Get transaction details - ensure it belongs to the merchant
            cursor.execute("""
                SELECT txn_id, reference_id, pg_partner, status, merchant_id
                FROM payout_transactions
                WHERE txn_id = %s AND merchant_id = %s
            """, (txn_id, merchant_id))
            
            txn = cursor.fetchone()
            
            if not txn:
                conn.close()
                return jsonify({'success': False, 'message': 'Transaction not found or unauthorized'}), 404
            
            if txn['pg_partner'] != 'Mudrape':
                conn.close()
                return jsonify({'success': False, 'message': 'Only Mudrape transactions can be checked'}), 400
            
            print(f"Merchant {merchant_id} checking status for {txn['txn_id']} - {txn['reference_id']}")
            
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
            
            print(f"✓ Transaction {txn_id} checked successfully - Status: {new_status}, UTR: {utr}")
            
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
            
            print(f"✓ Transaction {txn_id} synced successfully - Status: {new_status}, Created: {created_at_from_api}, Completed: {completed_at_from_api}")
            
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
