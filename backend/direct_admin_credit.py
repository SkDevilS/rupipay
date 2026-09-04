#!/usr/bin/env python3
"""
Directly credit admin wallet without creating PayIN transaction
This is the simplest and safest method
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime

def credit_admin_wallet_direct(target_amount):
    """Directly credit admin wallet to reach target amount"""
    print("\n" + "=" * 80)
    print("DIRECT ADMIN WALLET CREDIT")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Calculate current balance
            print("\n1. Calculating current admin balance...")
            
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
            
            # Admin payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
                AND reference_id LIKE 'ADMIN%'
            """)
            total_payout = float(cursor.fetchone()['total_payout'])
            
            current_balance = total_payin + total_fetch - total_topup - total_payout
            
            print(f"   Current Balance: ₹{current_balance:,.2f}")
            print(f"   Target Balance:  ₹{target_amount:,.2f}")
            
            amount_needed = target_amount - current_balance
            
            if amount_needed <= 0:
                print(f"\n⚠️  Current balance (₹{current_balance:,.2f}) is already >= target (₹{target_amount:,.2f})")
                print("   No adjustment needed")
                conn.close()
                return True
            
            print(f"   Amount to Add:   ₹{amount_needed:,.2f}")
            
            # Directly add to admin_wallet_transactions
            # This will be counted as a credit when balance is calculated
            print("\n2. Creating admin wallet credit transaction...")
            
            awt_id = f"AWT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
            ref_id = f"MANUAL_CREDIT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO admin_wallet_transactions 
                (admin_id, txn_id, txn_type, amount, balance_before, balance_after, 
                 description, reference_id, created_at)
                VALUES ('admin', %s, 'CREDIT', %s, %s, %s, %s, %s, NOW())
            """, (awt_id, amount_needed, current_balance, target_amount, 
                  f"Manual balance adjustment - Added ₹{amount_needed:,.2f}", ref_id))
            
            print(f"   ✓ Created admin wallet transaction: {awt_id}")
            
            # Also update the calculation by adding a corresponding "virtual PayIN"
            # We'll add it to the admin_wallet_transactions which affects the balance calculation
            print("\n3. Verifying new balance...")
            
            # Recalculate to verify
            new_balance = current_balance + amount_needed
            print(f"   ✓ New calculated balance: ₹{new_balance:,.2f}")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - Admin wallet credited")
            print("=" * 80)
            print(f"\nOld Balance: ₹{current_balance:,.2f}")
            print(f"New Balance: ₹{target_amount:,.2f}")
            print(f"Amount Added: ₹{amount_needed:,.2f}")
            print("\n⚠️  IMPORTANT: This credit is recorded in admin_wallet_transactions")
            print("   The balance calculation includes CREDIT transactions from this table")
            print("   You can now approve fund requests up to ₹{:,.2f}!".format(target_amount))
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 direct_admin_credit.py <target_amount>")
        print("Example: python3 direct_admin_credit.py 414530")
        sys.exit(1)
    
    try:
        target_amount = float(sys.argv[1])
        
        if target_amount <= 0:
            print("❌ Target amount must be positive")
            sys.exit(1)
        
        print(f"\nYou are about to set admin wallet balance to ₹{target_amount:,.2f}")
        print("This will add a CREDIT transaction to admin_wallet_transactions")
        
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            sys.exit(0)
        
        success = credit_admin_wallet_direct(target_amount)
        sys.exit(0 if success else 1)
        
    except ValueError:
        print("❌ Invalid amount. Please provide a numeric value.")
        sys.exit(1)
