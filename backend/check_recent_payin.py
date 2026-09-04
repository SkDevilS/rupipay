"""
Check the most recent payin transaction and its wallet impact
"""

from database import get_db_connection

def check_recent_payin():
    """Check recent payin and wallet transactions"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get the most recent payin
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    created_at,
                    completed_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            payin = cursor.fetchone()
            
            if not payin:
                print("No successful payin found")
                return
            
            print("=" * 80)
            print("MOST RECENT SUCCESSFUL PAYIN")
            print("=" * 80)
            print(f"TXN ID: {payin['txn_id']}")
            print(f"Merchant: {payin['merchant_id']}")
            print(f"Order ID: {payin['order_id']}")
            print(f"Amount: ₹{payin['amount']:.2f}")
            print(f"Charge: ₹{payin['charge_amount']:.2f}")
            print(f"Net Amount: ₹{payin['net_amount']:.2f}")
            print(f"Status: {payin['status']}")
            print(f"PG TXN ID: {payin['pg_txn_id']}")
            print(f"Bank Ref: {payin['bank_ref_no']}")
            print(f"Created: {payin['created_at']}")
            print(f"Completed: {payin['completed_at']}")
            print()
            
            # Check if there's a corresponding wallet transaction
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    balance_before,
                    balance_after,
                    description,
                    reference_id,
                    created_at
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s
                AND reference_id = %s
                ORDER BY created_at DESC
            """, (payin['merchant_id'], payin['txn_id']))
            
            wallet_txns = cursor.fetchall()
            
            print("=" * 80)
            print("RELATED WALLET TRANSACTIONS")
            print("=" * 80)
            if wallet_txns:
                for txn in wallet_txns:
                    print(f"TXN ID: {txn['txn_id']}")
                    print(f"  Type: {txn['txn_type']}")
                    print(f"  Amount: ₹{txn['amount']:.2f}")
                    print(f"  Before: ₹{txn['balance_before']:.2f}")
                    print(f"  After: ₹{txn['balance_after']:.2f}")
                    print(f"  Description: {txn['description']}")
                    print(f"  Reference: {txn['reference_id']}")
                    print(f"  Created: {txn['created_at']}")
                    print()
            else:
                print("❌ NO WALLET TRANSACTION FOUND!")
                print("This means the callback did NOT credit the wallet")
                print()
            
            # Check current wallet balance
            cursor.execute("""
                SELECT 
                    balance,
                    settled_balance,
                    unsettled_balance,
                    last_updated
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (payin['merchant_id'],))
            
            wallet = cursor.fetchone()
            
            print("=" * 80)
            print("CURRENT WALLET BALANCE")
            print("=" * 80)
            if wallet:
                print(f"Balance (legacy): ₹{wallet['balance']:.2f}")
                print(f"Settled Balance: ₹{wallet['settled_balance']:.2f}")
                print(f"Unsettled Balance: ₹{wallet['unsettled_balance']:.2f}")
                print(f"Last Updated: {wallet['last_updated']}")
                print()
                
                # Calculate expected unsettled balance
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_unsettled_credits
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s
                    AND txn_type = 'UNSETTLED_CREDIT'
                """, (payin['merchant_id'],))
                
                unsettled_credits = cursor.fetchone()
                total_unsettled = float(unsettled_credits['total_unsettled_credits'])
                
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_settlements
                    FROM settlement_transactions
                    WHERE merchant_id = %s
                """, (payin['merchant_id'],))
                
                settlements = cursor.fetchone()
                total_settled = float(settlements['total_settlements']) if settlements else 0
                
                expected_unsettled = total_unsettled - total_settled
                
                print(f"Total Unsettled Credits: ₹{total_unsettled:.2f}")
                print(f"Total Settlements: ₹{total_settled:.2f}")
                print(f"Expected Unsettled Balance: ₹{expected_unsettled:.2f}")
                print(f"Actual Unsettled Balance: ₹{float(wallet['unsettled_balance']):.2f}")
                
                if abs(expected_unsettled - float(wallet['unsettled_balance'])) > 0.01:
                    print("⚠ MISMATCH DETECTED!")
                else:
                    print("✓ Balance matches expected value")
            else:
                print("❌ NO WALLET FOUND!")
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_recent_payin()
