#!/usr/bin/env python3
"""
Diagnose admin wallet balance issue
"""
import sys
from database import get_db_connection

def diagnose_wallet():
    """Check all components of admin wallet balance"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*60)
            print("ADMIN WALLET DIAGNOSIS")
            print("="*60)
            
            # 1. Check admin_wallet table
            print("\n1. Admin Wallet Table:")
            cursor.execute("SELECT * FROM admin_wallet WHERE admin_id = 'admin'")
            wallet = cursor.fetchone()
            if wallet:
                print(f"   Main Balance: ₹{wallet.get('main_balance', 0):.2f}")
            else:
                print("   ❌ No wallet record found")
            
            # 2. Check admin_wallet_transactions
            print("\n2. Admin Wallet Transactions:")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                    COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit,
                    COUNT(*) as txn_count
                FROM admin_wallet_transactions
                WHERE admin_id = 'admin'
            """)
            txns = cursor.fetchone()
            if txns:
                print(f"   Total Credits: ₹{txns['total_credit']:.2f}")
                print(f"   Total Debits: ₹{txns['total_debit']:.2f}")
                print(f"   Net Balance: ₹{txns['total_credit'] - txns['total_debit']:.2f}")
                print(f"   Transaction Count: {txns['txn_count']}")
            
            # 3. Check PayIN balance (SUCCESS transactions)
            print("\n3. PayIN Balance (Source of funds):")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_payin,
                    COUNT(*) as payin_count
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            payin = cursor.fetchone()
            print(f"   Total PayIN: ₹{payin['total_payin']:.2f}")
            print(f"   PayIN Count: {payin['payin_count']}")
            
            # 4. Check approved fund requests (topups to merchants)
            print("\n4. Approved Fund Requests (Topups to Merchants):")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_topup,
                    COUNT(*) as topup_count
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            topup = cursor.fetchone()
            print(f"   Total Topups: ₹{topup['total_topup']:.2f}")
            print(f"   Topup Count: {topup['topup_count']}")
            
            # 5. Check fetch from merchants
            print("\n5. Fetch from Merchants:")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_fetch,
                    COUNT(*) as fetch_count
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            fetch = cursor.fetchone()
            print(f"   Total Fetched: ₹{fetch['total_fetch']:.2f}")
            print(f"   Fetch Count: {fetch['fetch_count']}")
            
            # 6. Check payout transactions
            print("\n6. Payout Transactions:")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_payout,
                    COUNT(*) as payout_count
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
            """)
            payout = cursor.fetchone()
            print(f"   Total Payouts: ₹{payout['total_payout']:.2f}")
            print(f"   Payout Count: {payout['payout_count']}")
            
            # 7. Calculate available balance (CORRECT LOGIC)
            print("\n" + "="*60)
            print("BALANCE CALCULATION:")
            print("="*60)
            
            total_payin = float(payin['total_payin'])
            total_fetch = float(fetch['total_fetch'])
            total_topup = float(topup['total_topup'])
            total_payout = float(payout['total_payout'])
            
            # CORRECT: Admin Wallet = PayIN + Fetch - Topups
            # Payouts are paid from MERCHANT wallets, not admin wallet
            admin_wallet_balance = total_payin + total_fetch - total_topup
            
            print(f"\n   ADMIN WALLET CALCULATION:")
            print(f"   PayIN (received):    + ₹{total_payin:.2f}")
            print(f"   Fetch (from merch):  + ₹{total_fetch:.2f}")
            print(f"   Topups (to merch):   - ₹{total_topup:.2f}")
            print(f"   " + "-"*40)
            print(f"   Admin Balance:       = ₹{admin_wallet_balance:.2f}")
            
            print(f"\n   💡 Flow Explanation:")
            print(f"      1. PayIN (₹{total_payin:.2f}) → Admin Wallet")
            print(f"      2. Topup (₹{total_topup:.2f}) → Admin Wallet → Merchant Wallet")
            print(f"      3. Payout (₹{total_payout:.2f}) → Merchant Wallet → Customer")
            print(f"      ")
            print(f"      Payouts are paid from MERCHANT wallets, NOT admin wallet!")
            
            # Show merchant wallet calculation for reference
            print(f"\n   MERCHANT WALLET CALCULATION (for reference):")
            print(f"   Topups received:     + ₹{total_topup:.2f}")
            print(f"   Fetch by admin:      - ₹{total_fetch:.2f}")
            print(f"   Payouts made:        - ₹{total_payout:.2f}")
            print(f"   " + "-"*40)
            merchant_balance = total_topup - total_fetch - total_payout
            print(f"   Merchant Balance:    = ₹{merchant_balance:.2f}")
            
            # 8. Show recent admin wallet transactions
            print("\n" + "="*60)
            print("RECENT ADMIN WALLET TRANSACTIONS (Last 10):")
            print("="*60)
            cursor.execute("""
                SELECT txn_id, txn_type, amount, description, created_at
                FROM admin_wallet_transactions
                WHERE admin_id = 'admin'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent = cursor.fetchall()
            if recent:
                for txn in recent:
                    print(f"\n   {txn['created_at']} | {txn['txn_type']}")
                    print(f"   Amount: ₹{txn['amount']:.2f}")
                    print(f"   Description: {txn['description']}")
            else:
                print("   No transactions found")
            
            print("\n" + "="*60)
            print("DIAGNOSIS COMPLETE")
            print("="*60 + "\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_wallet()
