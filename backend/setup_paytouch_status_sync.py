#!/usr/bin/env python3
"""
Setup PayTouch Status Sync
Creates a cron job to regularly sync PayTouch transaction statuses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from paytouch_service import PayTouchService
from wallet_service import WalletService
from datetime import datetime, timedelta
import json

def sync_paytouch_statuses():
    """
    Sync PayTouch transaction statuses for recent transactions
    """
    
    print("=" * 80)
    print(f"PayTouch Status Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    paytouch_service = PayTouchService()
    wallet_service = WalletService()
    
    try:
        with conn.cursor() as cursor:
            
            # Get PayTouch transactions from last 7 days that are not SUCCESS
            cursor.execute("""
                SELECT txn_id, pg_txn_id, reference_id, status, merchant_id, admin_id,
                       amount, net_amount, charge_amount, utr, created_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status IN ('FAILED', 'QUEUED', 'INPROCESS')
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            pending_txns = cursor.fetchall()
            
            if not pending_txns:
                print("✅ No pending PayTouch transactions to sync")
                return
            
            print(f"🔍 Found {len(pending_txns)} PayTouch transactions to check")
            
            updated_count = 0
            
            for txn in pending_txns:
                print(f"\n📊 Checking: {txn['txn_id']} (Status: {txn['status']})")
                
                # Check status with PayTouch API
                status_result = paytouch_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['pg_txn_id']
                )
                
                if not status_result['success']:
                    print(f"❌ API Error: {status_result['message']}")
                    continue
                
                api_status = status_result['status']
                api_utr = status_result.get('utr')
                
                print(f"📡 PayTouch Status: {api_status}")
                
                if api_status == txn['status']:
                    print(f"✅ Status matches - no update needed")
                    continue
                
                print(f"⚠️  STATUS MISMATCH: {txn['status']} → {api_status}")
                
                # Handle SUCCESS status
                if api_status == 'SUCCESS':
                    print(f"🎉 Transaction is SUCCESS in PayTouch!")
                    
                    # Check if wallet was already deducted
                    cursor.execute("""
                        SELECT txn_id FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'DEBIT'
                    """, (txn['txn_id'],))
                    
                    wallet_already_deducted = cursor.fetchone()
                    
                    # Handle wallet deduction for merchant transactions
                    if txn['merchant_id'] and not wallet_already_deducted:
                        print(f"💸 Debiting merchant wallet...")
                        
                        total_deduction = float(txn['amount'])
                        
                        debit_result = wallet_service.debit_merchant_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=total_deduction,
                            description=f"Payout: ₹{txn['net_amount']:.2f} + Charges: ₹{txn['charge_amount']:.2f}",
                            reference_id=txn['txn_id']
                        )
                        
                        if not debit_result['success']:
                            print(f"❌ Wallet debit failed: {debit_result['message']}")
                            continue
                        
                        print(f"✅ Wallet debited: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                    
                    # Update transaction to SUCCESS
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (api_status, api_utr, txn['txn_id']))
                    
                    updated_count += 1
                    print(f"✅ Updated to SUCCESS")
                
                # Handle FAILED status
                elif api_status == 'FAILED':
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (api_status, txn['txn_id']))
                    
                    updated_count += 1
                    print(f"❌ Updated to FAILED")
                
                # Handle other statuses
                else:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (api_status, txn['txn_id']))
                    
                    updated_count += 1
                    print(f"🔄 Updated to {api_status}")
                
                conn.commit()
            
            print(f"\n{'='*60}")
            print(f"Sync completed: {updated_count} transactions updated")
            print(f"{'='*60}")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def create_cron_job():
    """
    Create a cron job for PayTouch status sync
    """
    
    print("\n" + "=" * 80)
    print("PayTouch Cron Job Setup")
    print("=" * 80)
    
    cron_command = f"cd /var/www/moneyone/moneyone && python3 backend/setup_paytouch_status_sync.py"
    
    print("To set up automatic PayTouch status sync, add this cron job:")
    print("-" * 60)
    print("# PayTouch Status Sync - Every 30 minutes")
    print(f"*/30 * * * * {cron_command} >> /var/log/paytouch_sync.log 2>&1")
    print("-" * 60)
    
    print("\nTo add the cron job:")
    print("1. Run: crontab -e")
    print("2. Add the line above")
    print("3. Save and exit")
    
    print("\nTo check cron job status:")
    print("crontab -l")
    print("tail -f /var/log/paytouch_sync.log")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'setup-cron':
        create_cron_job()
    else:
        sync_paytouch_statuses()