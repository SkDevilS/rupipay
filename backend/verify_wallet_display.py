#!/usr/bin/env python3
"""
Verify that wallet balance displayed in frontend matches database calculation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def verify_wallet_balance():
    print("=" * 80)
    print("WALLET BALANCE VERIFICATION")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get all merchants with their wallet balances
            cursor.execute("""
                SELECT 
                    m.merchant_id,
                    m.full_name,
                    (SELECT COALESCE(SUM(amount), 0) 
                     FROM fund_requests 
                     WHERE merchant_id = m.merchant_id AND status = 'APPROVED') as approved_topup,
                    (SELECT COALESCE(SUM(amount), 0) 
                     FROM payout_transactions 
                     WHERE merchant_id = m.merchant_id AND status IN ('SUCCESS', 'QUEUED')) as total_payout,
                    (SELECT COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0)
                     FROM merchant_wallet_transactions
                     WHERE merchant_id = m.merchant_id) as wallet_credits,
                    (SELECT COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0)
                     FROM merchant_wallet_transactions
                     WHERE merchant_id = m.merchant_id) as wallet_debits,
                    (SELECT COALESCE(SUM(net_amount), 0)
                     FROM payin_transactions
                     WHERE merchant_id = m.merchant_id AND status = 'SUCCESS') as net_payin
                FROM merchants m
                ORDER BY m.merchant_id
            """)
            
            merchants = cursor.fetchall()
            
            if not merchants:
                print("❌ No merchants found")
                return
            
            print(f"{'Merchant ID':<15} {'Name':<20} {'Topup':<10} {'Payout':<10} {'Credits':<10} {'Debits':<10} {'Wallet':<10} {'PayIN':<10}")
            print("-" * 115)
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                name = merchant['full_name'][:18] if merchant['full_name'] else 'N/A'
                approved_topup = float(merchant['approved_topup'])
                total_payout = float(merchant['total_payout'])
                wallet_credits = float(merchant['wallet_credits'])
                wallet_debits = float(merchant['wallet_debits'])
                net_payin = float(merchant['net_payin'])
                
                # Calculate wallet balance (same as backend)
                wallet_balance = approved_topup - total_payout - wallet_debits + wallet_credits
                
                print(f"{merchant_id:<15} {name:<20} {approved_topup:<10.2f} {total_payout:<10.2f} {wallet_credits:<10.2f} {wallet_debits:<10.2f} {wallet_balance:<10.2f} {net_payin:<10.2f}")
            
            print()
            print("=" * 80)
            print("CALCULATION FORMULA")
            print("=" * 80)
            print("Wallet Balance = Approved Topup - Total Payout - Wallet Debits + Wallet Credits")
            print()
            print("Where:")
            print("  • Approved Topup: Sum of approved fund requests")
            print("  • Total Payout: Sum of successful/queued payouts")
            print("  • Wallet Debits: Admin fetch fund operations")
            print("  • Wallet Credits: Additional credits (if any)")
            print("  • Net PayIN: For display only (NOT part of wallet balance)")
            print()
            
            # Check if any merchant has wallet transactions
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
            """)
            txn_count = cursor.fetchone()['count']
            
            if txn_count > 0:
                print(f"⚠️  Found {txn_count} merchant_wallet_transactions entries")
                print("   These are fetch fund operations and affect wallet balance")
            else:
                print("✅ No merchant_wallet_transactions found")
                print("   Wallet balance = Approved Topup - Total Payout")
            
            print()
            print("=" * 80)
            print("FRONTEND DISPLAY")
            print("=" * 80)
            print("The Wallet Overview page should show:")
            print("  • Wallet Balance: Amount available for payout (from approved fund requests)")
            print("  • Net PayIN Amount: Total PayIN received (for information only)")
            print("  • These are TWO SEPARATE values")
            print()
            
    finally:
        conn.close()


def check_api_response():
    """Simulate API response for a merchant"""
    print("=" * 80)
    print("API RESPONSE SIMULATION")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Get first merchant
            cursor.execute("SELECT merchant_id FROM merchants LIMIT 1")
            merchant = cursor.fetchone()
            
            if not merchant:
                print("No merchant found")
                return
            
            merchant_id = merchant['merchant_id']
            
            # Simulate the API calculation
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            total_topup = float(cursor.fetchone()['total_topup'])
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
            """, (merchant_id,))
            total_settlements = float(cursor.fetchone()['total_settlements'])
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN txn_type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_credit,
                    COALESCE(SUM(CASE WHEN txn_type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_debit
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet_txn = cursor.fetchone()
            total_credit = float(wallet_txn['total_credit']) if wallet_txn else 0
            total_debit = float(wallet_txn['total_debit']) if wallet_txn else 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s AND status = 'SUCCESS'
            """, (merchant_id,))
            net_payin = float(cursor.fetchone()['net_amount'])
            
            wallet_balance = total_topup - total_settlements - total_debit + total_credit
            
            print(f"Merchant ID: {merchant_id}")
            print()
            print("API Response Data:")
            print(f"  balance: {wallet_balance:.2f}")
            print(f"  total_topup: {total_topup:.2f}")
            print(f"  total_settlements: {total_settlements:.2f}")
            print(f"  total_credit: {total_credit:.2f}")
            print(f"  total_debit: {total_debit:.2f}")
            print(f"  payin_amount: {net_payin:.2f}")
            print()
            print("Frontend Display:")
            print(f"  Wallet Balance: ₹{wallet_balance:.2f}")
            print(f"  Net PayIN Amount: ₹{net_payin:.2f}")
            print()
            
    finally:
        conn.close()


if __name__ == '__main__':
    verify_wallet_balance()
    print()
    check_api_response()
