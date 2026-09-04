#!/usr/bin/env python3
"""
Complete ViyonaPay Callback Check
Checks both database and server logs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import subprocess
import json
import re

def check_database():
    """Check database for ViyonaPay transactions and callbacks"""
    print("\n" + "="*80)
    print("  DATABASE CHECK")
    print("="*80)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Check payin_transactions
            print("\n📋 Checking payin_transactions...")
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    created_at,
                    updated_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if transactions:
                print(f"\n✅ Found {len(transactions)} ViyonaPay transaction(s):\n")
                for txn in transactions:
                    print(f"{'='*80}")
                    print(f"Transaction ID: {txn['txn_id']}")
                    print(f"Order ID: {txn['order_id']}")
                    print(f"Merchant ID: {txn['merchant_id']}")
                    print(f"Amount: ₹{txn['amount']}")
                    print(f"Status: {txn['status']}")
                    print(f"PG TXN ID: {txn['pg_txn_id']}")
                    print(f"Bank Ref No: {txn['bank_ref_no']}")
                    print(f"Payment Mode: {txn['payment_mode']}")
                    print(f"Created: {txn['created_at']}")
                    print(f"Updated: {txn['updated_at']}")
                    print(f"Completed: {txn['completed_at']}")
                    print()
            else:
                print("❌ No ViyonaPay transactions found")
            
            # Check callback_logs
            print("\n📋 Checking callback_logs...")
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE request_data LIKE '%VIYONAPAY%'
                   OR callback_url LIKE '%viyonapay%'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            callbacks = cursor.fetchall()
            
            if callbacks:
                print(f"\n✅ Found {len(callbacks)} callback log(s):\n")
                for cb in callbacks:
                    print(f"{'='*80}")
                    print(f"Callback ID: {cb['id']}")
                    print(f"Merchant ID: {cb['merchant_id']}")
                    print(f"Callback URL: {cb['callback_url']}")
                    print(f"Response Code: {cb['response_code']}")
                    print(f"Created: {cb['created_at']}")
                    
                    try:
                        request_data = json.loads(cb['request_data']) if cb['request_data'] else {}
                        print(f"\n📥 Request Data:")
                        print(json.dumps(request_data, indent=2))
                    except:
                        print(f"\n📥 Request Data: {cb['request_data'][:200]}")
                    
                    print()
            else:
                print("❌ No ViyonaPay callbacks found in callback_logs")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

def check_server_logs():
    """Check server logs for ViyonaPay callbacks"""
    print("\n" + "="*80)
    print("  SERVER LOGS CHECK")
    print("="*80)
    
    try:
        print("\n🔍 Searching systemd logs for ViyonaPay callbacks...")
        
        cmd = [
            'sudo', 'journalctl', '-u', 'moneyone-api',
            '-n', '500', '--no-pager'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            print(f"❌ Error reading logs: {result.stderr}")
            return
        
        logs = result.stdout
        lines = logs.split('\n')
        
        # Look for callback entries
        callback_count = 0
        for line in lines:
            if 'VIYONAPAY Payin Callback Received' in line:
                callback_count += 1
        
        if callback_count > 0:
            print(f"\n✅ Found {callback_count} ViyonaPay callback(s) in logs")
            print("\n💡 Run this for detailed callback data:")
            print("   python3 backend/check_viyonapay_callback_raw.py")
        else:
            print("\n❌ No ViyonaPay callbacks found in logs")
            
            # Check for endpoint hits
            endpoint_hits = 0
            for line in lines:
                if '/api/callback/viyonapay/payin' in line:
                    endpoint_hits += 1
            
            if endpoint_hits > 0:
                print(f"\n⚠️  Found {endpoint_hits} hits to callback endpoint")
                print("   (but no callback processing logs)")
            else:
                print("\n❌ No hits to /api/callback/viyonapay/payin endpoint")
                print("\n📋 This means ViyonaPay has NOT sent any callbacks yet")
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout reading logs")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ViyonaPay Callback Complete Check".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    check_database()
    check_server_logs()
    
    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    print("\n📋 Expected callback URL:")
    print("   https://api.moneyone.co.in/api/callback/viyonapay/payin")
    print("\n💡 If no callbacks received, check:")
    print("   1. Callback URL configured with ViyonaPay")
    print("   2. ViyonaPay IP whitelisted in firewall")
    print("   3. Transaction actually completed on ViyonaPay side")
    print("   4. Webhook secret key configured correctly")
    print()

if __name__ == "__main__":
    main()
