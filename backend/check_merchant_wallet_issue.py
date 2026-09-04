#!/usr/bin/env python3
"""
Check why wallet balance is showing PayIN amount instead of approved fund requests
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_wallet_issue():
    print("=" * 80)
    print("CHECKING WALLET BALANCE ISSUE")
    print("=" * 80)
    print()
    
    # The merchant ID from screenshot
    merchant_id = "7619163479"  # Change this to the actual merchant ID
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print(f"Checking merchant: {merchant_id}")
            print("-" * 80)
            
            # Check merchant_wallet table (OLD - should not be used)
            cursor.execute("""
                SELECT balance FROM merchant_wallet WHERE merchant_id = %s
            """, (merchant_id,))
            merchant_wallet = cursor.fetchone()
            
            if merchant_wallet:
                print(f"\n❌ ISSUE FOUND: merchant_wallet table has balance")
                print(f"   merchant_wallet.balance = ₹{merchant_wallet['balance']:.2f}")
                print(f"   This is the OLD table that was being updated by PayIN")
            else:
                print(f"\n✅ merchant_wallet table: No entry or balance = 0")
            
            # Check approved fund requests (CORRECT source)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            total_topup = float(cursor.fetchone()['total_topup'])
            print(f"\n✅ Approved fund requests: ₹{total_topup:.2f}")
            
            # Check total payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
            """, (merchant_id,))
            total_payout = float(cursor.fetchone()['total_payout'])
            print(f"✅ Total payouts: ₹{total_payout:.2f}")
            
            # Check merchant_wallet_transactions
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as credits,
                    COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as debits
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet_txns = cursor.fetchone()
            credits = float(wallet_txns['credits']) if wallet_txns else 0
            debits = float(wallet_txns['debits']) if wallet_txns else 0
            print(f"✅ Wallet transactions - Credits: ₹{credits:.2f}, Debits: ₹{debits:.2f}")
            
            # Check PayIN amount
            cursor.execute("""
                SELECT COALESCE(SUM(net_amount), 0) as net_payin
                FROM payin_transactions
                WHERE merchant_id = %s AND status = 'SUCCESS'
            """, (merchant_id,))
            net_payin = float(cursor.fetchone()['net_payin'])
            print(f"✅ Net PayIN amount: ₹{net_payin:.2f}")
            
            # Calculate correct wallet balance
            correct_balance = total_topup - total_payout - debits + credits
            
            print("\n" + "=" * 80)
            print("COMPARISON")
            print("=" * 80)
            
            if merchant_wallet:
                print(f"\n❌ WRONG: merchant_wallet.balance = ₹{merchant_wallet['balance']:.2f}")
                print(f"   (This is showing in the UI)")
            
            print(f"\n✅ CORRECT: Wallet Balance = ₹{correct_balance:.2f}")
            print(f"   Calculation: {total_topup:.2f} - {total_payout:.2f} - {debits:.2f} + {credits:.2f}")
            print(f"   (Approved Topup - Payouts - Debits + Credits)")
            
            print(f"\nℹ️  Net PayIN (for display only) = ₹{net_payin:.2f}")
            
            # Check if merchant_wallet balance matches PayIN
            if merchant_wallet and abs(float(merchant_wallet['balance']) - net_payin) < 1:
                print(f"\n🔴 CONFIRMED: merchant_wallet.balance matches PayIN amount!")
                print(f"   This confirms the old PayIN crediting code was running")
            
            print("\n" + "=" * 80)
            print("ROOT CAUSE")
            print("=" * 80)
            print("""
The issue is that the old merchant_wallet table still has PayIN amounts in it.
Even though we removed the code that updates it, the old data is still there.

The backend API might be reading from merchant_wallet table instead of
calculating from fund_requests.

SOLUTION:
1. Clear the merchant_wallet table (or set all balances to 0)
2. Ensure backend API uses fund_requests calculation only
3. Restart backend service
            """)
            
    finally:
        conn.close()


def check_all_merchants():
    """Check all merchants for the same issue"""
    print("\n" + "=" * 80)
    print("CHECKING ALL MERCHANTS")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.merchant_id,
                    COALESCE(mw.balance, 0) as merchant_wallet_balance,
                    (SELECT COALESCE(SUM(amount), 0) FROM fund_requests 
                     WHERE merchant_id = m.merchant_id AND status = 'APPROVED') as approved_topup,
                    (SELECT COALESCE(SUM(amount), 0) FROM payout_transactions 
                     WHERE merchant_id = m.merchant_id AND status IN ('SUCCESS', 'QUEUED')) as total_payout,
                    (SELECT COALESCE(SUM(net_amount), 0) FROM payin_transactions 
                     WHERE merchant_id = m.merchant_id AND status = 'SUCCESS') as net_payin
                FROM merchants m
                LEFT JOIN merchant_wallet mw ON m.merchant_id = mw.merchant_id
                ORDER BY m.merchant_id
            """)
            
            merchants = cursor.fetchall()
            
            print(f"{'Merchant ID':<15} {'MW Balance':<12} {'Approved':<12} {'Payout':<12} {'Correct':<12} {'PayIN':<12} {'Issue?'}")
            print("-" * 95)
            
            for m in merchants:
                mw_balance = float(m['merchant_wallet_balance'])
                approved = float(m['approved_topup'])
                payout = float(m['total_payout'])
                correct_balance = approved - payout
                payin = float(m['net_payin'])
                
                # Check if merchant_wallet balance is wrong
                has_issue = mw_balance > 0 and abs(mw_balance - correct_balance) > 1
                issue_marker = "❌ YES" if has_issue else "✅ No"
                
                print(f"{m['merchant_id']:<15} {mw_balance:<12.2f} {approved:<12.2f} {payout:<12.2f} {correct_balance:<12.2f} {payin:<12.2f} {issue_marker}")
            
            print("\n" + "=" * 80)
            print("LEGEND")
            print("=" * 80)
            print("MW Balance: merchant_wallet table balance (OLD - should be 0)")
            print("Approved: Sum of approved fund requests")
            print("Payout: Sum of successful payouts")
            print("Correct: Approved - Payout (what should be shown)")
            print("PayIN: Net PayIN amount (for display only)")
            print("Issue?: ❌ if MW Balance != Correct Balance")
            
    finally:
        conn.close()


if __name__ == '__main__':
    check_wallet_issue()
    check_all_merchants()
