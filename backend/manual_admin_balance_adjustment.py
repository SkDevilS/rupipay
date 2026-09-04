#!/usr/bin/env python3
"""
Manual Admin Balance Adjustment Script

This script adjusts the admin wallet balance by directly adding a transaction
to admin_wallet_transactions table WITHOUT creating any PayIN record.

This means:
- The adjustment WILL affect admin wallet balance calculations
- The adjustment WILL NOT appear in PayIN reports
- The adjustment WILL NOT appear in any merchant reports
- It's a pure admin balance adjustment for manual corrections

Usage:
    python3 manual_admin_balance_adjustment.py <amount> "<description>"
    
Examples:
    python3 manual_admin_balance_adjustment.py 100000 "Manual balance correction"
    python3 manual_admin_balance_adjustment.py -50000 "Balance adjustment for error correction"
    python3 manual_admin_balance_adjustment.py 351194 "Initial capital injection"
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection"""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'moneyone_db'),
        cursorclass=pymysql.cursors.DictCursor
    )

def calculate_admin_balance(cursor):
    """Calculate current admin balance dynamically"""
    # PayIN amount
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_payin
        FROM payin_transactions
        WHERE status = 'SUCCESS'
    """)
    total_payin = float(cursor.fetchone()['total_payin'])
    
    # Approved fund requests (topups to merchants)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_topup
        FROM fund_requests
        WHERE status = 'APPROVED'
    """)
    total_topup = float(cursor.fetchone()['total_topup'])
    
    # Fetch from merchants (money returned to admin)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_fetch
        FROM merchant_wallet_transactions
        WHERE txn_type = 'DEBIT' 
        AND description LIKE '%fetched by admin%'
    """)
    total_fetch = float(cursor.fetchone()['total_fetch'])
    
    # Admin payouts (personal payouts, not merchant payouts)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_payout
        FROM payout_transactions
        WHERE status IN ('SUCCESS', 'QUEUED')
        AND reference_id LIKE 'ADMIN%'
    """)
    total_payout = float(cursor.fetchone()['total_payout'])
    
    # Manual adjustments from admin_wallet_transactions
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
    
    return {
        'balance': balance,
        'payin': total_payin,
        'fetch': total_fetch,
        'topup': total_topup,
        'payout': total_payout,
        'adjustments': total_adjustments
    }

def adjust_admin_balance(amount, description):
    """
    Adjust admin balance by adding a transaction record
    
    Args:
        amount: Amount to adjust (positive for credit, negative for debit)
        description: Description of the adjustment
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Get current balance
            balance_info = calculate_admin_balance(cursor)
            balance_before = balance_info['balance']
            balance_after = balance_before + amount
            
            print("=" * 80)
            print("MANUAL ADMIN BALANCE ADJUSTMENT")
            print("=" * 80)
            print()
            print("Current Balance Breakdown:")
            print(f"  PayIN:        ₹{balance_info['payin']:,.2f}")
            print(f"  Fetch:        ₹{balance_info['fetch']:,.2f}")
            print(f"  Topups:      -₹{balance_info['topup']:,.2f}")
            print(f"  Payouts:     -₹{balance_info['payout']:,.2f}")
            print(f"  Adjustments:  ₹{balance_info['adjustments']:,.2f}")
            print(f"  " + "-" * 40)
            print(f"  Current:      ₹{balance_before:,.2f}")
            print()
            print(f"Adjustment:     {'₹' if amount >= 0 else '-₹'}{abs(amount):,.2f}")
            print(f"New Balance:    ₹{balance_after:,.2f}")
            print()
            print(f"Description:    {description}")
            print()
            
            # Confirm
            confirm = input("Proceed with adjustment? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("❌ Adjustment cancelled")
                conn.close()
                return
            
            print()
            print("Processing adjustment...")
            
            # Generate transaction ID
            txn_id = f"AWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Determine transaction type
            txn_type = 'CREDIT' if amount >= 0 else 'DEBIT'
            abs_amount = abs(amount)
            
            # Insert adjustment transaction
            cursor.execute("""
                INSERT INTO admin_wallet_transactions 
                (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'ADMIN',  # Default admin ID
                txn_id,
                txn_type,
                abs_amount,
                balance_before,
                balance_after,
                description,
                f"MANUAL_ADJ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ))
            
            conn.commit()
            
            print()
            print("✓ Adjustment completed successfully!")
            print()
            print(f"Transaction ID: {txn_id}")
            print(f"Type:           {txn_type}")
            print(f"Amount:         ₹{abs_amount:,.2f}")
            print(f"New Balance:    ₹{balance_after:,.2f}")
            print()
            print("NOTE: This adjustment:")
            print("  ✓ WILL affect admin wallet balance")
            print("  ✓ WILL appear in admin_wallet_transactions table")
            print("  ✗ WILL NOT appear in PayIN reports")
            print("  ✗ WILL NOT appear in merchant reports")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 manual_admin_balance_adjustment.py <amount> \"<description>\"")
        print()
        print("Examples:")
        print("  python3 manual_admin_balance_adjustment.py 100000 \"Manual balance correction\"")
        print("  python3 manual_admin_balance_adjustment.py -50000 \"Balance adjustment for error\"")
        print("  python3 manual_admin_balance_adjustment.py 351194 \"Initial capital injection\"")
        print()
        print("Note: Use positive amount for credit, negative for debit")
        sys.exit(1)
    
    try:
        amount = float(sys.argv[1])
        description = sys.argv[2]
        
        if not description or description.strip() == "":
            print("❌ Error: Description cannot be empty")
            sys.exit(1)
        
        adjust_admin_balance(amount, description)
        
    except ValueError:
        print("❌ Error: Amount must be a valid number")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
