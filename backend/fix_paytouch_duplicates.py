"""
Fix PayTouch Duplicate Transactions
Cleans up duplicate PayTouch transactions and adds UNIQUE constraints
"""

import pymysql
from database import get_db_connection
from datetime import datetime

def find_paytouch_duplicates():
    """Find duplicate PayTouch transactions"""
    print("=" * 80)
    print("Finding PayTouch Duplicate Transactions")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return []
    
    duplicates = []
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch transactions with same reference_id
            cursor.execute("""
                SELECT 
                    reference_id,
                    COUNT(*) as count,
                    GROUP_CONCAT(DISTINCT status ORDER BY status) as statuses,
                    GROUP_CONCAT(DISTINCT txn_id ORDER BY created_at) as txn_ids,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY reference_id
                HAVING COUNT(*) > 1
                ORDER BY last_created DESC
            """)
            
            results = cursor.fetchall()
            
            if not results:
                print("✓ No PayTouch duplicate transactions found")
                return []
            
            print(f"Found {len(results)} PayTouch reference_ids with duplicates:")
            print()
            
            for row in results:
                print(f"Reference ID: {row['reference_id']}")
                print(f"  Count: {row['count']}")
                print(f"  Statuses: {row['statuses']}")
                print(f"  TxnIDs: {row['txn_ids']}")
                print(f"  First: {row['first_created']}")
                print(f"  Last: {row['last_created']}")
                
                # Get detailed info
                cursor.execute("""
                    SELECT id, txn_id, status, amount, created_at, updated_at, pg_txn_id, utr
                    FROM payout_transactions
                    WHERE reference_id = %s AND pg_partner = 'PayTouch'
                    ORDER BY created_at ASC
                """, (row['reference_id'],))
                
                details = cursor.fetchall()
                for i, detail in enumerate(details, 1):
                    print(f"    Entry {i}: ID={detail['id']}, TxnID={detail['txn_id']}, "
                          f"Status={detail['status']}, UTR={detail['utr']}, Created={detail['created_at']}")
                
                duplicates.append({
                    'reference_id': row['reference_id'],
                    'details': details
                })
                print()
            
            return duplicates
            
    finally:
        conn.close()

def clean_paytouch_duplicates(dry_run=True):
    """Clean PayTouch duplicate transactions"""
    print("=" * 80)
    print("Cleaning PayTouch Duplicate Transactions")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch duplicates
            cursor.execute("""
                SELECT reference_id, COUNT(*) as count
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY reference_id
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                print("✓ No PayTouch duplicates to clean")
                return
            
            print(f"Found {len(duplicates)} PayTouch reference_ids with duplicates")
            print()
            
            cleaned_count = 0
            
            for dup in duplicates:
                reference_id = dup['reference_id']
                
                # Get all entries for this reference_id
                cursor.execute("""
                    SELECT id, txn_id, status, created_at, updated_at, completed_at, pg_txn_id, utr
                    FROM payout_transactions
                    WHERE reference_id = %s AND pg_partner = 'PayTouch'
                    ORDER BY 
                        CASE 
                            WHEN status IN ('SUCCESS', 'FAILED') THEN 1
                            WHEN status IN ('QUEUED', 'INPROCESS') THEN 2
                            ELSE 3
                        END,
                        CASE WHEN pg_txn_id IS NOT NULL THEN 1 ELSE 2 END,
                        CASE WHEN utr IS NOT NULL THEN 1 ELSE 2 END,
                        updated_at DESC,
                        created_at ASC
                """, (reference_id,))
                
                entries = cursor.fetchall()
                
                if len(entries) <= 1:
                    continue
                
                # Keep the first one (most complete status)
                keep_entry = entries[0]
                delete_entries = entries[1:]
                
                print(f"Reference ID: {reference_id}")
                print(f"  Keeping: ID={keep_entry['id']}, TxnID={keep_entry['txn_id']}, "
                      f"Status={keep_entry['status']}, UTR={keep_entry['utr']}")
                print(f"  Deleting {len(delete_entries)} duplicate(s):")
                
                for entry in delete_entries:
                    print(f"    - ID={entry['id']}, TxnID={entry['txn_id']}, "
                          f"Status={entry['status']}, UTR={entry['utr']}")
                    
                    if not dry_run:
                        cursor.execute("DELETE FROM payout_transactions WHERE id = %s", (entry['id'],))
                
                if not dry_run:
                    conn.commit()
                    cleaned_count += 1
                
                print()
            
            if not dry_run:
                print(f"✓ Cleaned {cleaned_count} PayTouch duplicate reference_ids")
            else:
                print(f"Would clean {len(duplicates)} PayTouch duplicate reference_ids")
                print()
                print("To actually clean, run:")
                print("  python3 backend/fix_paytouch_duplicates.py --execute")
            
    finally:
        conn.close()

def add_unique_constraints():
    """Add UNIQUE constraints to prevent future duplicates"""
    print()
    print("=" * 80)
    print("Adding UNIQUE Constraints")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if constraints already exist
            cursor.execute("""
                SELECT CONSTRAINT_NAME 
                FROM information_schema.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payout_transactions'
                AND CONSTRAINT_TYPE = 'UNIQUE'
            """)
            
            existing_constraints = [row['CONSTRAINT_NAME'] for row in cursor.fetchall()]
            print(f"Existing UNIQUE constraints: {existing_constraints}")
            print()
            
            # Add unique constraint on reference_id if not exists
            if 'unique_reference_id' not in existing_constraints:
                print("Adding UNIQUE constraint on reference_id...")
                try:
                    cursor.execute("""
                        ALTER TABLE payout_transactions 
                        ADD UNIQUE KEY unique_reference_id (reference_id)
                    """)
                    conn.commit()
                    print("✓ Added unique_reference_id constraint")
                except pymysql.err.IntegrityError as e:
                    print(f"❌ Cannot add constraint - duplicates exist: {e}")
                    print("   Run cleanup first: python3 backend/fix_paytouch_duplicates.py --execute")
            else:
                print("✓ unique_reference_id constraint already exists")
            
            print()
            
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Fix PayTouch Duplicate Transactions" + " " * 23 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Find duplicates
    duplicates = find_paytouch_duplicates()
    
    if duplicates:
        print()
        print("=" * 80)
        print("ROOT CAUSE")
        print("=" * 80)
        print()
        print("PayTouch service was creating duplicate INSERT statements:")
        print("  1. payout_routes.py creates transaction with INSERT")
        print("  2. paytouch_service.py creates ANOTHER INSERT (duplicate)")
        print()
        print("FIX APPLIED:")
        print("  - paytouch_service.py now checks if transaction exists first")
        print("  - Only creates INSERT if transaction doesn't exist")
        print()
        
        # Clean duplicates
        if '--execute' in sys.argv:
            print()
            response = input("Delete duplicate PayTouch transactions? (yes/no): ")
            if response.lower() == 'yes':
                clean_paytouch_duplicates(dry_run=False)
                print()
                add_unique_constraints()
            else:
                print("Cancelled")
        else:
            clean_paytouch_duplicates(dry_run=True)
    else:
        print()
        print("✓ No duplicates found - checking constraints...")
        add_unique_constraints()
    
    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Clean existing duplicates:")
    print("   python3 backend/fix_paytouch_duplicates.py --execute")
    print()
    print("2. Deploy fixed code:")
    print("   sudo systemctl restart moneyone_backend")
    print()
    print("3. Test PayTouch payout - should create only 1 transaction")
    print()
