"""
Cron job to check pending/initiated payout transactions and deduct wallet when successful.

This script should be run periodically (e.g., every 30 minutes) to:
1. Find payout transactions stuck in PENDING/INITIATED/QUEUED status for > 1 hour
2. Check their status from the payment gateway
3. If SUCCESS, deduct the merchant's wallet
4. Update transaction status accordingly

Usage:
    python cron_check_pending_payouts.py

Add to crontab:
    */30 * * * * cd /path/to/backend && python cron_check_pending_payouts.py >> logs/cron_payout_check.log 2>&1
"""

import sys
from datetime import datetime, timedelta
from database import get_db_connection
from wallet_service import wallet_svc
from mudrape_service import mudrape_service
from payu_payout_service import payu_payout_svc

def check_and_update_pending_payouts():
    """
    Check all pending payout transactions and update their status.
    Refund wallet if transaction failed.
    """
    print(f"\n{'='*60}")
    print(f"Payout Status Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find transactions in pending states older than 1 hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            cursor.execute("""
                SELECT txn_id, reference_id, merchant_id, amount, charge_amount, 
                       net_amount, pg_partner, status, created_at
                FROM payout_transactions
                WHERE status IN ('PENDING', 'INITIATED', 'QUEUED')
                AND created_at < %s
                ORDER BY created_at ASC
            """, (one_hour_ago,))
            
            pending_payouts = cursor.fetchall()
            
            if not pending_payouts:
                print("✓ No pending payouts to check")
                conn.close()
                return
            
            print(f"Found {len(pending_payouts)} pending payout(s) to check\n")
            
            updated_count = 0
            wallet_deducted_count = 0
            
            for payout in pending_payouts:
                txn_id = payout['txn_id']
                reference_id = payout['reference_id']
                merchant_id = payout['merchant_id']
                amount = float(payout['amount'])
                pg_partner = payout['pg_partner'].upper()
                current_status = payout['status']
                
                print(f"Checking: {txn_id} | Merchant: {merchant_id} | Amount: ₹{amount:.2f}")
                print(f"  Current Status: {current_status} | Gateway: {pg_partner}")
                
                new_status = None
                utr = None
                error_message = None
                
                # Check status from payment gateway
                if pg_partner == 'MUDRAPE':
                    status_result = mudrape_service.check_payout_status(reference_id)
                    if status_result.get('success'):
                        new_status = status_result.get('status', current_status)
                        utr = status_result.get('utr')
                        if new_status == 'FAILED':
                            error_message = status_result.get('message', 'Transaction failed')
                        print(f"  Mudrape Status: {new_status} | UTR: {utr}")
                    else:
                        print(f"  ⚠ Failed to check Mudrape status: {status_result.get('message')}")
                
                elif pg_partner == 'PAYU':
                    # Check PayU status
                    status_result = payu_payout_svc.check_transfer_status(reference_id)
                    if status_result.get('success'):
                        new_status = status_result.get('status', current_status)
                        utr = status_result.get('utr')
                        if new_status == 'FAILED':
                            error_message = status_result.get('message', 'Transaction failed')
                        print(f"  PayU Status: {new_status} | UTR: {utr}")
                    else:
                        print(f"  ⚠ Failed to check PayU status: {status_result.get('message')}")
                
                else:
                    print(f"  ⚠ Unknown gateway: {pg_partner}")
                    continue
                
                # Update transaction if status changed
                if new_status and new_status != current_status:
                    # Deduct wallet if status changed to SUCCESS
                    if new_status == 'SUCCESS':
                        debit_result = wallet_svc.debit_merchant_wallet(
                            merchant_id=merchant_id,
                            amount=amount,
                            description=f"Payout completed {txn_id}",
                            reference_id=txn_id
                        )
                        
                        if debit_result['success']:
                            wallet_deducted_count += 1
                            print(f"  💰 Wallet deducted: ₹{amount:.2f}")
                            print(f"     Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                        else:
                            print(f"  ❌ Wallet deduction failed: {debit_result['message']}")
                            # Mark transaction as failed if wallet deduction fails
                            new_status = 'FAILED'
                            error_message = f"Wallet deduction failed: {debit_result['message']}"
                    
                    if new_status in ['SUCCESS', 'FAILED']:
                        # Final status - set completed_at
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, error_message = %s, 
                                completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, utr, error_message, txn_id))
                    else:
                        # Still pending - just update status
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (new_status, utr, txn_id))
                    
                    conn.commit()
                    updated_count += 1
                    print(f"  ✓ Updated status: {current_status} → {new_status}")
                else:
                    print(f"  → No status change")
                
                print()
            
            print(f"{'='*60}")
            print(f"Summary:")
            print(f"  Total Checked: {len(pending_payouts)}")
            print(f"  Status Updated: {updated_count}")
            print(f"  Wallets Deducted: {wallet_deducted_count}")
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    try:
        check_and_update_pending_payouts()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
