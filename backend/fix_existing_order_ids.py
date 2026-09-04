#!/usr/bin/env python3
"""
Fix existing Mudrape transactions to use ref_id as order_id
This will allow callbacks to find the transactions
"""

from database import get_db_connection

def fix_order_ids():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("FIXING MUDRAPE TRANSACTION ORDER IDs")
            print("=" * 80)
            print()
            
            # Find Mudrape transactions where order_id doesn't match the pattern
            # Mudrape ref_id is 20 digits starting with timestamp
            cursor.execute("""
                SELECT txn_id, order_id, pg_txn_id, created_at
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                AND LENGTH(order_id) != 20
                ORDER BY created_at DESC
            """)
            
            txns_to_fix = cursor.fetchall()
            
            if not txns_to_fix:
                print("✓ No transactions need fixing!")
                return
            
            print(f"Found {len(txns_to_fix)} transactions to fix:\n")
            
            for txn in txns_to_fix:
                print(f"TXN: {txn['txn_id']}")
                print(f"  Current order_id: {txn['order_id']}")
                print(f"  Created: {txn['created_at']}")
                
                # Extract the ref_id from txn_id
                # Format: MUDRAPE_{merchant_id}_{original_orderid}_{timestamp}
                # We need to generate a new 20-digit ref_id based on the timestamp
                created_str = txn['created_at'].strftime('%Y%m%d%H%M%S')  # 14 digits
                
                # Get last 6 digits from original order_id as random part
                original_order = str(txn['order_id'])
                random_part = original_order[-6:].zfill(6)  # Last 6 digits, pad if needed
                
                new_ref_id = f"{created_str}{random_part}"  # 20 digits total
                
                print(f"  New ref_id: {new_ref_id}")
                print(f"  → This transaction cannot be fixed automatically")
                print(f"  → The ref_id sent to Mudrape is unknown")
                print(f"  → Callbacks will continue to fail for this transaction")
                print()
            
            print("=" * 80)
            print("IMPORTANT NOTE")
            print("=" * 80)
            print()
            print("These existing transactions CANNOT be fixed because:")
            print("  1. The ref_id sent to Mudrape is not stored")
            print("  2. We cannot determine what ref_id was used")
            print("  3. Mudrape callbacks will use the original ref_id")
            print()
            print("Solutions:")
            print("  1. Manually trigger callbacks using trigger_missed_callbacks.py")
            print("  2. New transactions will work correctly with the fix applied")
            print("  3. For existing transactions, use manual status polling")
            print()
            print("The fix has been applied to mudrape_service.py")
            print("All NEW transactions will store ref_id correctly")
            
    finally:
        conn.close()

if __name__ == '__main__':
    fix_order_ids()
