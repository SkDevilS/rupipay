#!/usr/bin/env python3
"""
Verify PayIn Unsettled Wallet Fix
This script checks if payin transactions are properly crediting unsettled wallets
"""

import pymysql
from database import get_db_connection
from datetime import datetime, timedelta

def verify_payin_unsettled_fix():
    """Verify that recent payins are in unsettled wallet, not old balance"""
    
    print("=" * 80)
    print("PayIn Unsettled Wallet Fix Verification")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check recent successful payins
            print("\n1. Checking recent successful payin transactions...")
            cursor.execute("""
                SELECT txn_id, merchant_id, amount, charge_amount, net_amount, 
                       status, pg_partner, completed_at
                FROM payin_transactions
                WHERE status = 'SUCCESS' 
                AND completed_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY completed_at DESC
                LIMIT 10
            """)
            
            recent_payins = cursor.fetchall()
            
            if not recent_payins:
                print("⚠️  No successful payins in last 24 hours")
                print("   Please test a payin transaction to verify the fix")
                return
            
            print(f"✓ Found {len(recent_payins)} successful payins in last 24 hours\n")
            
            # Check each payin
            for payin in recent_payins:
                print(f"\nChecking PayIn: {payin['txn_id']}")
                print(f"  Merchant: {payin['merchant_id']}")
                print(f"  Amount: ₹{payin['amount']}")
                print(f"  Charge: ₹{payin['charge_amount']}")
                print(f"  Net Amount: ₹{payin['net_amount']}")
                print(f"  Gateway: {payin['pg_partner']}")
                print(f"  Completed: {payin['completed_at']}")
                
                # Check merchant wallet transactions
                cursor.execute("""
                    SELECT txn_type, amount, description, created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (payin['txn_id'],))
                
                merchant_txns = cursor.fetchall()
                
                if merchant_txns:
                    print(f"\n  Merchant Wallet Transactions:")
                    for txn in merchant_txns:
                        print(f"    - Type: {txn['txn_type']}, Amount: ₹{txn['amount']}, Desc: {txn['description']}")
                        if txn['txn_type'] == 'UNSETTLED_CREDIT':
                            print(f"      ✓ CORRECT: Using unsettled wallet")
                        elif txn['txn_type'] == 'CREDIT':
                            print(f"      ❌ WRONG: Using old wallet system")
                else:
                    print(f"  ❌ No merchant wallet transaction found!")
                
                # Check admin wallet transactions
                cursor.execute("""
                    SELECT txn_type, amount, description, created_at
                    FROM admin_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (payin['txn_id'],))
                
                admin_txns = cursor.fetchall()
                
                if admin_txns:
                    print(f"\n  Admin Wallet Transactions:")
                    for txn in admin_txns:
                        print(f"    - Type: {txn['txn_type']}, Amount: ₹{txn['amount']}, Desc: {txn['description']}")
                        if txn['txn_type'] == 'UNSETTLED_CREDIT':
                            print(f"      ✓ CORRECT: Using unsettled wallet")
                        elif txn['txn_type'] == 'CREDIT':
                            print(f"      ❌ WRONG: Using old wallet system")
                else:
                    print(f"  ❌ No admin wallet transaction found!")
                
                # Check old wallet_transactions table (should be empty for new payins)
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM wallet_transactions
                    WHERE txn_id = %s
                """, (payin['txn_id'],))
                
                old_txn_count = cursor.fetchone()['count']
                if old_txn_count > 0:
                    print(f"\n  ❌ WARNING: Found {old_txn_count} entries in OLD wallet_transactions table!")
                    print(f"     This means the old wallet system is still being used")
            
            # Check current wallet balances
            print("\n" + "=" * 80)
            print("2. Checking current wallet balances...")
            print("=" * 80)
            
            # Merchant wallets
            cursor.execute("""
                SELECT merchant_id, balance, settled_balance, unsettled_balance
                FROM merchant_wallet
                ORDER BY unsettled_balance DESC
                LIMIT 5
            """)
            
            merchant_wallets = cursor.fetchall()
            
            print("\nTop 5 Merchant Wallets by Unsettled Balance:")
            for wallet in merchant_wallets:
                print(f"  Merchant: {wallet['merchant_id']}")
                print(f"    Old Balance: ₹{wallet['balance']}")
                print(f"    Settled: ₹{wallet['settled_balance']}")
                print(f"    Unsettled: ₹{wallet['unsettled_balance']}")
                
                if wallet['unsettled_balance'] > 0:
                    print(f"    ✓ Has unsettled balance")
                else:
                    print(f"    ⚠️  No unsettled balance")
            
            # Admin wallet
            cursor.execute("""
                SELECT admin_id, main_balance, unsettled_balance
                FROM admin_wallet
                WHERE admin_id = 'admin'
            """)
            
            admin_wallet = cursor.fetchone()
            
            if admin_wallet:
                print(f"\nAdmin Wallet:")
                print(f"  Main Balance: ₹{admin_wallet['main_balance']}")
                print(f"  Unsettled Balance: ₹{admin_wallet['unsettled_balance']}")
                
                if admin_wallet['unsettled_balance'] > 0:
                    print(f"  ✓ Has unsettled balance")
                else:
                    print(f"  ⚠️  No unsettled balance")
            
            # Summary
            print("\n" + "=" * 80)
            print("VERIFICATION SUMMARY")
            print("=" * 80)
            
            # Count correct vs incorrect transactions
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN txn_type = 'UNSETTLED_CREDIT' THEN 1 ELSE 0 END) as correct_count,
                    SUM(CASE WHEN txn_type = 'CREDIT' THEN 1 ELSE 0 END) as old_count
                FROM merchant_wallet_transactions
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                AND description LIKE '%Payin%'
            """)
            
            summary = cursor.fetchone()
            
            print(f"\nMerchant Wallet Transactions (Last 24h):")
            print(f"  ✓ Using Unsettled Wallet: {summary['correct_count']}")
            print(f"  ❌ Using Old Wallet: {summary['old_count']}")
            
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM admin_wallet_transactions
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                AND txn_type = 'UNSETTLED_CREDIT'
                AND description LIKE '%Payin%'
            """)
            
            admin_count = cursor.fetchone()['count']
            print(f"\nAdmin Wallet Transactions (Last 24h):")
            print(f"  ✓ Using Unsettled Wallet: {admin_count}")
            
            if summary['old_count'] == 0 and summary['correct_count'] > 0 and admin_count > 0:
                print("\n✅ FIX VERIFIED: All payin transactions are using unsettled wallet!")
            elif summary['old_count'] > 0:
                print("\n❌ FIX NOT WORKING: Some transactions still using old wallet system")
                print("   Please check if the deployment was successful")
            else:
                print("\n⚠️  No recent transactions to verify")
                print("   Please test a payin transaction")
    
    finally:
        conn.close()

if __name__ == '__main__':
    verify_payin_unsettled_fix()
