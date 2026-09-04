"""
Backfill missing admin wallet debit transactions for existing settlements
"""

from database import get_db_connection
from config import Config
import random
import string

def generate_txn_id(prefix='AWT'):
    """Generate unique transaction ID"""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{random_part}"

def backfill_admin_settlement_debits():
    print("=" * 80)
    print("BACKFILLING ADMIN WALLET SETTLEMENT DEBITS")
    print("=" * 80)
    print()
    
    try:
        conn = get_db_connection()
        if not conn:
            print("✗ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Get all settlements that don't have corresponding admin wallet transactions
            print("1. Finding settlements without admin wallet debits...")
            cursor.execute("""
                SELECT 
                    s.settlement_id,
                    s.merchant_id,
                    s.amount,
                    s.settled_by,
                    s.remarks,
                    s.created_at
                FROM settlement_transactions s
                LEFT JOIN admin_wallet_transactions awt 
                    ON awt.reference_id = s.settlement_id
                WHERE awt.txn_id IS NULL
                ORDER BY s.created_at ASC
            """)
            missing_settlements = cursor.fetchall()
            
            if not missing_settlements:
                print("✓ No missing admin wallet transactions found")
                conn.close()
                return True
            
            print(f"✓ Found {len(missing_settlements)} settlements without admin wallet debits")
            print()
            
            # Calculate admin balance at each point in time
            print("2. Backfilling admin wallet transactions...")
            
            for idx, settlement in enumerate(missing_settlements, 1):
                settlement_id = settlement['settlement_id']
                merchant_id = settlement['merchant_id']
                amount = float(settlement['amount'])
                admin_id = settlement['settled_by']
                created_at = settlement['created_at']
                
                # Calculate admin balance BEFORE this settlement
                # Get all transactions before this settlement
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE status = 'SUCCESS'
                    AND created_at < %s
                """, (created_at,))
                total_payin = float(cursor.fetchone()['total_payin'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE status = 'APPROVED'
                    AND created_at < %s
                """, (created_at,))
                total_topup = float(cursor.fetchone()['total_topup'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetch
                    FROM merchant_wallet_transactions
                    WHERE txn_type = 'DEBIT' 
                    AND description LIKE '%fetched by admin%'
                    AND created_at < %s
                """, (created_at,))
                total_fetch = float(cursor.fetchone()['total_fetch'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(
                        CASE 
                            WHEN txn_type = 'CREDIT' THEN amount
                            WHEN txn_type = 'DEBIT' THEN -amount
                            ELSE 0
                        END
                    ), 0) as total_adjustments
                    FROM admin_wallet_transactions
                    WHERE (description LIKE '%Manual balance%'
                    OR description LIKE '%Balance adjustment%'
                    OR description LIKE '%Initial capital%')
                    AND created_at < %s
                """, (created_at,))
                total_adjustments = float(cursor.fetchone()['total_adjustments'])
                
                # Get settlements before this one
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_settlements
                    FROM settlement_transactions
                    WHERE created_at < %s
                """, (created_at,))
                total_settlements = float(cursor.fetchone()['total_settlements'])
                
                admin_balance_before = total_payin + total_fetch - total_topup - total_settlements + total_adjustments
                admin_balance_after = admin_balance_before - amount
                
                # Insert admin wallet transaction with original timestamp
                admin_txn_id = generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id, created_at)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s, %s)
                """, (admin_id, admin_txn_id, amount, admin_balance_before, admin_balance_after,
                      f"Settlement for merchant {merchant_id} - {settlement_id}", settlement_id, created_at))
                
                print(f"  {idx}. ✓ Created {admin_txn_id} for {settlement_id}: ₹{amount:.2f} (Balance: ₹{admin_balance_before:.2f} → ₹{admin_balance_after:.2f})")
            
            print()
            print("3. Committing changes...")
            conn.commit()
            print("✓ All changes committed successfully")
            print()
            
            # Verify
            print("4. Verification:")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM settlement_transactions
            """)
            total_settlements = float(cursor.fetchone()['total_settlements'])
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_admin_settlement_debits
                FROM admin_wallet_transactions
                WHERE txn_type = 'DEBIT'
                AND (description LIKE '%Settlement%' OR reference_id LIKE 'STL%')
            """)
            total_admin_settlement_debits = float(cursor.fetchone()['total_admin_settlement_debits'])
            
            print(f"  Total in settlement_transactions: ₹{total_settlements:.2f}")
            print(f"  Total admin settlement debits: ₹{total_admin_settlement_debits:.2f}")
            
            if abs(total_settlements - total_admin_settlement_debits) < 0.01:
                print("  ✓ Settlements now match admin wallet debits!")
            else:
                print(f"  ✗ Still a mismatch: ₹{abs(total_settlements - total_admin_settlement_debits):.2f}")
            print()
        
        conn.close()
        
        print("=" * 80)
        print("BACKFILL COMPLETED SUCCESSFULLY")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    print()
    response = input("This will create admin wallet debit transactions for existing settlements. Continue? (yes/no): ")
    if response.lower() == 'yes':
        backfill_admin_settlement_debits()
    else:
        print("Backfill cancelled.")
