#!/usr/bin/env python3
"""
Diagnose payin unsettled wallet flow
Check if payin transactions are being created with net_amount and charge_amount
Check if callback is crediting the unsettled wallet
"""

import sys
sys.path.insert(0, '/home/ubuntu/moneyone/backend')

from database import get_db_connection
from datetime import datetime, timedelta

def check_recent_payins():
    """Check recent payin transactions"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent payin transactions
            cursor.execute("""
                SELECT 
                    txn_id, merchant_id, amount, charge_amount, net_amount, 
                    status, pg_partner, created_at
                FROM payin_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            payins = cursor.fetchall()
            print("\n📊 Recent PayIn Transactions:")
            print("=" * 100)
            
            if not payins:
                print("No payin transactions found")
                return
            
            for payin in payins:
                print(f"\nTxn ID: {payin['txn_id']}")
                print(f"  Merchant: {payin['merchant_id']}")
                print(f"  Amount: ₹{payin['amount']:.2f}")
                print(f"  Charge: ₹{payin['charge_amount']:.2f}")
                print(f"  Net Amount: ₹{payin['net_amount']:.2f}")
                print(f"  Status: {payin['status']}")
                print(f"  Gateway: {payin['pg_partner']}")
                print(f"  Created: {payin['created_at']}")
                
                # Check if merchant unsettled wallet was credited
                cursor.execute("""
                    SELECT 
                        txn_id, txn_type, amount, balance_before, balance_after
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (payin['txn_id'],))
                
                wallet_txn = cursor.fetchone()
                if wallet_txn:
                    print(f"  ✓ Merchant unsettled wallet credited: ₹{wallet_txn['amount']:.2f}")
                    print(f"    Balance before: ₹{wallet_txn['balance_before']:.2f}")
                    print(f"    Balance after: ₹{wallet_txn['balance_after']:.2f}")
                else:
                    print(f"  ❌ Merchant unsettled wallet NOT credited")
                
                # Check if admin wallet was credited
                cursor.execute("""
                    SELECT 
                        txn_id, txn_type, amount, balance_before, balance_after
                    FROM admin_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (payin['txn_id'],))
                
                admin_txn = cursor.fetchone()
                if admin_txn:
                    print(f"  ✓ Admin unsettled wallet credited: ₹{admin_txn['amount']:.2f}")
                    print(f"    Balance before: ₹{admin_txn['balance_before']:.2f}")
                    print(f"    Balance after: ₹{admin_txn['balance_after']:.2f}")
                else:
                    print(f"  ❌ Admin unsettled wallet NOT credited")
    
    finally:
        conn.close()

def check_merchant_wallet_status():
    """Check merchant wallet balances"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    merchant_id, balance, settled_balance, unsettled_balance, last_updated
                FROM merchant_wallet
                ORDER BY last_updated DESC
                LIMIT 5
            """)
            
            wallets = cursor.fetchall()
            print("\n💰 Recent Merchant Wallets:")
            print("=" * 100)
            
            for wallet in wallets:
                print(f"\nMerchant: {wallet['merchant_id']}")
                print(f"  Total Balance: ₹{wallet['balance']:.2f}")
                print(f"  Settled: ₹{wallet['settled_balance']:.2f}")
                print(f"  Unsettled: ₹{wallet['unsettled_balance']:.2f}")
                print(f"  Last Updated: {wallet['last_updated']}")
    
    finally:
        conn.close()

def check_admin_wallet_status():
    """Check admin wallet balance"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    admin_id, main_balance
                FROM admin_wallet
                WHERE admin_id = 'admin'
            """)
            
            wallet = cursor.fetchone()
            print("\n👨‍💼 Admin Wallet:")
            print("=" * 100)
            
            if wallet:
                print(f"Admin ID: {wallet['admin_id']}")
                print(f"  Main Balance: ₹{wallet['main_balance']:.2f}")
            else:
                print("Admin wallet not found")
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n🔍 PayIn Unsettled Wallet Flow Diagnosis")
    print("=" * 100)
    
    check_recent_payins()
    check_merchant_wallet_status()
    check_admin_wallet_status()
    
    print("\n" + "=" * 100)
    print("✅ Diagnosis complete")
