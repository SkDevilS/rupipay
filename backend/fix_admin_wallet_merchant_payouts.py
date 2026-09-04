"""
Fix Admin Wallet - Remove Merchant Payout Deductions
This script identifies merchant payouts that were incorrectly counted as admin wallet debits
and creates corrective credit entries in admin_wallet_transactions
"""

from database import get_db_connection
from datetime import datetime

def fix_admin_wallet_merchant_payouts():
    """
    Fix admin wallet by crediting back merchant payout amounts
    that were incorrectly debited from admin wallet
    """
    try:
        print("=" * 80)
        print("Fix Admin Wallet - Remove Merchant Payout Deductions")
        print("=" * 80)
        print()
        
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Step 1: Get all merchant payouts (reference_id NOT starting with 'ADMIN')
                print("Step 1: Identifying merchant payouts...")
                cursor.execute("""
                    SELECT 
                        txn_id,
                        reference_id,
                        merchant_id,
                        amount,
                        status,
                        created_at
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED')
                    AND reference_id NOT LIKE 'ADMIN%'
                    ORDER BY created_at ASC
                """)
                merchant_payouts = cursor.fetchall()
                
                if not merchant_payouts:
                    print("✓ No merchant payouts found. Admin wallet is correct.")
                    return True
                
                print(f"Found {len(merchant_payouts)} merchant payout(s)")
                print()
                
                # Step 2: Calculate total amount to credit back
                total_to_credit = sum(float(p['amount']) for p in merchant_payouts)
                
                print("Merchant Payouts Summary:")
                print("-" * 80)
                for payout in merchant_payouts:
                    print(f"  TXN: {payout['txn_id']}")
                    print(f"  Merchant: {payout['merchant_id']}")
                    print(f"  Amount: ₹{payout['amount']:.2f}")
                    print(f"  Status: {payout['status']}")
                    print(f"  Date: {payout['created_at']}")
                    print()
                
                print(f"Total amount incorrectly debited from admin wallet: ₹{total_to_credit:.2f}")
                print()
                
                # Step 3: Calculate current admin balance
                print("Step 2: Calculating current admin balance...")
                
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
                
                # Admin personal payouts ONLY (reference_id starts with 'ADMIN')
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_admin_payout
                    FROM payout_transactions
                    WHERE status IN ('SUCCESS', 'QUEUED')
                    AND reference_id LIKE 'ADMIN%'
                """)
                total_admin_payout = float(cursor.fetchone()['total_admin_payout'])
                
                # Current balance (BEFORE fix)
                current_balance = total_payin + total_fetch - total_topup - total_admin_payout - total_to_credit
                
                # Corrected balance (AFTER fix)
                corrected_balance = total_payin + total_fetch - total_topup - total_admin_payout
                
                print(f"  PayIN Amount: ₹{total_payin:.2f}")
                print(f"  Fetch Amount: ₹{total_fetch:.2f}")
                print(f"  Topup Amount: ₹{total_topup:.2f}")
                print(f"  Admin Payouts: ₹{total_admin_payout:.2f}")
                print(f"  Merchant Payouts (incorrect): ₹{total_to_credit:.2f}")
                print()
                print(f"  Current Balance (BEFORE fix): ₹{current_balance:.2f}")
                print(f"  Corrected Balance (AFTER fix): ₹{corrected_balance:.2f}")
                print(f"  Difference: ₹{corrected_balance - current_balance:.2f}")
                print()
                
                # Step 4: Confirm with user
                print("⚠️  WARNING: This will create corrective credit entries in admin_wallet_transactions")
                print(f"⚠️  Total credit to be added: ₹{total_to_credit:.2f}")
                print()
                confirm = input("Do you want to proceed? (yes/no): ")
                
                if confirm.lower() != 'yes':
                    print("❌ Operation cancelled by user")
                    return False
                
                # Step 5: Create corrective credit entries
                print()
                print("Step 3: Creating corrective credit entries...")
                
                for payout in merchant_payouts:
                    # Generate transaction ID
                    txn_id = f"AWT{datetime.now().strftime('%Y%m%d%H%M%S')}{payout['txn_id'][-6:]}"
                    
                    # Calculate balance before and after
                    cursor.execute("""
                        SELECT COALESCE(MAX(balance_after), 0) as last_balance
                        FROM admin_wallet_transactions
                    """)
                    last_balance = float(cursor.fetchone()['last_balance'] or 0)
                    
                    balance_before = last_balance
                    balance_after = balance_before + float(payout['amount'])
                    
                    # Insert corrective credit entry
                    cursor.execute("""
                        INSERT INTO admin_wallet_transactions 
                        (admin_id, txn_id, txn_type, amount, balance_before, balance_after, 
                         description, reference_id, created_at)
                        VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s, NOW())
                    """, (
                        'admin',
                        txn_id,
                        payout['amount'],
                        balance_before,
                        balance_after,
                        f"Correction: Merchant payout {payout['txn_id']} should not debit admin wallet",
                        payout['reference_id']
                    ))
                    
                    print(f"  ✓ Created credit entry: {txn_id} - ₹{payout['amount']:.2f}")
                
                conn.commit()
                
                print()
                print("=" * 80)
                print("✅ Fix completed successfully!")
                print("=" * 80)
                print()
                print(f"Total corrective credits added: ₹{total_to_credit:.2f}")
                print(f"Admin wallet balance corrected from ₹{current_balance:.2f} to ₹{corrected_balance:.2f}")
                print()
                print("Note: The wallet service has been updated to exclude merchant payouts")
                print("      from admin wallet calculations going forward.")
                print()
                
                return True
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print()
    print("This script will fix the admin wallet by crediting back amounts")
    print("that were incorrectly debited for merchant payouts.")
    print()
    
    success = fix_admin_wallet_merchant_payouts()
    
    if success:
        print("✅ Admin wallet has been corrected!")
    else:
        print("❌ Fix failed or was cancelled")
