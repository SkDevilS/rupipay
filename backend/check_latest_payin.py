#!/usr/bin/env python3
"""
Check the latest payin transaction and trace where the wallet credit went
"""

import pymysql
from database import get_db_connection
from datetime import datetime

def check_latest_payin():
    """Check the most recent payin transaction"""
    
    print("=" * 80)
    print("Latest PayIn Transaction Analysis")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get the most recent payin
            print("\n1. Finding most recent payin transaction...")
            cursor.execute("""
                SELECT * FROM payin_transactions
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            payin = cursor.fetchone()
            
            if not payin:
                print("❌ No payin transactions found")
                return
            
            print(f"\n✓ Found PayIn Transaction:")
            print(f"  TXN ID: {payin['txn_id']}")
            print(f"  Order ID: {payin['order_id']}")
            print(f"  Merchant: {payin['merchant_id']}")
            print(f"  Status: {payin['status']}")
            print(f"  Amount: ₹{payin['amount']}")
            print(f"  Charge: ₹{payin['charge_amount']}")
            print(f"  Net Amount: ₹{payin['net_amount']}")
            print(f"  Gateway: {payin.get('pg_partner', 'PayU')}")
            print(f"  Created: {payin['created_at']}")
            print(f"  Completed: {payin.get('completed_at', 'Not completed')}")
            
            # Check merchant_wallet_transactions
            print(f"\n2. Checking merchant_wallet_transactions...")
            cursor.execute("""
                SELECT * FROM merchant_wallet_transactions
                WHERE reference_id = %s OR merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (payin['txn_id'], payin['merchant_id']))
            
            merchant_txns = cursor.fetchall()
            
            if merchant_txns:
                print(f"  Found {len(merchant_txns)} merchant wallet transactions:")
                for txn in merchant_txns:
                    print(f"\n    TXN ID: {txn['txn_id']}")
                    print(f"    Type: {txn['txn_type']}")
                    print(f"    Amount: ₹{txn['amount']}")
                    print(f"    Balance Before: ₹{txn['balance_before']}")
                    print(f"    Balance After: ₹{txn['balance_after']}")
                    print(f"    Description: {txn['description']}")
                    print(f"    Reference: {txn.get('reference_id', 'N/A')}")
                    print(f"    Created: {txn['created_at']}")
                    
                    if txn.get('reference_id') == payin['txn_id']:
                        if txn['txn_type'] == 'UNSETTLED_CREDIT':
                            print(f"    ✓ CORRECT: This is the payin credit using unsettled wallet")
                        elif txn['txn_type'] == 'CREDIT':
                            print(f"    ❌ WRONG: This is using OLD wallet system")
            else:
                print(f"  ❌ No merchant wallet transactions found for this payin!")
            
            # Check old wallet_transactions table
            print(f"\n3. Checking old wallet_transactions table...")
            cursor.execute("""
                SELECT * FROM wallet_transactions
                WHERE txn_id = %s OR (merchant_id = %s AND created_at >= %s)
                ORDER BY created_at DESC
                LIMIT 5
            """, (payin['txn_id'], payin['merchant_id'], payin['created_at']))
            
            old_txns = cursor.fetchall()
            
            if old_txns:
                print(f"  ⚠️  Found {len(old_txns)} entries in OLD wallet_transactions table:")
                for txn in old_txns:
                    print(f"\n    TXN ID: {txn['txn_id']}")
                    print(f"    Type: {txn['txn_type']}")
                    print(f"    Amount: ₹{txn['amount']}")
                    print(f"    Description: {txn['description']}")
                    print(f"    Created: {txn['created_at']}")
                    print(f"    ❌ THIS IS THE PROBLEM - Using old wallet system!")
            else:
                print(f"  ✓ No entries in old wallet_transactions table")
            
            # Check admin_wallet_transactions
            print(f"\n4. Checking admin_wallet_transactions...")
            cursor.execute("""
                SELECT * FROM admin_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (payin['txn_id'],))
            
            admin_txns = cursor.fetchall()
            
            if admin_txns:
                print(f"  Found {len(admin_txns)} admin wallet transactions:")
                for txn in admin_txns:
                    print(f"\n    TXN ID: {txn['txn_id']}")
                    print(f"    Type: {txn['txn_type']}")
                    print(f"    Amount: ₹{txn['amount']}")
                    print(f"    Description: {txn['description']}")
                    print(f"    Created: {txn['created_at']}")
                    
                    if txn['txn_type'] == 'UNSETTLED_CREDIT':
                        print(f"    ✓ CORRECT: Admin unsettled wallet credited")
            else:
                print(f"  ❌ No admin wallet transactions found for this payin!")
            
            # Check current wallet balances
            print(f"\n5. Checking current wallet balances...")
            cursor.execute("""
                SELECT balance, settled_balance, unsettled_balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (payin['merchant_id'],))
            
            merchant_wallet = cursor.fetchone()
            
            if merchant_wallet:
                print(f"\n  Merchant Wallet ({payin['merchant_id']}):")
                print(f"    Old Balance: ₹{merchant_wallet['balance']}")
                print(f"    Settled: ₹{merchant_wallet['settled_balance']}")
                print(f"    Unsettled: ₹{merchant_wallet['unsettled_balance']}")
            
            cursor.execute("""
                SELECT main_balance, unsettled_balance
                FROM admin_wallet
                WHERE admin_id = 'admin'
            """)
            
            admin_wallet = cursor.fetchone()
            
            if admin_wallet:
                print(f"\n  Admin Wallet:")
                print(f"    Main Balance: ₹{admin_wallet['main_balance']}")
                print(f"    Unsettled: ₹{admin_wallet['unsettled_balance']}")
            
            # DIAGNOSIS
            print(f"\n" + "=" * 80)
            print("DIAGNOSIS")
            print("=" * 80)
            
            has_merchant_unsettled = False
            has_admin_unsettled = False
            has_old_wallet = False
            
            for txn in merchant_txns:
                if txn.get('reference_id') == payin['txn_id'] and txn['txn_type'] == 'UNSETTLED_CREDIT':
                    has_merchant_unsettled = True
            
            for txn in admin_txns:
                if txn['txn_type'] == 'UNSETTLED_CREDIT':
                    has_admin_unsettled = True
            
            if old_txns:
                has_old_wallet = True
            
            if has_merchant_unsettled and has_admin_unsettled and not has_old_wallet:
                print("\n✅ FIX IS WORKING CORRECTLY!")
                print("   - Merchant unsettled wallet credited")
                print("   - Admin unsettled wallet credited")
                print("   - Not using old wallet system")
            elif has_old_wallet:
                print("\n❌ STILL USING OLD WALLET SYSTEM!")
                print("   The code changes were not deployed or backend not restarted")
                print("\n   ACTION REQUIRED:")
                print("   1. Deploy the fix: ./deploy_payin_unsettled_fix.sh")
                print("   2. Or manually restart backend: sudo systemctl restart moneyone-backend")
            elif not has_merchant_unsettled:
                print("\n❌ MERCHANT UNSETTLED WALLET NOT CREDITED!")
                print("   The payin callback/status check did not execute properly")
            elif not has_admin_unsettled:
                print("\n❌ ADMIN UNSETTLED WALLET NOT CREDITED!")
                print("   The admin wallet credit logic is not working")
            else:
                print("\n⚠️  UNCLEAR STATUS")
                print("   Please check the logs for errors")
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_latest_payin()
