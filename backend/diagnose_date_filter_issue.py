"""
Diagnose date filter issue - check actual created_at values
"""
from database import get_db_connection
from datetime import datetime

def diagnose_date_filter():
    """Check actual created_at values for transactions"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Check database timezone
            cursor.execute("SELECT @@session.time_zone, @@global.time_zone, NOW(), UTC_TIMESTAMP()")
            timezone_info = cursor.fetchone()
            print("\n=== DATABASE TIMEZONE INFO ===")
            print(f"Session timezone: {timezone_info[0]}")
            print(f"Global timezone: {timezone_info[1]}")
            print(f"NOW(): {timezone_info[2]}")
            print(f"UTC_TIMESTAMP(): {timezone_info[3]}")
            
            # Get sample transactions from March 31 and April 1
            cursor.execute("""
                SELECT 
                    txn_id,
                    created_at,
                    DATE(created_at) as date_only,
                    TIME(created_at) as time_only,
                    UNIX_TIMESTAMP(created_at) as unix_ts
                FROM payin_transactions
                WHERE DATE(created_at) IN ('2026-03-31', '2026-04-01')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            transactions = cursor.fetchall()
            
            print("\n=== SAMPLE TRANSACTIONS (March 31 - April 1) ===")
            for txn in transactions:
                print(f"TxnID: {txn['txn_id']}")
                print(f"  created_at: {txn['created_at']}")
                print(f"  DATE(): {txn['date_only']}")
                print(f"  TIME(): {txn['time_only']}")
                print(f"  Unix TS: {txn['unix_ts']}")
                print()
            
            # Test the actual query with March 31
            print("\n=== TESTING QUERY WITH from_date='2026-03-31', to_date='2026-03-31' ===")
            cursor.execute("""
                SELECT 
                    txn_id,
                    created_at,
                    DATE(created_at) as date_only
                FROM payin_transactions
                WHERE DATE(created_at) >= '2026-03-31'
                AND DATE(created_at) <= '2026-03-31'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            results = cursor.fetchall()
            print(f"Found {len(results)} transactions")
            for txn in results:
                print(f"  {txn['txn_id']}: {txn['created_at']} (DATE: {txn['date_only']})")
            
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_date_filter()
