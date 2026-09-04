"""
Diagnose Payout Report Download Issue
Check if filters are working correctly
"""

from database import get_db_connection
from datetime import datetime

def test_payout_download_filters():
    """Test the payout download endpoint filters"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Test 1: Get total count without filters
            print("\n=== TEST 1: Total Payouts ===")
            cursor.execute("SELECT COUNT(*) as total FROM payout_transactions")
            total = cursor.fetchone()['total']
            print(f"Total payouts in database: {total}")
            
            # Test 2: Get recent payouts
            print("\n=== TEST 2: Recent Payouts (Last 10) ===")
            cursor.execute("""
                SELECT txn_id, merchant_id, admin_id, status, amount, 
                       DATE(created_at) as date, created_at
                FROM payout_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent = cursor.fetchall()
            for payout in recent:
                print(f"  {payout['txn_id']} | Status: {payout['status']} | "
                      f"Amount: {payout['amount']} | Date: {payout['date']}")
            
            # Test 3: Test status filter
            print("\n=== TEST 3: Filter by Status (SUCCESS) ===")
            cursor.execute("""
                SELECT COUNT(*) as count FROM payout_transactions
                WHERE status = 'SUCCESS'
            """)
            success_count = cursor.fetchone()['count']
            print(f"SUCCESS payouts: {success_count}")
            
            # Test 4: Test date filter (today)
            print("\n=== TEST 4: Filter by Today's Date ===")
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) as count FROM payout_transactions
                WHERE DATE(created_at) = %s
            """, (today,))
            today_count = cursor.fetchone()['count']
            print(f"Today's payouts ({today}): {today_count}")
            
            # Test 5: Test search filter
            print("\n=== TEST 5: Test Search Filter ===")
            cursor.execute("""
                SELECT COUNT(*) as count FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.txn_id LIKE %s OR
                      pt.reference_id LIKE %s OR
                      pt.order_id LIKE %s OR
                      pt.bene_name LIKE %s OR
                      pt.account_no LIKE %s OR
                      pt.ifsc_code LIKE %s OR
                      m.full_name LIKE %s
            """, ('%TXN%', '%TXN%', '%TXN%', '%TXN%', '%TXN%', '%TXN%', '%TXN%'))
            search_count = cursor.fetchone()['count']
            print(f"Payouts matching 'TXN': {search_count}")
            
            # Test 6: Check if there are any filters that return 0
            print("\n=== TEST 6: Potential Issue Detection ===")
            
            # Check for date range issues
            cursor.execute("""
                SELECT MIN(DATE(created_at)) as min_date, 
                       MAX(DATE(created_at)) as max_date
                FROM payout_transactions
            """)
            date_range = cursor.fetchone()
            print(f"Date range in database: {date_range['min_date']} to {date_range['max_date']}")
            
            # Check for merchant join issues
            cursor.execute("""
                SELECT COUNT(*) as count FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id IS NOT NULL AND m.merchant_id IS NULL
            """)
            orphan_count = cursor.fetchone()['count']
            if orphan_count > 0:
                print(f"⚠ Found {orphan_count} payouts with invalid merchant_id")
            
            print("\n=== DIAGNOSIS COMPLETE ===")
            print("\nRecommendations:")
            print("1. Check if frontend is sending correct filter parameters")
            print("2. Check if date format matches (YYYY-MM-DD)")
            print("3. Verify that search term is not too specific")
            print("4. Check browser console for API errors")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    test_payout_download_filters()
