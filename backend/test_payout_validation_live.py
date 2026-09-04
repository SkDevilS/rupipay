#!/usr/bin/env python3
"""
Test payout validation logic with current wallet balance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def test_validation(merchant_id, payout_amount):
    """Simulate the validation logic"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 60)
            print("PAYOUT VALIDATION TEST")
            print("=" * 60)
            print(f"Merchant ID: {merchant_id}")
            print(f"Requested Payout Amount: ₹{payout_amount:.2f}")
            print()
            
            # Get merchant scheme for charge calculation
            cursor.execute("""
                SELECT scheme_id FROM merchants WHERE merchant_id = %s
            """, (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print("❌ Merchant not found")
                return
            
            # Get scheme charges
            cursor.execute("""
                SELECT charge_type, charge_value 
                FROM schemes 
                WHERE scheme_id = %s AND service_type = 'PAYOUT'
            """, (merchant['scheme_id'],))
            scheme = cursor.fetchone()
            
            if scheme:
                if scheme['charge_type'] == 'PERCENTAGE':
                    charge_amount = (payout_amount * float(scheme['charge_value'])) / 100
                else:  # FLAT
                    charge_amount = float(scheme['charge_value'])
            else:
                charge_amount = 0.00
            
            total_deduction = payout_amount + charge_amount
            
            print(f"Charge Amount: ₹{charge_amount:.2f}")
            print(f"Total Deduction: ₹{total_deduction:.2f}")
            print()
            
            # Check wallet balance (NEW METHOD)
            print("NEW METHOD (merchant_wallet table):")
            print("-" * 60)
            cursor.execute("""
                SELECT balance FROM merchant_wallet WHERE merchant_id = %s
            """, (merchant_id,))
            wallet_row = cursor.fetchone()
            
            if wallet_row:
                available_balance = float(wallet_row['balance'])
                print(f"Available Balance: ₹{available_balance:.2f}")
                print(f"Validation: {total_deduction:.2f} > {available_balance:.2f} = {total_deduction > available_balance}")
                
                if total_deduction > available_balance:
                    print(f"❌ VALIDATION FAILED - Insufficient balance")
                    print(f"   Shortfall: ₹{(total_deduction - available_balance):.2f}")
                else:
                    print(f"✅ VALIDATION PASSED - Sufficient balance")
                    print(f"   Remaining after payout: ₹{(available_balance - total_deduction):.2f}")
            else:
                print("❌ No wallet found")
            print()
            
            # Check old method for comparison
            print("OLD METHOD (fund_requests - payouts):")
            print("-" * 60)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as wallet_balance
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            wallet_balance = float(cursor.fetchone()['wallet_balance'])
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payouts
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
            """, (merchant_id,))
            total_payouts = float(cursor.fetchone()['total_payouts'])
            
            old_available = wallet_balance - total_payouts
            
            print(f"Approved Funds: ₹{wallet_balance:.2f}")
            print(f"Total Payouts: ₹{total_payouts:.2f}")
            print(f"Available (Old): ₹{old_available:.2f}")
            print(f"Validation: {total_deduction:.2f} > {old_available:.2f} = {total_deduction > old_available}")
            
            if total_deduction > old_available:
                print(f"❌ OLD METHOD: Would FAIL")
            else:
                print(f"✅ OLD METHOD: Would PASS")
            print()
            
            print("=" * 60)
            print("CONCLUSION:")
            print("=" * 60)
            if wallet_row:
                if total_deduction > available_balance:
                    print("❌ Payout should be REJECTED (insufficient balance)")
                else:
                    print("✅ Payout should be APPROVED (sufficient balance)")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_payout_validation_live.py <merchant_id> <amount>")
        print("Example: python test_payout_validation_live.py 1 100")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    amount = float(sys.argv[2])
    test_validation(merchant_id, amount)
