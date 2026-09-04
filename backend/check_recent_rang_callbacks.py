#!/usr/bin/env python3
"""
Check if Rang callbacks were received for recent transactions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json

def check_recent_rang_transactions():
    """Check recent Rang transactions and their callback status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("RECENT RANG TRANSACTIONS (Last 24 hours)")
        print("=" * 80)
        
        # Get recent Rang transactions
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, status, 
                bank_ref_no, pg_txn_id, callback_url,
                created_at, completed_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY created_at DESC
        """)
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("❌ No Rang transactions found in the last 24 hours")
            return
        
        print(f"Found {len(transactions)} Rang transaction(s):")
        print()
        
        for txn in transactions:
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant: {txn['merchant_id']}")
            print(f"Amount: ₹{txn['amount']}")
            print(f"Status: {txn['status']}")
            print(f"UTR: {txn['bank_ref_no'] or 'None'}")
            print(f"PG TXN ID: {txn['pg_txn_id'] or 'None'}")
            print(f"Callback URL: {txn['callback_url'] or 'None'}")
            print(f"Created: {txn['created_at']}")
            print(f"Completed: {txn['completed_at'] or 'None'}")
            
            # Check if callback was received for this transaction
            print("\nCallback Status:")
            
            # Check callback logs
            cursor.execute("""
                SELECT 
                    callback_url, request_data, response_code, response_data, created_at
                FROM callback_logs 
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print(f"  ✅ {len(callback_logs)} callback(s) logged:")
                for log in callback_logs:
                    print(f"    - {log['created_at']}: Status {log['response_code']} to {log['callback_url']}")
                    if log['request_data']:
                        try:
                            request_data = json.loads(log['request_data'])
                            print(f"      Data: {request_data}")
                        except:
                            print(f"      Data: {log['request_data'][:100]}...")
            else:
                print("  ❌ No callback logs found")
            
            # Check wallet transactions
            cursor.execute("""
                SELECT 
                    txn_type, amount, description, created_at
                FROM merchant_wallet_transactions 
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                print(f"  ✅ {len(wallet_txns)} wallet transaction(s):")
                for wtxn in wallet_txns:
                    print(f"    - {wtxn['created_at']}: {wtxn['txn_type']} ₹{wtxn['amount']} - {wtxn['description']}")
            else:
                print("  ❌ No wallet transactions found")
            
            print("-" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")
        import traceback
        traceback.print_exc()

def check_rang_callback_endpoint():
    """Test if Rang callback endpoint is accessible"""
    print("\nRANG CALLBACK ENDPOINT TEST")
    print("=" * 80)
    
    import requests
    
    try:
        # Test the test endpoint first
        test_url = "https://api.moneyone.co.in/test-rang-callback"
        test_data = {'test': 'connectivity'}
        
        print(f"Testing: {test_url}")
        response = requests.post(test_url, data=test_data, timeout=10)
        
        print(f"Test endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Test endpoint is accessible")
        else:
            print(f"❌ Test endpoint returned: {response.text}")
        
        # Test main callback endpoint with dummy data
        main_url = "https://api.moneyone.co.in/rang-payin-callback"
        dummy_data = {
            'status_id': '1',
            'client_id': 'DUMMY_TEST_123',
            'amount': '100',
            'message': 'connectivity test'
        }
        
        print(f"\nTesting: {main_url}")
        response = requests.post(main_url, data=dummy_data, timeout=10)
        
        print(f"Main endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 404]:  # 404 is expected for dummy data
            print("✅ Main callback endpoint is accessible")
        else:
            print("❌ Main callback endpoint has issues")
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")

def check_server_logs_for_rang():
    """Check if there are any Rang-related entries in recent logs"""
    print("\nSERVER LOG ANALYSIS")
    print("=" * 80)
    
    try:
        # This would typically check actual log files
        # For now, we'll check database logs
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for any Rang-related callback logs in the last 24 hours
        cursor.execute("""
            SELECT 
                COUNT(*) as total_callbacks,
                COUNT(CASE WHEN response_code BETWEEN 200 AND 299 THEN 1 END) as successful_callbacks,
                COUNT(CASE WHEN response_code >= 400 THEN 1 END) as failed_callbacks
            FROM callback_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND (request_data LIKE '%Rang%' OR callback_url LIKE '%rang%')
        """)
        
        log_stats = cursor.fetchone()
        
        print(f"Rang callback activity (last 24 hours):")
        print(f"  Total callbacks: {log_stats['total_callbacks']}")
        print(f"  Successful: {log_stats['successful_callbacks']}")
        print(f"  Failed: {log_stats['failed_callbacks']}")
        
        if log_stats['total_callbacks'] == 0:
            print("  ⚠️ No Rang callback activity detected")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking logs: {e}")

def main():
    print("RANG CALLBACK DIAGNOSTIC REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check recent transactions
    check_recent_rang_transactions()
    
    # Test callback endpoints
    check_rang_callback_endpoint()
    
    # Check server logs
    check_server_logs_for_rang()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETED")
    print("=" * 80)
    
    print("\nNEXT STEPS:")
    print("1. If no callbacks received, check with Rang team if they're sending callbacks")
    print("2. Verify callback URL configuration: https://api.moneyone.co.in/rang-payin-callback")
    print("3. Check server logs for any Rang-related errors")
    print("4. Test with a real transaction to verify callback processing")

if __name__ == "__main__":
    main()