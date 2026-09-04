"""
Check current wallet balances to debug the settled/unsettled wallet issue
"""

from database import get_db_connection

def check_wallet_balances():
    """Check current wallet balances"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if columns exist
            cursor.execute("""
                SHOW COLUMNS FROM merchant_wallet LIKE 'settled_balance'
            """)
            settled_col = cursor.fetchone()
            
            cursor.execute("""
                SHOW COLUMNS FROM merchant_wallet LIKE 'unsettled_balance'
            """)
            unsettled_col = cursor.fetchone()
            
            print("=" * 80)
            print("COLUMN CHECK")
            print("=" * 80)
            print(f"settled_balance column exists: {settled_col is not None}")
            print(f"unsettled_balance column exists: {unsettled_col is not None}")
            print()
            
            if not settled_col or not unsettled_col:
                print("❌ Columns don't exist! Run migration first.")
                return
            
            # Get all merchant wallets
            cursor.execute("""
                SELECT 
                    merchant_id,
                    balance,
                    settled_balance,
                    unsettled_balance,
                    last_updated
                FROM merchant_wallet
            """)
            wallets = cursor.fetchall()
            
            print("=" * 80)
            print("MERCHANT WALLET BALANCES")
            print("=" * 80)
            for wallet in wallets:
                print(f"Merchant: {wallet['merchant_id']}")
                print(f"  Balance (legacy): ₹{wallet['balance']:.2f}")
                print(f"  Settled Balance: ₹{wallet['settled_balance']:.2f}")
                print(f"  Unsettled Balance: ₹{wallet['unsettled_balance']:.2f}")
                print(f"  Last Updated: {wallet['last_updated']}")
                print()
            
            # Check recent payin transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    amount,
                    net_amount,
                    charge_amount,
                    status,
                    created_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            payins = cursor.fetchall()
            
            print("=" * 80)
            print("RECENT SUCCESSFUL PAYINS")
            print("=" * 80)
            for payin in payins:
                print(f"TXN: {payin['txn_id']}")
                print(f"  Merchant: {payin['merchant_id']}")
                print(f"  Amount: ₹{payin['amount']:.2f}")
                print(f"  Charge: ₹{payin['charge_amount']:.2f}")
                print(f"  Net Amount: ₹{payin['net_amount']:.2f}")
                print(f"  Created: {payin['created_at']}")
                print()
            
            # Check wallet transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    txn_type,
                    amount,
                    balance_before,
                    balance_after,
                    description,
                    created_at
                FROM merchant_wallet_transactions
                WHERE txn_type = 'UNSETTLED_CREDIT'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            unsettled_txns = cursor.fetchall()
            
            print("=" * 80)
            print("RECENT UNSETTLED CREDIT TRANSACTIONS")
            print("=" * 80)
            if unsettled_txns:
                for txn in unsettled_txns:
                    print(f"TXN: {txn['txn_id']}")
                    print(f"  Merchant: {txn['merchant_id']}")
                    print(f"  Amount: ₹{txn['amount']:.2f}")
                    print(f"  Before: ₹{txn['balance_before']:.2f}")
                    print(f"  After: ₹{txn['balance_after']:.2f}")
                    print(f"  Description: {txn['description']}")
                    print(f"  Created: {txn['created_at']}")
                    print()
            else:
                print("No UNSETTLED_CREDIT transactions found")
                print()
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_wallet_balances()
