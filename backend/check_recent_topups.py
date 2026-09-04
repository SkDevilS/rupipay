#!/usr/bin/env python3
"""
Check recent topups to see if duplicates are being created
"""
from database import get_db_connection
from datetime import datetime, timedelta

def check_topups():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # First check table structure
            print("\n" + "="*70)
            print("FUND_REQUESTS TABLE STRUCTURE")
            print("="*70)
            cursor.execute("DESCRIBE fund_requests")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col['Field']}: {col['Type']}")
            
            print("\n" + "="*70)
            print("RECENT TOPUPS (Last 20)")
            print("="*70)
            
            cursor.execute("""
                SELECT *
                FROM fund_requests
                ORDER BY processed_at DESC
                LIMIT 20
            """)
            
            topups = cursor.fetchall()
            
            if not topups:
                print("No topups found")
            else:
                for i, topup in enumerate(topups, 1):
                    print(f"\n{i}. Request ID: {topup.get('request_id', 'N/A')}")
                    print(f"   Merchant: {topup.get('merchant_id', 'N/A')}")
                    print(f"   Amount: ₹{topup.get('amount', 0):,.2f}")
                    print(f"   Status: {topup.get('status', 'N/A')}")
                    print(f"   Processed By: {topup.get('processed_by', 'N/A')}")
                    print(f"   Processed: {topup.get('processed_at', 'N/A')}")
            
            # Check for potential duplicates (same amount, same merchant, recent)
            print("\n" + "="*70)
            print("CHECKING FOR POTENTIAL DUPLICATES")
            print("="*70)
            
            cursor.execute("""
                SELECT 
                    merchant_id,
                    amount,
                    COUNT(*) as count,
                    GROUP_CONCAT(request_id) as request_ids,
                    MIN(processed_at) as first_processed,
                    MAX(processed_at) as last_processed
                FROM fund_requests
                WHERE processed_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                GROUP BY merchant_id, amount
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                print("\n✓ No duplicate topups found in last hour")
            else:
                print(f"\n⚠️  Found {len(duplicates)} potential duplicate(s):")
                for dup in duplicates:
                    print(f"\n   Merchant: {dup['merchant_id']}")
                    print(f"   Amount: ₹{dup['amount']:,.2f}")
                    print(f"   Count: {dup['count']}")
                    print(f"   Request IDs: {dup['request_ids']}")
                    print(f"   Time range: {dup['first_processed']} to {dup['last_processed']}")
            
            print("\n" + "="*70)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_topups()
