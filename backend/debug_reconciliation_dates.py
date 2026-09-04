"""
Debug script to check what's happening with reconciliation date filtering
"""
import sys
sys.path.append('/home/ubuntu/moneyone/backend')

from database import get_db_connection
from datetime import datetime

def check_reconciliation_dates():
    """Check the actual dates in the database"""
    
    merchant_id = "9000000001"  # From the screenshot
    from_date = "2026-03-30"
    to_date = "2026-03-30"
    from_time = "00:00"
    to_time = "11:59"
    
    from_datetime = f"{from_date} {from_time}:00"
    to_datetime = f"{to_date} {to_time}:59"
    
    print(f"Checking reconciliation for merchant: {merchant_id}")
    print(f"Date range: {from_datetime} to {to_datetime}")
    print("=" * 80)
    
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        # Check what transactions exist
        cursor.execute("""
            SELECT 
                txn_id,
                DATE(created_at) as date_only,
                TIME(created_at) as time_only,
                created_at,
                status
            FROM payin_transactions
            WHERE merchant_id = %s
            AND status = 'INITIATED'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY created_at DESC
            LIMIT 20
        """, (merchant_id,))
        
        all_txns = cursor.fetchall()
        
        print(f"\nAll INITIATED transactions in last 7 days:")
        print("-" * 80)
        for txn in all_txns:
            print(f"TXN: {txn['txn_id']}")
            print(f"  Date: {txn['date_only']}, Time: {txn['time_only']}")
            print(f"  Full timestamp: {txn['created_at']}")
            print(f"  Status: {txn['status']}")
            print()
        
        # Now check with the filter
        print(f"\nTransactions with filter (>= {from_datetime} AND <= {to_datetime}):")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                txn_id,
                DATE(created_at) as date_only,
                TIME(created_at) as time_only,
                created_at,
                status
            FROM payin_transactions
            WHERE merchant_id = %s
            AND status = 'INITIATED'
            AND created_at >= %s
            AND created_at <= %s
            ORDER BY created_at DESC
        """, (merchant_id, from_datetime, to_datetime))
        
        filtered_txns = cursor.fetchall()
        
        for txn in filtered_txns:
            print(f"TXN: {txn['txn_id']}")
            print(f"  Date: {txn['date_only']}, Time: {txn['time_only']}")
            print(f"  Full timestamp: {txn['created_at']}")
            print(f"  Status: {txn['status']}")
            print()
        
        print(f"\nTotal filtered: {len(filtered_txns)}")
        
        # Check timezone
        cursor.execute("SELECT NOW(), @@session.time_zone, @@global.time_zone")
        tz_info = cursor.fetchone()
        print(f"\nDatabase timezone info:")
        print(f"  Current time: {tz_info['NOW()']}")
        print(f"  Session timezone: {tz_info['@@session.time_zone']}")
        print(f"  Global timezone: {tz_info['@@global.time_zone']}")
    
    conn.close()

if __name__ == '__main__':
    check_reconciliation_dates()
