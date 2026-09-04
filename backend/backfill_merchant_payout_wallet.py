#!/usr/bin/env python3
"""
Backfill Missing Payout Wallet Deductions for Specific Merchant (TODAY ONLY)
This script deducts wallet for TODAY's successful payouts that are missing wallet transactions.
Prevents double deduction by checking existing wallet transactions.
"""

import sys
import pymysql
import uuid
from decimal import Decimal
from datetime import datetime
from database import get_db_connection

def backfill_merchant_payout_wallet(merchant_id, dry_run=True):
    """
    Backfill missing wallet deductions for a specific merchant's successful payouts (TODAY ONLY).
    
    Args:
        merchant_id: The merchant ID to process
        dry_run: If True, only show what would be done without making changes
    """
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Verify merchant exists
            cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found")
                return False
            
            print(f"\n{'='*80}")
            print(f"Backfill Payout Wallet Deductions (TODAY ONLY)")
            print(f"{'='*80}")
            print(f"Merchant ID: {merchant['merchant_id']}")
            print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will make changes)'}")
            print(f"{'='*80}\n")
            
            # Get current wallet balance
            cursor.execute("""
                SELECT settled_balance, unsettled_balance 
                FROM merchant_wallet 
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet = cursor.fetchone()
            
            if wallet:
                print(f"Current Wallet Balance:")
                print(f"  Settled: ₹{float(wallet['settled_balance']):.2f}")
                print(f"  Unsettled: ₹{float(wallet['unsettled_balance']):.2f}")
            else:
                print(f"⚠️  No wallet found for merchant {merchant_id}")
            
            print(f"\n{'='*80}")
            print("Finding TODAY's successful payouts without wallet deductions...")
            print(f"{'='*80}\n")
            
            # Get today's date range
            from datetime import date
            today = date.today()
            print(f"Processing payouts for: {today.strftime('%Y-%m-%d')}\n")
            
            # Find successful payouts from TODAY that don't have corresponding wallet deductions
            cursor.execute("""
                SELECT 
                    p.txn_id,
                    p.reference_id,
                    p.order_id,
                    p.merchant_id,
                    p.amount,
                    p.charge_amount,
                    p.net_amount,
                    p.status,
                    p.pg_partner,
                    p.created_at,
                    p.completed_at,
                    COUNT(w.id) as wallet_txn_count
                FROM payout_transactions p
                LEFT JOIN merchant_wallet_transactions w 
                    ON w.reference_id = p.txn_id 
                    AND w.txn_type = 'DEBIT'
                    AND w.merchant_id = p.merchant_id
                WHERE p.merchant_id = %s
                    AND p.status = 'SUCCESS'
                    AND p.completed_at IS NOT NULL
                    AND DATE(p.completed_at) = CURDATE()
                GROUP BY p.txn_id
                HAVING wallet_txn_count = 0
                ORDER BY p.completed_at ASC
            """, (merchant_id,))
            
            missing_deductions = cursor.fetchall()
            
            if not missing_deductions:
                print("✅ No missing wallet deductions found for TODAY. All today's successful payouts have been deducted.")
                return True
            
            print(f"Found {len(missing_deductions)} successful payout(s) from TODAY without wallet deduction:\n")
            
            total_to_deduct = Decimal('0.00')
            processed_count = 0
            skipped_count = 0
            
            for idx, payout in enumerate(missing_deductions, 1):
                txn_id = payout['txn_id']
                reference_id = payout['reference_id']
                order_id = payout['order_id']
                amount = Decimal(str(payout['amount']))
                charge_amount = Decimal(str(payout['charge_amount']))
                net_amount = Decimal(str(payout['net_amount']))
                pg_partner = payout['pg_partner']
                created_at = payout['created_at']
                completed_at = payout['completed_at']
                
                print(f"{idx}. Transaction: {txn_id}")
                print(f"   Reference ID: {reference_id}")
                print(f"   Order ID: {order_id}")
                print(f"   Amount: ₹{float(amount):.2f}")
                print(f"   Charges: ₹{float(charge_amount):.2f}")
                print(f"   Net to Bank: ₹{float(net_amount):.2f}")
                print(f"   PG Partner: {pg_partner}")
                print(f"   Created: {created_at}")
                print(f"   Completed: {completed_at}")
                
                # Double-check: Verify no wallet transaction exists
                cursor.execute("""
                    SELECT id, amount, description, created_at 
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                        AND reference_id = %s 
                        AND txn_type = 'DEBIT'
                """, (merchant_id, txn_id))
                
                existing_wallet_txn = cursor.fetchone()
                
                if existing_wallet_txn:
                    print(f"   ⚠️  SKIPPED - Wallet transaction already exists (ID: {existing_wallet_txn['id']})")
                    print(f"       Amount: ₹{float(existing_wallet_txn['amount']):.2f}")
                    print(f"       Created: {existing_wallet_txn['created_at']}")
                    skipped_count += 1
                else:
                    total_to_deduct += amount
                    
                    if dry_run:
                        print(f"   🔍 WOULD DEDUCT: ₹{float(amount):.2f} from settled wallet")
                    else:
                        # Create wallet deduction transaction
                        description = f"Payout: ₹{float(net_amount):.2f} + Charges: ₹{float(charge_amount):.2f}"
                        
                        try:
                            # Generate unique wallet transaction ID
                            import uuid
                            wallet_txn_id = f"WT{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                            
                            # Insert wallet transaction
                            cursor.execute("""
                                INSERT INTO merchant_wallet_transactions
                                (txn_id, merchant_id, amount, txn_type, description, reference_id, created_at)
                                VALUES (%s, %s, %s, 'DEBIT', %s, %s, NOW())
                            """, (wallet_txn_id, merchant_id, amount, description, txn_id))
                            
                            # Update merchant wallet balance
                            cursor.execute("""
                                UPDATE merchant_wallet
                                SET settled_balance = settled_balance - %s
                                WHERE merchant_id = %s
                            """, (amount, merchant_id))
                            
                            conn.commit()
                            
                            print(f"   ✅ DEDUCTED: ₹{float(amount):.2f} from settled wallet")
                            processed_count += 1
                            
                        except Exception as e:
                            conn.rollback()
                            print(f"   ❌ ERROR: Failed to deduct wallet - {str(e)}")
                            skipped_count += 1
                
                print()
            
            print(f"{'='*80}")
            print("Summary")
            print(f"{'='*80}")
            print(f"Total Payouts Found: {len(missing_deductions)}")
            print(f"Processed: {processed_count}")
            print(f"Skipped: {skipped_count}")
            print(f"Total Amount to Deduct: ₹{float(total_to_deduct):.2f}")
            
            if dry_run:
                print(f"\n⚠️  DRY RUN MODE - No changes were made")
                print(f"Run with --live flag to apply changes")
            else:
                print(f"\n✅ Wallet deductions applied successfully")
                
                # Show updated wallet balance
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                """, (merchant_id,))
                updated_wallet = cursor.fetchone()
                
                if updated_wallet:
                    print(f"\nUpdated Wallet Balance:")
                    print(f"  Settled: ₹{float(updated_wallet['settled_balance']):.2f}")
                    print(f"  Unsettled: ₹{float(updated_wallet['unsettled_balance']):.2f}")
            
            print(f"{'='*80}\n")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python backfill_merchant_payout_wallet.py <merchant_id> [--live]")
        print("\nExamples:")
        print("  python backfill_merchant_payout_wallet.py 9000000001          # Dry run")
        print("  python backfill_merchant_payout_wallet.py 9000000001 --live   # Apply changes")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    dry_run = '--live' not in sys.argv
    
    if not dry_run:
        print("\n⚠️  WARNING: Running in LIVE mode. Changes will be applied to the database.")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    success = backfill_merchant_payout_wallet(merchant_id, dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
