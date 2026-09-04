#!/usr/bin/env python3
"""
Verify Admin Balance Calculation
Shows how admin balance is calculated with all components including manual adjustments
"""

import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'moneyone_db'),
        cursorclass=pymysql.cursors.DictCursor
    )

def verify_balance():
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("ADMIN BALANCE CALCULATION VERIFICATION")
            print("=" * 80)
            print()
            
            # PayIN
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = float(cursor.fetchone()['total_payin'])
            
            # Topups
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = float(cursor.fetchone()['total_topup'])
            
            # Fetch
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            total_fetch = float(cursor.fetchone()['total_fetch'])
            
            # Admin Payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
                AND reference_id LIKE 'ADMIN%'
            """)
            total_payout = float(cursor.fetchone()['total_payout'])
            
            # Manual Adjustments
            cursor.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN txn_type = 'CREDIT' THEN amount
                        WHEN txn_type = 'DEBIT' THEN -amount
                        ELSE 0
                    END
                ), 0) as total_adjustments
                FROM admin_wallet_transactions
                WHERE description LIKE '%Manual balance%'
                OR description LIKE '%Balance adjustment%'
                OR description LIKE '%Initial capital%'
            """)
            total_adjustments = float(cursor.fetchone()['total_adjustments'])
            
            # Calculate balance
            balance = total_payin + total_fetch - total_topup - total_payout + total_adjustments
            
            print("BALANCE COMPONENTS:")
            print("-" * 80)
            print(f"  PayIN (SUCCESS):              +₹{total_payin:,.2f}")
            print(f"  Fetch from Merchants:         +₹{total_fetch:,.2f}")
            print(f"  Topups to Merchants:          -₹{total_topup:,.2f}")
            print(f"  Admin Payouts:                -₹{total_payout:,.2f}")
            print(f"  Manual Adjustments:           {'+'if total_adjustments >= 0 else ''}₹{total_adjustments:,.2f}")
            print("-" * 80)
            print(f"  TOTAL ADMIN BALANCE:           ₹{balance:,.2f}")
            print()
            
            # Show recent manual adjustments
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    description,
                    created_at
                FROM admin_wallet_transactions
                WHERE description LIKE '%Manual balance%'
                OR description LIKE '%Balance adjustment%'
                OR description LIKE '%Initial capital%'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            adjustments = cursor.fetchall()
            
            if adjustments:
                print("RECENT MANUAL ADJUSTMENTS:")
                print("-" * 80)
                for adj in adjustments:
                    sign = '+' if adj['txn_type'] == 'CREDIT' else '-'
                    print(f"  {adj['created_at']} | {adj['txn_id']}")
                    print(f"    {sign}₹{adj['amount']:,.2f} - {adj['description']}")
                    print()
            else:
                print("No manual adjustments found.")
                print()
            
            print("=" * 80)
            print("VERIFICATION COMPLETE")
            print("=" * 80)
            print()
            print("This balance should match what's shown in:")
            print("  • Admin Panel → Fund Manager → TopUp Fund (Admin Wallet Balance card)")
            print("  • API: GET /api/wallet/admin/overview → data.main_balance")
            print()
            
    finally:
        conn.close()

if __name__ == "__main__":
    verify_balance()
