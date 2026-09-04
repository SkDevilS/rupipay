#!/usr/bin/env python3
"""
Add 10,000,000,000,000 (10 Trillion) to Admin Top Up Balance
This script adds a large amount to the admin wallet so admin can top up users
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import uuid
from decimal import Decimal

def add_admin_topup_balance():
    """Add 10 trillion to admin wallet for user top-ups"""
    
    AMOUNT_TO_ADD = Decimal('10000000000000.00')  # 10 trillion
    
    print("=" * 70)
    print("ADD ADMIN TOP UP BALANCE")
    print("=" * 70)
    print(f"\nAmount to add: ₹{AMOUNT_TO_ADD:,.2f}")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Step 1: Check current admin wallet
            print("\n1. Checking current admin wallet...")
            cursor.execute("""
                SELECT admin_id, main_balance, unsettled_balance
                FROM admin_wallet
                WHERE admin_id = 'admin'
            """)
            admin_wallet = cursor.fetchone()
            
            if admin_wallet:
                current_main = Decimal(str(admin_wallet['main_balance']))
                current_unsettled = Decimal(str(admin_wallet['unsettled_balance']))
                print(f"   ✓ Admin wallet found:")
                print(f"     Main Balance: ₹{current_main:,.2f}")
                print(f"     Unsettled Balance: ₹{current_unsettled:,.2f}")
                print(f"     Total: ₹{(current_main + current_unsettled):,.2f}")
            else:
                print("   ℹ Admin wallet not found, will create it")
                current_main = Decimal('0.00')
                current_unsettled = Decimal('0.00')
            
            # Step 2: Calculate current available balance for top-ups
            print("\n2. Calculating current available balance for top-ups...")
            
            # Get total PayIN
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = Decimal(str(cursor.fetchone()['total_payin']))
            
            # Get total top-ups already done
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = Decimal(str(cursor.fetchone()['total_topup']))
            
            # Get total fetch from merchants
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE %s
            """, ('%fetched by admin%',))
            total_fetch = Decimal(str(cursor.fetchone()['total_fetch']))
            
            # Get total settlements
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM settlement_transactions
            """)
            total_settlements = Decimal(str(cursor.fetchone()['total_settlements']))
            
            # Get manual adjustments
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
            total_adjustments = Decimal(str(cursor.fetchone()['total_adjustments']))
            
            # Calculate available balance
            # Admin Balance = PayIN + Fetch + Unsettled - Topups - Settlements + Manual Adjustments
            available_balance = (total_payin + total_fetch + current_unsettled - 
                               total_topup - total_settlements + total_adjustments)
            
            print(f"\n   Current Balance Breakdown:")
            print(f"     PayIN:              + ₹{total_payin:,.2f}")
            print(f"     Fetch from Merch:   + ₹{total_fetch:,.2f}")
            print(f"     Unsettled:          + ₹{current_unsettled:,.2f}")
            print(f"     Top-ups (done):     - ₹{total_topup:,.2f}")
            print(f"     Settlements:        - ₹{total_settlements:,.2f}")
            print(f"     Manual Adjustments: + ₹{total_adjustments:,.2f}")
            print(f"     " + "-" * 50)
            print(f"     Available Balance:  = ₹{available_balance:,.2f}")
            
            # Step 3: Add the new amount as a manual adjustment
            print(f"\n3. Adding ₹{AMOUNT_TO_ADD:,.2f} to admin wallet...")
            
            txn_id = f"ADM_TOPUP_{uuid.uuid4().hex[:12].upper()}"
            
            # Insert transaction record
            cursor.execute("""
                INSERT INTO admin_wallet_transactions (
                    admin_id,
                    txn_id,
                    txn_type,
                    amount,
                    description,
                    created_at
                ) VALUES (
                    'admin',
                    %s,
                    'CREDIT',
                    %s,
                    'Initial capital - Top-up fund for user funding',
                    CURRENT_TIMESTAMP
                )
            """, (txn_id, float(AMOUNT_TO_ADD)))
            
            print(f"   ✓ Transaction recorded: {txn_id}")
            
            # Create or update admin wallet
            cursor.execute("""
                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                VALUES ('admin', 0.00, 0.00)
                ON DUPLICATE KEY UPDATE admin_id = admin_id
            """)
            
            conn.commit()
            print(f"   ✓ Admin wallet updated")
            
            # Step 4: Verify new balance
            print("\n4. Verifying new balance...")
            
            # Recalculate with new adjustment
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
            new_total_adjustments = Decimal(str(cursor.fetchone()['total_adjustments']))
            
            new_available_balance = (total_payin + total_fetch + current_unsettled - 
                                   total_topup - total_settlements + new_total_adjustments)
            
            print(f"\n   New Balance Breakdown:")
            print(f"     PayIN:              + ₹{total_payin:,.2f}")
            print(f"     Fetch from Merch:   + ₹{total_fetch:,.2f}")
            print(f"     Unsettled:          + ₹{current_unsettled:,.2f}")
            print(f"     Top-ups (done):     - ₹{total_topup:,.2f}")
            print(f"     Settlements:        - ₹{total_settlements:,.2f}")
            print(f"     Manual Adjustments: + ₹{new_total_adjustments:,.2f}")
            print(f"     " + "-" * 50)
            print(f"     Available Balance:  = ₹{new_available_balance:,.2f}")
            
            print(f"\n   Balance Increase: ₹{(new_available_balance - available_balance):,.2f}")
            
            # Step 5: Show where this balance is used
            print("\n5. Where this balance is used:")
            print("   ✓ Admin Panel → Fund Manager → TopUp Fund")
            print("   ✓ API: GET /api/wallet/admin/overview → data.main_balance")
            print("   ✓ When admin tops up users via Fund Requests")
            
            print("\n✅ SUCCESS: Admin top-up balance increased!")
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n🚀 Starting admin top-up balance addition...\n")
    
    # Confirm with user
    print("⚠️  WARNING: This will add ₹10,000,000,000,000.00 (10 trillion) to admin wallet")
    print("This is a MANUAL ADJUSTMENT that will allow admin to top up users.")
    print("\nPress Enter to continue, or Ctrl+C to cancel...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(0)
    
    success = add_admin_topup_balance()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ ADMIN TOP-UP BALANCE SUCCESSFULLY ADDED")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Login to admin panel")
        print("2. Go to Fund Manager → TopUp Fund")
        print("3. You should see the new balance available")
        print("4. You can now approve user fund requests")
    else:
        print("\n" + "=" * 70)
        print("❌ FAILED TO ADD ADMIN TOP-UP BALANCE")
        print("=" * 70)
        sys.exit(1)
