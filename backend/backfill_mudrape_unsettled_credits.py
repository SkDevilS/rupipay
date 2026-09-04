#!/usr/bin/env python3
"""
Backfill missing unsettled wallet credits for Mudrape payins
This script credits the unsettled wallet for payins that were marked SUCCESS
but didn't get wallet credits due to the idempotency bug
"""

import sys
sys.path.insert(0, '/home/ubuntu/moneyone/backend')

from database import get_db_connection
from wallet_service import wallet_service
from datetime import datetime

def backfill_mudrape_credits():
    """Backfill missing unsettled wallet credits"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find all Mudrape payins with SUCCESS status that don't have wallet credits
            cursor.execute("""
                SELECT 
                    pt.txn_id, pt.merchant_id, pt.order_id, pt.net_amount, pt.charge_amount,
                    pt.created_at, pt.completed_at
                FROM payin_transactions pt
                WHERE pt.pg_partner = 'Mudrape'
                AND pt.status = 'SUCCESS'
                AND pt.txn_id NOT IN (
                    SELECT reference_id FROM merchant_wallet_transactions 
                    WHERE txn_type = 'UNSETTLED_CREDIT'
                )
                ORDER BY pt.created_at DESC
            """)
            
            missing_credits = cursor.fetchall()
            
            if not missing_credits:
                print("✅ No missing credits found - all payins have been credited")
                return
            
            print(f"\n🔄 Found {len(missing_credits)} payins with missing unsettled credits")
            print("=" * 100)
            
            credited_count = 0
            failed_count = 0
            
            for payin in missing_credits:
                txn_id = payin['txn_id']
                merchant_id = payin['merchant_id']
                net_amount = float(payin['net_amount'])
                charge_amount = float(payin['charge_amount'])
                order_id = payin['order_id']
                
                print(f"\nProcessing: {txn_id}")
                print(f"  Merchant: {merchant_id}")
                print(f"  Order ID: {order_id}")
                print(f"  Net Amount: ₹{net_amount:.2f}")
                print(f"  Charge Amount: ₹{charge_amount:.2f}")
                
                try:
                    # Credit merchant unsettled wallet
                    merchant_result = wallet_service.credit_unsettled_wallet(
                        merchant_id=merchant_id,
                        amount=net_amount,
                        description=f"Backfill: Payin credited to unsettled wallet - {order_id}",
                        reference_id=txn_id
                    )
                    
                    if merchant_result['success']:
                        print(f"  ✓ Merchant unsettled wallet credited: ₹{net_amount:.2f}")
                    else:
                        print(f"  ❌ Failed to credit merchant wallet: {merchant_result.get('message')}")
                        failed_count += 1
                        continue
                    
                    # Credit admin unsettled wallet
                    admin_result = wallet_service.credit_admin_unsettled_wallet(
                        admin_id='admin',
                        amount=charge_amount,
                        description=f"Backfill: Payin charge - {order_id}",
                        reference_id=txn_id
                    )
                    
                    if admin_result['success']:
                        print(f"  ✓ Admin unsettled wallet credited: ₹{charge_amount:.2f}")
                        credited_count += 1
                    else:
                        print(f"  ❌ Failed to credit admin wallet: {admin_result.get('message')}")
                        failed_count += 1
                
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    failed_count += 1
            
            print("\n" + "=" * 100)
            print(f"✅ Backfill Complete:")
            print(f"   Successfully credited: {credited_count}")
            print(f"   Failed: {failed_count}")
            print(f"   Total: {len(missing_credits)}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n🔄 Backfilling Missing Mudrape Unsettled Credits")
    print("=" * 100)
    
    backfill_mudrape_credits()
    
    print("\n✅ Backfill process complete")
