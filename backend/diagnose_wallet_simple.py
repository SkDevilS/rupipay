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
print(f"WALLET BALANCE DIAGNOSIS FOR MERCHANT: {merchant_id}")
print(f"{'='*80}\n")

# Get current wallet balance (checking what columns exist)
cursor.execute("SHOW COLUMNS FROM merchant_wallet")
columns = cursor.fetchall()
column_names = [col['Field'] for col in columns]

print("Available wallet columns:", column_names)
print()

# Get wallet balance
cursor.execute(f"SELECT * FROM merchant_wallet WHERE merchant_id = %s", (merchant_id,))
wallet = cursor.fetchone()

if wallet:
    print("CURRENT WALLET:")
    print(f"  Total Balance: ₹{wallet.get('balance', 0):,.2f}")
    print(f"  Settled Balance: ₹{wallet.get('settled_balance', 0):,.2f}")
    print(f"  Unsettled Balance: ₹{wallet.get('unsettled_balance', 0):,.2f}")
    print(f"  Last Updated: {wallet.get('last_updated', 'N/A')}")
else:
    print(f"❌ No wallet found for merchant {merchant_id}")
    connection.close()
    exit()

# Get payout summary
print(f"\n{'='*40}")
print("PAYOUT SUMMARY:")
print('='*40)

cursor.execute("""
    SELECT 
        status,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        SUM(charges) as total_charges,
        SUM(amount + charges) as total_deducted
    FROM payout_transactions
    WHERE merchant_id = %s
    GROUP BY status
    ORDER BY status
""", (merchant_id,))

payouts = cursor.fetchall()
total_payout_deducted = Decimal('0')

for payout in payouts:
    print(f"\n{payout['status']}:")
    print(f"  Count: {payout['count']}")
    print(f"  Amount: ₹{payout['total_amount']:,.2f}")
    print(f"  Charges: ₹{payout['total_charges']:,.2f}")
    print(f"  Total: ₹{payout['total_deducted']:,.2f}")
    
    if payout['status'] in ['SUCCESS', 'PENDING', 'INITIATED']:
        total_payout_deducted += payout['total_deducted']

print(f"\nTOTAL DEDUCTED (SUCCESS/PENDING/INITIATED): ₹{total_payout_deducted:,.2f}")

# Get payin summary
print(f"\n{'='*40}")
print("PAYIN SUMMARY:")
print('='*40)

cursor.execute("""
    SELECT 
        status,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        SUM(charges) as total_charges
    FROM payin_transactions
    WHERE merchant_id = %s
    GROUP BY status
    ORDER BY status
""", (merchant_id,))

payins = cursor.fetchall()
total_payin_credited = Decimal('0')

for payin in payins:
    print(f"\n{payin['status']}:")
    print(f"  Count: {payin['count']}")
    print(f"  Amount: ₹{payin['total_amount']:,.2f}")
    print(f"  Charges: ₹{payin['total_charges']:,.2f}")
    
    if payin['status'] == 'SUCCESS':
        total_payin_credited += (payin['total_amount'] - payin['total_charges'])

print(f"\nTOTAL CREDITED (SUCCESS): ₹{total_payin_credited:,.2f}")

# Check wallet transactions
print(f"\n{'='*40}")
print("WALLET TRANSACTIONS SUMMARY:")
print('='*40)

cursor.execute("""
    SELECT 
        txn_type,
        COUNT(*) as count,
        SUM(amount) as total
    FROM wallet_transactions
    WHERE merchant_id = %s
    GROUP BY txn_type
    ORDER BY txn_type
""", (merchant_id,))

wallet_txns = cursor.fetchall()

total_credits = Decimal('0')
total_debits = Decimal('0')

for txn in wallet_txns:
    print(f"{txn['txn_type']}: {txn['count']} txns, ₹{txn['total']:,.2f}")
    
    if txn['txn_type'] in ['PAYIN_CREDIT', 'PAYIN_UNSETTLED_CREDIT', 'TOPUP', 'REFUND', 'SETTLEMENT_CREDIT']:
        total_credits += txn['total']
    elif txn['txn_type'] in ['PAYOUT_DEBIT', 'PAYOUT_CHARGE', 'PAYIN_CHARGE', 'SETTLEMENT_DEBIT']:
        total_debits += txn['total']

print(f"\nTotal Credits: ₹{total_credits:,.2f}")
print(f"Total Debits: ₹{total_debits:,.2f}")
print(f"Expected Balance: ₹{total_credits - total_debits:,.2f}")

# Check for missing wallet transactions
print(f"\n{'='*40}")
print("CHECKING FOR MISSING TRANSACTIONS:")
print('='*40)

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
    LIMIT 10
""", (merchant_id,))

missing = cursor.fetchall()

if missing:
    print(f"\n⚠️  Found {len(missing)} payouts without proper wallet deductions:\n")
    
    missing_total = Decimal('0')
    
    for txn in missing:
        debit_status = "✅" if txn['has_debit'] else "❌"
        charge_status = "✅" if txn['has_charge'] else "❌"
        
        print(f"Txn: {txn['txn_id']} | {txn['created_at']}")
        print(f"  Amount: ₹{txn['amount']:,.2f} {debit_status} | Charges: ₹{txn['charges']:,.2f} {charge_status}")
        print(f"  Status: {txn['status']}")
        
        if not txn['has_debit']:
            missing_total += txn['amount']
        if not txn['has_charge']:
            missing_total += txn['charges']
        print()
    
    print(f"💸 TOTAL MISSING DEDUCTIONS: ₹{missing_total:,.2f}")
    print(f"\n🔍 THIS IS LIKELY THE CAUSE OF THE DISCREPANCY!")
else:
    print("\n✅ All payouts have proper wallet deductions")

# Recent wallet transactions
print(f"\n{'='*40}")
print("LAST 10 WALLET TRANSACTIONS:")
print('='*40 + "\n")

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

recent = cursor.fetchall()

for txn in recent:
    print(f"{txn['created_at']} | {txn['txn_type']}")
    print(f"  Amount: ₹{txn['amount']:,.2f} | Balance After: ₹{txn['balance_after']:,.2f}")
    print(f"  Ref: {txn['reference_id']}\n")

print("="*80 + "\n")

cursor.close()
connection.close()
