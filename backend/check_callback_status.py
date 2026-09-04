#!/usr/bin/env python3
"""
Check if Mudrape callbacks are being received
"""

import pymysql
from config import Config
from datetime import datetime, timedelta

def get_db_connection():
    """Get database connection"""
    try:
        return pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def check_callback_logs():
    """Check callback logs in database"""
    print("=" * 80)
    print("Checking Callback Logs")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if callback_logs table exists
            cursor.execute("""
                SHOW TABLES LIKE 'callback_logs'
            """)
            
            if not cursor.fetchone():
                print("\n❌ callback_logs table does not exist")
                print("   Callbacks are not being logged to database")
                return
            
            # Get recent callbacks
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    txn_id,
                    callback_url,
                    response_code,
                    LEFT(response_data, 100) as response_preview,
                    created_at
                FROM callback_logs
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            logs = cursor.fetchall()
            
            if not logs:
                print("\n⚠️  No callback logs found")
                print("   Either no callbacks received or logging not working")
            else:
                print(f"\n✅ Found {len(logs)} recent callback logs:")
                print("")
                for log in logs:
                    print(f"ID: {log['id']}")
                    print(f"  Merchant: {log['merchant_id']}")
                    print(f"  TXN ID: {log['txn_id']}")
                    print(f"  URL: {log['callback_url']}")
                    print(f"  Response Code: {log['response_code']}")
                    print(f"  Response: {log['response_preview']}")
                    print(f"  Time: {log['created_at']}")
                    print("")
            
            # Check callbacks in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM callback_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            recent_count = cursor.fetchone()['count']
            print(f"Callbacks in last 24 hours: {recent_count}")
            
    finally:
        conn.close()

def check_mudrape_transactions():
    """Check Mudrape transactions and their status"""
    print("\n" + "=" * 80)
    print("Checking Mudrape Transactions")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent Mudrape payins
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    created_at,
                    completed_at,
                    TIMESTAMPDIFF(MINUTE, created_at, NOW()) as age_minutes
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\n⚠️  No Mudrape transactions found")
            else:
                print(f"\n✅ Found {len(transactions)} recent Mudrape transactions:")
                print("")
                
                initiated_count = 0
                success_count = 0
                
                for txn in transactions:
                    status_icon = "✅" if txn['status'] == 'SUCCESS' else "⏳" if txn['status'] == 'INITIATED' else "❌"
                    print(f"{status_icon} {txn['txn_id']}")
                    print(f"  Order ID: {txn['order_id']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Status: {txn['status']}")
                    print(f"  PG TXN ID: {txn['pg_txn_id'] or 'Not set'}")
                    print(f"  UTR: {txn['bank_ref_no'] or 'Not set'}")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Age: {txn['age_minutes']} minutes")
                    
                    if txn['status'] == 'INITIATED':
                        initiated_count += 1
                        if txn['age_minutes'] > 30:
                            print(f"  ⚠️  Transaction stuck in INITIATED for {txn['age_minutes']} minutes")
                            print(f"     Callback may not have been received")
                    elif txn['status'] == 'SUCCESS':
                        success_count += 1
                        if txn['completed_at']:
                            print(f"  Completed: {txn['completed_at']}")
                    
                    print("")
                
                print(f"Summary:")
                print(f"  INITIATED: {initiated_count}")
                print(f"  SUCCESS: {success_count}")
                
                if initiated_count > 0:
                    print(f"\n⚠️  {initiated_count} transactions stuck in INITIATED")
                    print(f"   This suggests callbacks are NOT being received")
                    print(f"   Check:")
                    print(f"   1. Callback URL configured in Mudrape dashboard")
                    print(f"   2. Backend is accessible from internet")
                    print(f"   3. Firewall allows incoming HTTPS")
    
    finally:
        conn.close()

def check_backend_logs():
    """Check backend logs for callback activity"""
    print("\n" + "=" * 80)
    print("Checking Backend Logs")
    print("=" * 80)
    
    try:
        with open('../backend.log', 'r') as f:
            lines = f.readlines()
            
        # Search for callback activity
        callback_lines = [line for line in lines if 'Mudrape' in line and 'Callback' in line]
        
        if not callback_lines:
            print("\n⚠️  No callback activity found in backend.log")
            print("   Callbacks are likely NOT being received")
        else:
            print(f"\n✅ Found {len(callback_lines)} callback entries in logs")
            print("\nRecent callback activity:")
            for line in callback_lines[-10:]:
                print(f"  {line.strip()}")
    
    except FileNotFoundError:
        print("\n⚠️  backend.log not found")
        print("   Cannot check log file")

def main():
    print("\n" + "=" * 80)
    print("Mudrape Callback Status Check")
    print("=" * 80)
    print("")
    
    # Check 1: Database callback logs
    check_callback_logs()
    
    # Check 2: Transaction status
    check_mudrape_transactions()
    
    # Check 3: Backend logs
    check_backend_logs()
    
    # Recommendations
    print("\n" + "=" * 80)
    print("Recommendations")
    print("=" * 80)
    print("")
    print("If callbacks are NOT being received:")
    print("")
    print("1. Verify callback URL in Mudrape dashboard:")
    print("   https://admin.moneyone.co.in/api/callback/mudrape/payin")
    print("")
    print("2. Test callback endpoint:")
    print("   bash test_mudrape_callback.sh <ref_id>")
    print("")
    print("3. Check backend accessibility:")
    print("   curl https://admin.moneyone.co.in/api/callback/mudrape/payin")
    print("")
    print("4. Monitor callbacks in real-time:")
    print("   tail -f backend.log | grep -A 10 'Mudrape.*Callback'")
    print("")
    print("5. Contact Mudrape support to verify:")
    print("   - Callback URL is configured")
    print("   - Callbacks are being sent")
    print("   - No errors on their side")
    print("")

if __name__ == '__main__':
    main()
