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

merchant_id = input("Enter merchant_id: ").strip()

cursor = connection.cursor()

print(f"\n{'='*80}")
print(f"QUICK WALLET CHECK FOR MERCHANT: {merchant_id}")
print(f"{'='*80}\n")

# Current balance
cursor.execute("""
    SELECT settled_wallet_balance, unsettled_wallet_balance
    FROM merchant_wallet
    WHERE merchant_id = %s
""", (merchant_id,))
wallet = cursor.fetchone()

print(f"Current Settled Balance: ₹{wallet['settled_wallet_balance']:,.2f}")
print(f"Current Unsettled Balance: ₹{wallet['unsettled_wallet_balance']:,.2f}")
print(f"Total: ₹{wallet['settled_wallet_balance'] + wallet['unsettled_wallet_balance']:,.2f}")

# Payout summary
cursor.execute("""
    SELECT 
        SUM(amount) as total_amount,
        SUM(charges) as total_charges,
        SUM(amount + charges) as total_deducted
    FROM payout_transactions
    WHERE merchant_id = %s
    AND status IN ('SUCCESS', 'PENDING', 'INITIATED')
""", (merchant_id,))
payout = cursor.fetchone()

print(f"\nTotal Payouts (SUCCESS/PENDING/INITIATED):")
print(f"  Amount: ₹{payout['total_amount']:,.2f}")
print(f"  Charges: ₹{payout['total_charges']:,.2f}")
print(f"  Total Deducted: ₹{payout['total_deducted']:,.2f}")

# Expected remaining
cursor.execute("""
    SELECT 
        SUM(CASE WHEN txn_type IN ('PAYIN_CREDIT', 'PAYIN_UNSETTLED_CREDIT', 'TOPUP', 'REFUND', 'SETTLEMENT_CREDIT') THEN amount ELSE 0 END) as credits,
        SUM(CASE WHEN txn_type IN ('PAYOUT_DEBIT', 'PAYOUT_CHARGE', 'PAYIN_CHARGE', 'SETTLEMENT_DEBIT') THEN amount ELSE 0 END) as debits
    FROM wallet_transactions
    WHERE merchant_id = %s
""", (merchant_id,))
wallet_txn = cursor.fetchone()

credits = wallet_txn['credits'] or Decimal('0')
debits = wallet_txn['debits'] or Decimal('0')
expected = credits - debits

print(f"\nWallet Transaction Summary:")
print(f"  Total Credits: ₹{credits:,.2f}")
print(f"  Total Debits: ₹{debits:,.2f}")
print(f"  Expected Balance: ₹{expected:,.2f}")

print(f"\nDISCREPANCY: ₹{expected - (wallet['settled_wallet_balance'] + wallet['unsettled_wallet_balance']):,.2f}")

# Check for missing deductions
cursor.execute("""
    SELECT COUNT(*) as count
    FROM payout_transactions pt
    LEFT JOIN wallet_transactions wt ON wt.reference_id = pt.txn_id AND wt.txn_type = 'PAYOUT_DEBIT'
    WHERE pt.merchant_id = %s
    AND pt.status IN ('SUCCESS', 'PENDING', 'INITIATED')
    AND wt.id IS NULL
""", (merchant_id,))
missing = cursor.fetchone()

if missing['count'] > 0:
    print(f"\n⚠️  WARNING: {missing['count']} payouts found without wallet deductions!")
    
    cursor.execute("""
        SELECT pt.txn_id, pt.amount, pt.charges, pt.status, pt.created_at
        FROM payout_transactions pt
        LEFT JOIN wallet_transactions wt ON wt.reference_id = pt.txn_id AND wt.txn_type = 'PAYOUT_DEBIT'
        WHERE pt.merchant_id = %s
        AND pt.status IN ('SUCCESS', 'PENDING', 'INITIATED')
        AND wt.id IS NULL
        ORDER BY pt.created_at DESC
    """, (merchant_id,))
    
    missing_txns = cursor.fetchall()
    total_missing = Decimal('0')
    
    print("\nMissing Payout Deductions:")
    for txn in missing_txns:
        print(f"  {txn['txn_id']} | ₹{txn['amount']:,.2f} + ₹{txn['charges']:,.2f} | {txn['status']} | {txn['created_at']}")
        total_missing += txn['amount'] + txn['charges']
    
    print(f"\nTotal Missing: ₹{total_missing:,.2f}")

print(f"\n{'='*80}\n")

cursor.close()
connection.close()
