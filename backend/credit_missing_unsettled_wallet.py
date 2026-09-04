"""
Credit missing unsettled wallet amounts for successful payins
that didn't receive callbacks
"""

import pymysql
from database import get_db_connection
from wallet_service import wallet_service

def credit_missing_payins():
    """Credit unsettled wallet for payins that are missing wallet credits"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("CREDITING MISSING UNSETTLED WALLET AMOUNTS")
            print("=" * 80)
            
            # Find all successful payins without wallet credits
            cursor.execute("""
                SELECT 
                    p.txn_id, p.merchant_id, p.order_id, p.amount, 
                    p.charge_amount, p.net_amount, p.completed_at
                FROM payin_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON p.txn_id = mwt.reference_id 
                    AND mwt.txn_type = 'UNSETTLED_CREDIT'
                WHERE p.status = 'SUCCESS' 
                AND mwt.txn_id IS NULL
                ORDER BY p.completed_at DESC
            """)
            
            missing_payins = cursor.fetchall()
            
            if not missing_payins:
                print("\n✅ No missing wallet credits found!")
                return
            
            print(f"\nFound {len(missing_payins)} payins without wallet credits\n")
            
            total_credited = 0
            success_count = 0
            fail_count = 0
            
            for payin in missing_payins:
                print(f"\n{'='*70}")
                print(f"Processing: {payin['txn_id']}")
                print(f"Merchant: {payin['merchant_id']}")
                print(f"Net Amount: ₹{payin['net_amount']}")
                print(f"Charge: ₹{payin['charge_amount']}")
                print(f"Completed: {payin['completed_at']}")
                
                # Credit merchant unsettled wallet
                merchant_result = wallet_service.credit_unsettled_wallet(
                    merchant_id=payin['merchant_id'],
                    amount=float(payin['net_amount']),
                    description=f"Payin credited (backfill) - {payin['order_id']}",
                    reference_id=payin['txn_id']
                )
                
                if merchant_result['success']:
                    print(f"✅ Merchant wallet credited: ₹{payin['net_amount']}")
                    
                    # Credit admin unsettled wallet with charge
                    admin_result = wallet_service.credit_admin_unsettled_wallet(
                        admin_id='admin',
                        amount=float(payin['charge_amount']),
                        description=f"Payin charge (backfill) - {payin['order_id']}",
                        reference_id=payin['txn_id']
                    )
                    
                    if admin_result['success']:
                        print(f"✅ Admin wallet credited: ₹{payin['charge_amount']}")
                        total_credited += float(payin['net_amount'])
                        success_count += 1
                    else:
                        print(f"❌ Admin wallet credit failed: {admin_result.get('message')}")
                        fail_count += 1
                else:
                    print(f"❌ Merchant wallet credit failed: {merchant_result.get('message')}")
                    fail_count += 1
            
            print(f"\n{'='*80}")
            print(f"SUMMARY")
            print(f"{'='*80}")
            print(f"Total Payins Processed: {len(missing_payins)}")
            print(f"Successfully Credited: {success_count}")
            print(f"Failed: {fail_count}")
            print(f"Total Amount Credited: ₹{total_credited:.2f}")
            print(f"{'='*80}")
            
            # Show updated wallet balances
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(unsettled_balance), 0) as total_unsettled
                FROM merchant_wallet
            """)
            
            total = cursor.fetchone()
            print(f"\nNew Total Unsettled (All Merchants): ₹{total['total_unsettled']}")
            print("=" * 80)
            
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n⚠ WARNING: This will credit unsettled wallet for all successful payins")
    print("that don't have wallet transaction records.")
    print("\nThis should be run ONCE to fix missing credits.")
    
    response = input("\nDo you want to continue? (yes/no): ")
    
    if response.lower() == 'yes':
        credit_missing_payins()
    else:
        print("\nOperation cancelled.")
