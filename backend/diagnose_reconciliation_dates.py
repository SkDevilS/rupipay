#!/usr/bin/env python3
"""
Diagnose reconciliation date filtering issue
"""

from database import get_db_connection
from datetime import datetime

def diagnose_dates():
    """Check how dates are stored and filtered"""
    
    merchant_id = '9000000001'  # Replace with actual merchant ID
    from_date = '2026-01-01'
    to_date = '2026-01-31'
    
    conn = get_db_connection()
    
    with conn.cursor() as cursor:
        # Check what dates we have
        print("=" * 80)
        print("CHECKING PAYIN TRANSACTIONS DATES")
        print("=" * 80)
        
        # Get all INITIATED payins for this merchant
        cursor.execute("""
            SELECT 
                txn_id,
                created_at,
                DATE(created_at) as date_only,
                FROM_UNIXTIME(UNIX_TIMESTAMP(created_at)) as unix_time
            FROM payin_transactions
            WHERE merchant_id = %s
            AND status = 'INITIATED'
            ORDER BY created_at DESC
            LIMIT 20
        """, (merchant_id,))
        
        results = cursor.fetchall()
        
        print(f"\nFound {len(results)} INITIATED payins:")
        for row in results:
            print(f"  TXN: {row['txn_id']}")
            print(f"    created_at: {row['created_at']}")
            print(f"    DATE(created_at): {row['date_only']}")
            print(f"    unix_time: {row['unix_time']}")
            print()
        
        # Now test the filter
        print("=" * 80)
        print(f"TESTING FILTER: {from_date} to {to_date}")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                txn_id,
                created_at,
                DATE(created_at) as date_only
            FROM payin_transactions
            WHERE merchant_id = %s
            AND status = 'INITIATED'
            AND DATE(created_at) >= %s
            AND DATE(created_at) <= %s
            ORDER BY created_at DESC
        """, (merchant_id, from_date, to_date))
        
        filtered = cursor.fetchall()
        
        print(f"\nFiltered results ({len(filtered)} records):")
        for row in filtered:
            print(f"  TXN: {row['txn_id']}")
            print(f"    created_at: {row['created_at']}")
            print(f"    DATE(created_at): {row['date_only']}")
            print()
        
        # Check timezone
        cursor.execute("SELECT @@global.time_zone, @@session.time_zone, NOW()")
        tz_info = cursor.fetchone()
        print("=" * 80)
        print("TIMEZONE INFO")
        print("=" * 80)
        print(f"Global timezone: {tz_info['@@global.time_zone']}")
        print(f"Session timezone: {tz_info['@@session.time_zone']}")
        print(f"NOW(): {tz_info['NOW()']}")
        print()
    
    conn.close()

if __name__ == '__main__':
    diagnose_dates()
