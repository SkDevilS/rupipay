#!/usr/bin/env python3
"""
Check orphaned payout records in detail
"""

from database import get_db_connection

def check_orphaned_payouts():
    print("=" * 80)
    print("CHECKING ORPHANED PAYOUT RECORDS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get orphaned payouts with details
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.order_id,
                    pt.amount,
                    pt.status,
                    pt.bene_name,
                    pt.created_at,
                    m.merchant_id as actual_merchant_id
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id IS NOT NULL
                AND pt.merchant_id != ''
                AND m.merchant_id IS NULL
                ORDER BY pt.created_at DESC
            """)
            orphaned = cursor.fetchall()
            
            if orphaned:
                print(f"\n🔍 Found {len(orphaned)} orphaned payout records:")
                print("=" * 80)
                
                # Group by merchant_id to see patterns
                merchant_ids = {}
                for payout in orphaned:
                    mid = payout['merchant_id']
                    if mid not in merchant_ids:
                        merchant_ids[mid] = []
                    merchant_ids[mid].append(payout)
                
                print(f"\n📊 Orphaned payouts grouped by merchant_id:")
                for mid, payouts in merchant_ids.items():
                    print(f"\n  merchant_id: '{mid}' - {len(payouts)} payouts")
                    print(f"  First payout: {payouts[-1]['created_at']}")
                    print(f"  Last payout: {payouts[0]['created_at']}")
                    print(f"  Sample beneficiary: {payouts[0]['bene_name']}")
                
                print("\n" + "=" * 80)
                print("📋 Recent 10 orphaned payouts:")
                print("=" * 80)
                
                for payout in orphaned[:10]:
                    print(f"\nTXN ID: {payout['txn_id']}")
                    print(f"merchant_id: '{payout['merchant_id']}'")
                    print(f"Order ID: {payout['order_id']}")
                    print(f"Amount: ₹{payout['amount']:.2f}")
                    print(f"Status: {payout['status']}")
                    print(f"Beneficiary: {payout['bene_name']}")
                    print(f"Created: {payout['created_at']}")
                    print("-" * 80)
                
                print(f"\n💡 ANALYSIS:")
                print(f"These {len(orphaned)} records have merchant_id values that don't exist in merchants table.")
                print(f"This causes LEFT JOIN to return NULL, making them invisible in reports.")
                print(f"\n✅ SOLUTION:")
                print(f"1. If these are admin personal payouts: Run migration to add admin_id column")
                print(f"2. If these are test/invalid records: Clean them up or fix merchant_id")
                
            else:
                print(f"\n✅ No orphaned payout records found")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_orphaned_payouts()
