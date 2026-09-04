#!/usr/bin/env python3
"""
Check if Rang callbacks were received today
Analyzes callback logs and server access patterns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json

def check_callback_logs_today():
    """Check callback_logs table for Rang callbacks today"""
    print("CHECKING CALLBACK LOGS TABLE")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's date range
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check for any callbacks with Rang-related data
        cursor.execute("""
            SELECT 
                id, merchant_id, txn_id, callback_url, 
                request_data, response_code, response_data, created_at
            FROM callback_logs 
            WHERE DATE(created_at) = CURDATE()
            AND (
                callback_url LIKE '%rang%' 
                OR request_data LIKE '%Rang%'
                OR request_data LIKE '%rang%'
            )
            ORDER BY created_at DESC
        """)
        
        rang_callbacks = cursor.fetchall()
        
        if rang_callbacks:
            print(f"✅ Found {len(rang_callbacks)} Rang callback(s) today!")
            print()
            
            for cb in rang_callbacks:
                print(f"Callback ID: {cb['id']}")
                print(f"  Time: {cb['created_at']}")
                print(f"  Merchant: {cb['merchant_id']}")
                print(f"  TXN ID: {cb['txn_id']}")
                print(f"  URL: {cb['callback_url']}")
                print(f"  Response Code: {cb['response_code']}")
                
                if cb['request_data']:
                    try:
                        req_data = json.loads(cb['request_data'])
                        print(f"  Request Data: {json.dumps(req_data, indent=4)}")
                    except:
                        print(f"  Request Data: {cb['request_data'][:200]}")
                
                if cb['response_data']:
                    print(f"  Response: {cb['response_data'][:200]}")
                
                print("-" * 60)
        else:
            print("❌ No Rang callbacks found in callback_logs today")
        
        cursor.close()
        conn.close()
        
        return len(rang_callbacks) if rang_callbacks else 0
        
    except Exception as e:
        print(f"❌ Error checking callback logs: {e}")
        return 0

def check_rang_transactions_today():
    """Check Rang transactions created today"""
    print("\nCHECKING RANG TRANSACTIONS TODAY")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                txn_id, order_id, merchant_id, amount, status,
                bank_ref_no, pg_txn_id, created_at, completed_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            print(f"Found {len(transactions)} Rang transaction(s) today:")
            print()
            
            for txn in transactions:
                print(f"TXN ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Merchant: {txn['merchant_id']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Status: {txn['status']}")
                print(f"  UTR: {txn['bank_ref_no'] or 'None'}")
                print(f"  PG TXN ID: {txn['pg_txn_id'] or 'None'}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Completed: {txn['completed_at'] or 'None'}")
                print("-" * 60)
        else:
            print("❌ No Rang transactions created today")
        
        cursor.close()
        conn.close()
        
        return transactions if transactions else []
        
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")
        return []

def check_wallet_transactions_for_rang():
    """Check if any wallet transactions were created for Rang payins today"""
    print("\nCHECKING WALLET TRANSACTIONS")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check merchant wallet transactions with Rang reference
        cursor.execute("""
            SELECT 
                mwt.txn_id, mwt.merchant_id, mwt.txn_type, 
                mwt.amount, mwt.description, mwt.reference_id, mwt.created_at
            FROM merchant_wallet_transactions mwt
            WHERE DATE(mwt.created_at) = CURDATE()
            AND mwt.description LIKE '%Rang%'
            ORDER BY mwt.created_at DESC
        """)
        
        wallet_txns = cursor.fetchall()
        
        if wallet_txns:
            print(f"✅ Found {len(wallet_txns)} Rang wallet transaction(s) today!")
            print()
            
            for wtxn in wallet_txns:
                print(f"Wallet TXN: {wtxn['txn_id']}")
                print(f"  Merchant: {wtxn['merchant_id']}")
                print(f"  Type: {wtxn['txn_type']}")
                print(f"  Amount: ₹{wtxn['amount']}")
                print(f"  Description: {wtxn['description']}")
                print(f"  Reference: {wtxn['reference_id']}")
                print(f"  Time: {wtxn['created_at']}")
                print("-" * 60)
        else:
            print("❌ No Rang wallet transactions found today")
        
        cursor.close()
        conn.close()
        
        return len(wallet_txns) if wallet_txns else 0
        
    except Exception as e:
        print(f"❌ Error checking wallet transactions: {e}")
        return 0

def check_endpoint_accessibility():
    """Test if Rang callback endpoint is accessible"""
    print("\nTESTING CALLBACK ENDPOINT ACCESSIBILITY")
    print("=" * 60)
    
    import requests
    
    test_url = "https://api.moneyone.co.in/test-rang-callback"
    main_url = "https://api.moneyone.co.in/rang-payin-callback"
    
    # Test the test endpoint
    print(f"Testing: {test_url}")
    try:
        response = requests.post(
            test_url,
            data={'test': 'connectivity_check'},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✅ Test endpoint is accessible")
        else:
            print(f"  ⚠️ Test endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test main endpoint (will return 404 for dummy data, but confirms it's reachable)
    print(f"\nTesting: {main_url}")
    try:
        response = requests.post(
            main_url,
            data={'status_id': '1', 'client_id': 'TEST', 'amount': '100'},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code in [200, 404]:
            print(f"  ✅ Main callback endpoint is accessible")
        else:
            print(f"  ⚠️ Main endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def generate_summary(callback_count, transaction_count, wallet_count):
    """Generate summary report"""
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    print(f"Rang Transactions Created Today: {transaction_count}")
    print(f"Callbacks Logged Today: {callback_count}")
    print(f"Wallet Transactions Today: {wallet_count}")
    print()
    
    if callback_count > 0:
        print("✅ STATUS: Callbacks ARE being received from Rang!")
        print()
        print("Next Steps:")
        print("1. Review callback data above")
        print("2. Verify transaction status updates")
        print("3. Check wallet credit operations")
    elif transaction_count > 0:
        print("⚠️ STATUS: Transactions created but NO callbacks received")
        print()
        print("Possible Issues:")
        print("1. Rang team hasn't configured callback URL")
        print("2. Callback URL is incorrect on Rang side")
        print("3. Callbacks are being sent but not reaching our server")
        print()
        print("Action Required:")
        print("1. Contact Rang team to verify callback URL configuration")
        print("2. Provide them: https://api.moneyone.co.in/rang-payin-callback")
        print("3. Ask them to send a test callback")
    else:
        print("ℹ️ STATUS: No Rang transactions today")
        print()
        print("This is normal if no payments were made through Rang today")
    
    print("=" * 60)

def main():
    print("RANG CALLBACK RECEPTION CHECK")
    print("=" * 60)
    print(f"Checking for: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # Step 1: Check callback logs
    callback_count = check_callback_logs_today()
    
    # Step 2: Check transactions
    transactions = check_rang_transactions_today()
    transaction_count = len(transactions)
    
    # Step 3: Check wallet transactions
    wallet_count = check_wallet_transactions_for_rang()
    
    # Step 4: Test endpoint accessibility
    check_endpoint_accessibility()
    
    # Step 5: Generate summary
    generate_summary(callback_count, transaction_count, wallet_count)

if __name__ == "__main__":
    main()