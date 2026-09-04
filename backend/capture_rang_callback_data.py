#!/usr/bin/env python3
"""
Capture and analyze actual Rang callback data
"""

from database import get_db_connection
import json
from datetime import datetime, timedelta

def check_rang_callback_logs():
    """Check what callback data Rang is actually sending"""
    
    print("=" * 80)
    print("RANG CALLBACK DATA ANALYSIS")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check application logs for Rang callbacks (if logged)
    print("\n1. CHECKING APPLICATION LOGS FOR RANG CALLBACKS")
    print("-" * 50)
    
    # Look for recent Rang transactions that should have received callbacks
    cursor.execute("""
        SELECT txn_id, order_id, status, amount, pg_txn_id, created_at, updated_at, completed_at
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND DATE(created_at) = CURDATE()
        AND pg_txn_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    transactions = cursor.fetchall()
    
    print(f"Found {len(transactions)} Rang transactions with PG_TXN_ID today:")
    
    for txn in transactions:
        print(f"\nTXN: {txn['txn_id']}")
        print(f"Order ID: {txn['order_id']}")
        print(f"Status: {txn['status']}")
        print(f"Amount: ₹{txn['amount']}")
        print(f"PG TXN ID: {txn['pg_txn_id']}")
        print(f"Created: {txn['created_at']}")
        print(f"Updated: {txn['updated_at']}")
        print(f"Completed: {txn['completed_at']}")
        
        # Check if status was updated (updated_at > created_at indicates callback received)
        if txn['updated_at'] > txn['created_at']:
            time_diff = txn['updated_at'] - txn['created_at']
            print(f"✅ Status updated {time_diff} after creation (callback likely received)")
        else:
            print(f"❌ No status update (no callback received)")
    
    # Check callback_logs table for Rang callbacks
    print(f"\n\n2. CHECKING CALLBACK_LOGS TABLE")
    print("-" * 50)
    
    cursor.execute("""
        SELECT cl.*, pt.order_id, pt.pg_partner
        FROM callback_logs cl
        JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
        WHERE pt.pg_partner = 'Rang'
        AND DATE(cl.created_at) = CURDATE()
        ORDER BY cl.created_at DESC
        LIMIT 10
    """)
    
    callback_logs = cursor.fetchall()
    
    if callback_logs:
        print(f"Found {len(callback_logs)} Rang callback logs today:")
        
        for log in callback_logs:
            print(f"\n--- Callback Log ---")
            print(f"TXN ID: {log['txn_id']}")
            print(f"Order ID: {log['order_id']}")
            print(f"Callback URL: {log['callback_url']}")
            print(f"Response Code: {log['response_code']}")
            print(f"Created: {log['created_at']}")
            
            # Parse request data to see what we sent to merchant
            try:
                request_data = json.loads(log['request_data'])
                print(f"Request Data Sent to Merchant:")
                for key, value in request_data.items():
                    print(f"  {key}: {value}")
            except:
                print(f"Request Data (raw): {log['request_data']}")
            
            print(f"Response from Merchant: {log['response_data'][:200]}...")
    else:
        print("❌ No callback logs found for Rang transactions today")
    
    # Check for any raw callback data in application logs
    print(f"\n\n3. CHECKING FOR RAW CALLBACK DATA")
    print("-" * 50)
    
    # This would require checking application log files
    # For now, let's check if we can find any pattern in the database
    
    cursor.execute("""
        SELECT txn_id, order_id, status, bank_ref_no, pg_txn_id, 
               created_at, updated_at, completed_at
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND DATE(created_at) = CURDATE()
        AND (bank_ref_no IS NOT NULL OR completed_at IS NOT NULL)
        ORDER BY updated_at DESC
    """)
    
    processed_txns = cursor.fetchall()
    
    if processed_txns:
        print(f"Found {len(processed_txns)} Rang transactions that were processed:")
        
        for txn in processed_txns:
            print(f"\n--- Processed Transaction ---")
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Status: {txn['status']}")
            print(f"Bank Ref No (UTR): {txn['bank_ref_no']}")
            print(f"PG TXN ID: {txn['pg_txn_id']}")
            print(f"Created: {txn['created_at']}")
            print(f"Updated: {txn['updated_at']}")
            print(f"Completed: {txn['completed_at']}")
    else:
        print("❌ No processed Rang transactions found today")
    
    cursor.close()
    conn.close()

def analyze_callback_issues():
    """Analyze why callbacks might not be working"""
    
    print(f"\n\n4. CALLBACK ISSUE ANALYSIS")
    print("-" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check transactions that should have callbacks but don't
    cursor.execute("""
        SELECT txn_id, order_id, status, pg_txn_id, callback_url,
               created_at, updated_at
        FROM payin_transactions 
        WHERE pg_partner = 'Rang' 
        AND DATE(created_at) = CURDATE()
        AND pg_txn_id IS NOT NULL
        AND status = 'INITIATED'
        AND updated_at = created_at
        ORDER BY created_at DESC
    """)
    
    stuck_transactions = cursor.fetchall()
    
    if stuck_transactions:
        print(f"Found {len(stuck_transactions)} transactions stuck in INITIATED status:")
        
        for txn in stuck_transactions:
            print(f"\n--- Stuck Transaction ---")
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"PG TXN ID: {txn['pg_txn_id']}")
            print(f"Callback URL: {txn['callback_url']}")
            print(f"Created: {txn['created_at']}")
            print(f"Issue: Has PG_TXN_ID but no callback received")
    
    # Check merchant callback configuration
    cursor.execute("""
        SELECT merchant_id, payin_callback_url
        FROM merchant_callbacks
        WHERE merchant_id = '7679022140'
    """)
    
    merchant_config = cursor.fetchone()
    
    print(f"\n--- Merchant Callback Configuration ---")
    if merchant_config:
        print(f"Merchant ID: {merchant_config['merchant_id']}")
        print(f"Payin Callback URL: {merchant_config['payin_callback_url']}")
    else:
        print("❌ No merchant callback configuration found for merchant 7679022140")
    
    cursor.close()
    conn.close()

def suggest_fixes():
    """Suggest fixes for the callback issues"""
    
    print(f"\n\n5. SUGGESTED FIXES")
    print("-" * 50)
    
    print("""
ISSUE 1: Status Not Updating
- Problem: Transactions remain in INITIATED status despite having PG_TXN_ID
- Cause: Rang callbacks not reaching our endpoint or not being processed
- Fix: Check callback endpoint logs and verify Rang callback format

ISSUE 2: Merchant Forwarding Not Working  
- Problem: No entries in callback_logs table
- Cause: Our callback handler not executing merchant forwarding logic
- Fix: Debug callback handler execution

IMMEDIATE ACTIONS:
1. Check server logs: sudo tail -f /var/log/nginx/access.log | grep rang
2. Test callback endpoint: curl -X POST https://api.moneyone.co.in/rang-payin-callback
3. Verify Rang callback format matches our handler expectations
4. Check if callbacks are hitting webhook.site but not our server

DEBUGGING STEPS:
1. Add more logging to rang_callback_routes.py
2. Create test callback with known transaction
3. Verify merchant callback URL configuration
4. Check for any errors in application logs
    """)

if __name__ == "__main__":
    check_rang_callback_logs()
    analyze_callback_issues()
    suggest_fixes()