#!/usr/bin/env python3
"""
Fix Missing Mudrape Wallet Deductions
Backfills wallet deductions for SUCCESS Mudrape payouts that are missing them
"""

import sys
from database import get_db_connection
from wallet_service import WalletService
from datetime import datetime

def fix_missing_wallet_deductions(merchant_id=None, dry_run=True):
    """
    Fix SUCCESS Mudrape payouts that are missing wallet deductions
    
    Args:
        merchant_id: Optional specific merchant to fix (default: all merchants)
        dry_run: If True, only show what would be fixed without making changes
    """
    
    print("=" * 80)
    print("FIX MISSING MUDRAPE WALLET DEDUCTIONS")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE MODE (applying fixes)'}")
    if merchant_id:
        print(f"Merchant: {merchant_id}")
    else:
        print("Merchant: ALL")
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    wallet_svc = WalletService()
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS Mudrape payouts without wallet deduction
            query = """
                SELECT 
                    p.txn_id,
                    p.reference_id,
                    p.merchant_id,
                    p.amount,
                    p.net_amount,
                    p.charge_amount,
                    p.status,
                    p.pg_partner,
                    p.completed_at,
                    p.created_at,
                    mwt.txn_id as wallet_txn_id
                FROM payout_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON mwt.reference_id = p.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE p.status = 'SUCCESS'
                AND p.pg_partner = 'Mudrape'
                AND p.created_at >= '2026-03-09 00:00:00'
                AND mwt.txn_id IS NULL
            """
            
            params = []
            if merchant_id:
                query += " AND p.merchant_id = %s"
                params.append(merchant_id)
            
            query += " ORDER BY p.created_at ASC"
            
            cursor.execute(query, params)
            missing_deductions = cursor.fetchall()
            
            if not missing_deductions:
                print("✓ No missing wallet deductions found")
                conn.close()
                return
            
            print(f"Found {len(missing_deductions)} SUCCESS payouts missing wallet deduction")
            print()
            
            # Group by merchant
            merchants_affected = {}
            for payout in missing_deductions:
                mid = payout['merchant_id']
                if mid not in merchants_affected:
                    merchants_affected[mid] = []
                merchants_affected[mid].append(payout)
            
            print(f"Affected merchants: {len(merchants_affected)}")
            print()
            
            # Process each merchant
            for mid, payouts in merchants_affected.items():
                print(f"Merchant: {mid}")
                print(f"  Missing deductions: {len(payouts)}")
                
                # Get current wallet balance
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (mid,))
                
                wallet = cursor.fetchone()
                if not wallet:
                    print(f"  ❌ Wallet not found for merchant {mid}")
                    continue
                
                current_settled = float(wallet['settled_balance'])
                total_to_deduct = sum(float(p['amount']) for p in payouts)
                
                print(f"  Current settled balance: ₹{current_settled:.2f}")
                print(f"  Total to deduct: ₹{total_to_deduct:.2f}")
                print(f"  Balance after deduction: ₹{current_settled - total_to_deduct:.2f}")
                
                if current_settled < total_to_deduct:
                    print(f"  ⚠️  WARNING: Insufficient balance! Merchant needs ₹{total_to_deduct - current_settled:.2f} more")
                    print(f"  Skipping this merchant - manual intervention required")
                    print()
                    continue
                
                # Process each payout
                success_count = 0
                fail_count = 0
                
                for payout in payouts:
                    txn_id = payout['txn_id']
                    amount = float(payout['amount'])
                    net_amount = float(payout['net_amount'])
                    charge_amount = float(payout['charge_amount'])
                    
                    print(f"  Processing {txn_id}: ₹{amount:.2f} (Net: ₹{net_amount:.2f} + Charges: ₹{charge_amount:.2f})")
                    
                    if not dry_run:
                        # Debit wallet
                        debit_result = wallet_svc.debit_merchant_wallet(
                            merchant_id=mid,
                            amount=amount,
                            description=f"Payout: ₹{net_amount:.2f} + Charges: ₹{charge_amount:.2f} (Backfilled)",
                            reference_id=txn_id
                        )
                        
                        if debit_result['success']:
                            print(f"    ✓ Wallet debited: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                            success_count += 1
                        else:
                            print(f"    ✗ Failed: {debit_result['message']}")
                            fail_count += 1
                    else:
                        print(f"    [DRY RUN] Would debit ₹{amount:.2f}")
                        success_count += 1
                
                print(f"  Summary: {success_count} successful, {fail_count} failed")
                print()
            
            if not dry_run:
                conn.commit()
                print("✓ All changes committed to database")
            else:
                print("ℹ️  DRY RUN - No changes made. Run with --live to apply fixes")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            conn.rollback()
    finally:
        conn.close()
    
    print()
    print("=" * 80)
    print("FIX COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix missing Mudrape wallet deductions')
    parser.add_argument('--merchant', help='Specific merchant ID to fix')
    parser.add_argument('--live', action='store_true', help='Apply fixes (default is dry run)')
    
    args = parser.parse_args()
    
    fix_missing_wallet_deductions(
        merchant_id=args.merchant,
        dry_run=not args.live
    )
