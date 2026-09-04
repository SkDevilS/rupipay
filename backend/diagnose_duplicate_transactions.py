"""
Diagnose Duplicate Transactions in Payout Report
Identifies why transactions appear twice in the report
"""

import sys
import pymysql
from database import get_db_connection
from datetime import datetime

def check_duplicate_transactions():
    """Check for duplicate transactions"""
    print("=" * 80)
    print("Duplicate Transaction Diagnosis")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check 1: Duplicate txn_id
            print("1. Checking for duplicate txn_id...")
            cursor.execute("""
                SELECT txn_id, COUNT(*) as count
                FROM payout_transactions
                GROUP BY txn_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicate txn_id entries:")
                for dup in duplicates:
                    print(f"   - {dup['txn_id']}: {dup['count']} occurrences")
                    
                    # Show details
                    cursor.execute("""
                        SELECT id, txn_id, reference_id, merchant_id, admin_id, 
                               amount, status, pg_partner, created_at
                        FROM payout_transactions
                        WHERE txn_id = %s
                    """, (dup['txn_id'],))
                    
                    details = cursor.fetchall()
                    for detail in details:
                        print(f"     ID: {detail['id']}, Ref: {detail['reference_id']}, "
                              f"Status: {detail['status']}, Created: {detail['created_at']}")
            else:
                print("✓ No duplicate txn_id found")
            print()
            
            # Check 2: Duplicate reference_id
            print("2. Checking for duplicate reference_id...")
            cursor.execute("""
                SELECT reference_id, COUNT(*) as count
                FROM payout_transactions
                GROUP BY reference_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicate reference_id entries:")
                for dup in duplicates:
                    print(f"   - {dup['reference_id']}: {dup['count']} occurrences")
            else:
                print("✓ No duplicate reference_id found")
            print()
            
            # Check 3: Duplicate order_id
            print("3. Checking for duplicate order_id...")
            cursor.execute("""
                SELECT order_id, COUNT(*) as count
                FROM payout_transactions
                WHERE order_id IS NOT NULL AND order_id != ''
                GROUP BY order_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"❌ Found {len(duplicates)} duplicate order_id entries:")
                for dup in duplicates:
                    print(f"   - {dup['order_id']}: {dup['count']} occurrences")
            else:
                print("✓ No duplicate order_id found")
            print()
            
            # Check 4: Same transaction with different IDs
            print("4. Checking for same transaction with different IDs...")
            cursor.execute("""
                SELECT merchant_id, admin_id, amount, bene_name, account_no, 
                       DATE(created_at) as date, COUNT(*) as count
                FROM payout_transactions
                GROUP BY merchant_id, admin_id, amount, bene_name, account_no, DATE(created_at)
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"❌ Found {len(duplicates)} potential duplicate transactions:")
                for dup in duplicates:
                    merchant_admin = dup['merchant_id'] or dup['admin_id']
                    print(f"   - Merchant/Admin: {merchant_admin}, Amount: ₹{dup['amount']}, "
                          f"Date: {dup['date']}, Count: {dup['count']}")
            else:
                print("✓ No duplicate transactions found")
            print()
            
            # Check 5: Recent transactions from screenshot
            print("5. Checking specific transactions from screenshot...")
            
            # Admin Payout transactions
            cursor.execute("""
                SELECT txn_id, reference_id, order_id, merchant_id, admin_id, 
                       amount, charge_amount, status, pg_partner, created_at
                FROM payout_transactions
                WHERE merchant_id LIKE 'ADMIN%' OR admin_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            admin_txns = cursor.fetchall()
            print(f"Recent Admin Payout transactions: {len(admin_txns)}")
            for txn in admin_txns:
                print(f"   - TxnID: {txn['txn_id']}, Ref: {txn['reference_id']}, "
                      f"Amount: ₹{txn['amount']}, Status: {txn['status']}")
            print()
            
            # Check 6: Query used in report
            print("6. Simulating report query...")
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM payout_transactions
                WHERE DATE(created_at) = CURDATE()
            """)
            
            today_count = cursor.fetchone()
            print(f"Total transactions today: {today_count['total']}")
            print()
            
            # Check 7: Check for JOIN issues
            print("7. Checking if report uses JOINs that could cause duplicates...")
            print("   (This requires checking the actual report query)")
            print()
            
            # Recommendations
            print("=" * 80)
            print("DIAGNOSIS SUMMARY")
            print("=" * 80)
            print()
            print("Possible causes of duplicate transactions:")
            print()
            print("1. Database Level:")
            print("   - Duplicate INSERT statements")
            print("   - Missing UNIQUE constraints on txn_id/reference_id")
            print("   - Transaction retry logic creating duplicates")
            print()
            print("2. Application Level:")
            print("   - Double submission (user clicking twice)")
            print("   - API retry logic")
            print("   - Multiple backend instances processing same request")
            print()
            print("3. Report Query Level:")
            print("   - JOIN with another table causing row multiplication")
            print("   - Missing DISTINCT in SELECT")
            print("   - Grouping issues")
            print()
            print("4. Frontend Level:")
            print("   - Same data rendered twice")
            print("   - Pagination issues")
            print()
            
    finally:
        conn.close()

def check_specific_txn(txn_id):
    """Check specific transaction details"""
    print("=" * 80)
    print(f"Checking Transaction: {txn_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM payout_transactions
                WHERE txn_id = %s OR reference_id = %s
            """, (txn_id, txn_id))
            
            txns = cursor.fetchall()
            
            if not txns:
                print(f"❌ No transaction found with ID: {txn_id}")
                return
            
            print(f"Found {len(txns)} transaction(s):")
            print()
            
            for i, txn in enumerate(txns, 1):
                print(f"Transaction #{i}:")
                print(f"  Database ID: {txn.get('id')}")
                print(f"  TxnID: {txn.get('txn_id')}")
                print(f"  Reference ID: {txn.get('reference_id')}")
                print(f"  Order ID: {txn.get('order_id')}")
                print(f"  Merchant ID: {txn.get('merchant_id')}")
                print(f"  Admin ID: {txn.get('admin_id')}")
                print(f"  Amount: ₹{txn.get('amount')}")
                print(f"  Charge: ₹{txn.get('charge_amount')}")
                print(f"  Status: {txn.get('status')}")
                print(f"  PG Partner: {txn.get('pg_partner')}")
                print(f"  Created: {txn.get('created_at')}")
                print(f"  Updated: {txn.get('updated_at')}")
                print()
            
            if len(txns) > 1:
                print("❌ DUPLICATE FOUND!")
                print()
                print("Recommended action:")
                print("1. Keep the first transaction (oldest)")
                print("2. Delete duplicate entries")
                print(f"3. Run: DELETE FROM payout_transactions WHERE id IN ({','.join([str(t['id']) for t in txns[1:]])})")
            
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Check specific transaction
        check_specific_txn(sys.argv[1])
    else:
        # Run full diagnosis
        check_duplicate_transactions()
        
        print()
        print("To check a specific transaction:")
        print("  python3 diagnose_duplicate_transactions.py <txn_id>")
        print()
