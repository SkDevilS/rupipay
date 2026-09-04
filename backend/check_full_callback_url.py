#!/usr/bin/env python3
"""
Check full callback URL (not truncated)
"""

from database import get_db_connection

conn = get_db_connection()
if conn:
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT txn_id, order_id, callback_url, LENGTH(callback_url) as url_length
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                AND callback_url IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            txns = cursor.fetchall()
            
            print("Full Callback URLs:")
            print("=" * 80)
            for t in txns:
                print(f"\nOrder: {t['order_id']}")
                print(f"URL Length: {t['url_length']} characters")
                print(f"Full URL: {t['callback_url']}")
    finally:
        conn.close()
