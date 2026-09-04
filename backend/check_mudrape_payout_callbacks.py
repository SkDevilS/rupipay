#!/usr/bin/env python3
"""
Check Mudrape Payout Callback Status
Investigates why Mudrape payout callbacks are not being received
"""

import sys
import os
from database import get_db_connection
from datetime import datetime
import requests

def check_mudrape_callbacks():
    """Check Mudrape payout callback configuration and recent activity"""
    
    print("=" * 80)
    print("MUDRAPE PAYOUT CALLBACK DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Check if callback route is registered
    print("1. Checking callback route registration...")
    print("-" * 80)
    
    try:
        # Check if the route exists in app.py
        with open('app.py', 'r') as f:
            app_content = f.read()
            if 'mudrape_callback_bp' in app_content:
                print("✓ Mudrape callback blueprint registered in app.py")
            else:
                print("❌ Mudrape callback blueprint NOT found in app.py")
            
            if '/api/callback/mudrape' in app_content:
                print("✓ Mudrape callback route prefix configured")
            else:
                print("❌ Mudrape callback route prefix NOT configured")
    except Exception as e:
        print(f"❌ Error checking app.py: {e}")
    
    print()
    
    # Check callback endpoint accessibility
    print("2. Checking callback endpoint...")
    print("-" * 80)
    
    # Get server URL from environment
    server_url = os.getenv('SERVER_URL', 'http://localhost:5000')
    callback_url = f"{server_url}/api/callback/mudrape/payout"
    
    print(f"Expected callback URL: {callback_url}")
    print()
    
    # Check database for recent callbacks
    print("3. Checking recent Mudrape payout transactions...")
    print("-" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent Mudrape payouts
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    amount,
                    status,
                    pg_txn_id,
                    utr,
                    created_at,
                    completed_at,
                    updated_at
                FROM payout_transactions
                WHERE pg_partner = 'Mudrape'
                AND created_at >= '2026-03-09 00:00:00'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            recent_payouts = cursor.fetchall()
            
            if not recent_payouts:
                print("No recent Mudrape payouts found")
            else:
                print(f"Found {len(recent_payouts)} recent Mudrape payouts:")
                print()
                
                for payout in recent_payouts:
                    print(f"TXN: {payout['txn_id']}")
                    print(f"  Reference: {payout['reference_id']}")
                    print(f"  Status: {payout['status']}")
                    print(f"  PG TXN ID: {payout['pg_txn_id']}")
                    print(f"  UTR: {payout['utr']}")
                    print(f"  Created: {payout['created_at']}")
                    print(f"  Completed: {payout['completed_at']}")
                    print(f"  Updated: {payout['updated_at']}")
                    
                    # Check if callback was received
                    time_diff = None
                    if payout['completed_at'] and payout['created_at']:
                        time_diff = (payout['completed_at'] - payout['created_at']).total_seconds()
                        print(f"  Time to complete: {time_diff:.1f} seconds")
                    
                    # If status is SUCCESS but completed_at is set, callback was likely received
                    if payout['status'] == 'SUCCESS' and payout['completed_at']:
                        print(f"  ✓ Callback likely received (status updated to SUCCESS)")
                    elif payout['status'] in ['INITIATED', 'QUEUED', 'INPROCESS']:
                        print(f"  ⚠️  Still pending - callback not received yet")
                    
                    print()
            
            print()
            print("4. Checking callback logs (if table exists)...")
            print("-" * 80)
            
            # Check if callback_logs table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = 'callback_logs'
            """)
            
            table_exists = cursor.fetchone()['count'] > 0
            
            if table_exists:
                cursor.execute("""
                    SELECT 
                        merchant_id,
                        txn_id,
                        callback_url,
                        response_code,
                        created_at
                    FROM callback_logs
                    WHERE created_at >= '2026-03-09 00:00:00'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                callback_logs = cursor.fetchall()
                
                if callback_logs:
                    print(f"Found {len(callback_logs)} recent callback logs:")
                    for log in callback_logs:
                        print(f"  {log['created_at']}: TXN {log['txn_id']} → {log['callback_url']} (HTTP {log['response_code']})")
                else:
                    print("No recent callback logs found")
            else:
                print("callback_logs table does not exist")
            
            print()
            print("5. Checking Mudrape configuration...")
            print("-" * 80)
            
            # Check config.py for Mudrape settings
            try:
                from config import MUDRAPE_MERCHANT_ID, MUDRAPE_API_KEY, MUDRAPE_BASE_URL
                print(f"✓ Mudrape Merchant ID: {MUDRAPE_MERCHANT_ID}")
                print(f"✓ Mudrape Base URL: {MUDRAPE_BASE_URL}")
                print(f"✓ Mudrape API Key: {'*' * 20}{MUDRAPE_API_KEY[-4:] if len(MUDRAPE_API_KEY) > 4 else '****'}")
            except ImportError as e:
                print(f"❌ Error importing Mudrape config: {e}")
            
            print()
            print("6. Recommendations...")
            print("-" * 80)
            
            print("To fix the callback issue:")
            print()
            print("1. Verify Mudrape callback URL is configured in Mudrape dashboard:")
            print(f"   {callback_url}")
            print()
            print("2. Check if your server is accessible from Mudrape's servers:")
            print("   - Ensure firewall allows incoming connections")
            print("   - Verify NAT Gateway/Load Balancer configuration")
            print("   - Check security groups allow HTTP/HTTPS traffic")
            print()
            print("3. Check backend logs for incoming callback requests:")
            print("   tail -f /var/www/moneyone/logs/backend.log | grep 'Mudrape Payout Callback'")
            print()
            print("4. Test callback endpoint manually:")
            print(f"   curl -X POST {callback_url} -H 'Content-Type: application/json' -d '{{}}'")
            print()
            print("5. Contact Mudrape support to verify:")
            print("   - Callback URL is correctly configured")
            print("   - Callbacks are being sent")
            print("   - Check for any delivery failures")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    check_mudrape_callbacks()
