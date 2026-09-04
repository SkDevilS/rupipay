#!/usr/bin/env python3
"""
Diagnostic script to check personal payout flow and admin wallet balance
"""

import pymysql
from database import get_db_connection

def check_admin_balance(admin_id='admin'):
    """Check admin wallet balance from admin_wallet table"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check admin_wallet table (the source of truth)
            cursor.execute("""
                SELECT main_balance, unsettled_balance, last_updated
                FROM admin_wallet
                WHERE admin_id = %s
            """, (admin_id,))
            admin_wallet = cursor.fetchone()
            
            if admin_wallet:
                main_balance = float(admin_wallet['main_balance'])
                unsettled_balance = float(admin_wallet['unsettled_balance'])
                print(f"✓ Admin Wallet (from admin_wallet table):")
                print(f"  Main Balance: ₹{main_balance:.2f}")
                print(f"  Unsettled Balance: ₹{unsettled_balance:.2f}")
                print(f"  Last Updated: {admin_wallet['last_updated']}")
            else:
                print(f"❌ Admin wallet not found in admin_wallet table")
                main_balance = 0.00
            
            # Check admin wallet transactions
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                    COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit,
                    COUNT(*) as txn_count
                FROM admin_wallet_transactions
                WHERE admin_id = %s AND wallet_type = 'MAIN'
            """, (admin_id,))
            wallet_txns = cursor.fetchone()
            
            if wallet_txns and wallet_txns['txn_count'] > 0:
                print(f"\n✓ Admin Wallet Transactions (MAIN):")
                print(f"  Total Credits: ₹{float(wallet_txns['total_credit']):.2f}")
                print(f"  Total Debits: ₹{float(wallet_txns['total_debit']):.2f}")
                print(f"  Transaction Count: {wallet_txns['txn_count']}")
            
            # Check admin banks
            cursor.execute("""
                SELECT COUNT(*) as bank_count
                FROM admin_banks
                WHERE admin_id = %s AND is_active = TRUE
            """, (admin_id,))
            bank_count = cursor.fetchone()['bank_count']
            print(f"\n✓ Active Admin Banks: {bank_count}")
            
            if bank_count > 0:
                cursor.execute("""
                    SELECT id, bank_name, account_number, ifsc_code, account_holder_name
                    FROM admin_banks
                    WHERE admin_id = %s AND is_active = TRUE
                """, (admin_id,))
                banks = cursor.fetchall()
                for bank in banks:
                    print(f"  - Bank ID {bank['id']}: {bank['bank_name']}")
                    print(f"    Account: {bank['account_number']} ({bank['ifsc_code']})")
                    print(f"    Holder: {bank['account_holder_name']}")
            
            # Check recent payout transactions
            cursor.execute("""
                SELECT txn_id, reference_id, amount, status, pg_partner, created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (admin_id,))
            recent_payouts = cursor.fetchall()
            
            if recent_payouts:
                print(f"\n📋 Recent Admin Payouts:")
                for payout in recent_payouts:
                    print(f"  - {payout['txn_id']}: ₹{payout['amount']:.2f} - {payout['status']} ({payout['pg_partner']}) - {payout['created_at']}")
            else:
                print(f"\n📋 No recent admin payouts found")
            
            # Check recent wallet transactions
            cursor.execute("""
                SELECT txn_id, txn_type, amount, balance_before, balance_after, description, created_at
                FROM admin_wallet_transactions
                WHERE admin_id = %s AND wallet_type = 'MAIN'
                ORDER BY created_at DESC
                LIMIT 5
            """, (admin_id,))
            recent_wallet_txns = cursor.fetchall()
            
            if recent_wallet_txns:
                print(f"\n📋 Recent Wallet Transactions:")
                for txn in recent_wallet_txns:
                    print(f"  - {txn['txn_id']}: {txn['txn_type']} ₹{txn['amount']:.2f}")
                    print(f"    Before: ₹{txn['balance_before']:.2f} → After: ₹{txn['balance_after']:.2f}")
                    print(f"    {txn['description']} - {txn['created_at']}")
            
            print("\n" + "="*60)
            print("DIAGNOSIS COMPLETE")
            print("="*60)
            
            if main_balance >= 1500:
                print(f"✅ Balance sufficient for ₹1500 payout")
                print(f"   Current Balance: ₹{main_balance:.2f}")
                print(f"   Remaining after payout: ₹{main_balance - 1500:.2f}")
            else:
                print(f"❌ Insufficient balance for ₹1500 payout")
                print(f"   Current Balance: ₹{main_balance:.2f}")
                print(f"   Shortfall: ₹{1500 - main_balance:.2f}")
            
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\n✓ Connection closed properly")

if __name__ == '__main__':
    print("="*60)
    print("PERSONAL PAYOUT DIAGNOSTIC")
    print("="*60)
    check_admin_balance()
