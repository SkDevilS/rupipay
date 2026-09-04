"""
Fix Duplicate Payout Report Issue
Identifies and fixes the root cause of duplicate transactions in reports
"""

import pymysql
from database import get_db_connection

def check_merchant_duplicates():
    """Check if merchants table has duplicate merchant_id entries"""
    print("=" * 80)
    print("Checking for Duplicate Merchant IDs")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check for duplicate merchant_id
            cursor.execute("""
                SELECT merchant_id, COUNT(*) as count
                FROM merchants
                GROUP BY merchant_id
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicate merchant_id entries:")
                for dup in duplicates:
                    print(f"   - Merchant ID: {dup['merchant_id']}, Count: {dup['count']}")
                    
                    # Show details
                    cursor.execute("""
                        SELECT id, merchant_id, full_name, email, is_active, created_at
                        FROM merchants
                        WHERE merchant_id = %s
                    """, (dup['merchant_id'],))
                    
                    details = cursor.fetchall()
                    for detail in details:
                        print(f"     DB ID: {detail['id']}, Name: {detail['full_name']}, "
                              f"Active: {detail['is_active']}, Created: {detail['created_at']}")
                
                print()
                print("⚠️  This is causing duplicate rows in payout report!")
                print("   The LEFT JOIN with merchants table multiplies rows")
                return True
            else:
                print("✓ No duplicate merchant_id found in merchants table")
                return False
    finally:
        conn.close()

def check_payout_duplicates():
    """Check if payout_transactions table has actual duplicates"""
    print()
    print("=" * 80)
    print("Checking for Duplicate Payout Transactions")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check for duplicate txn_id
            cursor.execute("""
                SELECT txn_id, COUNT(*) as count
                FROM payout_transactions
                GROUP BY txn_id
                HAVING COUNT(*) > 1
                LIMIT 10
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicate txn_id entries:")
                for dup in duplicates:
                    print(f"   - TxnID: {dup['txn_id']}, Count: {dup['count']}")
                
                print()
                print("⚠️  Payout transactions table has duplicate entries!")
                return True
            else:
                print("✓ No duplicate txn_id found in payout_transactions table")
                return False
    finally:
        conn.close()

def fix_report_query():
    """Provide fixed query for payout report"""
    print()
    print("=" * 80)
    print("SOLUTION: Fixed Payout Report Query")
    print("=" * 80)
    print()
    
    print("The issue is likely caused by:")
    print("1. Duplicate merchant_id in merchants table")
    print("2. Missing DISTINCT in SELECT query")
    print()
    
    print("Fixed Query (add DISTINCT):")
    print()
    print("""
SELECT DISTINCT
    pt.id,
    pt.txn_id,
    pt.merchant_id,
    pt.reference_id,
    pt.order_id,
    pt.amount,
    pt.charge_amount,
    pt.status,
    pt.pg_partner,
    pt.created_at,
    m.full_name,
    m.mobile
FROM payout_transactions pt
LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
WHERE 1=1
    """)
    print()
    
    print("OR use subquery to get unique merchant data:")
    print()
    print("""
SELECT 
    pt.*,
    (SELECT full_name FROM merchants WHERE merchant_id = pt.merchant_id LIMIT 1) as full_name,
    (SELECT mobile FROM merchants WHERE merchant_id = pt.merchant_id LIMIT 1) as mobile
FROM payout_transactions pt
WHERE 1=1
    """)
    print()

def clean_duplicate_merchants():
    """Clean duplicate merchant entries (keep most recent)"""
    print()
    print("=" * 80)
    print("Cleaning Duplicate Merchants")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find duplicates
            cursor.execute("""
                SELECT merchant_id, COUNT(*) as count
                FROM merchants
                GROUP BY merchant_id
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                print("✓ No duplicates to clean")
                return
            
            print(f"Found {len(duplicates)} duplicate merchant_id entries")
            print()
            
            for dup in duplicates:
                merchant_id = dup['merchant_id']
                
                # Get all entries for this merchant_id
                cursor.execute("""
                    SELECT id, merchant_id, full_name, is_active, created_at
                    FROM merchants
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                """, (merchant_id,))
                
                entries = cursor.fetchall()
                
                # Keep the most recent one
                keep_id = entries[0]['id']
                delete_ids = [e['id'] for e in entries[1:]]
                
                print(f"Merchant ID: {merchant_id}")
                print(f"  Keeping DB ID: {keep_id} (most recent)")
                print(f"  Deleting DB IDs: {delete_ids}")
                
                # NOTE: Don't actually delete without user confirmation
                # Uncomment below to execute deletion
                # for delete_id in delete_ids:
                #     cursor.execute("DELETE FROM merchants WHERE id = %s", (delete_id,))
                # conn.commit()
                # print(f"  ✓ Deleted {len(delete_ids)} duplicate entries")
                
            print()
            print("⚠️  Deletion is commented out for safety")
            print("   Review the duplicates above and uncomment deletion code if needed")
            
    finally:
        conn.close()

if __name__ == '__main__':
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Duplicate Payout Report Fix" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Run diagnostics
    has_merchant_dups = check_merchant_duplicates()
    has_payout_dups = check_payout_duplicates()
    
    # Provide solution
    fix_report_query()
    
    # Offer to clean duplicates
    if has_merchant_dups:
        clean_duplicate_merchants()
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    if has_merchant_dups:
        print("❌ Issue: Duplicate merchant_id in merchants table")
        print("   Solution: Clean duplicates OR add DISTINCT to query")
    elif has_payout_dups:
        print("❌ Issue: Duplicate transactions in payout_transactions table")
        print("   Solution: Clean duplicate transactions")
    else:
        print("✓ No duplicates found in database")
        print("  Issue might be in frontend rendering or pagination")
    
    print()
    print("Next steps:")
    print("1. Run: python3 diagnose_duplicate_transactions.py")
    print("2. Check frontend PayoutReport.jsx for rendering issues")
    print("3. Add DISTINCT to payout report query")
    print("4. Add UNIQUE constraint on txn_id and reference_id")
    print()
