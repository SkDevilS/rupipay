#!/usr/bin/env python3
"""
Diagnose Fetch Fund Error
This script helps identify the exact error in the fetch fund functionality
"""

import sys
import traceback
from database import get_db_connection

def test_merchant_wallet_overview(merchant_id):
    """Test the merchant wallet overview query"""
    print("\n=== Testing Merchant Wallet Overview ===")
    print(f"Merchant ID: {merchant_id}")
    
    try:
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Test 1: Get approved fund requests
            print("\n1. Testing approved fund requests query...")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            result = cursor.fetchone()
            total_topup = float(result['total_topup']) if result else 0
            print(f"   Total Topup: Rs.{total_topup}")
            
            # Test 2: Get total settlements
            print("\n2. Testing settlements query...")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
            """, (merchant_id,))
            result = cursor.fetchone()
            total_settlements = float(result['total_settlements']) if result else 0
            print(f"   Total Settlements: Rs.{total_settlements}")
            
            # Test 3: Get total fetched by admin
            print("\n3. Testing fetched funds query...")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetched
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s 
                AND txn_type = 'DEBIT'
                AND description LIKE %s
            """, (merchant_id, '%fetched by admin%'))
            result = cursor.fetchone()
            total_fetched = float(result['total_fetched']) if result else 0
            print(f"   Total Fetched: Rs.{total_fetched}")
            
            # Calculate balance
            wallet_balance = total_topup - total_settlements - total_fetched
            print(f"\n   Calculated Balance: Rs.{wallet_balance}")
            print(f"   Formula: {total_topup} - {total_settlements} - {total_fetched} = {wallet_balance}")
            
            # Test 4: Get PayIN data
            print("\n4. Testing PayIN query...")
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as gross_amount,
                    COALESCE(SUM(charge_amount), 0) as total_charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s AND status = 'SUCCESS'
            """, (merchant_id,))
            payin_result = cursor.fetchone()
            gross_payin = float(payin_result['gross_amount']) if payin_result else 0
            total_charges = float(payin_result['total_charges']) if payin_result else 0
            net_payin = float(payin_result['net_amount']) if payin_result else 0
            print(f"   Gross PayIN: Rs.{gross_payin}")
            print(f"   Total Charges: Rs.{total_charges}")
            print(f"   Net PayIN: Rs.{net_payin}")
            
            print("\n✅ All queries executed successfully!")
            print(f"\nFinal Wallet Balance: Rs.{wallet_balance}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

def test_fetch_fund_insert(merchant_id, amount, reason):
    """Test the fetch fund insert query"""
    print("\n=== Testing Fetch Fund Insert ===")
    print(f"Merchant ID: {merchant_id}")
    print(f"Amount: Rs.{amount}")
    print(f"Reason: {reason}")
    
    try:
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Calculate balance first
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as wallet_balance
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            wallet_balance = float(cursor.fetchone()['wallet_balance'])
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
            """, (merchant_id,))
            total_settlements = float(cursor.fetchone()['total_settlements'])
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetched
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s 
                AND txn_type = 'DEBIT'
                AND description LIKE %s
            """, (merchant_id, '%fetched by admin%'))
            total_fetched = float(cursor.fetchone()['total_fetched'])
            
            available_balance = wallet_balance - total_settlements - total_fetched
            balance_after = available_balance - amount
            
            print(f"\nAvailable Balance: Rs.{available_balance}")
            print(f"Balance After: Rs.{balance_after}")
            
            # Test the INSERT query
            print("\nTesting INSERT query...")
            txn_id = f"TEST{int(amount)}"
            description = "Fund fetched by admin - {}".format(reason)
            
            print(f"  txn_id: {txn_id}")
            print(f"  description: {description}")
            
            # Don't actually insert, just test the query construction
            insert_query = """
                INSERT INTO merchant_wallet_transactions 
                (merchant_id, txn_id, txn_type, amount, balance_before, balance_after,
                 description, reference_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            insert_values = (
                merchant_id,
                txn_id,
                'DEBIT',
                amount,
                available_balance,
                balance_after,
                description,
                reason
            )
            
            print("\nQuery parameters:")
            for i, val in enumerate(insert_values):
                print(f"  {i+1}. {val} (type: {type(val).__name__})")
            
            print("\n✅ Query construction successful!")
            print("Note: Not actually inserting to avoid test data")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with the merchant from the screenshot
    merchant_id = "7679022140"
    
    print("=" * 60)
    print("FETCH FUND ERROR DIAGNOSIS")
    print("=" * 60)
    
    # Test 1: Wallet Overview
    test_merchant_wallet_overview(merchant_id)
    
    # Test 2: Fetch Fund Insert
    test_fetch_fund_insert(merchant_id, 100.0, "Test fetch")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
