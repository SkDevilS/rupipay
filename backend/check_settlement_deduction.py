"""
Check if settlement transactions are properly deducting from admin wallet
"""

from database import get_db_connection
from config import Config

def check_settlement_deduction():
    print("=" * 80)
    print("CHECKING SETTLEMENT DEDUCTION FROM ADMIN WALLET")
    print("=" * 80)
    print()
    
    try:
        conn = get_db_connection()
        if not conn:
            print("✗ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check settlement_transactions table
            print("1. Checking settlement_transactions table...")
            cursor.execute("""
                SELECT 
                    settlement_id,
                    merchant_id,
                    amount,
                    settled_by,
                    remarks,
                    created_at
                FROM settlement_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            settlements = cursor.fetchall()
            
            if settlements:
                print(f"✓ Found {len(settlements)} recent settlements:")
                for s in settlements:
                    print(f"  - {s['settlement_id']}: ₹{s['amount']} for {s['merchant_id']} on {s['created_at']}")
            else:
                print("✗ No settlements found")
            print()
            
            # Check total settlements
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM settlement_transactions
            """)
            total_settlements = float(cursor.fetchone()['total_settlements'])
            print(f"2. Total settlements: ₹{total_settlements:.2f}")
            print()
            
            # Check admin wallet transactions for settlement debits
            print("3. Checking admin_wallet_transactions for settlement debits...")
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    description,
                    reference_id,
                    created_at
                FROM admin_wallet_transactions
                WHERE description LIKE '%Settlement%'
                OR reference_id LIKE 'STL%'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            admin_txns = cursor.fetchall()
            
            if admin_txns:
                print(f"✓ Found {len(admin_txns)} admin wallet settlement transactions:")
                for txn in admin_txns:
                    print(f"  - {txn['txn_id']}: {txn['txn_type']} ₹{txn['amount']} - {txn['description']}")
            else:
                print("✗ No admin wallet settlement transactions found")
            print()
            
            # Calculate admin balance
            print("4. Calculating admin wallet balance...")
            
            # Total PayIN
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = float(cursor.fetchone()['total_payin'])
            print(f"  Total PayIN: ₹{total_payin:.2f}")
            
            # Total Topups
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = float(cursor.fetchone()['total_topup'])
            print(f"  Total Topups: ₹{total_topup:.2f}")
            
            # Total Fetch
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            total_fetch = float(cursor.fetchone()['total_fetch'])
            print(f"  Total Fetch: ₹{total_fetch:.2f}")
            
            # Manual adjustments
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
            print(f"  Manual Adjustments: ₹{total_adjustments:.2f}")
            
            # Calculate balance
            admin_balance = total_payin + total_fetch - total_topup - total_settlements + total_adjustments
            print()
            print(f"  Admin Balance = PayIN + Fetch - Topups - Settlements + Adjustments")
            print(f"  Admin Balance = {total_payin:.2f} + {total_fetch:.2f} - {total_topup:.2f} - {total_settlements:.2f} + {total_adjustments:.2f}")
            print(f"  Admin Balance = ₹{admin_balance:.2f}")
            print()
            
            # Check if settlements match admin transactions
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_admin_settlement_debits
                FROM admin_wallet_transactions
                WHERE txn_type = 'DEBIT'
                AND (description LIKE '%Settlement%' OR reference_id LIKE 'STL%')
            """)
            total_admin_settlement_debits = float(cursor.fetchone()['total_admin_settlement_debits'])
            
            print("5. Verification:")
            print(f"  Total in settlement_transactions: ₹{total_settlements:.2f}")
            print(f"  Total admin settlement debits: ₹{total_admin_settlement_debits:.2f}")
            
            if abs(total_settlements - total_admin_settlement_debits) < 0.01:
                print("  ✓ Settlements match admin wallet debits")
            else:
                print(f"  ✗ MISMATCH! Difference: ₹{abs(total_settlements - total_admin_settlement_debits):.2f}")
            print()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_settlement_deduction()
