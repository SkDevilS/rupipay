#!/usr/bin/env python3
"""
View Callback Logs
Simple script to view recent callback logs from the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime

def view_callback_logs(limit=10, filter_viyonapay=False):
    """View recent callback logs"""
    
    print("\n" + "="*80)
    print("  CALLBACK LOGS VIEWER")
    print("="*80)
    print(f"\nShowing last {limit} callback logs")
    if filter_viyonapay:
        print("Filtered: ViyonaPay only")
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Build query
            if filter_viyonapay:
                query = """
                    SELECT id, merchant_id, txn_id, callback_url, 
                           request_data, response_code, response_data, created_at
                    FROM callback_logs
                    WHERE callback_url LIKE '%viyonapay%'
                       OR request_data LIKE '%paymentStatus%'
                       OR request_data LIKE '%transactionId%'
                    ORDER BY created_at DESC
                    LIMIT %s
                """
            else:
                query = """
                    SELECT id, merchant_id, txn_id, callback_url, 
                           request_data, response_code, response_data, created_at
                    FROM callback_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                """
            
            cursor.execute(query, (limit,))
            logs = cursor.fetchall()
            
            if not logs:
                print("❌ No callback logs found")
                if filter_viyonapay:
                    print("\nThis means NO ViyonaPay callbacks have been received.")
                    print("\nTry viewing all callbacks:")
                    print("  python3 view_callback_logs.py --all")
                return
            
            print(f"✓ Found {len(logs)} callback logs\n")
            
            for i, log in enumerate(logs, 1):
                print("="*80)
                print(f"Callback #{i} - ID: {log['id']}")
                print("="*80)
                print(f"Time:         {log['created_at']}")
                print(f"Merchant ID:  {log['merchant_id']}")
                print(f"Transaction:  {log['txn_id'] or 'N/A'}")
                print(f"Callback URL: {log['callback_url']}")
                print(f"Response:     {log['response_code']}")
                
                print(f"\nRequest Data:")
                print("-" * 80)
                try:
                    request_data = json.loads(log['request_data'])
                    print(json.dumps(request_data, indent=2))
                    
                    # Check if it's ViyonaPay
                    if 'paymentStatus' in request_data:
                        print("\n✓ This is a ViyonaPay callback")
                        print(f"  Payment Status: {request_data.get('paymentStatus')}")
                        print(f"  Transaction ID: {request_data.get('transactionId')}")
                        print(f"  Order ID:       {request_data.get('orderId')}")
                        print(f"  Amount:         ₹{request_data.get('amount')}")
                except:
                    print(log['request_data'][:500])
                
                if log['response_data']:
                    print(f"\nResponse Data:")
                    print("-" * 80)
                    print(log['response_data'][:300])
                    if len(log['response_data']) > 300:
                        print("... (truncated)")
                
                print()
    
    finally:
        conn.close()

def view_viyonapay_callbacks_summary():
    """Show summary of ViyonaPay callbacks"""
    
    print("\n" + "="*80)
    print("  VIYONAPAY CALLBACKS SUMMARY")
    print("="*80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Count ViyonaPay callbacks
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM callback_logs
                WHERE callback_url LIKE '%viyonapay%'
                   OR request_data LIKE '%paymentStatus%'
            """)
            
            result = cursor.fetchone()
            total = result['total'] if result else 0
            
            print(f"\nTotal ViyonaPay callbacks: {total}")
            
            if total == 0:
                print("\n❌ NO ViyonaPay callbacks found in the database")
                print("\nThis confirms that ViyonaPay is NOT sending webhooks to your server.")
                print("\nPossible reasons:")
                print("  1. Callback URL not registered with ViyonaPay")
                print("  2. Webhooks not enabled for your account")
                print("  3. Network/firewall blocking ViyonaPay's requests")
                print("  4. Wrong callback URL configured")
                return
            
            # Get status breakdown
            cursor.execute("""
                SELECT 
                    JSON_EXTRACT(request_data, '$.paymentStatus') as status,
                    COUNT(*) as count
                FROM callback_logs
                WHERE callback_url LIKE '%viyonapay%'
                   OR request_data LIKE '%paymentStatus%'
                GROUP BY status
            """)
            
            status_counts = cursor.fetchall()
            
            if status_counts:
                print("\nBreakdown by status:")
                for row in status_counts:
                    status = row['status'].strip('"') if row['status'] else 'Unknown'
                    count = row['count']
                    print(f"  {status}: {count}")
            
            # Get latest callback
            cursor.execute("""
                SELECT id, created_at, request_data
                FROM callback_logs
                WHERE callback_url LIKE '%viyonapay%'
                   OR request_data LIKE '%paymentStatus%'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            latest = cursor.fetchone()
            if latest:
                print(f"\nLatest callback:")
                print(f"  Time: {latest['created_at']}")
                print(f"  ID:   {latest['id']}")
                
                try:
                    data = json.loads(latest['request_data'])
                    print(f"  Status: {data.get('paymentStatus')}")
                    print(f"  Order:  {data.get('orderId')}")
                except:
                    pass
    
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View callback logs from database')
    parser.add_argument('--limit', type=int, default=10, help='Number of logs to show (default: 10)')
    parser.add_argument('--all', action='store_true', help='Show all callbacks (not just ViyonaPay)')
    parser.add_argument('--summary', action='store_true', help='Show ViyonaPay callbacks summary')
    
    args = parser.parse_args()
    
    if args.summary:
        view_viyonapay_callbacks_summary()
    else:
        view_callback_logs(limit=args.limit, filter_viyonapay=not args.all)
    
    print("\n" + "="*80)
    print("\nUsage examples:")
    print("  python3 view_callback_logs.py                  # Show last 10 ViyonaPay callbacks")
    print("  python3 view_callback_logs.py --limit 20       # Show last 20 ViyonaPay callbacks")
    print("  python3 view_callback_logs.py --all            # Show all callbacks (all gateways)")
    print("  python3 view_callback_logs.py --summary        # Show ViyonaPay summary")
    print("="*80 + "\n")
