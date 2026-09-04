"""
Backfill Missing Payout Wallet Deductions
Fix wallet balances for SUCCESS payouts that didn't get deducted due to the callback bug
"""

import sys
sys.path.append('/var/www/moneyone/backend')

from database import get_db_connection
from wallet_service import WalletService
from datetime import datetime, date

def backfill_missing_payout_deductions(dry_run=True, target_date=None):
    """
    Find SUCCESS payouts without wallet deductions and fix them
    
    Args:
        dry_run: If True, only show what would be fixed without making changes
        target_date: Date to process (default: today). Format: 'YYYY-MM-DD'
    """
    
    print("=" * 80)
    print("Backfill Missing Payout Wallet Deductions")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will make changes)'}")
    
    if target_date:
        print(f"Target Date: {target_date}")
    else:
        target_date = date.today().strftime('%Y-%m-%d')
        print(f"Target Date: {target_date} (today)")
    
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    wallet_svc = WalletService()
    fixed_count = 0
    error_count = 0
    total_amount_to_deduct = 0.0
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS payouts without wallet deduction
            print("Step 1: Finding SUCCESS payouts without wallet deduction")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    p.txn_id,
                    p.reference_id,
                    p.merchant_id,
                    p.amount,
                    p.net_amount,
                    p.charge_amount,
                    p.pg_partner,
                    p.status,
                    p.completed_at,
                    p.created_at
                FROM payout_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON mwt.reference_id = p.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE p.status = 'SUCCESS'
                AND p.pg_partner IN ('PayTouch', 'Mudrape')
                AND p.merchant_id IS NOT NULL
                AND mwt.txn_id IS NULL
                AND DATE(p.completed_at) = %s
                ORDER BY p.completed_at ASC
            """, (target_date,))
            
            missing_deductions = cursor.fetchall()
            
            if not missing_deductions:
                print(f"✓ No missing wallet deductions found for {target_date}")
                print("All SUCCESS payouts have been properly deducted!")
                return
            
            print(f"Found {len(missing_deductions)} SUCCESS payouts without wallet deduction\n")
            
            # Show summary
            print("Step 2: Summary of transactions to fix")
            print("-" * 80)
            
            for payout in missing_deductions:
                total_amount_to_deduct += float(payout['amount'])
                print(f"Transaction: {payout['txn_id']}")
                print(f"  Reference: {payout['reference_id']}")
                print(f"  Merchant: {payout['merchant_id']}")
                print(f"  PG Partner: {payout['pg_partner']}")
                print(f"  Amount to Deduct: ₹{payout['amount']:.2f}")
                print(f"    - Net Amount: ₹{payout['net_amount']:.2f}")
                print(f"    - Charges: ₹{payout['charge_amount']:.2f}")
                print(f"  Completed: {payout['completed_at']}")
                print()
            
            print(f"Total Amount to Deduct: ₹{total_amount_to_deduct:.2f}")
            print()
            
            if dry_run:
                print("=" * 80)
                print("DRY RUN MODE - No changes made")
                print("=" * 80)
                print()
                print("To apply these fixes, run:")
                print(f"  python3 backfill_missing_payout_deductions.py --live --date {target_date}")
                return
            
            # Confirm before proceeding
            print("=" * 80)
            print("⚠️  WARNING: This will deduct wallet balances")
            print("=" * 80)
            response = input("\nType 'YES' to proceed with wallet deductions: ")
            
            if response != 'YES':
                print("Aborted by user")
                return
            
            print()
            print("Step 3: Processing wallet deductions")
            print("-" * 80)
            
            for payout in missing_deductions:
                merchant_id = payout['merchant_id']
                txn_id = payout['txn_id']
                total_deduction = float(payout['amount'])
                net_amount = float(payout['net_amount'])
                charge_amount = float(payout['charge_amount'])
                
                print(f"\nProcessing: {txn_id}")
                print(f"  Merchant: {merchant_id}")
                print(f"  Deducting: ₹{total_deduction:.2f}")
                
                # Check current wallet balance
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                
                if not wallet:
                    print(f"  ✗ ERROR: Wallet not found for merchant {merchant_id}")
                    error_count += 1
                    continue
                
                current_settled = float(wallet['settled_balance'])
                print(f"  Current Settled Balance: ₹{current_settled:.2f}")
                
                # Check if sufficient balance
                if current_settled < total_deduction:
                    print(f"  ✗ ERROR: Insufficient balance (need ₹{total_deduction:.2f}, have ₹{current_settled:.2f})")
                    print(f"  ⚠️  This payout was successful but merchant doesn't have enough balance now!")
                    print(f"  ⚠️  Manual intervention required - contact merchant or admin")
                    error_count += 1
                    continue
                
                # Debit wallet
                debit_result = wallet_svc.debit_merchant_wallet(
                    merchant_id=merchant_id,
                    amount=total_deduction,
                    description=f"Backfill: Payout ₹{net_amount:.2f} + Charges ₹{charge_amount:.2f} (missed deduction)",
                    reference_id=txn_id
                )
                
                if debit_result['success']:
                    print(f"  ✓ Wallet debited successfully")
                    print(f"    Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                    fixed_count += 1
                else:
                    print(f"  ✗ ERROR: Wallet debit failed - {debit_result['message']}")
                    error_count += 1
            
            print()
            print("=" * 80)
            print("Backfill Complete")
            print("=" * 80)
            print(f"Successfully Fixed: {fixed_count}")
            print(f"Errors: {error_count}")
            print(f"Total Amount Deducted: ₹{total_deduction * fixed_count / len(missing_deductions):.2f}")
            print()
            
            if error_count > 0:
                print("⚠️  Some transactions had errors - review the output above")
                print("   Merchants with insufficient balance need manual intervention")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def show_affected_merchants(target_date=None):
    """Show which merchants are affected and their current balances"""
    
    if not target_date:
        target_date = date.today().strftime('%Y-%m-%d')
    
    print("=" * 80)
    print(f"Affected Merchants Analysis - {target_date}")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get affected merchants with their wallet balances
            cursor.execute("""
                SELECT 
                    p.merchant_id,
                    COUNT(*) as missing_deductions,
                    SUM(p.amount) as total_to_deduct,
                    mw.settled_balance,
                    mw.unsettled_balance,
                    mw.balance
                FROM payout_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON mwt.reference_id = p.txn_id AND mwt.txn_type = 'DEBIT'
                LEFT JOIN merchant_wallet mw ON mw.merchant_id = p.merchant_id
                WHERE p.status = 'SUCCESS'
                AND p.pg_partner IN ('PayTouch', 'Mudrape')
                AND p.merchant_id IS NOT NULL
                AND mwt.txn_id IS NULL
                AND DATE(p.completed_at) = %s
                GROUP BY p.merchant_id, mw.settled_balance, mw.unsettled_balance, mw.balance
                ORDER BY total_to_deduct DESC
            """, (target_date,))
            
            merchants = cursor.fetchall()
            
            if not merchants:
                print("No affected merchants found")
                return
            
            print(f"Found {len(merchants)} affected merchants\n")
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                missing_count = merchant['missing_deductions']
                total_to_deduct = float(merchant['total_to_deduct'])
                settled_balance = float(merchant['settled_balance']) if merchant['settled_balance'] else 0.0
                unsettled_balance = float(merchant['unsettled_balance']) if merchant['unsettled_balance'] else 0.0
                
                print(f"Merchant: {merchant_id}")
                print(f"  Missing Deductions: {missing_count} transactions")
                print(f"  Total to Deduct: ₹{total_to_deduct:.2f}")
                print(f"  Current Settled Balance: ₹{settled_balance:.2f}")
                print(f"  Current Unsettled Balance: ₹{unsettled_balance:.2f}")
                
                if settled_balance >= total_to_deduct:
                    print(f"  Status: ✓ Sufficient balance")
                else:
                    shortfall = total_to_deduct - settled_balance
                    print(f"  Status: ✗ INSUFFICIENT BALANCE (short by ₹{shortfall:.2f})")
                    print(f"  ⚠️  Manual intervention required!")
                
                print()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill missing payout wallet deductions')
    parser.add_argument('--live', action='store_true', help='Apply changes (default is dry-run)')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD, default: today)')
    parser.add_argument('--analyze', action='store_true', help='Show affected merchants analysis')
    
    args = parser.parse_args()
    
    if args.analyze:
        show_affected_merchants(args.date)
    else:
        backfill_missing_payout_deductions(dry_run=not args.live, target_date=args.date)
