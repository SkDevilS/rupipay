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

merchant_id = "9000000001"

cursor = connection.cursor()

print(f"\n{'='*80}")
print(f"FINDING THE MISSING ₹3.91 LAKH FOR MERCHANT: {merchant_id}")
print(f"{'='*80}\n")

# Expected calculation
starting_balance = Decimal('8019150.00')
payout_amount = Decimal('7567108.04')
payout_charges = Decimal('60605.04')
total_deducted = payout_amount + payout_charges
expected_remaining = starting_balance - total_deducted
current_balance = Decimal('471.04')
missing_amount = expected_remaining - current_balance

print(f"EXPECTED CALCULATION:")
print(f"  Starting Balance: ₹{starting_balance:,.2f}")
print(f"  Payout Amount: ₹{payout_amount:,.2f}")
print(f"  Payout Charges: ₹{payout_charges:,.2f}")
print(f"  Total Deducted: ₹{total_deducted:,.2f}")
print(f"  Expected Remaining: ₹{expected_remaining:,.2f}")
print(f"  Current Balance: ₹{current_balance:,.2f}")
print(f"  ⚠️  MISSING: ₹{missing_amount:,.2f}\n")

# Get ALL wallet transactions that are DEBITS
print(f"{'='*80}")
print("ALL DEBIT TRANSACTIONS FROM WALLET:")
print(f"{'='*80}\n")

cursor.execute("""
    SELECT 
        id,
        txn_type,
        amount,
        balance_after,
        reference_id,
        created_at,
        description
    FROM merchant_wallet_transactions
    WHERE merchant_id = %s
    AND txn_type IN ('DEBIT', 'SETTLEMENT')
    ORDER BY created_at DESC
""", (merchant_id,))

debits = cursor.fetchall()
total_debits = Decimal('0')

for txn in debits:
    print(f"{txn['created_at']} | {txn['txn_type']}")
    print(f"  Amount: ₹{txn['amount']:,.2f}")
    print(f"  Balance After: ₹{txn['balance_after']:,.2f}")
    print(f"  Reference: {txn['reference_id']}")
    print(f"  Description: {txn['description']}\n")
    total_debits += txn['amount']

print(f"TOTAL DEBITS: ₹{total_debits:,.2f}\n")

# Get ALL payouts
print(f"{'='*80}")
print("ALL PAYOUTS:")
print(f"{'='*80}\n")

cursor.execute("""
    SELECT 
        txn_id,
        amount,
        charge_amount,
        status,
        created_at
    FROM payout_transactions
    WHERE merchant_id = %s
    ORDER BY created_at DESC
""", (merchant_id,))

payouts = cursor.fetchall()
total_payout_amount = Decimal('0')
total_payout_charges = Decimal('0')

for payout in payouts:
    print(f"{payout['created_at']} | {payout['txn_id']}")
    print(f"  Amount: ₹{payout['amount']:,.2f}")
    print(f"  Charges: ₹{payout['charge_amount']:,.2f}")
    print(f"  Total: ₹{payout['amount'] + payout['charge_amount']:,.2f}")
    print(f"  Status: {payout['status']}\n")
    
    if payout['status'] in ['SUCCESS', 'PENDING', 'INITIATED']:
        total_payout_amount += payout['amount']
        total_payout_charges += payout['charge_amount']

print(f"TOTAL PAYOUT AMOUNT (SUCCESS/PENDING/INITIATED): ₹{total_payout_amount:,.2f}")
print(f"TOTAL PAYOUT CHARGES: ₹{total_payout_charges:,.2f}")
print(f"TOTAL: ₹{total_payout_amount + total_payout_charges:,.2f}\n")

# Compare
print(f"{'='*80}")
print("COMPARISON:")
print(f"{'='*80}\n")
print(f"Total Wallet Debits: ₹{total_debits:,.2f}")
print(f"Total Payouts + Charges: ₹{total_payout_amount + total_payout_charges:,.2f}")
print(f"Difference: ₹{total_debits - (total_payout_amount + total_payout_charges):,.2f}\n")

# Check if there are settlement debits
cursor.execute("""
    SELECT 
        id,
        amount,
        balance_after,
        reference_id,
        created_at,
        description
    FROM merchant_wallet_transactions
    WHERE merchant_id = %s
    AND txn_type = 'SETTLEMENT'
    ORDER BY created_at DESC
""", (merchant_id,))

settlements = cursor.fetchall()

if settlements:
    print(f"{'='*80}")
    print("SETTLEMENT DEBITS FOUND:")
    print(f"{'='*80}\n")
    
    total_settlement = Decimal('0')
    for txn in settlements:
        print(f"{txn['created_at']}")
        print(f"  Amount: ₹{txn['amount']:,.2f}")
        print(f"  Balance After: ₹{txn['balance_after']:,.2f}")
        print(f"  Reference: {txn['reference_id']}")
        print(f"  Description: {txn['description']}\n")
        total_settlement += txn['amount']
    
    print(f"TOTAL SETTLEMENT DEBITS: ₹{total_settlement:,.2f}\n")
    print(f"⚠️  THIS COULD BE THE MISSING AMOUNT!")

print(f"{'='*80}\n")

cursor.close()
connection.close()
