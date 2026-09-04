"""
Diagnose why real payin transactions are not crediting unsettled wallet
"""

import pymysql
from database import get_db_connection
from datetime import datetime, timedelta

def diagnose_recent_payins():
    """Check recent successful payins and their wallet credits"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("DIAGNOSING RECENT PAYIN TRANSACTIONS")
            print("=" * 80)
            
            # Get the most recent 5 successful payins
            cursor.execute("""
                SELECT 
                    txn_id, merchant_id, order_id, amount, charge_amount, net_amount,
                    status, pg_partner, completed_at, created_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                ORDER BY completed_at DESC
                LIMIT 5
            """)
            
            payins = cursor.fetchall()
            
            if not payins:
                print("\n❌ No successful payins found")
                return
            
            print(f"\nFound {len(payins)} recent successful payins\n")
            
            total_missing = 0
            
            for idx, payin in enumerate(payins, 1):
                print(f"\n{'='*70}")
                print(f"PAYIN #{idx}")
                print(f"{'='*70}")
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
                    print(f"\n✅ WALLET WAS CREDITED:")
                    print(f"   Wallet TXN: {wallet_txn['txn_id']}")
                    print(f"   Amount: ₹{wallet_txn['amount']}")
                    print(f"   Balance Before: ₹{wallet_txn['balance_before']}")
                    print(f"   Balance After: ₹{wallet_txn['balance_after']}")
                    print(f"   Credited At: {wallet_txn['created_at']}")
                else:
                    print(f"\n❌ WALLET NOT CREDITED!")
                    print(f"   This payin did NOT credit the unsettled wallet")
                    print(f"   Missing credit: ₹{payin['net_amount']}")
                    total_missing += 1
                    
                    # Check merchant wallet current balance
                    cursor.execute("""
                        SELECT unsettled_balance, settled_balance, balance
                        FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (payin['merchant_id'],))
                    
                    wallet = cursor.fetchone()
                    if wallet:
                        print(f"\n   Current Merchant Wallet:")
                        print(f"   - Unsettled: ₹{wallet['unsettled_balance']}")
                        print(f"   - Settled: ₹{wallet['settled_balance']}")
                        print(f"   - Total: ₹{wallet['balance']}")
                    else:
                        print(f"\n   ⚠ Merchant wallet doesn't exist!")
            
            print(f"\n{'='*80}")
            print(f"SUMMARY")
            print(f"{'='*80}")
            print(f"Total Payins Checked: {len(payins)}")
            print(f"Missing Wallet Credits: {total_missing}")
            
            if total_missing > 0:
                print(f"\n⚠ {total_missing} payin(s) did NOT credit the unsettled wallet!")
                print(f"\nPossible reasons:")
                print(f"1. Callback was not received from payment gateway")
                print(f"2. Callback processing failed with an error")
                print(f"3. Transaction was manually marked as SUCCESS without wallet credit")
                print(f"\nTo fix:")
                print(f"1. Check backend logs for callback errors")
                print(f"2. Manually credit the missing amounts")
                print(f"3. Ensure callback URL is configured correctly")
            else:
                print(f"\n✅ All recent payins have credited the unsettled wallet correctly!")
            
            # Show total unsettled across all merchants
            print(f"\n{'='*80}")
            print(f"CURRENT WALLET BALANCES")
            print(f"{'='*80}")
            
            cursor.execute("""
                SELECT merchant_id, unsettled_balance, settled_balance, balance
                FROM merchant_wallet
                WHERE unsettled_balance > 0 OR settled_balance > 0
                ORDER BY unsettled_balance DESC
            """)
            
            wallets = cursor.fetchall()
            
            if wallets:
                for wallet in wallets:
                    print(f"\nMerchant: {wallet['merchant_id']}")
                    print(f"  Unsettled: ₹{wallet['unsettled_balance']}")
                    print(f"  Settled: ₹{wallet['settled_balance']}")
                    print(f"  Total: ₹{wallet['balance']}")
            else:
                print("\nNo merchant wallets with balances found")
            
            # Calculate total
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(unsettled_balance), 0) as total_unsettled,
                    COALESCE(SUM(settled_balance), 0) as total_settled
                FROM merchant_wallet
            """)
            
            totals = cursor.fetchone()
            print(f"\n{'='*80}")
            print(f"TOTAL UNSETTLED (ALL MERCHANTS): ₹{totals['total_unsettled']}")
            print(f"TOTAL SETTLED (ALL MERCHANTS): ₹{totals['total_settled']}")
            print(f"{'='*80}")
            
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_recent_payins()
