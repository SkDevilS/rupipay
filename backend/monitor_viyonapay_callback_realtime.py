#!/usr/bin/env python3
"""
Real-time ViyonaPay Callback Monitor
Run this script and then complete a transaction to see if callbacks are received
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import time
from datetime import datetime
import json

def monitor_callbacks():
    """Monitor for new ViyonaPay callbacks in real-time"""
    
    print("\n" + "="*80)
    print("  REAL-TIME VIYONAPAY CALLBACK MONITOR")
    print("="*80)
    print("\n🔍 Monitoring for ViyonaPay callbacks...")
    print("📝 This script checks the database every 2 seconds for new callbacks")
    print("⏰ Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\n" + "="*80)
    print("  NOW COMPLETE YOUR VIYONAPAY TRANSACTION")
    print("="*80)
    print("\nWaiting for callbacks... (Press Ctrl+C to stop)\n")
    
    last_callback_id = 0
    last_transaction_id = None
    check_count = 0
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        # Get the latest callback ID to start monitoring from
        with conn.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(id), 0) as max_id FROM callback_logs")
            result = cursor.fetchone()
            last_callback_id = result['max_id'] if result else 0
            
            # Get latest ViyonaPay transaction
            cursor.execute("""
                SELECT txn_id, order_id, status, created_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            latest_txn = cursor.fetchone()
            if latest_txn:
                last_transaction_id = latest_txn['txn_id']
                print(f"📊 Latest ViyonaPay transaction: {latest_txn['txn_id']}")
                print(f"   Order ID: {latest_txn['order_id']}")
                print(f"   Status: {latest_txn['status']}")
                print(f"   Created: {latest_txn['created_at']}")
                print()
        
        conn.close()
        
        while True:
            check_count += 1
            conn = get_db_connection()
            
            if not conn:
                print("❌ Database connection lost")
                time.sleep(2)
                continue
            
            try:
                with conn.cursor() as cursor:
                    # Check for new callbacks
                    cursor.execute("""
                        SELECT id, merchant_id, callback_url, request_data, 
                               response_code, response_data, created_at
                        FROM callback_logs
                        WHERE id > %s
                        ORDER BY id ASC
                    """, (last_callback_id,))
                    
                    new_callbacks = cursor.fetchall()
                    
                    if new_callbacks:
                        for callback in new_callbacks:
                            print("\n" + "🎉"*40)
                            print("  NEW CALLBACK RECEIVED!")
                            print("🎉"*40)
                            print(f"\n⏰ Time: {callback['created_at']}")
                            print(f"📋 Callback ID: {callback['id']}")
                            print(f"👤 Merchant ID: {callback['merchant_id']}")
                            print(f"🔗 Callback URL: {callback['callback_url']}")
                            print(f"📊 Response Code: {callback['response_code']}")
                            
                            print("\n" + "="*80)
                            print("  REQUEST DATA (What was received)")
                            print("="*80)
                            
                            try:
                                request_data = json.loads(callback['request_data'])
                                print(json.dumps(request_data, indent=2))
                                
                                # Check if it's ViyonaPay
                                if any(key in request_data for key in ['paymentStatus', 'transactionId', 'orderId']):
                                    print("\n✅ This looks like a ViyonaPay callback!")
                                    print(f"\n💳 Payment Details:")
                                    print(f"   Status: {request_data.get('paymentStatus', 'N/A')}")
                                    print(f"   Transaction ID: {request_data.get('transactionId', 'N/A')}")
                                    print(f"   Order ID: {request_data.get('orderId', 'N/A')}")
                                    print(f"   Amount: ₹{request_data.get('amount', 'N/A')}")
                                    print(f"   Payment Mode: {request_data.get('paymentMode', 'N/A')}")
                                    print(f"   Bank Ref: {request_data.get('bankRefId', 'N/A')}")
                            except:
                                print(callback['request_data'])
                            
                            if callback['response_data']:
                                print("\n" + "="*80)
                                print("  RESPONSE DATA (What we sent back)")
                                print("="*80)
                                print(callback['response_data'][:500])
                            
                            last_callback_id = callback['id']
                            print("\n" + "="*80)
                    
                    # Check for new ViyonaPay transactions
                    cursor.execute("""
                        SELECT txn_id, order_id, status, pg_txn_id, created_at
                        FROM payin_transactions
                        WHERE pg_partner = 'VIYONAPAY'
                          AND (txn_id != %s OR %s IS NULL)
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (last_transaction_id, last_transaction_id))
                    
                    new_txn = cursor.fetchone()
                    
                    if new_txn and new_txn['txn_id'] != last_transaction_id:
                        print("\n" + "🆕"*40)
                        print("  NEW VIYONAPAY TRANSACTION DETECTED!")
                        print("🆕"*40)
                        print(f"\n⏰ Time: {new_txn['created_at']}")
                        print(f"📋 Transaction ID: {new_txn['txn_id']}")
                        print(f"📦 Order ID: {new_txn['order_id']}")
                        print(f"📊 Status: {new_txn['status']}")
                        print(f"🔗 PG TXN ID: {new_txn['pg_txn_id']}")
                        print("\n⏳ Waiting for callback from ViyonaPay...")
                        print("="*80 + "\n")
                        
                        last_transaction_id = new_txn['txn_id']
                    
                    # Check if existing transaction status changed
                    if last_transaction_id:
                        cursor.execute("""
                            SELECT txn_id, order_id, status, pg_txn_id, updated_at
                            FROM payin_transactions
                            WHERE txn_id = %s
                        """, (last_transaction_id,))
                        
                        current_txn = cursor.fetchone()
                        if current_txn and current_txn['status'] != 'INITIATED':
                            print("\n" + "✅"*40)
                            print("  TRANSACTION STATUS UPDATED!")
                            print("✅"*40)
                            print(f"\n⏰ Time: {current_txn['updated_at']}")
                            print(f"📋 Transaction ID: {current_txn['txn_id']}")
                            print(f"📊 New Status: {current_txn['status']}")
                            print(f"🔗 PG TXN ID: {current_txn['pg_txn_id']}")
                            print("\n🎉 Callback was processed successfully!")
                            print("="*80 + "\n")
                
            finally:
                conn.close()
            
            # Show heartbeat every 10 checks (20 seconds)
            if check_count % 10 == 0:
                print(f"💓 Still monitoring... ({check_count} checks, {datetime.now().strftime('%H:%M:%S')})")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("  MONITORING STOPPED")
        print("="*80)
        print(f"\n⏰ Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total checks: {check_count}")
        print(f"📋 Last callback ID: {last_callback_id}")
        
        if last_transaction_id:
            print(f"\n📝 Checking final status of transaction: {last_transaction_id}")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT txn_id, order_id, status, pg_txn_id, 
                                   created_at, updated_at
                            FROM payin_transactions
                            WHERE txn_id = %s
                        """, (last_transaction_id,))
                        
                        final_txn = cursor.fetchone()
                        if final_txn:
                            print(f"\n   Transaction ID: {final_txn['txn_id']}")
                            print(f"   Order ID: {final_txn['order_id']}")
                            print(f"   Status: {final_txn['status']}")
                            print(f"   PG TXN ID: {final_txn['pg_txn_id']}")
                            print(f"   Created: {final_txn['created_at']}")
                            print(f"   Updated: {final_txn['updated_at']}")
                            
                            if final_txn['status'] == 'INITIATED':
                                print("\n⚠️  Transaction still INITIATED - No callback received!")
                                print("\n💡 This confirms ViyonaPay is NOT sending callbacks.")
                                print("   Contact ViyonaPay support to enable webhooks.")
                            else:
                                print("\n✅ Transaction updated - Callback was received!")
                finally:
                    conn.close()
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    monitor_callbacks()
