"""
Verify Payout Wallet Deduction Fix
Check if settled wallet is being properly deducted for PayTouch payouts
"""

import sys
sys.path.append('/var/www/moneyone/backend')

from database import get_db_connection
from datetime import datetime, timedelta

def verify_payout_wallet_deduction():
    """Check recent PayTouch payouts and their wallet deductions"""
    
    print("=" * 80)
    print("PayTouch Payout Wallet Deduction Verification")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent PayTouch SUCCESS payouts
            print("\n1. Recent PayTouch SUCCESS Payouts")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    created_at,
                    completed_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status = 'SUCCESS'
                AND created_at >= NOW() - INTERVAL 7 DAY
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            payouts = cursor.fetchall()
            
            if not payouts:
                print("No recent SUCCESS PayTouch payouts found")
            else:
                print(f"Found {len(payouts)} recent SUCCESS payouts\n")
                
                for payout in payouts:
                    print(f"Transaction: {payout['txn_id']}")
                    print(f"  Reference: {payout['reference_id']}")
                    print(f"  Merchant: {payout['merchant_id']}")
                    print(f"  Amount (Total): ₹{payout['amount']:.2f}")
                    print(f"  Net Amount: ₹{payout['net_amount']:.2f}")
                    print(f"  Charges: ₹{payout['charge_amount']:.2f}")
                    print(f"  Status: {payout['status']}")
                    print(f"  Created: {payout['created_at']}")
                    print(f"  Completed: {payout['completed_at']}")
                    
                    # Check if wallet was debited
                    cursor.execute("""
                        SELECT 
                            txn_id,
                            txn_type,
                            amount,
                            balance_before,
                            balance_after,
                            description,
                            created_at
                        FROM merchant_wallet_transactions
                        WHERE reference_id = %s
                        AND txn_type = 'DEBIT'
                    """, (payout['txn_id'],))
                    
                    wallet_txn = cursor.fetchone()
                    
                    if wallet_txn:
                        print(f"  ✅ Wallet Deducted:")
                        print(f"     Amount: ₹{wallet_txn['amount']:.2f}")
                        print(f"     Balance: ₹{wallet_txn['balance_before']:.2f} → ₹{wallet_txn['balance_after']:.2f}")
                        print(f"     Description: {wallet_txn['description']}")
                        print(f"     Time: {wallet_txn['created_at']}")
                        
                        # Verify correct amount
                        expected_deduction = float(payout['amount'])
                        actual_deduction = float(wallet_txn['amount'])
                        
                        if abs(expected_deduction - actual_deduction) < 0.01:
                            print(f"     ✅ CORRECT: Deducted amount matches total")
                        else:
                            print(f"     ❌ ERROR: Deducted ₹{actual_deduction:.2f} but should be ₹{expected_deduction:.2f}")
                    else:
                        print(f"  ❌ NO WALLET DEDUCTION FOUND!")
                    
                    print()
            
            # Check for QUEUED/PENDING payouts that need wallet deduction
            print("\n2. Pending PayTouch Payouts (Awaiting Callback)")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    created_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status IN ('QUEUED', 'PENDING', 'INITIATED', 'INPROCESS')
                AND created_at >= NOW() - INTERVAL 7 DAY
                ORDER BY created_at DESC
            """)
            
            pending_payouts = cursor.fetchall()
            
            if not pending_payouts:
                print("No pending PayTouch payouts")
            else:
                print(f"Found {len(pending_payouts)} pending payouts\n")
                
                for payout in pending_payouts:
                    print(f"Transaction: {payout['txn_id']}")
                    print(f"  Reference: {payout['reference_id']}")
                    print(f"  Merchant: {payout['merchant_id']}")
                    print(f"  Amount: ₹{payout['amount']:.2f} (Net: ₹{payout['net_amount']:.2f} + Charges: ₹{payout['charge_amount']:.2f})")
                    print(f"  Status: {payout['status']}")
                    print(f"  Created: {payout['created_at']}")
                    print(f"  ⏳ Waiting for callback to deduct wallet")
                    print()
            
            # Check merchant wallet balances
            print("\n3. Merchant Wallet Balances")
            print("-" * 80)
            
            cursor.execute("""
                SELECT DISTINCT merchant_id FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND created_at >= NOW() - INTERVAL 7 DAY
            """)
            
            merchants = cursor.fetchall()
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                
                cursor.execute("""
                    SELECT 
                        settled_balance,
                        unsettled_balance,
                        balance,
                        last_updated
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                
                if wallet:
                    print(f"Merchant: {merchant_id}")
                    print(f"  Settled Balance: ₹{wallet['settled_balance']:.2f}")
                    print(f"  Unsettled Balance: ₹{wallet['unsettled_balance']:.2f}")
                    print(f"  Total Balance: ₹{wallet['balance']:.2f}")
                    print(f"  Last Updated: {wallet['last_updated']}")
                    print()
            
            print("=" * 80)
            print("Verification Complete")
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    verify_payout_wallet_deduction()
