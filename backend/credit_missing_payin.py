#!/usr/bin/env python3
"""
Credit wallet for payin transactions that were marked SUCCESS but wallet was not credited
This is a one-time fix for transactions that happened before the unsettled wallet fix was deployed
"""

import pymysql
from database import get_db_connection
from wallet_service import wallet_service

def credit_missing_payin(txn_id):
    """Credit wallet for a specific payin that was missed"""
    
    print("=" * 80)
    print(f"Crediting Missing PayIn: {txn_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get payin details
            cursor.execute("""
                SELECT * FROM payin_transactions WHERE txn_id = %s
            """, (txn_id,))
            
            payin = cursor.fetchone()
            
            if not payin:
                print(f"❌ PayIn {txn_id} not found")
                return False
            
            if payin['status'] != 'SUCCESS':
                print(f"❌ PayIn status is {payin['status']}, not SUCCESS")
                return False
            
            print(f"\nPayIn Details:")
            print(f"  Merchant: {payin['merchant_id']}")
            print(f"  Amount: ₹{payin['amount']}")
            print(f"  Charge: ₹{payin['charge_amount']}")
            print(f"  Net: ₹{payin['net_amount']}")
            
            # Check if already credited
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                WHERE reference_id = %s
            """, (txn_id,))
            
            if cursor.fetchone()['count'] > 0:
                print(f"\n⚠️  This payin was already credited to merchant wallet")
                return False
            
            # Credit merchant unsettled wallet
            print(f"\nCrediting merchant unsettled wallet...")
            merchant_result = wallet_service.credit_unsettled_wallet(
                merchant_id=payin['merchant_id'],
                amount=float(payin['net_amount']),
                description=f"PayIn received (Backfill) - {payin['order_id']}",
                reference_id=txn_id
            )
            
            if merchant_result['success']:
                print(f"✓ Merchant unsettled wallet credited: ₹{payin['net_amount']}")
                print(f"  Unsettled before: ₹{merchant_result['unsettled_before']}")
                print(f"  Unsettled after: ₹{merchant_result['unsettled_after']}")
            else:
                print(f"❌ Failed to credit merchant wallet: {merchant_result.get('message')}")
                return False
            
            # Credit admin unsettled wallet
            print(f"\nCrediting admin unsettled wallet...")
            admin_result = wallet_service.credit_admin_unsettled_wallet(
                admin_id='admin',
                amount=float(payin['charge_amount']),
                description=f"PayIn charge (Backfill) - {payin['order_id']}",
                reference_id=txn_id
            )
            
            if admin_result['success']:
                print(f"✓ Admin unsettled wallet credited: ₹{payin['charge_amount']}")
                print(f"  Unsettled before: ₹{admin_result['unsettled_before']}")
                print(f"  Unsettled after: ₹{admin_result['unsettled_after']}")
            else:
                print(f"❌ Failed to credit admin wallet: {admin_result.get('message')}")
                return False
            
            print(f"\n✅ Successfully credited wallets for payin {txn_id}")
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def credit_all_missing_payins():
    """Credit all SUCCESS payins that don't have wallet transactions"""
    
    print("=" * 80)
    print("Finding All Missing PayIn Credits")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS payins without wallet transactions
            cursor.execute("""
                SELECT pt.txn_id, pt.merchant_id, pt.amount, pt.charge_amount, pt.net_amount, pt.order_id
                FROM payin_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON pt.txn_id = mwt.reference_id
                WHERE pt.status = 'SUCCESS'
                AND mwt.id IS NULL
                ORDER BY pt.created_at DESC
            """)
            
            missing_payins = cursor.fetchall()
            
            if not missing_payins:
                print("\n✓ No missing payin credits found")
                return
            
            print(f"\nFound {len(missing_payins)} payins without wallet credits:")
            for payin in missing_payins:
                print(f"  - {payin['txn_id']}: ₹{payin['amount']} (Net: ₹{payin['net_amount']})")
            
            print(f"\n" + "=" * 80)
            response = input(f"Credit all {len(missing_payins)} missing payins? (yes/no): ")
            
            if response.lower() != 'yes':
                print("Cancelled")
                return
            
            success_count = 0
            fail_count = 0
            
            for payin in missing_payins:
                print(f"\n" + "-" * 80)
                if credit_missing_payin(payin['txn_id']):
                    success_count += 1
                else:
                    fail_count += 1
            
            print(f"\n" + "=" * 80)
            print(f"SUMMARY")
            print(f"=" * 80)
            print(f"  Successfully credited: {success_count}")
            print(f"  Failed: {fail_count}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            credit_all_missing_payins()
        else:
            credit_missing_payin(sys.argv[1])
    else:
        print("Usage:")
        print("  python3 credit_missing_payin.py <txn_id>  - Credit specific transaction")
        print("  python3 credit_missing_payin.py --all     - Credit all missing transactions")
        print("")
        print("Example:")
        print("  python3 credit_missing_payin.py MUDRAPE_7679022140_ORD1772483055064984_20260303015416")
