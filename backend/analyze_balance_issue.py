"""
Analyze the wallet balance discrepancy issue

Given information:
- Settled wallet balance: 8,019,150
- Payout done: 75,67,108.04 (₹7,567,108.04)
- Charges: 60,605.04
- Current showing: 471

Expected calculation:
Starting balance: 8,019,150
Payout amount: 7,567,108.04
Charges: 60,605.04
Total deducted: 7,567,108.04 + 60,605.04 = 7,627,713.08

Expected remaining: 8,019,150 - 7,627,713.08 = 391,436.92

But showing: 471

Discrepancy: 391,436.92 - 471 = 390,965.92 missing!
"""

import pymysql
from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv()

connection = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor
)

print("\n" + "="*80)
print("WALLET BALANCE DISCREPANCY ANALYSIS")
print("="*80)

merchant_id = input("\nEnter merchant_id: ").strip()

cursor = connection.cursor()

# Get current wallet state
cursor.execute("""
    SELECT 
        settled_wallet_balance,
        unsettled_wallet_balance,
        settled_wallet_balance + unsettled_wallet_balance as total
    FROM merchant_wallet
    WHERE merchant_id = %s
""", (merchant_id,))

wallet = cursor.fetchone()

if not wallet:
    print(f"❌ Merchant {merchant_id} not found!")
    connection.close()
    exit()

print(f"\n📊 CURRENT WALLET STATE:")
print(f"   Settled: ₹{wallet['settled_wallet_balance']:,.2f}")
print(f"   Unsettled: ₹{wallet['unsettled_wallet_balance']:,.2f}")
print(f"   Total: ₹{wallet['total']:,.2f}")

# Get all wallet transactions to trace the flow
cursor.execute("""
    SELECT 
        txn_type,
        SUM(amount) as total_amount,
        COUNT(*) as count
    FROM wallet_transactions
    WHERE merchant_id = %s
    GROUP BY txn_type
    ORDER BY txn_type
""", (merchant_id,))

print(f"\n💰 WALLET TRANSACTION BREAKDOWN:")
wallet_txns = cursor.fetchall()

total_in = Decimal('0')
total_out = Decimal('0')

for txn in wallet_txns:
    print(f"   {txn['txn_type']}: ₹{txn['total_amount']:,.2f} ({txn['count']} txns)")
    
    if txn['txn_type'] in ['PAYIN_CREDIT', 'PAYIN_UNSETTLED_CREDIT', 'TOPUP', 'REFUND', 'SETTLEMENT_CREDIT']:
        total_in += txn['total_amount']
    elif txn['txn_type'] in ['PAYOUT_DEBIT', 'PAYOUT_CHARGE', 'PAYIN_CHARGE', 'SETTLEMENT_DEBIT']:
        total_out += txn['total_amount']

print(f"\n   Total IN: ₹{total_in:,.2f}")
print(f"   Total OUT: ₹{total_out:,.2f}")
print(f"   Expected Balance: ₹{total_in - total_out:,.2f}")
print(f"   Actual Balance: ₹{wallet['total']:,.2f}")
print(f"   ⚠️  DISCREPANCY: ₹{(total_in - total_out) - wallet['total']:,.2f}")

# Check for payouts without wallet deductions
cursor.execute("""
    SELECT 
        pt.txn_id,
        pt.amount,
        pt.charges,
        pt.status,
        pt.created_at,
        wt_debit.id as has_debit,
        wt_charge.id as has_charge
    FROM payout_transactions pt
    LEFT JOIN wallet_transactions wt_debit 
        ON wt_debit.reference_id = pt.txn_id 
        AND wt_debit.txn_type = 'PAYOUT_DEBIT'
    LEFT JOIN wallet_transactions wt_charge 
        ON wt_charge.reference_id = pt.txn_id 
        AND wt_charge.txn_type = 'PAYOUT_CHARGE'
    WHERE pt.merchant_id = %s
    AND pt.status IN ('SUCCESS', 'PENDING', 'INITIATED')
    AND (wt_debit.id IS NULL OR wt_charge.id IS NULL)
    ORDER BY pt.created_at DESC
""", (merchant_id,))

missing_deductions = cursor.fetchall()

if missing_deductions:
    print(f"\n🚨 FOUND {len(missing_deductions)} PAYOUTS WITHOUT PROPER WALLET DEDUCTIONS:")
    
    missing_total = Decimal('0')
    
    for txn in missing_deductions:
        missing_debit = "❌" if not txn['has_debit'] else "✅"
        missing_charge = "❌" if not txn['has_charge'] else "✅"
        
        print(f"\n   Txn: {txn['txn_id']}")
        print(f"   Amount: ₹{txn['amount']:,.2f} {missing_debit}")
        print(f"   Charges: ₹{txn['charges']:,.2f} {missing_charge}")
        print(f"   Status: {txn['status']}")
        print(f"   Date: {txn['created_at']}")
        
        if not txn['has_debit']:
            missing_total += txn['amount']
        if not txn['has_charge']:
            missing_total += txn['charges']
    
    print(f"\n   💸 TOTAL MISSING DEDUCTIONS: ₹{missing_total:,.2f}")
    print(f"\n   This explains the discrepancy!")
else:
    print(f"\n✅ All payouts have proper wallet deductions")

# Check payout summary
cursor.execute("""
    SELECT 
        status,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        SUM(charges) as total_charges
    FROM payout_transactions
    WHERE merchant_id = %s
    GROUP BY status
""", (merchant_id,))

print(f"\n📤 PAYOUT SUMMARY:")
payouts = cursor.fetchall()

for payout in payouts:
    print(f"   {payout['status']}: {payout['count']} txns")
    print(f"      Amount: ₹{payout['total_amount']:,.2f}")
    print(f"      Charges: ₹{payout['total_charges']:,.2f}")

# Check recent transactions
cursor.execute("""
    SELECT 
        txn_type,
        amount,
        balance_after,
        reference_id,
        created_at
    FROM wallet_transactions
    WHERE merchant_id = %s
    ORDER BY created_at DESC
    LIMIT 10
""", (merchant_id,))

print(f"\n📜 LAST 10 WALLET TRANSACTIONS:")
recent = cursor.fetchall()

for txn in recent:
    print(f"   {txn['created_at']} | {txn['txn_type']}")
    print(f"      Amount: ₹{txn['amount']:,.2f} | Balance After: ₹{txn['balance_after']:,.2f}")
    print(f"      Ref: {txn['reference_id']}")

print("\n" + "="*80 + "\n")

cursor.close()
connection.close()
