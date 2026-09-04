"""
Wallet Service
Centralized wallet management for admin and merchants
"""

from database import get_db_connection
from datetime import datetime
import uuid


class WalletService:
    """Wallet management service"""
    
    def __init__(self):
        pass
    
    def generate_txn_id(self, prefix='WT'):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"{prefix}{timestamp}{unique_id}"
    
    # ==================== ADMIN WALLET ====================
    
    def get_admin_wallet(self, admin_id='admin'):
        """Get admin wallet balance with totals"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM admin_wallet WHERE admin_id = %s
                """, (admin_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO admin_wallet (admin_id, main_balance)
                        VALUES (%s, 0.00)
                    """, (admin_id,))
                    conn.commit()
                    wallet = {'admin_id': admin_id, 'main_balance': 0.00}
                
                # Get total credits and debits
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                        COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit
                    FROM admin_wallet_transactions
                    WHERE admin_id = %s
                """, (admin_id,))
                totals = cursor.fetchone()
                
                if totals:
                    wallet['total_credit'] = float(totals['total_credit'])
                    wallet['total_debit'] = float(totals['total_debit'])
                else:
                    wallet['total_credit'] = 0.00
                    wallet['total_debit'] = 0.00
            
            conn.close()
            return wallet
            
        except Exception as e:
            print(f"Get admin wallet error: {e}")
            return None
    
    def credit_admin_wallet(self, admin_id, amount, description, reference_id=None):
        """Credit admin wallet"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get current balance
                cursor.execute("""
                    SELECT main_balance FROM admin_wallet WHERE admin_id = %s
                """, (admin_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet
                    cursor.execute("""
                        INSERT INTO admin_wallet (admin_id, main_balance)
                        VALUES (%s, 0.00)
                    """, (admin_id,))
                    balance_before = 0.00
                else:
                    balance_before = float(wallet['main_balance'])
                
                balance_after = balance_before + float(amount)
                
                # Update balance
                cursor.execute("""
                    UPDATE admin_wallet 
                    SET main_balance = %s 
                    WHERE admin_id = %s
                """, (balance_after, admin_id))
                
                # Record transaction
                txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s)
                """, (admin_id, txn_id, amount, balance_before, balance_after, description, reference_id))
                
                conn.commit()
            
            conn.close()
            return {
                'success': True,
                'txn_id': txn_id,
                'balance_before': balance_before,
                'balance_after': balance_after
            }
            
        except Exception as e:
            print(f"Credit admin wallet error: {e}")
            return {'success': False, 'message': str(e)}
    
    def debit_admin_wallet(self, admin_id, amount, description, reference_id=None, conn=None):
        """
        Debit admin wallet - balance calculated dynamically

        Args:
            admin_id: Admin user ID
            amount: Amount to debit
            description: Transaction description
            reference_id: Optional reference ID
            conn: Optional existing database connection for transaction support
                  If provided, caller is responsible for commit/rollback
        """
        should_close_conn = False
        try:
            if conn is None:
                conn = get_db_connection()
                should_close_conn = True

            if not conn:
                return {'success': False, 'message': 'Database connection failed'}

            with conn.cursor() as cursor:
                # Calculate current balance dynamically
                # PayIN amount
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                """)
                total_payin = float(cursor.fetchone()['total_payin'])

                # Approved fund requests (debits)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                """)
                total_topup = float(cursor.fetchone()['total_topup'])

                # Fetch from merchants (credits)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetch
                    FROM merchant_wallet_transactions
                    WHERE txn_type = 'DEBIT' 
                    AND description LIKE '%fetched by admin%'
                """)
                total_fetch = float(cursor.fetchone()['total_fetch'])

                # Personal payouts (ONLY admin payouts, not merchant payouts)
                # Admin payouts have reference_id starting with 'ADMIN'
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payout
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED')
                    AND reference_id LIKE 'ADMIN%'
                """)
                total_payout = float(cursor.fetchone()['total_payout'])

                # Manual adjustments from admin_wallet_transactions
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

                # Calculate balance
                balance_before = total_payin + total_fetch - total_topup - total_payout + total_adjustments

                if balance_before < float(amount):
                    if should_close_conn:
                        conn.close()
                    return {
                        'success': False, 
                        'message': f'Insufficient balance in wallet, remaining balance in wallet: ₹{balance_before:.2f}'
                    }

                balance_after = balance_before - float(amount)

                # Record transaction (no need to update admin_wallet table)
                txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s)
                """, (admin_id, txn_id, amount, balance_before, balance_after, description, reference_id))

                # Only commit if we created the connection
                if should_close_conn:
                    conn.commit()
                    conn.close()

            return {
                'success': True,
                'txn_id': txn_id,
                'balance_before': balance_before,
                'balance_after': balance_after
            }

        except Exception as e:
            print(f"Debit admin wallet error: {e}")
            if should_close_conn and conn:
                conn.close()
            return {'success': False, 'message': str(e)}


    
    def get_admin_transactions(self, admin_id, filters=None):
        """Get admin wallet transactions"""
        try:
            conn = get_db_connection()
            if not conn:
                return []
            
            with conn.cursor() as cursor:
                query = """
                    SELECT * FROM admin_wallet_transactions
                    WHERE admin_id = %s
                """
                params = [admin_id]
                
                if filters:
                    if filters.get('from_date'):
                        query += " AND DATE(created_at) >= %s"
                        params.append(filters['from_date'])
                    if filters.get('to_date'):
                        query += " AND DATE(created_at) <= %s"
                        params.append(filters['to_date'])
                    if filters.get('txn_type'):
                        query += " AND txn_type = %s"
                        params.append(filters['txn_type'])
                
                query += " ORDER BY created_at DESC"
                
                if filters and filters.get('limit'):
                    query += f" LIMIT {filters['limit']}"
                
                cursor.execute(query, params)
                transactions = cursor.fetchall()
            
            conn.close()
            return transactions
            
        except Exception as e:
            print(f"Get admin transactions error: {e}")
            return []
    
    # ==================== MERCHANT WALLET ====================
    
    def get_merchant_wallet(self, merchant_id):
        """Get merchant wallet balance with totals"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet if doesn't exist
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance)
                        VALUES (%s, 0.00)
                    """, (merchant_id,))
                    conn.commit()
                    wallet = {'merchant_id': merchant_id, 'balance': 0.00}
                
                # Get total credits and debits
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                        COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s
                """, (merchant_id,))
                totals = cursor.fetchone()
                
                if totals:
                    wallet['total_credit'] = float(totals['total_credit'])
                    wallet['total_debit'] = float(totals['total_debit'])
                else:
                    wallet['total_credit'] = 0.00
                    wallet['total_debit'] = 0.00
            
            conn.close()
            return wallet
            
        except Exception as e:
            print(f"Get merchant wallet error: {e}")
            return None
    
    def credit_merchant_wallet(self, merchant_id, amount, description, reference_id=None):
        """Credit merchant wallet (to settled balance) - used for fund requests/topups with row-level locking"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get current settled balance with row lock
                cursor.execute("""
                    SELECT settled_balance, balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                    FOR UPDATE
                """, (merchant_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, %s, %s, 0.00)
                    """, (merchant_id, amount, amount))
                    settled_before = 0.00
                else:
                    settled_before = float(wallet['settled_balance'])
                
                settled_after = settled_before + float(amount)
                
                # Update settled balance (and legacy balance for backward compatibility)
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET settled_balance = %s, balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (settled_after, settled_after, merchant_id))
                
                # Record transaction
                txn_id = self.generate_txn_id('MWT')
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, 
                     description, reference_id)
                    VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s)
                """, (merchant_id, txn_id, amount, settled_before, settled_after, 
                      description, reference_id))
                
                conn.commit()
            
            conn.close()
            return {
                'success': True,
                'txn_id': txn_id,
                'balance_before': settled_before,
                'balance_after': settled_after
            }
            
        except Exception as e:
            print(f"Credit merchant wallet error: {e}")
            return {'success': False, 'message': str(e)}
    
    def debit_merchant_wallet(self, merchant_id, amount, description, reference_id=None):
        """Debit merchant wallet (from settled balance) with row-level locking"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get current settled balance with row lock to prevent race conditions
                # FOR UPDATE locks the row until transaction commits
                cursor.execute("""
                    SELECT settled_balance, balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                    FOR UPDATE
                """, (merchant_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    conn.close()
                    return {'success': False, 'message': 'Wallet not found'}
                
                settled_before = float(wallet['settled_balance'])
                
                if settled_before < float(amount):
                    conn.close()
                    return {
                        'success': False, 
                        'message': f'Insufficient balance in wallet, remaining balance in wallet: ₹{settled_before:.2f}'
                    }
                
                settled_after = settled_before - float(amount)
                
                # Update settled balance (and legacy balance for backward compatibility)
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET settled_balance = %s, balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (settled_after, settled_after, merchant_id))
                
                # Record transaction
                txn_id = self.generate_txn_id('MWT')
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after,
                     description, reference_id)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s)
                """, (merchant_id, txn_id, amount, settled_before, settled_after,
                      description, reference_id))
                
                conn.commit()
            
            conn.close()
            return {
                'success': True,
                'txn_id': txn_id,
                'balance_before': settled_before,
                'balance_after': settled_after
            }
            
        except Exception as e:
            print(f"Debit merchant wallet error: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_merchant_transactions(self, merchant_id, filters=None):
        """Get merchant wallet transactions"""
        try:
            conn = get_db_connection()
            if not conn:
                return []
            
            with conn.cursor() as cursor:
                query = """
                    SELECT * FROM merchant_wallet_transactions
                    WHERE merchant_id = %s
                """
                params = [merchant_id]
                
                if filters:
                    if filters.get('from_date'):
                        query += " AND DATE(created_at) >= %s"
                        params.append(filters['from_date'])
                    if filters.get('to_date'):
                        query += " AND DATE(created_at) <= %s"
                        params.append(filters['to_date'])
                    if filters.get('txn_type'):
                        query += " AND txn_type = %s"
                        params.append(filters['txn_type'])
                
                query += " ORDER BY created_at DESC"
                
                if filters and filters.get('limit'):
                    query += f" LIMIT {filters['limit']}"
                
                cursor.execute(query, params)
                transactions = cursor.fetchall()
            
            conn.close()
            return transactions
            
        except Exception as e:
            print(f"Get merchant transactions error: {e}")
            return []
    
    # ==================== SETTLED/UNSETTLED WALLET ====================
    
    def credit_unsettled_wallet(self, merchant_id, amount, description, reference_id=None):
        """Credit unsettled wallet (called from payin callback) with row-level locking"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get current balances with row lock
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                    FOR UPDATE
                """, (merchant_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    # Create wallet
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, 0.00, 0.00, %s)
                    """, (merchant_id, amount))
                    unsettled_before = 0.00
                else:
                    unsettled_before = float(wallet['unsettled_balance'])
                
                unsettled_after = unsettled_before + float(amount)
                
                # Update unsettled balance
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET unsettled_balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (unsettled_after, merchant_id))
                
                # Record transaction
                txn_id = self.generate_txn_id('MWT')
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, 
                     description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                """, (merchant_id, txn_id, amount, unsettled_before, unsettled_after, 
                      description, reference_id))
                
                conn.commit()
            
            conn.close()
            return {
                'success': True,
                'txn_id': txn_id,
                'unsettled_before': unsettled_before,
                'unsettled_after': unsettled_after
            }
            
        except Exception as e:
            print(f"Credit unsettled wallet error: {e}")
            return {'success': False, 'message': str(e)}
    def credit_admin_unsettled_wallet(self, admin_id, amount, description, reference_id=None):
        """Credit admin unsettled wallet (called from payin callback for charges)"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}

            with conn.cursor() as cursor:
                # Get current admin wallet - FIXED: Get unsettled_balance instead of main_balance
                cursor.execute("""
                    SELECT unsettled_balance FROM admin_wallet WHERE admin_id = %s
                """, (admin_id,))
                wallet = cursor.fetchone()

                if not wallet:
                    # Create wallet with unsettled_balance
                    cursor.execute("""
                        INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                        VALUES (%s, 0.00, %s)
                    """, (admin_id, amount))
                    balance_before = 0.00
                else:
                    balance_before = float(wallet['unsettled_balance'])

                balance_after = balance_before + float(amount)

                # Update unsettled_balance - FIXED: Update correct column
                cursor.execute("""
                    UPDATE admin_wallet
                    SET unsettled_balance = %s, last_updated = NOW()
                    WHERE admin_id = %s
                """, (balance_after, admin_id))

                # Record transaction
                txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
                """, (admin_id, txn_id, amount, balance_before, balance_after, description, reference_id))

                conn.commit()

            conn.close()
            return {
                'success': True,
                'txn_id': txn_id,
                'balance_before': balance_before,
                'balance_after': balance_after
            }

        except Exception as e:
            print(f"Credit admin unsettled wallet error: {e}")
            return {'success': False, 'message': str(e)}

    
    def settle_wallet(self, merchant_id, amount, admin_id, remarks=None):
        """Transfer amount from unsettled to settled wallet (admin action) with row-level locking
        
        This also debits the admin wallet because:
        - PayIN goes to merchant unsettled wallet
        - When admin settles, merchant can use the funds
        - Admin wallet should be debited to reflect this release of funds
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}
            
            with conn.cursor() as cursor:
                # Get current balances with row lock
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                    FOR UPDATE
                """, (merchant_id,))
                wallet = cursor.fetchone()
                
                if not wallet:
                    conn.close()
                    return {'success': False, 'message': 'Wallet not found'}
                
                unsettled_balance = float(wallet['unsettled_balance'])
                settled_balance = float(wallet['settled_balance'])
                
                if unsettled_balance < float(amount):
                    conn.close()
                    return {
                        'success': False, 
                        'message': f'Insufficient unsettled balance. Available: ₹{unsettled_balance:.2f}'
                    }
                
                # Update merchant balances
                new_unsettled = unsettled_balance - float(amount)
                new_settled = settled_balance + float(amount)
                
                cursor.execute("""
                    UPDATE merchant_wallet 
                    SET settled_balance = %s, unsettled_balance = %s, balance = %s, last_updated = NOW()
                    WHERE merchant_id = %s
                """, (new_settled, new_unsettled, new_settled, merchant_id))
                
                # Generate settlement ID
                settlement_id = self.generate_txn_id('STL')
                
                # Record settlement transaction
                cursor.execute("""
                    INSERT INTO settlement_transactions 
                    (settlement_id, merchant_id, amount, settled_by, remarks)
                    VALUES (%s, %s, %s, %s, %s)
                """, (settlement_id, merchant_id, amount, admin_id, remarks))
                
                # Record merchant wallet transaction
                txn_id = self.generate_txn_id('MWT')
                cursor.execute("""
                    INSERT INTO merchant_wallet_transactions 
                    (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, 
                     description, reference_id)
                    VALUES (%s, %s, 'SETTLEMENT', %s, %s, %s, %s, %s)
                """, (merchant_id, txn_id, amount, settled_balance, new_settled, 
                      f'Settled by admin - {remarks or ""}', settlement_id))
                
                # Settlement complete - no admin wallet involvement needed
                # The settlement simply moves funds from merchant unsettled to settled
                
            conn.commit()
            
            conn.close()
            return {
                'success': True,
                'settlement_id': settlement_id,
                'settled_balance': new_settled,
                'unsettled_balance': new_unsettled
            }
            
        except Exception as e:
            print(f"Settle wallet error: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
                conn.close()
            return {'success': False, 'message': f'Settlement failed: {str(e)}'}
    
    def get_all_merchants_wallet_summary(self):
        """
        Get total settled and unsettled amounts across all merchants
        
        Total Settled = All topups (historical) + current settled_balance (cumulative, never decreases)
        Total Unsettled = All net PayIns after charges (current unsettled amounts)
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'total_settled': 0, 'total_unsettled': 0}
            
            with conn.cursor() as cursor:
                # Total Settled = All approved topups (historical) + current settled_balance
                # This represents all money that has been settled to merchants over time
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topups
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                """)
                total_topups = float(cursor.fetchone()['total_topups'])
                
                # Add current settled balances (money currently available for payout)
                cursor.execute("""
                    SELECT COALESCE(SUM(settled_balance), 0) as current_settled
                    FROM merchant_wallet
                """)
                current_settled = float(cursor.fetchone()['current_settled'])
                
                # Total settled = historical topups + current settled balance
                # This is cumulative and represents all money settled to merchants
                total_settled = total_topups + current_settled
                
                # Total Unsettled = Sum of all net PayIns (after charges)
                # For historical data, use net_amount from payin_transactions
                # For current data, use unsettled_balance from merchant_wallet
                cursor.execute("""
                    SELECT COALESCE(SUM(net_amount), 0) as total_net_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                """)
                total_net_payin = float(cursor.fetchone()['total_net_payin'])
                
                # Current unsettled balance (what's pending settlement now)
                cursor.execute("""
                    SELECT COALESCE(SUM(unsettled_balance), 0) as current_unsettled
                    FROM merchant_wallet
                """)
                current_unsettled = float(cursor.fetchone()['current_unsettled'])
                
                # Use current unsettled balance as it reflects the actual pending amount
                total_unsettled = current_unsettled
            
            conn.close()
            return {
                'total_settled': total_settled,
                'total_unsettled': total_unsettled,
                'total_topups': total_topups,
                'current_settled': current_settled,
                'total_net_payin': total_net_payin
            }
            
        except Exception as e:
            print(f"Get wallet summary error: {e}")
            return {
                'total_settled': 0, 
                'total_unsettled': 0,
                'total_topups': 0,
                'current_settled': 0,
                'total_net_payin': 0
            }


# Create singleton instance
wallet_service = WalletService()
