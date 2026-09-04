#!/usr/bin/env python3
"""
Diagnose Admin Wallet Balance Issue
Shows detailed breakdown of admin wallet calculation
"""

import sys
sys.path.append('/home/ubuntu/backend')

from database import get_db_connection

def diagnose_admin_wallet():
    """Show detailed admin wallet balance breakdown"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("ADMIN WALLET BALANCE DIAGNOSIS")
            print("="*80)
            
            # Total PayIN
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = float(cursor.fetchone()['total_payin'])
            print(f"\n1. Total Successful PayIN: ₹{total_payin:,.2f}")
            
            # Total Top-ups (Admin adds money)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = float(cursor.fetchone()['total_topup'])
            print(f"2. Total Approved Top-ups: ₹{total_topup:,.2f}")
            
            # Total Fetch (Admin withdraws money)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            total_fetch = float(cursor.fetchone()['total_fetch'])
            print(f"3. Total Fetched by Admin: ₹{total_fetch:,.2f}")
            
            # Total Payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
                AND reference_id LIKE 'ADMIN%'
            """)
            total_payout = float(cursor.fetchone()['total_payout'])
            print(f"4. Total Admin Payouts: ₹{total_payout:,.2f}")
            
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
            print(f"5. Manual Adjustments: ₹{total_adjustments:,.2f}")
            
            # Total Settlements
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM settlement_transactions
            """)
            total_settlements = float(cursor.fetchone()['total_settlements'])
            print(f"6. Total Settlements Done: ₹{total_settlements:,.2f}")
            
            # Calculate admin balance
            admin_balance = total_payin + total_fetch - total_topup - total_payout + total_adjustments - total_settlements
            
            print("\n" + "-"*80)
            print("CALCULATION:")
            print(f"  PayIN + Fetch - Topups - Payouts + Adjustments - Settlements")
            print(f"  {total_payin:,.2f} + {total_fetch:,.2f} - {total_topup:,.2f} - {total_payout:,.2f} + {total_adjustments:,.2f} - {total_settlements:,.2f}")
            print(f"\n  = ₹{admin_balance:,.2f}")
            print("-"*80)
            
            # Check admin wallet table
            cursor.execute("""
                SELECT settled_balance, unsettled_balance 
                FROM admin_wallet 
                WHERE admin_id = 'admin'
            """)
            admin_wallet = cursor.fetchone()
            
            if admin_wallet:
                print(f"\nADMIN WALLET TABLE:")
                print(f"  Settled Balance: ₹{float(admin_wallet['settled_balance']):,.2f}")
                print(f"  Unsettled Balance: ₹{float(admin_wallet['unsettled_balance']):,.2f}")
                print(f"  Total: ₹{float(admin_wallet['settled_balance']) + float(admin_wallet['unsettled_balance']):,.2f}")
            
            # Check pending settlements
            cursor.execute("""
                SELECT merchant_id, unsettled_balance 
                FROM merchant_wallet 
                WHERE unsettled_balance > 0
                ORDER BY unsettled_balance DESC
            """)
            pending_settlements = cursor.fetchall()
            
            if pending_settlements:
                print(f"\n\nMERCHANTS WITH UNSETTLED BALANCE:")
                print(f"{'Merchant ID':<20} {'Unsettled Balance':>20}")
                print("-"*42)
                total_unsettled = 0
                for row in pending_settlements:
                    unsettled = float(row['unsettled_balance'])
                    total_unsettled += unsettled
                    print(f"{row['merchant_id']:<20} ₹{unsettled:>18,.2f}")
                print("-"*42)
                print(f"{'TOTAL':<20} ₹{total_unsettled:>18,.2f}")
            
            print("\n" + "="*80)
            
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnose_admin_wallet()
