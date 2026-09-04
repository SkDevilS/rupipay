#!/usr/bin/env python3
"""
Diagnose the topup issue where large amounts fail with insufficient balance error
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from decimal import Decimal

def diagnose_topup_issue():
    print("\n" + "=" * 80)
    print("DIAGNOSING TOPUP ISSUE - Large Amounts Failing")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Check admin wallet balance calculation
            print("\n1. ADMIN WALLET BALANCE CALCULATION:")
            print("-" * 80)
            
            # PayIN amount
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = cursor.fetchone()['total_payin']
            print(f"   Total PayIN (SUCCESS):        ₹{float(total_payin):,.2f}")
            print(f"   Type: {type(total_payin)}, Value: {total_payin}")
            
            # Approved fund requests (debits)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = cursor.fetchone()['total_topup']
            print(f"   Total Topups (APPROVED):      ₹{float(total_topup):,.2f}")
            print(f"   Type: {type(total_topup)}, Value: {total_topup}")
            
            # Fetch from merchants (credits)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            total_fetch = cursor.fetchone()['total_fetch']
            print(f"   Total Fetch (from merchants): ₹{float(total_fetch):,.2f}")
            print(f"   Type: {type(total_fetch)}, Value: {total_fetch}")
            
            # Admin payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
                AND reference_id LIKE 'ADMIN%'
            """)
            total_payout = cursor.fetchone()['total_payout']
            print(f"   Total Admin Payouts:          ₹{float(total_payout):,.2f}")
            print(f"   Type: {type(total_payout)}, Value: {total_payout}")
            
            # Calculate balance using float conversion (current code)
            balance_float = float(total_payin) + float(total_fetch) - float(total_topup) - float(total_payout)
            print(f"\n   CALCULATED BALANCE (float):   ₹{balance_float:,.2f}")
            
            # Calculate balance using Decimal (correct way)
            balance_decimal = Decimal(str(total_payin)) + Decimal(str(total_fetch)) - Decimal(str(total_topup)) - Decimal(str(total_payout))
            print(f"   CALCULATED BALANCE (Decimal): ₹{float(balance_decimal):,.2f}")
            
            # Check for precision issues
            if abs(balance_float - float(balance_decimal)) > 0.01:
                print(f"\n   ⚠️  PRECISION ISSUE DETECTED!")
                print(f"   Difference: ₹{abs(balance_float - float(balance_decimal)):,.2f}")
            
            # 2. Check recent failed topup attempts
            print("\n\n2. RECENT FUND REQUESTS:")
            print("-" * 80)
            cursor.execute("""
                SELECT request_id, merchant_id, amount, status, requested_at
                FROM fund_requests
                ORDER BY requested_at DESC
                LIMIT 10
            """)
            requests = cursor.fetchall()
            
            for req in requests:
                print(f"   {req['request_id']}: ₹{float(req['amount']):,.2f} - {req['status']} ({req['merchant_id']})")
            
            # 3. Check admin wallet transactions
            print("\n\n3. RECENT ADMIN WALLET TRANSACTIONS:")
            print("-" * 80)
            cursor.execute("""
                SELECT txn_id, txn_type, amount, balance_before, balance_after, description, created_at
                FROM admin_wallet_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            txns = cursor.fetchall()
            
            for txn in txns:
                print(f"   {txn['txn_id']}: {txn['txn_type']} ₹{float(txn['amount']):,.2f}")
                print(f"      Before: ₹{float(txn['balance_before']):,.2f}, After: ₹{float(txn['balance_after']):,.2f}")
                print(f"      {txn['description'][:60]}")
            
            # 4. Test with sample amounts
            print("\n\n4. TESTING BALANCE CHECK WITH SAMPLE AMOUNTS:")
            print("-" * 80)
            test_amounts = [1000, 10000, 50000, 100000, 200000, 400000, 500000]
            
            for test_amount in test_amounts:
                sufficient = balance_float >= test_amount
                status = "✓ PASS" if sufficient else "✗ FAIL"
                print(f"   Amount: ₹{test_amount:>8,.0f} - {status} (Balance: ₹{balance_float:,.2f})")
            
            # 5. Check data type issues
            print("\n\n5. DATA TYPE ANALYSIS:")
            print("-" * 80)
            print(f"   total_payin type:  {type(total_payin).__name__}")
            print(f"   total_topup type:  {type(total_topup).__name__}")
            print(f"   total_fetch type:  {type(total_fetch).__name__}")
            print(f"   total_payout type: {type(total_payout).__name__}")
            
            # Check if conversion to float causes issues
            print(f"\n   Float conversion test:")
            print(f"   float(total_payin):  {float(total_payin)}")
            print(f"   float(total_topup):  {float(total_topup)}")
            
            # 6. Check for orphaned transactions
            print("\n\n6. CHECKING FOR ORPHANED TRANSACTIONS:")
            print("-" * 80)
            
            # Check if there are admin wallet debits without corresponding fund requests
            cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM admin_wallet_transactions
                WHERE txn_type = 'DEBIT'
                AND reference_id NOT IN (SELECT request_id FROM fund_requests WHERE status = 'APPROVED')
                AND reference_id IS NOT NULL
            """)
            orphaned = cursor.fetchone()
            print(f"   Orphaned admin debits: {orphaned['count']} transactions, ₹{float(orphaned['total']):,.2f}")
            
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_topup_issue()
