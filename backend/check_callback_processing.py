#!/usr/bin/env python3
"""
Check why callbacks are received but not processed
"""

from database import get_db_connection
import json

def check_processing():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("CHECKING CALLBACK PROCESSING ISSUES")
            print("=" * 80)
            print()
            
            # Get recent transactions that should have received callbacks
            # Based on journalctl showing callbacks at 09:33:18, 09:40:01, 09:42:01
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    callback_url,
                    bank_ref_no,
                    pg_txn_id,
                    created_at,
                    completed_at,
                    updated_at
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                AND DATE(completed_at) = CURDATE()
                ORDER BY completed_at DESC
            """)
            
            today_txns = cursor.fetchall()
            
            print(f"Transactions completed today: {len(today_txns)}\n")
            
            for txn in today_txns:
                print("=" * 80)
                print(f"Order ID: {txn['order_id']}")
                print(f"TXN ID: {txn['txn_id']}")
                print(f"Status: {txn['status']}")
                print(f"Completed: {txn['completed_at']}")
                print(f"Callback URL: {txn['callback_url']}")
                
                # Check if callback was logged
                cursor.execute("""
                    SELECT COUNT(*) as count FROM callback_logs
                    WHERE txn_id = %s
                """, (txn['txn_id'],))
                
                log_count = cursor.fetchone()['count']
                
                if log_count > 0:
                    print(f"✓ Callback logged ({log_count} attempt(s))")
                    
                    # Show callback details
                    cursor.execute("""
                        SELECT callback_url, response_code, response_data, created_at
                        FROM callback_logs
                        WHERE txn_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (txn['txn_id'],))
                    
                    log = cursor.fetchone()
                    print(f"  URL: {log['callback_url']}")
                    print(f"  Response: {log['response_code']}")
                    print(f"  Time: {log['created_at']}")
                else:
                    print(f"❌ NO callback logged")
                    
                    # This is the problem - callback was received but not forwarded
                    if txn['callback_url']:
                        print(f"  → Callback URL exists: {txn['callback_url']}")
                        print(f"  → But callback was NOT forwarded!")
                        print(f"  → Check logs around: {txn['completed_at']}")
                    else:
                        print(f"  → No callback URL in transaction")
                
                print()
            
            print("=" * 80)
            print("ANALYSIS")
            print("=" * 80)
            print()
            
            # Count transactions with/without callbacks
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN EXISTS (
                        SELECT 1 FROM callback_logs cl WHERE cl.txn_id = pt.txn_id
                    ) THEN 1 ELSE 0 END) as with_callback,
                    SUM(CASE WHEN callback_url IS NOT NULL AND callback_url != '' THEN 1 ELSE 0 END) as has_url
                FROM payin_transactions pt
                WHERE pg_partner = 'Mudrape'
                AND status = 'SUCCESS'
                AND DATE(completed_at) = CURDATE()
            """)
            
            stats = cursor.fetchone()
            
            print(f"Today's SUCCESS transactions: {stats['total']}")
            print(f"  - With callback URL: {stats['has_url']}")
            print(f"  - With callback sent: {stats['with_callback']}")
            print(f"  - Missing callbacks: {stats['has_url'] - stats['with_callback']}")
            print()
            
            if stats['has_url'] > stats['with_callback']:
                print("⚠ PROBLEM IDENTIFIED:")
                print("  Callbacks are being RECEIVED by server (journalctl shows them)")
                print("  But they are NOT being FORWARDED to merchant URLs")
                print()
                print("Possible causes:")
                print("  1. Exception in callback forwarding code")
                print("  2. Callback URL lookup failing")
                print("  3. Transaction not found by order_id")
                print("  4. Silent failure in try-except block")
                print()
                print("Next steps:")
                print("  1. Check detailed logs: sudo journalctl -u moneyone-api --since '09:30' | grep -A 30 'Mudrape Payin Callback'")
                print("  2. Look for exceptions or errors after 'Callback Received'")
                print("  3. Check if 'MERCHANT CALLBACK FORWARDING' appears in logs")
                print("  4. Manually trigger callbacks: python3 trigger_missed_callbacks.py")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_processing()
