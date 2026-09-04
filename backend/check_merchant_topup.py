#!/usr/bin/env python3
"""
Check if merchant received the topup in their wallet
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

merchant_id = "7679022140"  # Test User

print("\n" + "=" * 80)
print(f"CHECKING MERCHANT WALLET: {merchant_id}")
print("=" * 80)

try:
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Check merchant_wallet table
        print("\n1. MERCHANT_WALLET TABLE:")
        cursor.execute("""
            SELECT merchant_id, balance, settled_balance, unsettled_balance, last_updated
            FROM merchant_wallet
            WHERE merchant_id = %s
        """, (merchant_id,))
        wallet = cursor.fetchone()
        
        if wallet:
            print(f"   Balance: ₹{float(wallet['balance']):,.2f}")
            print(f"   Settled: ₹{float(wallet['settled_balance']):,.2f}")
            print(f"   Unsettled: ₹{float(wallet['unsettled_balance']):,.2f}")
            print(f"   Last Updated: {wallet['last_updated']}")
        else:
            print("   No wallet found")
        
        # Check recent fund requests
        print("\n2. RECENT FUND REQUESTS:")
        cursor.execute("""
            SELECT request_id, amount, status, requested_at, processed_at
            FROM fund_requests
            WHERE merchant_id = %s
            ORDER BY requested_at DESC
            LIMIT 5
        """, (merchant_id,))
        requests = cursor.fetchall()
        
        for req in requests:
            print(f"   {req['request_id']}: ₹{float(req['amount']):,.2f} - {req['status']}")
            print(f"      Requested: {req['requested_at']}, Processed: {req['processed_at']}")
        
        # Check merchant_wallet_transactions
        print("\n3. RECENT WALLET TRANSACTIONS:")
        cursor.execute("""
            SELECT txn_id, txn_type, amount, balance_before, balance_after, description, created_at
            FROM merchant_wallet_transactions
            WHERE merchant_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (merchant_id,))
        txns = cursor.fetchall()
        
        for txn in txns:
            print(f"   {txn['txn_id']}: {txn['txn_type']} ₹{float(txn['amount']):,.2f}")
            print(f"      Before: ₹{float(txn['balance_before']):,.2f}, After: ₹{float(txn['balance_after']):,.2f}")
            print(f"      {txn['description']}")
            print(f"      {txn['created_at']}")
            print()
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
