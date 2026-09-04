"""
Check why unsettled wallet is not being credited for recent payins
"""

import pymysql
from database import get_db_connection
from datetime import datetime, timedelta

def check_recent_payins():
    """Check recent successful payins and their wallet credits"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("CHECKING RECENT SUCCESSFUL PAYINS")
            print("=" * 80)
            
            # Get recent successful payins
            cursor.execute("""
                SELECT 
                    txn_id, merchant_id, order_id, amount, charge_amount, net_amount,
                    status, pg_partner, completed_at, created_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                ORDER BY completed_at DESC
                LIMIT 10
            """)
            
            payins = cursor.fetchall()
            
            if not payins:
                print("No successful payins found")
                return
            
            print(f"\nFound {len(payins)} recent successful payins:\n")
            
            for payin in payins:
                print(f"\n{'='*60}")
                print(f"TXN ID: {payin['txn_id']}")
                print(f"Merchant: {payin['merchant_id']}")
                print(f"Order ID: {payin['order_id']}")
                print(f"Amount: ₹{payin['amount']}")
                print(f"Charge: ₹{payin['charge_amount']}")
                print(f"Net Amount: ₹{payin['net_amount']}")
                print(f"PG Partner: {payin['pg_partner']}")
                print(f"Completed: {payin['completed_at']}")
                
                # Check if wallet was credited
                cursor.execute("""
                    SELECT txn_id, txn_type, amount, balance_before, balance_after, created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (payin['txn_id'],))
                
                wallet_txn = cursor.fetchone()
                
                if wallet_txn:
                    print(f"✅ WALLET CREDITED:")
                    print(f"   Wallet TXN: {wallet_txn['txn_id']}")
                    print(f"   Amount: ₹{wallet_txn['amount']}")
                    print(f"   Balance Before: ₹{wallet_txn['balance_before']}")
                    print(f"   Balance After: ₹{wallet_txn['balance_after']}")
                    print(f"   Credited At: {wallet_txn['created_at']}")
                else:
                    print(f"❌ WALLET NOT CREDITED!")
                    print(f"   This payin did NOT credit the unsettled wallet")
                    
                    # Check merchant wallet current balance
                    cursor.execute("""
                        SELECT unsettled_balance, settled_balance, balance
                        FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (payin['merchant_id'],))
                    
                    wallet = cursor.fetchone()
                    if wallet:
                        print(f"   Current Merchant Wallet:")
                        print(f"   - Unsettled: ₹{wallet['unsettled_balance']}")
                        print(f"   - Settled: ₹{wallet['settled_balance']}")
                        print(f"   - Total: ₹{wallet['balance']}")
            
            print(f"\n{'='*80}")
            print("MERCHANT WALLET SUMMARY")
            print("=" * 80)
            
            # Get all merchant wallets
            cursor.execute("""
                SELECT merchant_id, unsettled_balance, settled_balance, balance, last_updated
                FROM merchant_wallet
                ORDER BY unsettled_balance DESC
            """)
            
            wallets = cursor.fetchall()
            
            for wallet in wallets:
                print(f"\nMerchant: {wallet['merchant_id']}")
                print(f"  Unsettled: ₹{wallet['unsettled_balance']}")
                print(f"  Settled: ₹{wallet['settled_balance']}")
                print(f"  Total: ₹{wallet['balance']}")
                print(f"  Last Updated: {wallet['last_updated']}")
            
            # Calculate total unsettled
            cursor.execute("""
                SELECT SUM(unsettled_balance) as total_unsettled
                FROM merchant_wallet
            """)
            
            total = cursor.fetchone()
            print(f"\n{'='*80}")
            print(f"TOTAL UNSETTLED (ALL MERCHANTS): ₹{total['total_unsettled']}")
            print("=" * 80)
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_recent_payins()
