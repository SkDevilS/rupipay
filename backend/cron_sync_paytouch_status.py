"""
Cron Job: Sync PayTouch Payout Status
Automatically check and update status for pending PayTouch transactions
Run every 15 minutes
"""

from database import get_db_connection
from paytouch_service import paytouch_service
from wallet_service import wallet_service
from datetime import datetime, timedelta
import json

def sync_paytouch_status():
    """Check and update status for pending PayTouch transactions"""
    
    print("=" * 80)
    print(f"PayTouch Status Sync - {datetime.now()}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch transactions that are pending and older than 5 minutes
            # (give PayTouch time to send callback first)
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, created_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                  AND status IN ('PENDING', 'QUEUED', 'INPROCESS', 'INITIATED')
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                  AND created_at <= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                ORDER BY created_at ASC
                LIMIT 50
            """)
            
            pending_txns = cursor.fetchall()
            
            if not pending_txns:
                print("No pending PayTouch transactions found")
                return
            
            print(f"\nFound {len(pending_txns)} pending PayTouch transactions")
            print("-" * 80)
            
            updated_count = 0
            failed_count = 0
            
            for txn in pending_txns:
                print(f"\nChecking {txn['txn_id']} (Ref: {txn['reference_id']})")
                print(f"  Current Status: {txn['status']}")
                print(f"  Created: {txn['created_at']}")
                
                try:
                    # Check status from PayTouch
                    status_result = paytouch_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if not status_result.get('success'):
                        print(f"  ✗ Failed to check status: {status_result.get('message')}")
                        failed_count += 1
                        continue
                    
                    paytouch_status = status_result.get('status')
                    paytouch_utr = status_result.get('utr')
                    
                    # Map PayTouch status
                    status_map = {
                        'SUCCESS': 'SUCCESS',
                        'PENDING': 'QUEUED',
                        'FAILED': 'FAILED',
                        'PROCESSING': 'INPROCESS'
                    }
                    mapped_status = status_map.get(paytouch_status, 'QUEUED')
                    
                    print(f"  PayTouch Status: {paytouch_status} → {mapped_status}")
                    
                    if mapped_status == txn['status']:
                        print(f"  ✓ Status unchanged, skipping")
                        continue
                    
                    # Status changed - update transaction
                    if mapped_status == 'SUCCESS':
                        # Debit wallet if this is a merchant transaction
                        if txn['merchant_id']:
                            total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                            
                            print(f"  Debiting merchant wallet: ₹{total_deduction}")
                            debit_result = wallet_service.debit_merchant_wallet(
                                merchant_id=txn['merchant_id'],
                                amount=total_deduction,
                                description=f"Payout - {txn['reference_id']} (Auto-Sync)",
                                reference_id=txn['txn_id']
                            )
                            
                            if debit_result['success']:
                                print(f"  ✅ WALLET DEBITED - Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                            else:
                                print(f"  ⚠️  WALLET DEBIT FAILED: {debit_result['message']}")
                                # Update to FAILED if wallet debit fails
                                cursor.execute("""
                                    UPDATE payout_transactions
                                    SET status = 'FAILED', 
                                        error_message = %s,
                                        completed_at = NOW(), 
                                        updated_at = NOW()
                                    WHERE txn_id = %s
                                """, (f"Wallet debit failed: {debit_result['message']}", txn['txn_id']))
                                conn.commit()
                                failed_count += 1
                                continue
                        
                        # Update transaction to SUCCESS
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, paytouch_utr, txn['txn_id']))
                        
                    elif mapped_status == 'FAILED':
                        # Update to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, 
                                error_message = %s,
                                completed_at = NOW(), 
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, 'Failed at PayTouch', txn['txn_id']))
                        
                    else:
                        # Update to intermediate status
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, txn['txn_id']))
                    
                    conn.commit()
                    updated_count += 1
                    print(f"  ✅ Updated to {mapped_status}")
                    
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    failed_count += 1
                    continue
            
            print("\n" + "=" * 80)
            print(f"Sync Complete")
            print(f"  Updated: {updated_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Unchanged: {len(pending_txns) - updated_count - failed_count}")
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    sync_paytouch_status()
