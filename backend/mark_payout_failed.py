#!/usr/bin/env python3
"""
Script to mark payout transactions as failed by reference ID
Usage: python mark_payout_failed.py <ref_id_1> <ref_id_2>
"""

import sys
import pymysql
from database_pooled import get_db_connection

def mark_payout_as_failed(reference_id):
    """Mark a payout transaction as failed by reference ID"""
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Check if payout exists by reference ID
        cursor.execute("""
            SELECT id, merchant_id, order_id, reference_id, status, amount, pg_txn_id
            FROM payout_transactions
            WHERE reference_id = %s
        """, (reference_id,))
        
        payout = cursor.fetchone()
        
        if not payout:
            print(f"❌ Payout with reference_id {reference_id} not found")
            return False
        
        print(f"\n📋 Found payout:")
        print(f"   ID: {payout['id']}")
        print(f"   Merchant ID: {payout['merchant_id']}")
        print(f"   Order ID: {payout['order_id']}")
        print(f"   Reference ID: {payout['reference_id']}")
        print(f"   Current Status: {payout['status']}")
        print(f"   Amount: {payout['amount']}")
        print(f"   PG Txn ID: {payout['pg_txn_id']}")
        
        if payout['status'] == 'FAILED':
            print(f"⚠️  Payout is already marked as failed")
            return True
        
        # Update status to failed
        cursor.execute("""
            UPDATE payout_transactions
            SET status = 'FAILED',
                updated_at = NOW()
            WHERE reference_id = %s
        """, (reference_id,))
        
        connection.commit()
        print(f"✅ Successfully marked payout {reference_id} as failed")
        
        # Verify the update
        cursor.execute("""
            SELECT status, updated_at
            FROM payout_transactions
            WHERE reference_id = %s
        """, (reference_id,))
        
        updated = cursor.fetchone()
        print(f"   New Status: {updated['status']}")
        print(f"   Updated At: {updated['updated_at']}")
        
        return True
        
    except Exception as e:
        connection.rollback()
        print(f"❌ Error marking payout {reference_id} as failed: {str(e)}")
        return False
        
    finally:
        cursor.close()
        connection.close()

def main():
    if len(sys.argv) < 3:
        print("Usage: python mark_payout_failed.py <reference_id_1> <reference_id_2>")
        print("Example: python mark_payout_failed.py DP20260324225039E80736 DP202603242250112EA787")
        sys.exit(1)
    
    reference_id_1 = sys.argv[1]
    reference_id_2 = sys.argv[2]
    
    print("=" * 60)
    print("MARK PAYOUT TRANSACTIONS AS FAILED (BY REFERENCE ID)")
    print("=" * 60)
    
    print(f"\n🔄 Processing Reference ID 1: {reference_id_1}")
    success_1 = mark_payout_as_failed(reference_id_1)
    
    print(f"\n🔄 Processing Reference ID 2: {reference_id_2}")
    success_2 = mark_payout_as_failed(reference_id_2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Reference ID 1 ({reference_id_1}): {'✅ Success' if success_1 else '❌ Failed'}")
    print(f"Reference ID 2 ({reference_id_2}): {'✅ Success' if success_2 else '❌ Failed'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
