import pymysql
from decimal import Decimal
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
connection = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor
)

def diagnose_wallet_discrepancy(merchant_id):
    """
    Diagnose wallet balance discrepancy for a merchant
    """
    cursor = connection.cursor()
    
    print(f"\n{'='*80}")
    print(f"WALLET BALANCE DISCREPANCY DIAGNOSIS FOR MERCHANT: {merchant_id}")
    print(f"{'='*80}\n")
    
    # 1. Get current wallet balances
    print("1. CURRENT WALLET BALANCES:")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            merchant_id,
            settled_wallet_balance,
            unsettled_wallet_balance,
            settled_wallet_balance + unsettled_wallet_balance as total_balance
        FROM merchant_wallet
        WHERE merchant_id = %s
    """, (merchant_id,))
    
    wallet = cursor.fetchone()
    if wallet:
        print(f"Settled Wallet Balance: ₹{wallet['settled_wallet_balance']:,.2f}")
        print(f"Unsettled Wallet Balance: ₹{wallet['unsettled_wallet_balance']:,.2f}")
        print(f"Total Balance: ₹{wallet['total_balance']:,.2f}")
    else:
        print(f"No wallet found for merchant {merchant_id}")
        return
    
    # 2. Get payout summary
    print(f"\n2. PAYOUT SUMMARY:")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            COUNT(*) as total_payouts,
            SUM(amount) as total_payout_amount,
            SUM(charges) as total_charges,
            SUM(amount + charges) as total_deducted,
            status
        FROM payout_transactions
        WHERE merchant_id = %s
        GROUP BY status
        ORDER BY status
    """, (merchant_id,))
    
    payouts = cursor.fetchall()
    total_payout_amount = Decimal('0')
    total_charges = Decimal('0')
    total_deducted = Decimal('0')
    
    for payout in payouts:
        print(f"\nStatus: {payout['status']}")
        print(f"  Count: {payout['total_payouts']}")
        print(f"  Total Amount: ₹{payout['total_payout_amount']:,.2f}")
        print(f"  Total Charges: ₹{payout['total_charges']:,.2f}")
        print(f"  Total Deducted: ₹{payout['total_deducted']:,.2f}")
        
        if payout['status'] in ['SUCCESS', 'PENDING', 'INITIATED']:
            total_payout_amount += payout['total_payout_amount'] or Decimal('0')
            total_charges += payout['total_charges'] or Decimal('0')
            total_deducted += payout['total_deducted'] or Decimal('0')
    
    print(f"\nTOTAL (SUCCESS + PENDING + INITIATED):")
    print(f"  Payout Amount: ₹{total_payout_amount:,.2f}")
    print(f"  Charges: ₹{total_charges:,.2f}")
    print(f"  Total Deducted: ₹{total_deducted:,.2f}")
    
    # 3. Get payin summary
    print(f"\n3. PAYIN SUMMARY:")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            COUNT(*) as total_payins,
            SUM(amount) as total_payin_amount,
            SUM(charges) as total_payin_charges,
            status
        FROM payin_transactions
        WHERE merchant_id = %s
        GROUP BY status
        ORDER BY status
    """, (merchant_id,))
    
    payins = cursor.fetchall()
    total_payin_amount = Decimal('0')
    total_payin_charges = Decimal('0')
    
    for payin in payins:
        print(f"\nStatus: {payin['status']}")
        print(f"  Count: {payin['total_payins']}")
        print(f"  Total Amount: ₹{payin['total_payin_amount']:,.2f}")
        print(f"  Total Charges: ₹{payin['total_payin_charges']:,.2f}")
        
        if payin['status'] == 'SUCCESS':
            total_payin_amount += payin['total_payin_amount'] or Decimal('0')
            total_payin_charges += payin['total_payin_charges'] or Decimal('0')
    
    print(f"\nTOTAL SUCCESS PAYINS:")
    print(f"  Amount: ₹{total_payin_amount:,.2f}")
    print(f"  Charges: ₹{total_payin_charges:,.2f}")
    print(f"  Net Credit: ₹{total_payin_amount - total_payin_charges:,.2f}")
    
    # 4. Get wallet transaction summary
    print(f"\n4. WALLET TRANSACTION SUMMARY:")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            txn_type,
            COUNT(*) as count,
            SUM(amount) as total_amount
        FROM wallet_transactions
        WHERE merchant_id = %s
        GROUP BY txn_type
        ORDER BY txn_type
    """, (merchant_id,))
    
    wallet_txns = cursor.fetchall()
    for txn in wallet_txns:
        print(f"{txn['txn_type']}: {txn['count']} transactions, ₹{txn['total_amount']:,.2f}")
    
    # 5. Calculate expected balance
    print(f"\n5. EXPECTED BALANCE CALCULATION:")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN txn_type IN ('PAYIN_CREDIT', 'PAYIN_UNSETTLED_CREDIT', 'TOPUP', 'REFUND', 'SETTLEMENT_CREDIT') THEN amount ELSE 0 END) as total_credits,
            SUM(CASE WHEN txn_type IN ('PAYOUT_DEBIT', 'PAYOUT_CHARGE', 'PAYIN_CHARGE', 'SETTLEMENT_DEBIT') THEN amount ELSE 0 END) as total_debits
        FROM wallet_transactions
        WHERE merchant_id = %s
    """, (merchant_id,))
    
    wallet_summary = cursor.fetchone()
    total_credits = wallet_summary['total_credits'] or Decimal('0')
    total_debits = wallet_summary['total_debits'] or Decimal('0')
    expected_balance = total_credits - total_debits
    
    print(f"Total Credits: ₹{total_credits:,.2f}")
    print(f"Total Debits: ₹{total_debits:,.2f}")
    print(f"Expected Balance: ₹{expected_balance:,.2f}")
    print(f"Actual Balance: ₹{wallet['total_balance']:,.2f}")
    print(f"Discrepancy: ₹{expected_balance - wallet['total_balance']:,.2f}")
    
    # 6. Check for missing wallet transactions
    print(f"\n6. CHECKING FOR MISSING WALLET TRANSACTIONS:")
    print("-" * 80)
    
    # Check payouts without wallet deductions
    cursor.execute("""
        SELECT 
            pt.txn_id,
            pt.amount,
            pt.charges,
            pt.status,
            pt.created_at
        FROM payout_transactions pt
        LEFT JOIN wallet_transactions wt_debit ON wt_debit.reference_id = pt.txn_id AND wt_debit.txn_type = 'PAYOUT_DEBIT'
        LEFT JOIN wallet_transactions wt_charge ON wt_charge.reference_id = pt.txn_id AND wt_charge.txn_type = 'PAYOUT_CHARGE'
        WHERE pt.merchant_id = %s
        AND pt.status IN ('SUCCESS', 'PENDING', 'INITIATED')
        AND (wt_debit.id IS NULL OR wt_charge.id IS NULL)
        ORDER BY pt.created_at DESC
        LIMIT 20
    """, (merchant_id,))
    
    missing_payout_txns = cursor.fetchall()
    if missing_payout_txns:
        print(f"\nFound {len(missing_payout_txns)} payouts without proper wallet deductions:")
        missing_amount = Decimal('0')
        missing_charges = Decimal('0')
        
        for txn in missing_payout_txns:
            print(f"\nTxn ID: {txn['txn_id']}")
            print(f"  Amount: ₹{txn['amount']:,.2f}")
            print(f"  Charges: ₹{txn['charges']:,.2f}")
            print(f"  Status: {txn['status']}")
            print(f"  Date: {txn['created_at']}")
            missing_amount += txn['amount']
            missing_charges += txn['charges']
        
        print(f"\nTotal Missing Deductions:")
        print(f"  Amount: ₹{missing_amount:,.2f}")
        print(f"  Charges: ₹{missing_charges:,.2f}")
        print(f"  Total: ₹{missing_amount + missing_charges:,.2f}")
    else:
        print("All payouts have corresponding wallet transactions.")
    
    # 7. Check for payins without wallet credits
    cursor.execute("""
        SELECT 
            pt.txn_id,
            pt.amount,
            pt.charges,
            pt.status,
            pt.created_at
        FROM payin_transactions pt
        LEFT JOIN wallet_transactions wt ON wt.reference_id = pt.txn_id 
            AND wt.txn_type IN ('PAYIN_CREDIT', 'PAYIN_UNSETTLED_CREDIT')
        WHERE pt.merchant_id = %s
        AND pt.status = 'SUCCESS'
        AND wt.id IS NULL
        ORDER BY pt.created_at DESC
        LIMIT 20
    """, (merchant_id,))
    
    missing_payin_txns = cursor.fetchall()
    if missing_payin_txns:
        print(f"\nFound {len(missing_payin_txns)} payins without wallet credits:")
        missing_payin_amount = Decimal('0')
        
        for txn in missing_payin_txns:
            print(f"\nTxn ID: {txn['txn_id']}")
            print(f"  Amount: ₹{txn['amount']:,.2f}")
            print(f"  Charges: ₹{txn['charges']:,.2f}")
            print(f"  Status: {txn['status']}")
            print(f"  Date: {txn['created_at']}")
            missing_payin_amount += txn['amount'] - txn['charges']
        
        print(f"\nTotal Missing Credits: ₹{missing_payin_amount:,.2f}")
    else:
        print("\nAll success payins have corresponding wallet credits.")
    
    # 8. Recent wallet transactions
    print(f"\n8. RECENT WALLET TRANSACTIONS (Last 20):")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            id,
            txn_type,
            amount,
            balance_after,
            reference_id,
            created_at
        FROM wallet_transactions
        WHERE merchant_id = %s
        ORDER BY created_at DESC
        LIMIT 20
    """, (merchant_id,))
    
    recent_txns = cursor.fetchall()
    for txn in recent_txns:
        print(f"\n{txn['created_at']} | {txn['txn_type']}")
        print(f"  Amount: ₹{txn['amount']:,.2f}")
        print(f"  Balance After: ₹{txn['balance_after']:,.2f}")
        print(f"  Reference: {txn['reference_id']}")
    
    print(f"\n{'='*80}\n")
    
    cursor.close()

if __name__ == "__main__":
    # Replace with the actual merchant_id you want to diagnose
    merchant_id = input("Enter merchant_id to diagnose: ").strip()
    
    try:
        diagnose_wallet_discrepancy(merchant_id)
    finally:
        connection.close()
