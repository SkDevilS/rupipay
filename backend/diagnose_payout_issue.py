#!/usr/bin/env python3
"""
Diagnose why payout is still processing with insufficient balance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def diagnose_payout_issue(merchant_id):
    """Check merchant wallet and recent payouts"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 60)
            print("MERCHANT WALLET DIAGNOSIS")
            print("=" * 60)
            print(f"Merchant ID: {merchant_id}")
            print()
            
            # Check merchant_wallet table
            print("1. MERCHANT WALLET TABLE:")
            print("-" * 60)
            cursor.execute("""
                SELECT * FROM merchant_wallet WHERE merchant_id = %s
            """, (merchant_id,))
            wallet = cursor.fetchone()
            
            if wallet:
                print(f"   Balance: ₹{float(wallet['balance']):.2f}")
                print(f"   Last Updated: {wallet.get('updated_at', 'N/A')}")
            else:
                print("   ❌ No wallet found!")
            print()
            
            # Check recent wallet transactions
            print("2. RECENT WALLET TRANSACTIONS (Last 10):")
            print("-" * 60)
            cursor.execute("""
                SELECT txn_id, txn_type, amount, balance_before, balance_after, 
                       description, created_at
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (merchant_id,))
            transactions = cursor.fetchall()
            
            if transactions:
                for txn in transactions:
                    print(f"   {txn['txn_type']}: ₹{float(txn['amount']):.2f}")
                    print(f"      Before: ₹{float(txn['balance_before']):.2f} → After: ₹{float(txn['balance_after']):.2f}")
                    print(f"      Description: {txn['description']}")
                    print(f"      Time: {txn['created_at']}")
                    print()
            else:
                print("   No transactions found")
            print()
            
            # Check recent payouts
            print("3. RECENT PAYOUT TRANSACTIONS (Last 10):")
            print("-" * 60)
            cursor.execute("""
                SELECT txn_id, order_id, amount, charge_amount, net_amount, 
                       status, created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (merchant_id,))
            payouts = cursor.fetchall()
            
            if payouts:
                for payout in payouts:
                    print(f"   TXN: {payout['txn_id']}")
                    print(f"      Order ID: {payout['order_id']}")
                    print(f"      Amount: ₹{float(payout['amount']):.2f}")
                    print(f"      Charges: ₹{float(payout['charge_amount']):.2f}")
                    print(f"      Net: ₹{float(payout['net_amount']):.2f}")
                    print(f"      Status: {payout['status']}")
                    print(f"      Time: {payout['created_at']}")
                    print()
            else:
                print("   No payouts found")
            print()
            
            # Check fund requests (old system)
            print("4. FUND REQUESTS (Old System):")
            print("-" * 60)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_approved
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            fund_total = cursor.fetchone()
            print(f"   Total Approved: ₹{float(fund_total['total_approved']):.2f}")
            print()
            
            # Summary
            print("5. SUMMARY:")
            print("-" * 60)
            if wallet:
                current_balance = float(wallet['balance'])
                print(f"   Current Wallet Balance: ₹{current_balance:.2f}")
                
                if current_balance < 0:
                    print(f"   ⚠️  NEGATIVE BALANCE DETECTED!")
                elif current_balance == 0:
                    print(f"   ℹ️  Zero balance")
                else:
                    print(f"   ✅ Positive balance")
            
            print()
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_payout_issue.py <merchant_id>")
        print("Example: python diagnose_payout_issue.py 1")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    diagnose_payout_issue(merchant_id)
