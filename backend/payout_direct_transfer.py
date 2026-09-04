# Add this new endpoint to payout_routes.py after the client_settle_fund function

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
        required_fields = ['amount', 'tpin', 'account_holder_name', 'account_number', 'ifsc_code', 'bank_name']
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
                
                # Calculate net amount to be sent to bank (amount - charges)
                net_amount_to_bank = amount - charges['charge_amount']
                
                if net_amount_to_bank <= 0:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Payout amount is too low to cover charges'}), 400
                
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
                
                # Check if available balance is sufficient
                if amount > available_balance:
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'message': f'Insufficient balance. Required: ₹{amount}, Available: ₹{available_balance}'
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
                    (txn_id, reference_id, merchant_id, amount, charge_amount, charge_type, 
                     net_amount, bene_name, bene_email, bene_mobile, bene_bank, account_no, 
                     ifsc_code, payment_type, purpose, pg_partner, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'INITIATED', NOW())
                """, (txn_id, reference_id, merchant_id, amount, 
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
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'net_amount': net_amount_to_bank,
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
                        
                        print(f"DEBUG: Mudrape payout initiated - Status: {status}, TxnID: {mudrape_txn_id}")
                        
                        # Set completed_at if status is final
                        if status in ['SUCCESS', 'FAILED']:
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE reference_id = %s
                            """, (status, mudrape_txn_id, reference_id))
                        else:
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                WHERE reference_id = %s
                            """, (status, mudrape_txn_id, reference_id))
                        
                        conn.commit()
                        print(f"DEBUG: Initial UPDATE committed")
                        
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
                                
                                # Update with latest status
                                if updated_status in ['SUCCESS', 'FAILED']:
                                    if completed_at_from_api:
                                        # Use the timestamp from Mudrape
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = %s, updated_at = NOW()
                                            WHERE reference_id = %s
                                        """, (updated_status, utr, completed_at_from_api, reference_id))
                                    else:
                                        # Fallback to NOW() if no timestamp from Mudrape
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                            WHERE reference_id = %s
                                        """, (updated_status, utr, reference_id))
                                else:
                                    cursor.execute("""
                                        UPDATE payout_transactions 
                                        SET status = %s, utr = %s, updated_at = NOW()
                                        WHERE reference_id = %s
                                    """, (updated_status, utr, reference_id))
                                
                                conn.commit()
                                print(f"DEBUG: Final UPDATE committed")
                                status = updated_status
                        
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'message': 'Payout initiated successfully',
                            'txn_id': txn_id,
                            'reference_id': reference_id,
                            'amount': amount,
                            'charges': charges['charge_amount'],
                            'net_amount': net_amount_to_bank,
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
                        'amount': amount,
                        'charges': charges['charge_amount'],
                        'net_amount': net_amount_to_bank,
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
