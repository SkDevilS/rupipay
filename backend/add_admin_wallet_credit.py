#!/usr/bin/env python3
"""
Add credit to admin wallet to increase balance
This creates a PayIN transaction to add funds
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime

def add_admin_credit(amount, description="Manual balance adjustment"):
    """Add credit to admin wallet"""
    print("\n" + "=" * 80)
    print("ADD ADMIN WALLET CREDIT")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # First, calculate current balance
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
            print(f"   Amount to Add:   ₹{amount:,.2f}")
            
            new_balance = current_balance + amount
            print(f"   New Balance:     ₹{new_balance:,.2f}")
            
            # Create a PayIN transaction to add the credit
            print("\n2. Creating PayIN transaction...")
            
            txn_id = f"PAYIN{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO payin_transactions 
                (txn_id, merchant_id, amount, status, payment_method, 
                 customer_name, customer_email, customer_phone, created_at)
                VALUES (%s, 'ADMIN_CREDIT', %s, 'SUCCESS', 'MANUAL_ADJUSTMENT',
                        'Admin', 'admin@moneyone.co.in', '0000000000', NOW())
            """, (txn_id, amount))
            
            print(f"   ✓ Created PayIN transaction: {txn_id}")
            
            # Record in admin wallet transactions
            print("\n3. Recording admin wallet transaction...")
            
            awt_id = f"AWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute("""
                INSERT INTO admin_wallet_transactions 
                (admin_id, txn_id, txn_type, amount, balance_before, balance_after, 
                 description, reference_id, created_at)
                VALUES ('admin', %s, 'CREDIT', %s, %s, %s, %s, %s, NOW())
            """, (awt_id, amount, current_balance, new_balance, description, txn_id))
            
            print(f"   ✓ Recorded admin wallet transaction: {awt_id}")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - Admin wallet credited")
            print("=" * 80)
            print(f"\nBalance updated from ₹{current_balance:,.2f} to ₹{new_balance:,.2f}")
            print(f"Amount added: ₹{amount:,.2f}")
            
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
        print("Usage: python3 add_admin_wallet_credit.py <amount> [description]")
        print("Example: python3 add_admin_wallet_credit.py 419289 'Balance adjustment'")
        sys.exit(1)
    
    try:
        amount = float(sys.argv[1])
        description = sys.argv[2] if len(sys.argv) > 2 else "Manual balance adjustment"
        
        if amount <= 0:
            print("❌ Amount must be positive")
            sys.exit(1)
        
        print(f"\nYou are about to add ₹{amount:,.2f} to admin wallet")
        print(f"Description: {description}")
        
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            sys.exit(0)
        
        success = add_admin_credit(amount, description)
        sys.exit(0 if success else 1)
        
    except ValueError:
        print("❌ Invalid amount. Please provide a numeric value.")
        sys.exit(1)
