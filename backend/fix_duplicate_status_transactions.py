"""
Fix Duplicate Transactions Due to Status Updates
The issue: When status changes from INITIATED/QUEUED to SUCCESS/FAILED,
a new transaction is being created instead of updating the existing one.
"""

import pymysql
from database import get_db_connection
from datetime import datetime, timedelta

def find_duplicate_status_transactions():
    """Find transactions that appear twice with different statuses"""
    print("=" * 80)
    print("Finding Duplicate Status Transactions")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return []
    
    duplicates = []
    
    try:
        with conn.cursor() as cursor:
            # Find transactions with same reference_id but different statuses
            cursor.execute("""
                SELECT 
                    reference_id,
                    COUNT(DISTINCT status) as status_count,
                    COUNT(*) as total_count,
                    GROUP_CONCAT(DISTINCT status ORDER BY status) as statuses,
                    GROUP_CONCAT(DISTINCT txn_id ORDER BY created_at) as txn_ids,
                    MIN(created_at) as first_created,
                    MAX(created_at) as last_created
                FROM payout_transactions
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY reference_id
                HAVING COUNT(*) > 1
                ORDER BY last_created DESC
                LIMIT 50
            """)
            
            results = cursor.fetchall()
            
            if not results:
                print("✓ No duplicate status transactions found")
                return []
            
            print(f"Found {len(results)} reference_ids with multiple entries:")
            print()
            
            for row in results:
                print(f"Reference ID: {row['reference_id']}")
                print(f"  Total Entries: {row['total_count']}")
                print(f"  Statuses: {row['statuses']}")
                print(f"  TxnIDs: {row['txn_ids']}")
                print(f"  First Created: {row['first_created']}")
                print(f"  Last Created: {row['last_created']}")
                
                # Get detailed info
                cursor.execute("""
                    SELECT id, txn_id, status, amount, pg_partner, created_at, updated_at
                    FROM payout_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at ASC
                """, (row['reference_id'],))
                
                details = cursor.fetchall()
                for i, detail in enumerate(details, 1):
                    print(f"    Entry {i}: ID={detail['id']}, TxnID={detail['txn_id']}, "
                          f"Status={detail['status']}, Created={detail['created_at']}")
                
                duplicates.append({
                    'reference_id': row['reference_id'],
                    'details': details
                })
                print()
            
            return duplicates
            
    finally:
        conn.close()

def clean_duplicate_transactions(dry_run=True):
    """Clean duplicate transactions - keep the most recent one"""
    print("=" * 80)
    print("Cleaning Duplicate Transactions")
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
            # Find duplicates
            cursor.execute("""
                SELECT reference_id, COUNT(*) as count
                FROM payout_transactions
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY reference_id
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                print("✓ No duplicates to clean")
                return
            
            print(f"Found {len(duplicates)} reference_ids with duplicates")
            print()
            
            cleaned_count = 0
            
            for dup in duplicates:
                reference_id = dup['reference_id']
                
                # Get all entries for this reference_id
                cursor.execute("""
                    SELECT id, txn_id, status, created_at, updated_at, completed_at
                    FROM payout_transactions
                    WHERE reference_id = %s
                    ORDER BY 
                        CASE 
                            WHEN status IN ('SUCCESS', 'FAILED') THEN 1
                            WHEN status IN ('QUEUED', 'INPROCESS') THEN 2
                            ELSE 3
                        END,
                        updated_at DESC,
                        created_at DESC
                """, (reference_id,))
                
                entries = cursor.fetchall()
                
                if len(entries) <= 1:
                    continue
                
                # Keep the first one (most relevant status, most recent)
                keep_entry = entries[0]
                delete_entries = entries[1:]
                
                print(f"Reference ID: {reference_id}")
                print(f"  Keeping: ID={keep_entry['id']}, TxnID={keep_entry['txn_id']}, "
                      f"Status={keep_entry['status']}")
                print(f"  Deleting {len(delete_entries)} duplicate(s):")
                
                for entry in delete_entries:
                    print(f"    - ID={entry['id']}, TxnID={entry['txn_id']}, "
                          f"Status={entry['status']}")
                    
                    if not dry_run:
                        cursor.execute("DELETE FROM payout_transactions WHERE id = %s", (entry['id'],))
                
                if not dry_run:
                    conn.commit()
                    cleaned_count += 1
                
                print()
            
            if not dry_run:
                print(f"✓ Cleaned {cleaned_count} duplicate reference_ids")
            else:
                print(f"Would clean {len(duplicates)} duplicate reference_ids")
                print()
                print("To actually clean, run:")
                print("  python3 fix_duplicate_status_transactions.py --execute")
            
    finally:
        conn.close()

def check_callback_logic():
    """Check if callback is creating new transactions instead of updating"""
    print()
    print("=" * 80)
    print("Checking Callback Logic")
    print("=" * 80)
    print()
    
    print("The issue is likely in the callback handling:")
    print()
    print("❌ WRONG (creates duplicate):")
    print("""
    # In callback handler
    cursor.execute('''
        INSERT INTO payout_transactions (...)
        VALUES (...)
    ''')
    """)
    print()
    
    print("✅ CORRECT (updates existing):")
    print("""
    # In callback handler
    cursor.execute('''
        UPDATE payout_transactions
        SET status = %s, utr = %s, completed_at = NOW()
        WHERE pg_txn_id = %s OR reference_id = %s
    ''', (status, utr, pg_txn_id, reference_id))
    """)
    print()
    
    print("Files to check:")
    print("  - backend/paytouch_callback_routes.py")
    print("  - backend/mudrape_callback_routes.py")
    print("  - backend/tourquest_callback_routes.py")
    print()

def add_unique_constraints():
    """Provide SQL to add unique constraints"""
    print()
    print("=" * 80)
    print("Preventing Future Duplicates")
    print("=" * 80)
    print()
    
    print("Add UNIQUE constraints to prevent duplicates:")
    print()
    print("SQL Commands:")
    print()
    print("-- Add unique constraint on txn_id")
    print("ALTER TABLE payout_transactions ADD UNIQUE KEY unique_txn_id (txn_id);")
    print()
    print("-- Add unique constraint on reference_id")
    print("ALTER TABLE payout_transactions ADD UNIQUE KEY unique_reference_id (reference_id);")
    print()
    print("-- Add unique constraint on order_id (for merchant payouts)")
    print("ALTER TABLE payout_transactions ADD UNIQUE KEY unique_order_id (merchant_id, order_id);")
    print()
    
    print("⚠️  Before adding constraints, clean existing duplicates first!")
    print()

if __name__ == '__main__':
    import sys
    
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Fix Duplicate Status Transactions" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Find duplicates
    duplicates = find_duplicate_status_transactions()
    
    # Check callback logic
    check_callback_logic()
    
    # Show how to prevent future duplicates
    add_unique_constraints()
    
    # Clean duplicates
    if '--execute' in sys.argv:
        print()
        response = input("Are you sure you want to delete duplicate transactions? (yes/no): ")
        if response.lower() == 'yes':
            clean_duplicate_transactions(dry_run=False)
        else:
            print("Cancelled")
    else:
        clean_duplicate_transactions(dry_run=True)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Root Cause:")
    print("  When transaction status changes (INITIATED → SUCCESS/FAILED),")
    print("  the system is creating a NEW transaction instead of UPDATING")
    print("  the existing one.")
    print()
    print("Solution:")
    print("  1. Clean existing duplicates (run with --execute)")
    print("  2. Fix callback handlers to UPDATE instead of INSERT")
    print("  3. Add UNIQUE constraints to prevent future duplicates")
    print()
    print("Next Steps:")
    print("  1. Run: python3 fix_duplicate_status_transactions.py --execute")
    print("  2. Check callback files for INSERT statements")
    print("  3. Add UNIQUE constraints to database")
    print()
