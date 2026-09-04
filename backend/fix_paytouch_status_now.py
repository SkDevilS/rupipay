#!/usr/bin/env python3
"""
Quick fix for PayTouch status mismatches
Updates transactions where PayTouch API shows SUCCESS but DB shows FAILED/PENDING
"""

from database import get_db_connection
from paytouch_service import PayTouchService
from wallet_service import WalletService
import json
from datetime import datetime

def fix_paytouch_status_mismatches():
    """Fix PayTouch transactions with status mismatches"""
    
    print("=" * 80)
    print(f"PayTouch Status Mismatch Fix - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch transactions that might have status issues
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, utr, error_message,
                    created_at, updated_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                  AND status IN ('FAILED', 'PENDING', 'QUEUED', 'INPROCESS')
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            problem_txns = cursor.fetchall()
            
            if not problem_txns:
                print("✅ No problematic PayTouch transactions found")
                return
            
            print(f"🔍 Found {len(problem_txns)} potentially problematic transactions")
            print("-" * 80)
            
            paytouch_service = PayTouchService()
            wallet_service = WalletService()
            
            fixed_count = 0
            
            for i, txn in enumerate(problem_txns, 1):
                print(f"\n{i}. Checking {txn['reference_id']}")
                print(f"   Current Status: {txn['status']}")
                print(f"   Created: {txn['created_at']}")
                
                try:
                    # Check PayTouch API status
                    status_result = paytouch_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if not status_result.get('success'):
                        print(f"   ❌ API Error: {status_result.get('message')}")
                        continue
                    
                    api_status = status_result.get('status')
                    api_utr = status_result.get('utr')
                    
                    print(f"   PayTouch API Status: {api_status}")
                    
                    if api_status == txn['status']:
                        print(f"   ✅ Status matches, no fix needed")
                        continue
                    
                    if api_status == 'SUCCESS':
                        print(f"   🔥 MISMATCH: API=SUCCESS, DB={txn['status']}")
                        print(f"   🔧 Fixing transaction...")
                        
                        # Check if wallet was already deducted
                        cursor.execute("""
                            SELECT txn_id FROM merchant_wallet_transactions
                            WHERE reference_id = %s AND txn_type = 'DEBIT'
                        """, (txn['txn_id'],))
                        
                        wallet_already_deducted = cursor.fetchone()
                        
                        if wallet_already_deducted:
                            print(f"   ⚠️  Wallet already deducted, just updating status")
                        else:
                            # Debit wallet for merchant transactions
                            if txn['merchant_id']:
                                total_deduction = float(txn['amount'])
                                
                                print(f"   💰 Debiting merchant wallet: ₹{total_deduction}")
                                debit_result = wallet_service.debit_merchant_wallet(
                                    merchant_id=txn['merchant_id'],
                                    amount=total_deduction,
                                    description=f"Payout - {txn['reference_id']} (Status Fix)",
                                    reference_id=txn['txn_id']
                                )
                                
                                if debit_result['success']:
                                    print(f"   ✅ Wallet debited: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                                else:
                                    print(f"   ❌ Wallet debit failed: {debit_result['message']}")
                                    continue
                        
                        # Update transaction status
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'SUCCESS', 
                                utr = %s, 
                                completed_at = NOW(), 
                                updated_at = NOW(),
                                error_message = NULL
                            WHERE txn_id = %s
                        """, (api_utr, txn['txn_id']))
                        
                        conn.commit()
                        
                        print(f"   ✅ Transaction updated to SUCCESS")
                        print(f"   📝 UTR: {api_utr or 'None'}")
                        
                        fixed_count += 1
                        
                    elif api_status == 'FAILED':
                        print(f"   ❌ PayTouch confirms FAILED, updating DB")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', 
                                completed_at = NOW(), 
                                updated_at = NOW(),
                                error_message = 'Confirmed failed by PayTouch API'
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        
                        conn.commit()
                        fixed_count += 1
                        
                    else:
                        print(f"   📝 Updating to intermediate status: {api_status}")
                        
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (api_status, txn['txn_id']))
                        
                        conn.commit()
                        fixed_count += 1
                
                except Exception as e:
                    print(f"   ❌ Error processing transaction: {e}")
                    continue
            
            print(f"\n" + "=" * 80)
            print(f"FIX COMPLETE")
            print(f"Transactions processed: {len(problem_txns)}")
            print(f"Transactions fixed: {fixed_count}")
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    fix_paytouch_status_mismatches()