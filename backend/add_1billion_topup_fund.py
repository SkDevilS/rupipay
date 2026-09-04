#!/usr/bin/env python3
"""
Add ₹1,000,000,000 (1 Billion) to Admin Top Up Fund
======================================================
This script credits 1 billion rupees to the admin wallet so the admin
can top up merchant wallets from the Fund Manager → TopUp Fund section.

HOW IT WORKS:
- Inserts a CREDIT record in admin_wallet_transactions with description
  matching 'Initial capital - ...' so the wallet_routes.py balance
  formula picks it up as a manual adjustment.
- Formula: admin_balance = total_payin + total_fetch + admin_unsettled
                           - total_topup - total_settlements
                           + total_adjustments  ← this script adds here

USAGE:
    cd backend
    python add_1billion_topup_fund.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import uuid
from decimal import Decimal


AMOUNT_TO_ADD = Decimal('1000000000.00')  # ₹1,000,000,000  (1 Billion)
DESCRIPTION   = 'Initial capital - Top-up fund credit of 1 Billion'


def show_banner():
    print("\n" + "=" * 70)
    print("  ADD ₹1,000,000,000 (1 BILLION) TO ADMIN TOP-UP FUND")
    print("=" * 70)
    print(f"\n  Amount to add : ₹{AMOUNT_TO_ADD:,.2f}")
    print(f"  Description   : {DESCRIPTION}")
    print(f"  Affects       : Admin Panel → Fund Manager → TopUp Fund")
    print("=" * 70 + "\n")


def get_current_balance(cursor):
    """Re-use the exact same formula as wallet_routes.py /api/wallet/admin/overview"""

    # Total successful payin
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as v
        FROM payin_transactions
        WHERE status = 'SUCCESS'
    """)
    total_payin = Decimal(str(cursor.fetchone()['v']))

    # Total approved fund requests (topups already given to merchants)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as v
        FROM fund_requests
        WHERE status = 'APPROVED'
    """)
    total_topup = Decimal(str(cursor.fetchone()['v']))

    # Total fetch from merchants
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as v
        FROM merchant_wallet_transactions
        WHERE txn_type = 'DEBIT'
        AND description LIKE %s
    """, ('%fetched by admin%',))
    total_fetch = Decimal(str(cursor.fetchone()['v']))

    # Total settlements
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as v
        FROM settlement_transactions
    """)
    total_settlements = Decimal(str(cursor.fetchone()['v']))

    # Admin unsettled balance
    cursor.execute("""
        SELECT COALESCE(unsettled_balance, 0) as v
        FROM admin_wallet
        WHERE admin_id = 'admin'
    """)
    row = cursor.fetchone()
    admin_unsettled = Decimal(str(row['v'])) if row else Decimal('0')

    # Manual adjustments (the ones that affect admin_balance)
    cursor.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN txn_type = 'CREDIT' THEN amount
                WHEN txn_type = 'DEBIT'  THEN -amount
                ELSE 0
            END
        ), 0) as v
        FROM admin_wallet_transactions
        WHERE description LIKE '%Manual balance%'
        OR    description LIKE '%Balance adjustment%'
        OR    description LIKE '%Initial capital%'
    """)
    total_adjustments = Decimal(str(cursor.fetchone()['v']))

    admin_balance = (total_payin + total_fetch + admin_unsettled
                     - total_topup - total_settlements + total_adjustments)

    return {
        'total_payin'      : total_payin,
        'total_fetch'      : total_fetch,
        'admin_unsettled'  : admin_unsettled,
        'total_topup'      : total_topup,
        'total_settlements': total_settlements,
        'total_adjustments': total_adjustments,
        'admin_balance'    : admin_balance,
    }


def print_balance_breakdown(label, data):
    print(f"\n  {label}")
    print(f"    PayIN received         : + ₹{data['total_payin']:>20,.2f}")
    print(f"    Fetched from merchants : + ₹{data['total_fetch']:>20,.2f}")
    print(f"    Unsettled balance      : + ₹{data['admin_unsettled']:>20,.2f}")
    print(f"    Fund Requests approved : - ₹{data['total_topup']:>20,.2f}")
    print(f"    Settlements done       : - ₹{data['total_settlements']:>20,.2f}")
    print(f"    Manual adjustments     : + ₹{data['total_adjustments']:>20,.2f}")
    print(f"    {'─' * 48}")
    print(f"    Admin TopUp Balance    : = ₹{data['admin_balance']:>20,.2f}")


def add_balance():
    show_banner()

    conn = get_db_connection()
    if not conn:
        print("  ❌  Database connection failed. Check your .env / database config.")
        return False

    try:
        with conn.cursor() as cursor:
            # ── Step 0: Find admin_id ──────────────────────────────────────
            cursor.execute("SELECT admin_id FROM admin_users LIMIT 1")
            row = cursor.fetchone()
            admin_id = row['admin_id'] if row else 'admin'
            print(f"  Step 0: Target Admin ID identified: {admin_id}")

            # ── Step 1: Show current balance ────────────────────────────────
            print("  Step 1: Checking current admin TopUp Fund balance...")
            before = get_current_balance(cursor)
            print_balance_breakdown("BEFORE", before)

            # ── Step 2: Ensure admin_wallet row exists ──────────────────────
            print("\n  Step 2: Ensuring admin_wallet row exists...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("""
                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                VALUES (%s, 0.00, 0.00)
                ON DUPLICATE KEY UPDATE admin_id = admin_id
            """, (admin_id,))
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            print("    ✓ admin_wallet row OK")

            # ── Step 3: Insert the credit transaction ───────────────────────
            txn_id = f"ADM_1B_{uuid.uuid4().hex[:12].upper()}"
            print(f"\n  Step 3: Inserting credit transaction ({txn_id})...")
            cursor.execute("""
                INSERT INTO admin_wallet_transactions
                    (admin_id, txn_id, txn_type, amount, description, created_at)
                VALUES
                    (%s, %s, 'CREDIT', %s, %s, CURRENT_TIMESTAMP)
            """, (admin_id, txn_id, float(AMOUNT_TO_ADD), DESCRIPTION))
            print(f"    ✓ Transaction inserted: {txn_id}")

            conn.commit()

            # ── Step 4: Verify new balance ──────────────────────────────────
            print("\n  Step 4: Verifying new balance...")
            after = get_current_balance(cursor)
            print_balance_breakdown("AFTER", after)

            increase = after['admin_balance'] - before['admin_balance']
            print(f"\n  Balance increase: ₹{increase:,.2f}")

            if increase != AMOUNT_TO_ADD:
                print(f"\n  ⚠️  Warning: Expected increase of ₹{AMOUNT_TO_ADD:,.2f} "
                      f"but got ₹{increase:,.2f}. Please investigate.")
            else:
                print(f"\n  ✅  Verified: Balance increased by exactly ₹{AMOUNT_TO_ADD:,.2f}")

            return True

    except Exception as exc:
        print(f"\n  ❌  Error: {exc}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  ⚠️   WARNING: This will add ₹1,000,000,000 (1 Billion) to the admin")
    print("       TopUp Fund balance. This cannot be undone easily.")
    print("\n  Press Enter to continue, or Ctrl+C to cancel...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\n  ❌  Cancelled by user.")
        sys.exit(0)

    success = add_balance()

    print("\n" + "=" * 70)
    if success:
        print("  ✅  DONE — Admin TopUp Fund credited with ₹1,000,000,000")
        print("\n  Next steps:")
        print("  1. Login to the Admin Panel")
        print("  2. Go to Fund Manager → TopUp Fund")
        print("  3. The new balance should be visible there")
        print("  4. You can now approve / create fund top-ups for merchants")
    else:
        print("  ❌  FAILED — No changes were committed to the database")
    print("=" * 70 + "\n")

    sys.exit(0 if success else 1)
