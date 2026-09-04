#!/usr/bin/env python3
"""
PayTouch Callback Activity Checker
Checks if PayTouch has sent any callbacks today and analyzes callback patterns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json

def check_paytouch_callback_activity():
    """
    Check PayTouch callback activity for today and recent days
    """
    
    print("=" * 80)
    print(f"PayTouch Callback Activity Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            
            # Check if we have any callback logging mechanism
            print("🔍 Checking callback logging infrastructure...")
            
            # Check if callback_logs table exists
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'callback_logs'
            """)
            callback_logs_exists = cursor.fetchone()
            
            if callback_logs_exists:
                print("✅ callback_logs table exists")
                
                # Check PayTouch callbacks in callback_logs
                cursor.execute("""
                    SELECT DATE(created_at) as callback_date, 
                           COUNT(*) as callback_count,
                           COUNT(CASE WHEN response_code = 200 THEN 1 END) as successful_callbacks,
                           COUNT(CASE WHEN response_code != 200 THEN 1 END) as failed_callbacks
                    FROM callback_logs 
                    WHERE callback_url LIKE '%paytouch%' 
                       OR request_data LIKE '%PayTouch%'
                       OR request_data LIKE '%paytouch%'
                    AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                    GROUP BY DATE(created_at)
                    ORDER BY callback_date DESC
                """)
                
                callback_activity = cursor.fetchall()
                
                if callback_activity:
                    print("\n📊 PayTouch Callback Activity (Last 7 Days):")
                    print("-" * 60)
                    for activity in callback_activity:
                        print(f"Date: {activity['callback_date']}")
                        print(f"  Total Callbacks: {activity['callback_count']}")
                        print(f"  Successful: {activity['successful_callbacks']}")
                        print(f"  Failed: {activity['failed_callbacks']}")
                        print()
                else:
                    print("❌ No PayTouch callbacks found in callback_logs")
            else:
                print("⚠️  callback_logs table does not exist")
            
            # Check for any server logs or access logs that might contain callback data
            print("\n🔍 Checking for PayTouch callback endpoint hits...")
            
            # Check if we can find any evidence of callback attempts in application logs
            # This would typically be in server access logs, but we'll check what we can from database
            
            # Check PayTouch transactions and their callback status
            print("\n📊 PayTouch Transaction Analysis (Today):")
            print("-" * 60)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_txns,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_txns,
                    COUNT(CASE WHEN status = 'QUEUED' THEN 1 END) as queued_txns,
                    COUNT(CASE WHEN status = 'INPROCESS' THEN 1 END) as inprocess_txns,
                    COUNT(CASE WHEN utr IS NOT NULL AND utr != '' THEN 1 END) as txns_with_utr,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_txns
                FROM payout_transactions 
                WHERE pg_partner = 'PayTouch' 
                AND DATE(created_at) = CURDATE()
            """)
            
            today_stats = cursor.fetchone()
            
            print(f"Total PayTouch Transactions Today: {today_stats['total_transactions']}")
            print(f"  ✅ Successful: {today_stats['successful_txns']}")
            print(f"  ❌ Failed: {today_stats['failed_txns']}")
            print(f"  ⏳ Queued: {today_stats['queued_txns']}")
            print(f"  🔄 In Process: {today_stats['inprocess_txns']}")
            print(f"  🏦 With UTR: {today_stats['txns_with_utr']}")
            print(f"  ✅ Completed: {today_stats['completed_txns']}")
            
            # Check recent PayTouch transactions in detail
            print(f"\n📋 Recent PayTouch Transactions (Last 24 Hours):")
            print("-" * 80)
            
            cursor.execute("""
                SELECT txn_id, pg_txn_id, status, amount, utr, 
                       created_at, completed_at, updated_at,
                       CASE 
                           WHEN completed_at IS NOT NULL THEN 'Callback Received'
                           WHEN utr IS NOT NULL AND utr != '' THEN 'UTR Available'
                           ELSE 'No Callback'
                       END as callback_status
                FROM payout_transactions 
                WHERE pg_partner = 'PayTouch' 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            recent_txns = cursor.fetchall()
            
            if recent_txns:
                for txn in recent_txns:
                    print(f"TXN: {txn['txn_id']}")
                    print(f"  PG TXN ID: {txn['pg_txn_id']}")
                    print(f"  Status: {txn['status']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  UTR: {txn['utr'] or 'None'}")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Completed: {txn['completed_at'] or 'Not completed'}")
                    print(f"  Last Updated: {txn['updated_at']}")
                    print(f"  Callback Status: {txn['callback_status']}")
                    print("-" * 40)
            else:
                print("No PayTouch transactions found in last 24 hours")
            
            # Check callback endpoint configuration
            print(f"\n🔧 PayTouch Callback Configuration Check:")
            print("-" * 60)
            print("Configured Callback URL: https://api.moneyone.co.in/api/callback/paytouch/payout")
            
            # Check if the callback endpoint is properly registered in routes
            print("✅ Callback endpoint should be available at: /api/callback/paytouch/payout")
            
            # Analyze callback patterns
            print(f"\n📈 Callback Pattern Analysis (Last 7 Days):")
            print("-" * 60)
            
            cursor.execute("""
                SELECT 
                    DATE(created_at) as txn_date,
                    COUNT(*) as total_txns,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as callback_received,
                    COUNT(CASE WHEN completed_at IS NULL THEN 1 END) as no_callback,
                    ROUND(
                        (COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) * 100.0 / COUNT(*)), 2
                    ) as callback_rate
                FROM payout_transactions 
                WHERE pg_partner = 'PayTouch' 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                GROUP BY DATE(created_at)
                ORDER BY txn_date DESC
            """)
            
            callback_patterns = cursor.fetchall()
            
            if callback_patterns:
                for pattern in callback_patterns:
                    print(f"Date: {pattern['txn_date']}")
                    print(f"  Total Transactions: {pattern['total_txns']}")
                    print(f"  Callbacks Received: {pattern['callback_received']}")
                    print(f"  No Callback: {pattern['no_callback']}")
                    print(f"  Callback Rate: {pattern['callback_rate']}%")
                    print()
            else:
                print("No PayTouch transactions found in last 7 days")
            
            # Check for any webhook/callback related errors
            print(f"\n🚨 Error Analysis:")
            print("-" * 60)
            
            cursor.execute("""
                SELECT error_message, COUNT(*) as error_count
                FROM payout_transactions 
                WHERE pg_partner = 'PayTouch' 
                AND error_message IS NOT NULL 
                AND error_message != ''
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                GROUP BY error_message
                ORDER BY error_count DESC
            """)
            
            errors = cursor.fetchall()
            
            if errors:
                print("Recent PayTouch Errors:")
                for error in errors:
                    print(f"  Error: {error['error_message']}")
                    print(f"  Count: {error['error_count']}")
                    print()
            else:
                print("✅ No recent PayTouch errors found")
            
            # Summary and recommendations
            print(f"\n{'='*80}")
            print("SUMMARY & RECOMMENDATIONS")
            print(f"{'='*80}")
            
            if today_stats['total_transactions'] == 0:
                print("📊 No PayTouch transactions today")
            else:
                callback_rate = (today_stats['completed_txns'] / today_stats['total_transactions']) * 100
                print(f"📊 Today's Callback Rate: {callback_rate:.1f}%")
                
                if callback_rate < 50:
                    print("🚨 LOW CALLBACK RATE - PayTouch may not be sending callbacks properly")
                    print("\n🔧 Recommended Actions:")
                    print("1. Check PayTouch dashboard for callback configuration")
                    print("2. Verify callback URL is correctly configured: https://api.moneyone.co.in/api/callback/paytouch/payout")
                    print("3. Check server logs for incoming callback requests")
                    print("4. Test callback endpoint manually")
                    print("5. Contact PayTouch support to verify webhook configuration")
                elif callback_rate < 80:
                    print("⚠️  MODERATE CALLBACK RATE - Some callbacks may be missing")
                    print("\n🔧 Recommended Actions:")
                    print("1. Monitor callback patterns")
                    print("2. Check for intermittent network issues")
                    print("3. Verify callback endpoint is always accessible")
                else:
                    print("✅ GOOD CALLBACK RATE - PayTouch callbacks are working well")
            
            # Check specific transactions mentioned in the original issue
            print(f"\n🔍 Checking Specific Transactions from Original Issue:")
            print("-" * 60)
            
            specific_txns = [
                'ADMIN20260310182521A6904E',
                'ADMIN20260310182131FF1C8D'
            ]
            
            for pg_txn_id in specific_txns:
                cursor.execute("""
                    SELECT txn_id, status, utr, created_at, completed_at, updated_at
                    FROM payout_transactions 
                    WHERE pg_txn_id = %s AND pg_partner = 'PayTouch'
                """, (pg_txn_id,))
                
                txn = cursor.fetchone()
                
                if txn:
                    print(f"Transaction: {pg_txn_id}")
                    print(f"  Status: {txn['status']}")
                    print(f"  UTR: {txn['utr'] or 'None'}")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Completed: {txn['completed_at'] or 'No callback received'}")
                    print(f"  Last Updated: {txn['updated_at']}")
                    
                    if not txn['completed_at']:
                        print(f"  ❌ NO CALLBACK RECEIVED for this transaction")
                    else:
                        print(f"  ✅ Callback was received")
                    print()
                else:
                    print(f"Transaction {pg_txn_id} not found in database")
                    print()
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print(f"\n{'='*80}")
    print("Analysis completed")
    print(f"{'='*80}")

if __name__ == "__main__":
    check_paytouch_callback_activity()