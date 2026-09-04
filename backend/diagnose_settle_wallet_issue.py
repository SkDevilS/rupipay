#!/usr/bin/env python3
"""
Diagnose Settle Wallet Balance Update Issue
Checks if successful payout transactions are properly deducting from settled wallet
"""

import sys
from database import get_db_connection
from datetime import datetime, timedelta

def diagnose_settle_wallet_issue():
    """Check for successful payouts without wallet deductions"""
    
    print("=" * 80)
    print("SETTLE WALLET BALANCE UPDATE DIAGNOSTIC")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check for SUCCESS payouts in the last 7 days without wallet deduction
            print("1. Checking for SUCCESS payouts without wallet deduction (last 7 days)...")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    p.txn_id,
                    p.reference_id,
                    p.merchant_id,
                    p.amount,
                    p.net_amount,
                    p.charge_amount,
                    p.status,
                    p.pg_partner,
                    p.completed_at,
                    p.created_at,
                    mwt.txn_id as wallet_txn_id,
                    mwt.amount as wallet_deducted
                FROM payout_transactions p
                LEFT JOIN merchant_wallet_transactions mwt 
                    ON mwt.reference_id = p.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE p.status = 'SUCCESS'
                AND p.created_at >= NOW() - INTERVAL 7 DAY
                ORDER BY p.created_at DESC
            """)
            
            payouts = cursor.fetchall()
            
            if not payouts:
                print("✓ No SUCCESS payouts found in the last 7 days")
            else:
                missing_deductions = []
                correct_deductions = []
                
                for payout in payouts:
                    if not payout['wallet_txn_id']:
                        missing_deductions.append(payout)
                    else:
                        correct_deductions.append(payout)
                
                print(f"Total SUCCESS payouts: {len(payouts)}")
                print(f"✓ With wallet deduction: {len(correct_deductions)}")
                print(f"❌ Missing wallet deduction: {len(missing_deductions)}")
                print()
                
                if missing_deductions:
                    print("PAYOUTS MISSING WALLET DEDUCTION:")
                    print("-" * 80)
                    for payout in missing_deductions:
                        print(f"TXN ID: {payout['txn_id']}")
                        print(f"  Merchant: {payout['merchant_id']}")
                        print(f"  Reference: {payout['reference_id']}")
                        print(f"  Amount: ₹{payout['amount']:.2f} (Net: ₹{payout['net_amount']:.2f} + Charges: ₹{payout['charge_amount']:.2f})")
                        print(f"  PG Partner: {payout['pg_partner']}")
                        print(f"  Completed: {payout['completed_at']}")
                        print(f"  Created: {payout['created_at']}")
                        print()
                
                if correct_deductions:
                    print("RECENT PAYOUTS WITH CORRECT WALLET DEDUCTION:")
                    print("-" * 80)
                    for payout in correct_deductions[:5]:  # Show last 5
                        print(f"TXN ID: {payout['txn_id']}")
                        print(f"  Merchant: {payout['merchant_id']}")
                        print(f"  Amount: ₹{payout['amount']:.2f}")
                        print(f"  Wallet Deducted: ₹{payout['wallet_deducted']:.2f}")
                        print(f"  PG Partner: {payout['pg_partner']}")
                        print(f"  Completed: {payout['completed_at']}")
                        print()
            
            print()
            print("2. Checking merchant wallet balances...")
            print("-" * 80)
            
            # Get merchants with recent payouts
            cursor.execute("""
                SELECT DISTINCT merchant_id
                FROM payout_transactions
                WHERE created_at >= NOW() - INTERVAL 7 DAY
                AND status = 'SUCCESS'
            """)
            
            merchants = cursor.fetchall()
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                
                # Get wallet balance
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance, balance, last_updated
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                wallet = cursor.fetchone()
                
                if wallet:
                    print(f"Merchant: {merchant_id}")
                    print(f"  Settled Balance: ₹{wallet['settled_balance']:.2f}")
                    print(f"  Unsettled Balance: ₹{wallet['unsettled_balance']:.2f}")
                    print(f"  Legacy Balance: ₹{wallet['balance']:.2f}")
                    print(f"  Last Updated: {wallet['last_updated']}")
                    
                    # Get recent wallet transactions
                    cursor.execute("""
                        SELECT txn_id, txn_type, amount, balance_after, description, created_at
                        FROM merchant_wallet_transactions
                        WHERE merchant_id = %s
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (merchant_id,))
                    
                    wallet_txns = cursor.fetchall()
                    
                    if wallet_txns:
                        print(f"  Recent Wallet Transactions:")
                        for txn in wallet_txns:
                            print(f"    - {txn['txn_type']}: ₹{txn['amount']:.2f} | Balance After: ₹{txn['balance_after']:.2f}")
                            print(f"      {txn['description']} ({txn['created_at']})")
                    print()
            
            print()
            print("3. Checking for PENDING/INITIATED payouts (awaiting callback)...")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    amount,
                    status,
                    pg_partner,
                    created_at
                FROM payout_transactions
                WHERE status IN ('PENDING', 'INITIATED', 'QUEUED', 'INPROCESS')
                AND created_at >= NOW() - INTERVAL 7 DAY
                ORDER BY created_at DESC
            """)
            
            pending_payouts = cursor.fetchall()
            
            if not pending_payouts:
                print("✓ No pending payouts found")
            else:
                print(f"Found {len(pending_payouts)} pending payouts:")
                for payout in pending_payouts:
                    print(f"TXN ID: {payout['txn_id']}")
                    print(f"  Merchant: {payout['merchant_id']}")
                    print(f"  Reference: {payout['reference_id']}")
                    print(f"  Amount: ₹{payout['amount']:.2f}")
                    print(f"  Status: {payout['status']}")
                    print(f"  PG Partner: {payout['pg_partner']}")
                    print(f"  Created: {payout['created_at']}")
                    print()
            
            print()
            print("4. Checking callback configuration...")
            print("-" * 80)
            
            # Check if callback routes are properly configured
            cursor.execute("""
                SELECT DISTINCT pg_partner
                FROM payout_transactions
                WHERE created_at >= NOW() - INTERVAL 7 DAY
            """)
            
            pg_partners = cursor.fetchall()
            
            print("Payment gateways in use:")
            for pg in pg_partners:
                print(f"  - {pg['pg_partner']}")
            
            print()
            print("Expected callback endpoints:")
            print("  - Mudrape: POST /api/callback/mudrape/payout")
            print("  - PayTouch: POST /api/callback/paytouch/payout")
            print("  - PayU: (handled inline in settle-fund endpoint)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    diagnose_settle_wallet_issue()
