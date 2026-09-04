#!/usr/bin/env python3
"""
Test the wallet balance fix - should show Approved Fund Requests - Payouts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def test_wallet_calculation():
    print("=" * 80)
    print("TESTING WALLET BALANCE CALCULATION")
    print("=" * 80)
    print("\nFormula: Wallet Balance = Approved Fund Requests - Payouts")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get all merchants
            cursor.execute("""
                SELECT 
                    m.merchant_id,
                    m.full_name,
                    (SELECT COALESCE(SUM(amount), 0) 
                     FROM fund_requests 
                     WHERE merchant_id = m.merchant_id AND status = 'APPROVED') as approved_topup,
                    (SELECT COALESCE(SUM(amount), 0) 
                     FROM payout_transactions 
                     WHERE merchant_id = m.merchant_id AND status IN ('SUCCESS', 'QUEUED')) as total_payout
                FROM merchants m
                ORDER BY m.merchant_id
            """)
            
            merchants = cursor.fetchall()
            
            if not merchants:
                print("❌ No merchants found")
                return
            
            print(f"{'Merchant ID':<15} {'Name':<25} {'Approved Topup':<15} {'Payouts':<15} {'Wallet Balance':<15}")
            print("-" * 90)
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                name = (merchant['full_name'][:23] + '..') if merchant['full_name'] and len(merchant['full_name']) > 25 else (merchant['full_name'] or 'N/A')
                approved_topup = float(merchant['approved_topup'])
                total_payout = float(merchant['total_payout'])
                
                # Simple calculation
                wallet_balance = approved_topup - total_payout
                
                print(f"{merchant_id:<15} {name:<25} ₹{approved_topup:<14.2f} ₹{total_payout:<14.2f} ₹{wallet_balance:<14.2f}")
            
            print()
            print("=" * 80)
            print("EXPLANATION")
            print("=" * 80)
            print("""
This is what should be displayed in the Wallet Overview page:

1. Wallet Balance (Green Card): Approved Topup - Payouts
   - This is the withdrawable amount
   - Comes from approved fund requests only
   - NOT from PayIN amounts

2. Net PayIN Amount (Purple Card): Total PayIN received
   - This is for information only
   - Shows how much PayIN merchant has received
   - NOT part of wallet balance

The two values are SEPARATE and serve different purposes.
            """)
            
    finally:
        conn.close()


def simulate_api_response():
    """Simulate what the API will return after the fix"""
    print("\n" + "=" * 80)
    print("SIMULATING API RESPONSE")
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
            
            # Get approved fund requests
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_topup
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            total_topup = float(cursor.fetchone()['total_topup'])
            
            # Get payouts
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_settlements
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED')
            """, (merchant_id,))
            total_settlements = float(cursor.fetchone()['total_settlements'])
            
            # Get PayIN (for display only)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as gross_amount,
                    COALESCE(SUM(charge_amount), 0) as charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s AND status = 'SUCCESS'
            """, (merchant_id,))
            payin = cursor.fetchone()
            
            # Calculate wallet balance
            wallet_balance = total_topup - total_settlements
            
            print(f"Merchant ID: {merchant_id}")
            print()
            print("API Endpoint: GET /api/wallet/merchant/overview")
            print()
            print("Response:")
            print("{")
            print('  "success": true,')
            print('  "data": {')
            print(f'    "balance": {wallet_balance:.2f},           // Wallet Balance (GREEN CARD)')
            print(f'    "total_topup": {total_topup:.2f},        // Approved fund requests')
            print(f'    "total_settlements": {total_settlements:.2f},   // Total payouts')
            print(f'    "payin_amount": {float(payin["net_amount"]):.2f},      // Net PayIN (PURPLE CARD - for display only)')
            print(f'    "gross_payin": {float(payin["gross_amount"]):.2f},')
            print(f'    "payin_charges": {float(payin["charges"]):.2f}')
            print('  }')
            print('}')
            print()
            print("Frontend Display:")
            print(f"  🟢 Wallet Balance: ₹{wallet_balance:,.2f}")
            print(f"  🟣 Net PayIN Amount: ₹{float(payin['net_amount']):,.2f}")
            print()
            
    finally:
        conn.close()


if __name__ == '__main__':
    test_wallet_calculation()
    simulate_api_response()
    
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Restart the backend service:
   sudo systemctl restart gunicorn

2. Clear browser cache and refresh the Wallet Overview page

3. Verify the Wallet Balance shows: Approved Topup - Payouts

4. The fix is complete!
    """)
