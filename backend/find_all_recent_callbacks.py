#!/usr/bin/env python3
"""
Find ALL recent callbacks regardless of content
This will help us locate the ViyonaPay callback data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime, timedelta

def find_all_callbacks():
    """Find all recent callbacks from any source"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("  CHECKING ALL RECENT CALLBACKS (Last 24 hours)")
            print("="*80)
            
            # Get all callbacks from last 24 hours
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
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            callbacks = cursor.fetchall()
            
            if not callbacks:
                print("\n❌ No callbacks found in last 24 hours")
                print("\nLet's check if the table exists and has any data...")
                
                cursor.execute("SHOW TABLES LIKE 'callback_logs'")
                if not cursor.fetchone():
                    print("❌ callback_logs table does not exist!")
                    return
                
                cursor.execute("SELECT COUNT(*) as count FROM callback_logs")
                count = cursor.fetchone()
                print(f"\nTotal callbacks in table: {count['count']}")
                
                if count['count'] > 0:
                    cursor.execute("""
                        SELECT created_at 
                        FROM callback_logs 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    latest = cursor.fetchone()
                    print(f"Most recent callback: {latest['created_at']}")
                
                return
            
            print(f"\n✅ Found {len(callbacks)} callback(s) in last 24 hours\n")
            
            for idx, callback in enumerate(callbacks, 1):
                print(f"\n{'='*80}")
                print(f"  CALLBACK #{idx}")
                print(f"{'='*80}")
                print(f"ID: {callback['id']}")
                print(f"Merchant ID: {callback['merchant_id']}")
                print(f"Callback URL: {callback['callback_url']}")
                print(f"Response Code: {callback.get('response_code', 'N/A')}")
                print(f"Created: {callback['created_at']}")
                
                print("\n" + "-"*80)
                print("  REQUEST DATA (First 500 chars)")
                print("-"*80)
                
                request_data = callback['request_data'] or ''
                print(request_data[:500])
                
                if len(request_data) > 500:
                    print(f"\n... (truncated, total length: {len(request_data)} chars)")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(request_data)
                    print("\n✓ Valid JSON structure")
                    print(f"  Keys: {list(parsed.keys())}")
                except:
                    print("\n⚠️  Not JSON or invalid JSON")
                
                if callback['response_data']:
                    print("\n" + "-"*80)
                    print("  RESPONSE DATA (First 200 chars)")
                    print("-"*80)
                    print(str(callback['response_data'])[:200])
            
            print("\n" + "="*80)
            print("  CHECKING PAYIN_TRANSACTIONS")
            print("="*80)
            
            # Check recent payin transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_partner,
                    pg_txn_id,
                    created_at
                FROM payin_transactions
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            if transactions:
                print(f"\n✅ Found {len(transactions)} recent transaction(s):\n")
                for txn in transactions:
                    print(f"  • {txn['created_at']} | {txn['pg_partner']:15} | {txn['txn_id']} | Status: {txn['status']}")
            else:
                print("\n❌ No recent transactions found")
            
            # Check for ViyonaPay specifically
            print("\n" + "="*80)
            print("  CHECKING FOR VIYONAPAY TRANSACTIONS")
            print("="*80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    utr,
                    created_at,
                    updated_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            viyona_txns = cursor.fetchall()
            
            if viyona_txns:
                print(f"\n✅ Found {len(viyona_txns)} ViyonaPay transaction(s):\n")
                for txn in viyona_txns:
                    print(f"\n{'-'*80}")
                    print(f"Transaction ID: {txn['txn_id']}")
                    print(f"Order ID: {txn['order_id']}")
                    print(f"Amount: ₹{txn['amount']}")
                    print(f"Status: {txn['status']}")
                    print(f"PG TXN ID: {txn['pg_txn_id']}")
                    print(f"Bank Ref: {txn['bank_ref_no']}")
                    print(f"UTR: {txn['utr']}")
                    print(f"Created: {txn['created_at']}")
                    print(f"Updated: {txn['updated_at']}")
            else:
                print("\n❌ No ViyonaPay transactions found")
            
            # Check application logs table if it exists
            print("\n" + "="*80)
            print("  CHECKING APPLICATION LOGS")
            print("="*80)
            
            cursor.execute("SHOW TABLES LIKE '%log%'")
            log_tables = cursor.fetchall()
            
            if log_tables:
                print("\nAvailable log tables:")
                for table in log_tables:
                    table_name = list(table.values())[0]
                    print(f"  • {table_name}")
            else:
                print("\n⚠️  No log tables found")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  Find All Recent Callbacks")
    print("  Comprehensive callback search tool")
    print("="*80)
    find_all_callbacks()
    print("\n" + "="*80)
