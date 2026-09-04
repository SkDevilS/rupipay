#!/usr/bin/env python3
"""
Check balance mismatch between display and validation
"""
import sys
from database import get_db_connection

def check_balance():
    """Check both calculations"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*60)
            print("BALANCE MISMATCH DIAGNOSIS")
            print("="*60)
            
            # Get PayIN
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payin
                FROM payin_transactions
                WHERE status = 'SUCCESS'
            """)
            total_payin = float(cursor.fetchone()['total_payin'])
            
            # Get Topups
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE status = 'APPROVED'
            """)
            total_topup = float(cursor.fetchone()['total_topup'])
            
            # Get Fetch
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_fetch
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT' 
                AND description LIKE '%fetched by admin%'
            """)
            total_fetch = float(cursor.fetchone()['total_fetch'])
            
            # Get Payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payout
                FROM payout_transactions
                WHERE status IN ('SUCCESS', 'QUEUED')
            """)
            total_payout = float(cursor.fetchone()['total_payout'])
            
            print(f"\nDATA:")
            print(f"  PayIN:   ₹{total_payin:,.2f}")
            print(f"  Topups:  ₹{total_topup:,.2f}")
            print(f"  Fetch:   ₹{total_fetch:,.2f}")
            print(f"  Payouts: ₹{total_payout:,.2f}")
            
            print(f"\n" + "="*60)
            print("CALCULATION 1: Display Balance (wallet_routes.py)")
            print("="*60)
            display_balance = total_payin + total_fetch - total_topup
            print(f"  Formula: PayIN + Fetch - Topups")
            print(f"  = ₹{total_payin:,.2f} + ₹{total_fetch:,.2f} - ₹{total_topup:,.2f}")
            print(f"  = ₹{display_balance:,.2f}")
            
            print(f"\n" + "="*60)
            print("CALCULATION 2: Validation Balance (payout_routes.py)")
            print("="*60)
            
            # Check what's in payout_routes.py
            print("  Checking current validation logic...")
            
            # Try to read the actual calculation from the file
            try:
                with open('/var/www/moneyone/moneyone/backend/payout_routes.py', 'r') as f:
                    content = f.read()
                    if 'available_balance = total_payin + total_fetch - total_topup - total_payout' in content:
                        validation_balance = total_payin + total_fetch - total_topup - total_payout
                        print(f"  ❌ OLD FORMULA STILL IN USE!")
                        print(f"  Formula: PayIN + Fetch - Topups - Payouts")
                        print(f"  = ₹{total_payin:,.2f} + ₹{total_fetch:,.2f} - ₹{total_topup:,.2f} - ₹{total_payout:,.2f}")
                        print(f"  = ₹{validation_balance:,.2f}")
                    elif 'available_balance = total_payin + total_fetch - total_topup' in content:
                        validation_balance = total_payin + total_fetch - total_topup
                        print(f"  ✓ NEW FORMULA IN USE")
                        print(f"  Formula: PayIN + Fetch - Topups")
                        print(f"  = ₹{total_payin:,.2f} + ₹{total_fetch:,.2f} - ₹{total_topup:,.2f}")
                        print(f"  = ₹{validation_balance:,.2f}")
                    else:
                        print(f"  ⚠️  Cannot determine formula from file")
            except Exception as e:
                print(f"  ⚠️  Could not read payout_routes.py: {e}")
            
            print(f"\n" + "="*60)
            print("CONCLUSION")
            print("="*60)
            print(f"\nIf display shows ₹7,91,987 but validation shows ₹1,06,041:")
            print(f"  → The payout_routes.py file was NOT updated on production")
            print(f"  → It's still using the OLD formula with payouts subtracted")
            print(f"\nExpected balance: ₹{display_balance:,.2f}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_balance()
