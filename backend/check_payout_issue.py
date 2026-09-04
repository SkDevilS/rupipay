#!/usr/bin/env python3
"""
Quick check to confirm the payout disappearance issue
"""

from database import get_db_connection

def check_issue():
    print("=" * 80)
    print("CHECKING PAYOUT DISAPPEARANCE ISSUE")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check for payouts where merchant_id is not in merchants table
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.order_id,
                    pt.amount,
                    pt.status,
                    pt.created_at,
                    m.merchant_id as actual_merchant_id,
                    m.full_name
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id IS NOT NULL
                AND m.merchant_id IS NULL
                ORDER BY pt.created_at DESC
                LIMIT 20
            """)
            orphaned_payouts = cursor.fetchall()
            
            if orphaned_payouts:
                print(f"\n🔍 ISSUE CONFIRMED!")
                print(f"Found {len(orphaned_payouts)} payout records with invalid merchant_id:")
                print("=" * 80)
                
                for payout in orphaned_payouts:
                    print(f"\nTXN ID: {payout['txn_id']}")
                    print(f"merchant_id in DB: {payout['merchant_id']}")
                    print(f"Order ID: {payout['order_id']}")
                    print(f"Amount: ₹{payout['amount']:.2f}")
                    print(f"Status: {payout['status']}")
                    print(f"Created: {payout['created_at']}")
                    print(f"Merchant Found: {payout['actual_merchant_id']}")
                    print(f"Merchant Name: {payout['full_name']}")
                    print("-" * 80)
                
                print(f"\n💡 ROOT CAUSE:")
                print(f"These records have admin_id (like 'admin') stored in merchant_id field.")
                print(f"When report queries join with merchants table, these records return NULL.")
                print(f"Frontend filters out or doesn't display records with NULL merchant data.")
                print(f"\n✅ SOLUTION:")
                print(f"Run: python backend/fix_payout_admin_id.py")
                print(f"This will add admin_id column and migrate the data properly.")
                
            else:
                print(f"\n✅ No orphaned payout records found")
                print(f"The issue may be something else. Check:")
                print(f"1. Transaction isolation/commit issues")
                print(f"2. Connection pooling problems")
                print(f"3. Frontend filtering logic")
            
            # Show total payout counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN m.merchant_id IS NOT NULL THEN 1 ELSE 0 END) as valid_merchant,
                    SUM(CASE WHEN m.merchant_id IS NULL AND pt.merchant_id IS NOT NULL THEN 1 ELSE 0 END) as invalid_merchant,
                    SUM(CASE WHEN pt.merchant_id IS NULL THEN 1 ELSE 0 END) as null_merchant
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
            """)
            stats = cursor.fetchone()
            
            print(f"\n📊 PAYOUT STATISTICS:")
            print(f"Total Payouts: {stats['total']}")
            print(f"Valid Merchant Payouts: {stats['valid_merchant']}")
            print(f"Invalid Merchant ID (Admin Payouts): {stats['invalid_merchant']}")
            print(f"NULL Merchant ID: {stats['null_merchant']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    check_issue()
