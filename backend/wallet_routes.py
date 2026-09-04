"""
Wallet Routes
API endpoints for admin and merchant wallet management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import wallet_service

wallet_bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')
wallet_svc = wallet_service.wallet_service

# ==================== ADMIN WALLET ROUTES ====================

@wallet_bp.route('/admin/overview', methods=['GET'])
@jwt_required()
def get_admin_wallet_overview():
    """Get admin wallet overview - calculated from PayIN + Fetch - Topups - Payouts"""
    try:
        admin_id = get_jwt_identity()
        
        from database import get_db_connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        with conn.cursor() as cursor:
            # Calculate total successful PayIN amount (credits to admin)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_payin,
                    COUNT(*) as payin_count
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            payin_stats = cursor.fetchone()
            total_payin = float(payin_stats['total_payin'])
            
            # Calculate total approved fund requests (debits from admin)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            topup_stats = cursor.fetchone()
            total_topup = float(topup_stats['total_topup'])
            
            # Calculate total fetch from merchants (credits to admin)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE %s
            """, ('%fetched by admin%',))
            fetch_stats = cursor.fetchone()
            total_fetch = float(fetch_stats['total_fetch'])
            
            # Calculate total settlements (debits from admin)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_settlements
                FROM settlement_transactions
            """)
            settlement_stats = cursor.fetchone()
            total_settlements = float(settlement_stats['total_settlements'])
            
            # Get admin unsettled balance (payin charges collected but not yet settled)
            cursor.execute("""
                SELECT COALESCE(unsettled_balance, 0) as unsettled_balance
                FROM admin_wallet
                WHERE admin_id = 'admin'
            """)
            admin_wallet_row = cursor.fetchone()
            admin_unsettled = float(admin_wallet_row['unsettled_balance']) if admin_wallet_row else 0.00
            
            # Calculate manual adjustments from admin_wallet_transactions
            # These are manual balance corrections that don't appear in PayIN reports
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(
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
            adjustment_stats = cursor.fetchone()
            total_adjustments = float(adjustment_stats['total_adjustments'])
            
            # Admin Balance = PayIN + Fetch + Unsettled - Topups - Settlements + Manual Adjustments
            # Topups transfer money FROM admin wallet TO merchant wallets
            # Settlements transfer money FROM admin TO merchant (releasing unsettled funds)
            # Unsettled balance contains payin charges that haven't been settled yet
            # Payouts are paid from merchant wallets, NOT from admin wallet
            # Manual adjustments are balance corrections that don't appear in reports
            admin_balance = total_payin + total_fetch + admin_unsettled - total_topup - total_settlements + total_adjustments
            
            # Get recent transactions from admin_wallet_transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    description,
                    created_at
                FROM admin_wallet_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent_transactions = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'main_balance': admin_balance,  # Calculated: PayIN + Fetch + Unsettled - Topups - Settlements + Manual Adjustments
                'total_credit': total_payin + total_fetch + admin_unsettled,
                'total_debit': total_topup + total_settlements,
                'payin_amount': total_payin,
                'topup_amount': total_topup,
                'fetch_amount': total_fetch,
                'settlement_amount': total_settlements,
                'unsettled_balance': admin_unsettled,
                'manual_adjustments': total_adjustments,
                'recent_transactions': recent_transactions
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@wallet_bp.route('/admin/statement', methods=['GET'])
@jwt_required()
def get_admin_wallet_statement():
    """Get admin wallet statement - from PayIN and wallet transactions"""
    try:
        admin_id = get_jwt_identity()
        
        # Get filters from query params
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        txn_type = request.args.get('txn_type')
        
        from database import get_db_connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        with conn.cursor() as cursor:
            # Build query for combined transactions
            query = """
                SELECT * FROM (
                    (SELECT 
                        id,
                        txn_id,
                        'CREDIT' as txn_type,
                        amount,
                        0 as balance_before,
                        0 as balance_after,
                        CONCAT('PayIN from merchant ', merchant_id) as description,
                        txn_id as reference_id,
                        created_at
                    FROM payin_transactions
                    WHERE status = 'SUCCESS')
                    
                    UNION ALL
                    
                    (SELECT 
                        id,
                        txn_id,
                        CASE 
                            WHEN txn_type = 'CREDIT' THEN 'DEBIT'
                            ELSE 'CREDIT'
                        END as txn_type,
                        amount,
                        balance_before,
                        balance_after,
                        description,
                        reference_id,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE description LIKE %s)
                    
                    UNION ALL
                    
                    (SELECT 
                        id,
                        txn_id,
                        'DEBIT' as txn_type,
                        amount,
                        0 as balance_before,
                        0 as balance_after,
                        CONCAT('Personal Payout - ', txn_id) as description,
                        reference_id,
                        created_at
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED'))
                ) as combined_transactions
                WHERE 1=1
            """
            
            params = ['%admin%']  # Initialize with the LIKE parameter
            
            if from_date:
                query += " AND DATE(created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(created_at) <= %s"
                params.append(to_date)
            
            if txn_type:
                query += " AND txn_type = %s"
                params.append(txn_type)
            
            query += " ORDER BY created_at DESC LIMIT 100"
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            # Calculate current balance
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            payin_total = float(cursor.fetchone()['total_payin'])
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_topup,
                    COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE description LIKE %s
            """, ('%admin%',))
            wallet_totals = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
            """)
            payout_total = float(cursor.fetchone()['total_payout'])
            
            current_balance = payin_total - float(wallet_totals['total_topup']) + float(wallet_totals['total_fetch']) - payout_total
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': transactions,
            'wallet': {
                'main_balance': current_balance
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== MERCHANT WALLET ROUTES ====================

@wallet_bp.route('/merchant/overview', methods=['GET'])
@jwt_required()
def get_merchant_wallet_overview():
    """Get merchant wallet overview with balance and recent transactions"""
    try:
        # Check if merchant_id is provided in query params (for admin viewing merchant wallet)
        merchant_id = request.args.get('merchant_id')
        
        if not merchant_id:
            # If not provided, use JWT identity (merchant viewing their own wallet)
            merchant_id = get_jwt_identity()
        
        from database import get_db_connection
        conn = get_db_connection()
        
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        with conn.cursor() as cursor:
            # Get settled and unsettled balances from merchant_wallet
            # Use FOR UPDATE to ensure we read the latest committed data
            cursor.execute("""
                SELECT settled_balance, unsettled_balance, balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet_result = cursor.fetchone()
            
            if wallet_result:
                settled_balance = float(wallet_result['settled_balance'])
                unsettled_balance = float(wallet_result['unsettled_balance'])
                # Use the old balance field as settled_balance if settled_balance is 0
                if settled_balance == 0 and wallet_result['balance']:
                    settled_balance = float(wallet_result['balance'])
            else:
                # Create wallet if doesn't exist
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00, 0.00)
                """, (merchant_id,))
                conn.commit()
                settled_balance = 0.00
                unsettled_balance = 0.00
            
            # Wallet Balance = Settled Balance (no calculation, just use the field directly)
            wallet_balance = settled_balance
            
            # Get total payouts (for display only)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payouts
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
            """, (merchant_id,))
            payout_result = cursor.fetchone()
            total_payouts = float(payout_result['total_payouts']) if payout_result else 0
            
            # Get total fetched by admin (for display)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetched
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s 
                AND txn_type = 'DEBIT'
                AND description LIKE '%%fetched by admin%%'
            """, (merchant_id,))
            fetch_result = cursor.fetchone()
            total_fetched = float(fetch_result['total_fetched']) if fetch_result else 0
            
            # Get total fund requests (for display - legacy)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            topup_result = cursor.fetchone()
            total_topup = float(topup_result['total_topup']) if topup_result else 0
            
            # Get total PayIN amount (net amount after charges) - for display only
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as gross_amount,
                    COALESCE(SUM(charge_amount), 0) as total_charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s AND status = 'SUCCESS'
            """, (merchant_id,))
            payin_result = cursor.fetchone()
            gross_payin = float(payin_result['gross_amount']) if payin_result else 0
            total_charges = float(payin_result['total_charges']) if payin_result else 0
            net_payin = float(payin_result['net_amount']) if payin_result else 0
            
            # Get total Payout charges - for display only
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(charge_amount), 0) as total_payout_charges
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
            """, (merchant_id,))
            payout_charge_result = cursor.fetchone()
            total_payout_charges = float(payout_charge_result['total_payout_charges']) if payout_charge_result else 0
        
        conn.close()
        
        # Get recent transactions
        recent_transactions = wallet_svc.get_merchant_transactions(merchant_id, {'limit': 10})
        
        response = jsonify({
            'success': True,
            'data': {
                'balance': wallet_balance,  # Settled Balance (available for payout)
                'settled_balance': settled_balance,  # Same as balance
                'unsettled_balance': unsettled_balance,  # Unsettled amount pending admin approval
                'on_hold': 0.00,
                'total_credit': 0,  # Legacy field
                'total_debit': 0,  # Legacy field
                'total_topup': total_topup,  # Total topped up by admin (for display)
                'total_fetched': total_fetched,  # Total fetched by admin (for display)
                'payin_amount': net_payin,  # Net PayIN amount (for display)
                'gross_payin': gross_payin,  # Gross PayIN amount (for display)
                'payin_charges': total_charges,  # Total PayIN charges (for display)
                'total_settlements': total_payouts,  # Total payouts (for display)
                'payout_charges': total_payout_charges,  # Total payout charges (for display)
                'recent_transactions': recent_transactions
            }
        })
        
        # Prevent caching of balance data
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response, 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@wallet_bp.route('/merchant/statement', methods=['GET'])
@jwt_required()
def get_merchant_wallet_statement():
    """Get merchant wallet statement with filters - shows fund topups, fetches, fund requests, and settlements"""
    try:
        # Check if merchant_id is provided in query params (for admin viewing merchant wallet)
        merchant_id = request.args.get('merchant_id')
        
        if not merchant_id:
            # If not provided, use JWT identity (merchant viewing their own wallet)
            merchant_id = get_jwt_identity()
        
        # Get filters from query params
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        filter_type = request.args.get('filter_type')  # New filter: topup, fetch, fund_request, settlement, unsettled_settlement
        
        from database import get_db_connection
        conn = get_db_connection()
        
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        with conn.cursor() as cursor:
            # Build query based on filter_type
            queries = []
            params = []
            
            # 1. Fund Topped Up by Admin (CREDIT)
            if not filter_type or filter_type == 'topup':
                queries.append("""
                    SELECT 
                        id,
                        CAST(request_id AS CHAR) as txn_id,
                        'TOPUP' as category,
                        'CREDIT' as txn_type,
                        amount,
                        0 as balance_before,
                        0 as balance_after,
                        CAST(CONCAT('Fund Topped Up by Admin - ', COALESCE(remarks, '')) AS CHAR) as description,
                        CAST(request_id AS CHAR) as reference_id,
                        COALESCE(processed_at, requested_at) as created_at,
                        'APPROVED' as status
                    FROM fund_requests
                    WHERE merchant_id = %s AND status = 'APPROVED'
                """)
                params.append(merchant_id)
            
            # 2. Fund Fetched by Admin (DEBIT)
            if not filter_type or filter_type == 'fetch':
                queries.append("""
                    SELECT 
                        id,
                        CAST(txn_id AS CHAR) as txn_id,
                        'FETCH' as category,
                        'DEBIT' as txn_type,
                        amount,
                        balance_before,
                        balance_after,
                        CAST(description AS CHAR) as description,
                        CAST(reference_id AS CHAR) as reference_id,
                        created_at,
                        'COMPLETED' as status
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                    AND txn_type = 'DEBIT'
                    AND description LIKE '%%fetched by admin%%'
                """)
                params.append(merchant_id)
            
            # 3. Fund Requests (PENDING/APPROVED/REJECTED)
            if not filter_type or filter_type == 'fund_request':
                queries.append("""
                    SELECT 
                        id,
                        CAST(request_id AS CHAR) as txn_id,
                        'FUND_REQUEST' as category,
                        CASE 
                            WHEN status = 'APPROVED' THEN 'CREDIT'
                            ELSE 'PENDING'
                        END as txn_type,
                        amount,
                        0 as balance_before,
                        0 as balance_after,
                        CAST(CONCAT('Fund Request ', status, ' - ', COALESCE(remarks, '')) AS CHAR) as description,
                        CAST(request_id AS CHAR) as reference_id,
                        COALESCE(processed_at, requested_at) as created_at,
                        status
                    FROM fund_requests
                    WHERE merchant_id = %s
                """)
                params.append(merchant_id)
            
            # 4. Settled from Unsettled Wallet (CREDIT)
            if not filter_type or filter_type == 'unsettled_settlement':
                queries.append("""
                    SELECT 
                        id,
                        CAST(settlement_id AS CHAR) as txn_id,
                        'UNSETTLED_SETTLEMENT' as category,
                        'CREDIT' as txn_type,
                        amount,
                        0 as balance_before,
                        0 as balance_after,
                        CAST(CONCAT('Settled from Unsettled Wallet - ', COALESCE(remarks, '')) AS CHAR) as description,
                        CAST(settlement_id AS CHAR) as reference_id,
                        created_at,
                        'COMPLETED' as status
                    FROM settlement_transactions
                    WHERE merchant_id = %s
                """)
                params.append(merchant_id)
            
            if not queries:
                return jsonify({
                    'success': False,
                    'message': 'Invalid filter_type'
                }), 400
            
            # Combine all queries
            query = f"""
                SELECT 
                    id,
                    txn_id,
                    category,
                    txn_type,
                    amount,
                    balance_before,
                    balance_after,
                    description,
                    reference_id,
                    created_at,
                    status
                FROM (
                    {' UNION ALL '.join(f'({q})' for q in queries)}
                ) as combined_transactions
                WHERE 1=1
            """
            
            if from_date:
                query += " AND DATE(created_at) >= %s"
                params.append(from_date)
            
            if to_date:
                query += " AND DATE(created_at) <= %s"
                params.append(to_date)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            # Format dates to isoformat (same as PayinReport)
            for txn in transactions:
                if txn.get('created_at'):
                    txn['created_at'] = txn['created_at'].isoformat()
                # Convert Decimal to float
                if txn.get('amount'):
                    txn['amount'] = float(txn['amount'])
                if txn.get('balance_before'):
                    txn['balance_before'] = float(txn['balance_before'])
                if txn.get('balance_after'):
                    txn['balance_after'] = float(txn['balance_after'])
            
            # Get current wallet balance
            cursor.execute("""
                SELECT settled_balance, unsettled_balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet_result = cursor.fetchone()
            
            if wallet_result:
                settled_balance = float(wallet_result['settled_balance'])
                unsettled_balance = float(wallet_result['unsettled_balance'])
            else:
                settled_balance = 0.00
                unsettled_balance = 0.00
        
        conn.close()
        
        return jsonify({
            'success': True,
            'wallet': {
                'settled_balance': settled_balance,
                'unsettled_balance': unsettled_balance
            },
            'transactions': transactions
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== SETTLEMENT ROUTES ====================

@wallet_bp.route('/admin/settle', methods=['POST'])
@jwt_required()
def settle_merchant_wallet():
    """Admin endpoint to settle merchant wallet (transfer unsettled to settled)"""
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        
        merchant_id = data.get('merchant_id')
        amount = data.get('amount')
        remarks = data.get('remarks', '')
        
        if not merchant_id or not amount:
            return jsonify({
                'success': False,
                'message': 'merchant_id and amount are required'
            }), 400
        
        try:
            amount = float(amount)
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
        
        # Settle wallet
        result = wallet_svc.settle_wallet(merchant_id, amount, admin_id, remarks)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Wallet settled successfully',
                'data': {
                    'settlement_id': result['settlement_id'],
                    'settled_balance': result['settled_balance'],
                    'unsettled_balance': result['unsettled_balance']
                }
            }), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@wallet_bp.route('/admin/wallet-summary', methods=['GET'])
@jwt_required()
def get_wallet_summary():
    """Get total settled and unsettled amounts across all merchants"""
    try:
        admin_id = get_jwt_identity()
        
        summary = wallet_svc.get_all_merchants_wallet_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@wallet_bp.route('/merchant/wallet-details', methods=['GET'])
@jwt_required()
def get_merchant_wallet_details():
    """Get merchant wallet details with settled and unsettled balances"""
    try:
        # Check if merchant_id is provided in query params (for admin viewing merchant wallet)
        merchant_id = request.args.get('merchant_id')
        
        if not merchant_id:
            # If not provided, use JWT identity (merchant viewing their own wallet)
            merchant_id = get_jwt_identity()
        
        from database import get_db_connection
        conn = get_db_connection()
        
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        with conn.cursor() as cursor:
            # Get wallet balances
            cursor.execute("""
                SELECT settled_balance, unsettled_balance, balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            wallet = cursor.fetchone()
            
            if not wallet:
                # Create wallet if doesn't exist
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00, 0.00)
                """, (merchant_id,))
                conn.commit()
                
                wallet = {
                    'settled_balance': 0.00,
                    'unsettled_balance': 0.00,
                    'balance': 0.00
                }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'settled_balance': float(wallet['settled_balance']),
                'unsettled_balance': float(wallet['unsettled_balance']),
                'total_balance': float(wallet['balance'])
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@wallet_bp.route('/admin/merchant-summary', methods=['GET'])
@jwt_required()
def get_merchant_wallet_summary():
    """Get merchant wallet summary with payin/payout details and date filters"""
    try:
        admin_id = get_jwt_identity()
        
        # Get parameters
        merchant_id = request.args.get('merchant_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'merchant_id is required'
            }), 400
        
        from database import get_db_connection
        conn = get_db_connection()
        
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        try:
            with conn.cursor() as cursor:
                # Get wallet balances
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance, balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                
                if not wallet:
                    wallet = {
                        'settled_balance': 0.00,
                        'unsettled_balance': 0.00,
                        'balance': 0.00
                    }
                
                # Build payin query with date filters
                payin_query = """
                    SELECT 
                        COUNT(*) as payin_count,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(SUM(charge_amount), 0) as total_charges
                    FROM payin_transactions
                    WHERE merchant_id = %s AND status = 'SUCCESS'
                """
                payin_params = [merchant_id]
                
                if from_date:
                    payin_query += " AND DATE(created_at) >= %s"
                    payin_params.append(from_date)
                
                if to_date:
                    payin_query += " AND DATE(created_at) <= %s"
                    payin_params.append(to_date)
                
                cursor.execute(payin_query, payin_params)
                payin_stats = cursor.fetchone()
                
                # Build payout query with date filters
                payout_query = """
                    SELECT 
                        COUNT(*) as payout_count,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(SUM(charge_amount), 0) as total_charges
                    FROM payout_transactions
                    WHERE merchant_id = %s AND status = 'SUCCESS'
                """
                payout_params = [merchant_id]
                
                if from_date:
                    payout_query += " AND DATE(created_at) >= %s"
                    payout_params.append(from_date)
                
                if to_date:
                    payout_query += " AND DATE(created_at) <= %s"
                    payout_params.append(to_date)
                
                cursor.execute(payout_query, payout_params)
                payout_stats = cursor.fetchone()
                
                # Calculate totals
                payin_total_amount = float(payin_stats['total_amount'] or 0)
                payin_total_charges = float(payin_stats['total_charges'] or 0)
                payin_count = int(payin_stats['payin_count'] or 0)
                
                payout_total_amount = float(payout_stats['total_amount'] or 0)
                payout_total_charges = float(payout_stats['total_charges'] or 0)
                payout_count = int(payout_stats['payout_count'] or 0)
                
                # PAYIN: Amount in DB is before deducting charges (larger), after deduction is smaller
                # Before deducting charges = total amount (larger)
                # After deducting charges = amount - charges (smaller)
                payin_before_charges = payin_total_amount  # Before deducting charges (LARGER)
                payin_after_charges = payin_total_amount - payin_total_charges  # After deducting charges (SMALLER)
                
                # PAYOUT: Amount in DB is base payout (smaller), after adding charges is larger
                # Before adding charges = base amount (smaller)
                # After adding charges = amount + charges (larger)
                payout_before_charges = payout_total_amount  # Before adding charges (SMALLER)
                payout_after_charges = payout_total_amount + payout_total_charges  # After adding charges (LARGER)
                
                summary = {
                    'merchant_id': merchant_id,
                    'settled_balance': float(wallet['settled_balance']),
                    'unsettled_balance': float(wallet['unsettled_balance']),
                    'total_balance': float(wallet['balance']),
                    
                    # Payin details
                    'payin_count': payin_count,
                    'payin_before_charges': payin_before_charges,
                    'payin_after_charges': payin_after_charges,
                    'payin_total_charges': payin_total_charges,
                    
                    # Payout details
                    'payout_count': payout_count,
                    'payout_before_charges': payout_before_charges,
                    'payout_after_charges': payout_after_charges,
                    'payout_total_charges': payout_total_charges,
                    
                    # Date range
                    'from_date': from_date,
                    'to_date': to_date
                }
                
                return jsonify({
                    'success': True,
                    'data': summary
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
