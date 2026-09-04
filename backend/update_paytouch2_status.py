#!/usr/bin/env python3
"""
Update PayTouch2 Status
Manually check and update status for PayTouch2 transactions
This fixes transactions that were incorrectly marked as FAILED due to delayed callbacks
"""

from database import get_db_connection
from paytouch2_service import paytouch2_service
from wallet_service import WalletService
from datetime import datetime, timedelta
import json

def update_paytouch2_status():
    """Update PayTouch2 transaction status by checking with API"""
    
    print("🔄 Updating PayTouch2 Transaction Status")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch2 transactions that might need status update
            # Include FAILED transactions that might have been incorrectly marked
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, created_at, completed_at,
                    error_message
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                  AND status IN ('PENDING', 'QUEUED', 'INPROCESS', 'INITIATED', 'FAILED')
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY created_at DESC
                LIMIT 100
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("ℹ️  No PayTouch2 transactions found to update")
                return True
            
            print(f"Found {len(transactions)} PayTouch2 transactions to check")
            print("-" * 80)
            
            updated_count = 0
            failed_count = 0
            unchanged_count = 0
            wallet_fixed_count = 0
            
            for txn in transactions:
                print(f"\n🔍 Checking {txn['txn_id']} (Ref: {txn['reference_id']})")
                print(f"   Current Status: {txn['status']}")
                print(f"   Created: {txn['created_at']}")
                print(f"   PG TXN ID: {txn['pg_txn_id'] or 'N/A'}")
                
                if txn['status'] == 'FAILED':
                    print(f"   Error: {txn['error_message'] or 'N/A'}")
                
                try:
                    # Check status from PayTouch2 API
                    status_result = paytouch2_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if not status_result.get('success'):
                        print(f"   ❌ API Error: {status_result.get('message')}")
                        failed_count += 1
                        continue
                    
                    api_status = status_result.get('status')
                    api_utr = status_result.get('utr')
                    api_txn_id = status_result.get('transaction_id')
                    
                    # Map PayTouch2 status to internal status
                    status_map = {
                        'SUCCESS': 'SUCCESS',
                        'PENDING': 'QUEUED',
                        'FAILED': 'FAILED',
                        'PROCESSING': 'INPROCESS'
                    }
                    mapped_status = status_map.get(api_status, 'QUEUED')
                    
                    print(f"   PayTouch2 API: {api_status} → {mapped_status}")
                    print(f"   UTR: {api_utr or 'N/A'}")
                    
                    # Check if status changed
                    if mapped_status == txn['status']:
                        print(f"   ✓ Status unchanged")
                        unchanged_count += 1
                        continue
                    
                    # Status changed - update transaction
                    print(f"   🔄 Updating status: {txn['status']} → {mapped_status}")
                    
                    if mapped_status == 'SUCCESS':
                        # Handle SUCCESS status
                        if txn['merchant_id']:
                            # Check if wallet was already deducted
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'DEBIT'
                            """, (txn['txn_id'],))
                            
                            wallet_deducted = cursor.fetchone()['count'] > 0
                            
                            if not wallet_deducted:
                                # Debit merchant wallet
                                total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                                
                                print(f"   💰 Debiting wallet: ₹{total_deduction}")
                                
                                wallet_svc = WalletService()
                                debit_result = wallet_svc.debit_merchant_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=total_deduction,
                                    description=f"PayTouch2 Payout - {txn['reference_id']} (Status Update)",
                                    reference_id=txn['txn_id']
                                )
                                
                                if debit_result['success']:
                                    print(f"   ✅ WALLET DEBITED: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                                    wallet_fixed_count += 1
                                else:
                                    print(f"   ❌ WALLET DEBIT FAILED: {debit_result['message']}")
                                    # Don't update to SUCCESS if wallet debit fails
                                    cursor.execute("""
                                        UPDATE payout_transactions
                                        SET error_message = %s, updated_at = NOW()
                                        WHERE txn_id = %s
                                    """, (f"Wallet debit failed: {debit_result['message']}", txn['txn_id']))
                                    conn.commit()
                                    failed_count += 1
                                    continue
                            else:
                                print(f"   ✓ Wallet already debited")
                        
                        # Update to SUCCESS with completion time
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, utr = %s, pg_txn_id = %s, 
                                completed_at = NOW(), updated_at = NOW(),
                                error_message = NULL
                            WHERE txn_id = %s
                        """, (mapped_status, api_utr, api_txn_id, txn['txn_id']))
                        
                    elif mapped_status == 'FAILED':
                        # Update to FAILED
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, 
                                error_message = %s,
                                completed_at = NOW(), 
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (mapped_status, f'Failed at PayTouch2: {api_status}', txn['txn_id']))
                        
                    else:
                        # Update to intermediate status
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, pg_txn_id = %s, updated_at = NOW(),
                                error_message = NULL
                            WHERE txn_id = %s
                        """, (mapped_status, api_txn_id, txn['txn_id']))
                    
                    conn.commit()
                    updated_count += 1
                    print(f"   ✅ Updated to {mapped_status}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed_count += 1
                    continue
            
            print("\n" + "=" * 80)
            print("📊 Update Summary:")
            print(f"   ✅ Updated: {updated_count}")
            print(f"   💰 Wallet Fixed: {wallet_fixed_count}")
            print(f"   ❌ Failed: {failed_count}")
            print(f"   ➖ Unchanged: {unchanged_count}")
            print("=" * 80)
            
            return updated_count > 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

def fix_failed_paytouch2_transactions():
    """Fix PayTouch2 transactions that were incorrectly marked as FAILED"""
    
    print("🔧 Fixing Incorrectly Failed PayTouch2 Transactions")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find FAILED PayTouch2 transactions from last 24 hours
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, status, pg_txn_id, 
                    created_at, error_message
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                  AND status = 'FAILED'
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            failed_txns = cursor.fetchall()
            
            if not failed_txns:
                print("✅ No recently failed PayTouch2 transactions found")
                return True
            
            print(f"Found {len(failed_txns)} recently failed PayTouch2 transactions")
            print("Checking if any are actually successful...")
            print("-" * 60)
            
            fixed_count = 0
            still_failed_count = 0
            
            for txn in failed_txns:
                print(f"\n🔍 Checking {txn['txn_id']}")
                print(f"   Error: {txn['error_message'] or 'N/A'}")
                
                try:
                    # Check actual status from PayTouch2
                    status_result = paytouch2_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if not status_result.get('success'):
                        print(f"   ❌ API Error: {status_result.get('message')}")
                        still_failed_count += 1
                        continue
                    
                    api_status = status_result.get('status')
                    api_utr = status_result.get('utr')
                    
                    if api_status == 'SUCCESS':
                        print(f"   🎉 Actually SUCCESS! UTR: {api_utr}")
                        
                        # Fix the transaction
                        if txn['merchant_id']:
                            # Check if wallet needs to be debited
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                                WHERE reference_id = %s AND txn_type = 'DEBIT'
                            """, (txn['txn_id'],))
                            
                            wallet_deducted = cursor.fetchone()['count'] > 0
                            
                            if not wallet_deducted:
                                total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                                
                                print(f"   💰 Debiting wallet: ₹{total_deduction}")
                                
                                wallet_svc = WalletService()
                                debit_result = wallet_svc.debit_merchant_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=total_deduction,
                                    description=f"PayTouch2 Payout - {txn['reference_id']} (Fixed)",
                                    reference_id=txn['txn_id']
                                )
                                
                                if not debit_result['success']:
                                    print(f"   ❌ Wallet debit failed: {debit_result['message']}")
                                    still_failed_count += 1
                                    continue
                                
                                print(f"   ✅ Wallet debited successfully")
                        
                        # Update transaction to SUCCESS
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'SUCCESS', utr = %s, 
                                completed_at = NOW(), updated_at = NOW(),
                                error_message = NULL
                            WHERE txn_id = %s
                        """, (api_utr, txn['txn_id']))
                        
                        conn.commit()
                        fixed_count += 1
                        print(f"   ✅ Fixed transaction!")
                        
                    else:
                        print(f"   ❌ Still failed: {api_status}")
                        still_failed_count += 1
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    still_failed_count += 1
                    continue
            
            print(f"\n📊 Fix Summary:")
            print(f"   ✅ Fixed: {fixed_count}")
            print(f"   ❌ Still Failed: {still_failed_count}")
            
            return fixed_count > 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'fix-failed':
        success = fix_failed_paytouch2_transactions()
    else:
        success = update_paytouch2_status()
    
    if success:
        print("\n✅ PayTouch2 status update completed!")
    else:
        print("\n❌ PayTouch2 status update failed!")

if __name__ == '__main__':
    main()