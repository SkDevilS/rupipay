#!/usr/bin/env python3
"""
Cron Job: Check Pending Payin Transactions
Runs every 5 minutes to reconcile transactions that didn't receive callbacks

This ensures all transactions eventually get their status updated from Mudrape
even if the callback fails or is delayed.

Usage:
    python cron_check_pending_payins.py

Crontab Entry:
    */5 * * * * cd /path/to/backend && python cron_check_pending_payins.py >> /var/log/payin_cron.log 2>&1
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from mudrape_service import MudrapeService
from wallet_service import WalletService

def check_pending_transactions():
    """Check all pending payin transactions and update their status"""
    
    print("=" * 80)
    print(f"CRON JOB: Check Pending Payins - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    mudrape_service = MudrapeService()
    wallet_service = WalletService()
    
    try:
        with conn.cursor() as cursor:
            # Get all pending transactions from last 24 hours
            # (older than 24 hours are likely abandoned)
            cursor.execute("""
                SELECT 
                    txn_id, order_id, merchant_id, amount, net_amount, 
                    charge_amount, pg_txn_id, status, created_at
                FROM payin_transactions
                WHERE status IN ('INITIATED', 'PENDING')
                AND pg_partner = 'Mudrape'
                AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at ASC
            """)
            
            pending_txns = cursor.fetchall()
            
            if not pending_txns:
                print("✓ No pending transactions found")
                return
            
            print(f"\nFound {len(pending_txns)} pending transaction(s):\n")
            
            success_count = 0
            failed_count = 0
            still_pending_count = 0
            error_count = 0
            
            for txn in pending_txns:
                txn_id = txn['txn_id']
                order_id = txn['order_id']
                merchant_id = txn['merchant_id']
                net_amount = float(txn['net_amount'])
                charge_amount = float(txn['charge_amount'])
                pg_txn_id = txn.get('pg_txn_id')
                
                print(f"\n{'─' * 80}")
                print(f"Checking: {txn_id}")
                print(f"  Order ID: {order_id}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Current Status: {txn['status']}")
                
                # Use pg_txn_id if available, otherwise use order_id
                identifier = pg_txn_id if pg_txn_id else order_id
                
                # Check status from Mudrape
                status_result = mudrape_service.check_payment_status(identifier)
                
                if not status_result.get('success'):
                    print(f"  ⚠ Status check failed: {status_result.get('message')}")
                    error_count += 1
                    continue
                
                mudrape_status = status_result.get('status', '').upper()
                utr = status_result.get('utr')
                mudrape_txn_id = status_result.get('txnId')
                
                print(f"  Mudrape Status: {mudrape_status}")
                print(f"  UTR: {utr if utr else 'N/A'}")
                print(f"  Mudrape TXN ID: {mudrape_txn_id if mudrape_txn_id else 'N/A'}")
                
                if mudrape_status == 'SUCCESS':
                    # Update transaction to SUCCESS
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'SUCCESS',
                            bank_ref_no = %s,
                            pg_txn_id = %s,
                            payment_mode = 'UPI',
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (utr, mudrape_txn_id, txn_id))
                    
                    # Check if wallet already credited (idempotency)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn_id,))
                    
                    wallet_already_credited = cursor.fetchone()['count'] > 0
                    
                    if not wallet_already_credited:
                        # Credit merchant unsettled wallet
                        wallet_result = wallet_service.credit_unsettled_wallet(
                            merchant_id=merchant_id,
                            amount=net_amount,
                            description=f"PayIn received (Cron reconciliation) - {order_id}",
                            reference_id=txn_id
                        )
                        
                        if wallet_result['success']:
                            print(f"  ✓ Merchant wallet credited: ₹{net_amount}")
                        else:
                            print(f"  ✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                        
                        # Credit admin unsettled wallet
                        admin_wallet_result = wallet_service.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=charge_amount,
                            description=f"PayIn charge (Cron reconciliation) - {order_id}",
                            reference_id=txn_id
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"  ✓ Admin wallet credited: ₹{charge_amount}")
                        else:
                            print(f"  ✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"  ⚠ Wallet already credited (duplicate callback)")
                    
                    conn.commit()
                    success_count += 1
                    print(f"  ✓ Transaction updated to SUCCESS")
                    
                elif mudrape_status == 'FAILED':
                    # Update transaction to FAILED
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = 'FAILED',
                            pg_txn_id = %s,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mudrape_txn_id, txn_id))
                    
                    conn.commit()
                    failed_count += 1
                    print(f"  ✓ Transaction updated to FAILED")
                    
                else:
                    # Still pending/initiated
                    still_pending_count += 1
                    print(f"  ℹ Transaction still {mudrape_status}")
            
            print(f"\n{'=' * 80}")
            print("SUMMARY")
            print(f"{'=' * 80}")
            print(f"Total Checked: {len(pending_txns)}")
            print(f"  ✓ Updated to SUCCESS: {success_count}")
            print(f"  ✗ Updated to FAILED: {failed_count}")
            print(f"  ⏳ Still Pending: {still_pending_count}")
            print(f"  ❌ Errors: {error_count}")
            print(f"{'=' * 80}\n")
            
    except Exception as e:
        print(f"\n❌ Error in cron job: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    check_pending_transactions()
