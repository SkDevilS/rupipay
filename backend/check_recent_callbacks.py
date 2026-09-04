#!/usr/bin/env python3
"""
Check recent callback activity for Mudrape payin transactions
"""

from database import get_db_connection
import json

def check_recent_callbacks():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("RECENT MUDRAPE PAYIN TRANSACTIONS & CALLBACK STATUS")
            print("=" * 80)
            print()
            
            # Get recent SUCCESS transactions
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.order_id,
                    pt.amount,
                    pt.status,
                    pt.callback_url,
                    pt.pg_txn_id,
                    pt.bank_ref_no,
                    pt.created_at,
                    pt.completed_at,
                    (SELECT COUNT(*) FROM callback_logs cl WHERE cl.txn_id = pt.txn_id) as callback_count
                FROM payin_transactions pt
                WHERE pt.pg_partner = 'Mudrape'
                AND pt.status = 'SUCCESS'
                ORDER BY pt.completed_at DESC
                LIMIT 10
            """)
            
            success_txns = cursor.fetchall()
            
            if not success_txns:
                print("⚠ No successful Mudrape transactions found")
                return
            
            print(f"Found {len(success_txns)} recent successful transactions:\n")
            
            for txn in success_txns:
                print("=" * 80)
                print(f"Transaction: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Merchant: {txn['merchant_id']}")
                print(f"Amount: {txn['amount']}")
                print(f"Status: {txn['status']}")
                print(f"UTR: {txn['bank_ref_no']}")
                print(f"Completed: {txn['completed_at']}")
                print(f"Callback URL: {txn['callback_url']}")
                print(f"Callback Attempts: {txn['callback_count']}")
                
                # Get callback logs for this transaction
                cursor.execute("""
                    SELECT id, callback_url, request_data, response_code, 
                           response_data, created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                logs = cursor.fetchall()
                
                if logs:
                    print(f"\nCallback Logs ({len(logs)}):")
                    for log in logs:
                        print(f"\n  Log ID: {log['id']}")
                        print(f"  Time: {log['created_at']}")
                        print(f"  URL: {log['callback_url']}")
                        print(f"  Response Code: {log['response_code']}")
                        
                        # Parse and show request data
                        try:
                            request_data = json.loads(log['request_data'])
                            print(f"  Request Data:")
                            print(f"    - txn_id: {request_data.get('txn_id')}")
                            print(f"    - order_id: {request_data.get('order_id')}")
                            print(f"    - status: {request_data.get('status')}")
                            print(f"    - amount: {request_data.get('amount')}")
                            print(f"    - utr: {request_data.get('utr')}")
                        except:
                            print(f"  Request Data: {log['request_data'][:100]}")
                        
                        # Show response
                        if log['response_code'] == 200:
                            print(f"  ✓ Callback successful!")
                        else:
                            print(f"  ❌ Callback failed!")
                        
                        if log['response_data']:
                            print(f"  Response: {log['response_data'][:200]}")
                else:
                    print("\n  ❌ NO CALLBACK LOGS FOUND!")
                    print("  → Callback was NOT sent to merchant")
                    print(f"  → Expected to send to: {txn['callback_url']}")
                
                print()
            
            # Summary
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            
            total_with_callbacks = sum(1 for t in success_txns if t['callback_count'] > 0)
            total_without_callbacks = len(success_txns) - total_with_callbacks
            
            print(f"\nTotal SUCCESS transactions: {len(success_txns)}")
            print(f"  ✓ With callbacks sent: {total_with_callbacks}")
            print(f"  ❌ Without callbacks: {total_without_callbacks}")
            
            if total_without_callbacks > 0:
                print("\n⚠ WARNING: Some successful transactions did NOT receive callbacks!")
                print("   Possible reasons:")
                print("   1. Callback URL was empty/null in transaction")
                print("   2. Callback forwarding logic failed")
                print("   3. Mudrape callback was not received by your server")
                print("\n   Check server logs: tail -f /var/log/gunicorn/error.log | grep -i callback")
            else:
                print("\n✓ All successful transactions have callback logs!")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_recent_callbacks()
