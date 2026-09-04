"""
Check timezone handling in reconciliation queries
"""
import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def check_timezone_conversion():
    """Check how timezone conversion is working"""
    
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Check database timezone settings
            print("=" * 60)
            print("DATABASE TIMEZONE SETTINGS")
            print("=" * 60)
            
            cursor.execute("SELECT @@global.time_zone, @@session.time_zone")
            result = cursor.fetchone()
            print(f"Global timezone: {result['@@global.time_zone']}")
            print(f"Session timezone: {result['@@session.time_zone']}")
            print()
            
            # Check current time in different formats
            print("=" * 60)
            print("CURRENT TIME COMPARISON")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    NOW() as current_utc,
                    DATE_ADD(NOW(), INTERVAL 330 MINUTE) as current_ist,
                    CONVERT_TZ(NOW(), '+00:00', '+05:30') as convert_tz_ist
            """)
            result = cursor.fetchone()
            print(f"NOW() (database time): {result['current_utc']}")
            print(f"DATE_ADD +330 min: {result['current_ist']}")
            print(f"CONVERT_TZ result: {result['convert_tz_ist']}")
            print()
            
            # Check sample transactions
            print("=" * 60)
            print("SAMPLE TRANSACTIONS - TIMEZONE CONVERSION")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    created_at as stored_time,
                    DATE_ADD(created_at, INTERVAL 330 MINUTE) as ist_time,
                    DATE(DATE_ADD(created_at, INTERVAL 330 MINUTE)) as ist_date,
                    CONVERT_TZ(created_at, '+00:00', '+05:30') as convert_tz_result,
                    DATE(CONVERT_TZ(created_at, '+00:00', '+05:30')) as convert_tz_date
                FROM payin_transactions
                WHERE status = 'INITIATED'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            for txn in transactions:
                print(f"\nTransaction: {txn['txn_id']}")
                print(f"  Stored time:        {txn['stored_time']}")
                print(f"  DATE_ADD IST:       {txn['ist_time']}")
                print(f"  DATE_ADD date:      {txn['ist_date']}")
                print(f"  CONVERT_TZ IST:     {txn['convert_tz_result']}")
                print(f"  CONVERT_TZ date:    {txn['convert_tz_date']}")
            
            print()
            print("=" * 60)
            print("DATE FILTER TEST - January 2026")
            print("=" * 60)
            
            # Test with DATE_ADD
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND DATE(DATE_ADD(created_at, INTERVAL 330 MINUTE)) BETWEEN '2026-01-01' AND '2026-01-31'
            """)
            result = cursor.fetchone()
            print(f"DATE_ADD method: {result['count']} transactions")
            
            # Test with CONVERT_TZ
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND DATE(CONVERT_TZ(created_at, '+00:00', '+05:30')) BETWEEN '2026-01-01' AND '2026-01-31'
            """)
            result = cursor.fetchone()
            print(f"CONVERT_TZ method: {result['count']} transactions")
            
            # Test without timezone conversion
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND DATE(created_at) BETWEEN '2026-01-01' AND '2026-01-31'
            """)
            result = cursor.fetchone()
            print(f"No conversion (direct): {result['count']} transactions")
            
            print()
            print("=" * 60)
            print("TRANSACTIONS SHOWING IN APRIL")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    created_at,
                    DATE_ADD(created_at, INTERVAL 330 MINUTE) as ist_time,
                    DATE(DATE_ADD(created_at, INTERVAL 330 MINUTE)) as ist_date
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND DATE(DATE_ADD(created_at, INTERVAL 330 MINUTE)) BETWEEN '2026-04-01' AND '2026-04-30'
                LIMIT 5
            """)
            
            april_txns = cursor.fetchall()
            
            if april_txns:
                for txn in april_txns:
                    print(f"\nTransaction: {txn['txn_id']}")
                    print(f"  Stored (DB):  {txn['created_at']}")
                    print(f"  IST time:     {txn['ist_time']}")
                    print(f"  IST date:     {txn['ist_date']}")
            else:
                print("No transactions found in April 2026")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_timezone_conversion()
