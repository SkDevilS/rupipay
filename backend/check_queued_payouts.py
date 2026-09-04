#!/usr/bin/env python3
"""
Check Queued Payouts - Diagnostic Script
Shows exactly what's in the database for queued payouts
"""

import sys
from datetime import date
from database import get_db_connection

def check_queued_payouts(merchant_id):
    """Check what queued payouts exist for a merchant"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            print(f"\n{'='*80}")
            print(f"Diagnostic: Checking Queued Payouts for Merchant {merchant_id}")
            print(f"{'='*80}\n")
            
            # Check 1: Count all payouts for this merchant today
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND DATE(created_at) = CURDATE()
            """, (merchant_id,))
            result = cursor.fetchone()
            print(f"Total payouts TODAY: {result['total']}")
            
            # Check 2: Count by status (case-sensitive)
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND DATE(created_at) = CURDATE()
                GROUP BY status
            """, (merchant_id,))
            statuses = cursor.fetchall()
            print(f"\nPayouts by Status (case-sensitive):")
            for s in statuses:
                print(f"  {s['status']}: {s['count']}")
            
            # Check 3: Count by pg_partner
            cursor.execute("""
                SELECT pg_partner, COUNT(*) as count
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND DATE(created_at) = CURDATE()
                GROUP BY pg_partner
            """, (merchant_id,))
            partners = cursor.fetchall()
            print(f"\nPayouts by PG Partner:")
            for p in partners:
                print(f"  {p['pg_partner']}: {p['count']}")
            
            # Check 4: Show sample queued payouts (exact match)
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    status,
                    pg_partner,
                    amount,
                    created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND status = 'Queued'
                    AND DATE(created_at) = CURDATE()
                LIMIT 5
            """, (merchant_id,))
            queued = cursor.fetchall()
            
            if queued:
                print(f"\nSample Queued Payouts (status = 'Queued'):")
                for q in queued:
                    print(f"  {q['txn_id']} | {q['status']} | {q['pg_partner']} | ₹{float(q['amount']):.2f} | {q['created_at']}")
            else:
                print(f"\n⚠️  No payouts with status = 'Queued' found")
            
            # Check 5: Try case-insensitive search
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    status,
                    pg_partner,
                    amount,
                    created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND UPPER(status) IN ('QUEUED', 'PENDING', 'INITIATED')
                    AND DATE(created_at) = CURDATE()
                    AND UPPER(pg_partner) = 'MUDRAPE'
                LIMIT 5
            """, (merchant_id,))
            queued_upper = cursor.fetchall()
            
            if queued_upper:
                print(f"\nSample Queued Payouts (case-insensitive, Mudrape only):")
                for q in queued_upper:
                    print(f"  {q['txn_id']} | {q['status']} | {q['pg_partner']} | ₹{float(q['amount']):.2f} | {q['created_at']}")
            else:
                print(f"\n⚠️  No payouts found with case-insensitive search")
            
            # Check 6: Show today's date from database
            cursor.execute("SELECT CURDATE() as today, NOW() as now")
            db_date = cursor.fetchone()
            print(f"\nDatabase Date/Time:")
            print(f"  CURDATE(): {db_date['today']}")
            print(f"  NOW(): {db_date['now']}")
            
            # Check 7: Show created_at dates for this merchant
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM payout_transactions
                WHERE merchant_id = %s
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at) DESC
                LIMIT 5
            """, (merchant_id,))
            dates = cursor.fetchall()
            print(f"\nPayouts by Date (last 5 days):")
            for d in dates:
                print(f"  {d['date']}: {d['count']} payouts")
            
            print(f"\n{'='*80}\n")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_queued_payouts.py <merchant_id>")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    check_queued_payouts(merchant_id)


if __name__ == '__main__':
    main()
