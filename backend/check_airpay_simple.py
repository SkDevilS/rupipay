#!/usr/bin/env python3
"""
Simple checker for recent Airpay transactions
"""
from database import get_db_connection

def check_transactions():
    print("=" * 100)
    print("AIRPAY RECENT TRANSACTIONS")
    print("=" * 100)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get most recent 2 Airpay transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    payee_name,
                    payee_email,
                    payee_mobile,
                    callback_url,
                    created_at,
                    updated_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 2
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No Airpay transactions found")
                return
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{'='*100}")
                print(f"TRANSACTION #{idx}")
                print(f"{'='*100}")
                print(f"📌 Transaction Details:")
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Amount: ₹{txn['amount']}")
                print(f"Charge: ₹{txn['charge_amount']}")
                print(f"Net Amount: ₹{txn['net_amount']}")
                print(f"Status: {txn['status']}")
                print(f"PG Txn ID: {txn['pg_txn_id']}")
                print(f"Bank Ref/UTR: {txn['bank_ref_no']}")
                print(f"Payment Mode: {txn['payment_mode']}")
                print(f"Payee: {txn['payee_name']}")
                print(f"Email: {txn['payee_email']}")
                print(f"Mobile: {txn['payee_mobile']}")
                print(f"Callback URL: {txn['callback_url']}")
                print(f"Created: {txn['created_at']}")
                print(f"Updated: {txn['updated_at']}")
                print(f"Completed: {txn['completed_at']}")
                
                # Check if status was updated (indicates callback was received)
                if txn['created_at'] != txn['updated_at']:
                    print(f"\n✅ Transaction was updated (callback likely received)")
                    print(f"   Time difference: {txn['updated_at'] - txn['created_at']}")
                else:
                    print(f"\n⚠️  Transaction not updated (no callback received yet)")
                
                # Check wallet transactions
                print(f"\n💰 Wallet Transactions:")
                print(f"{'-'*100}")
                cursor.execute("""
                    SELECT 
                        wallet_txn_id,
                        merchant_id,
                        txn_type,
                        amount,
                        balance_after,
                        description,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    for wtxn in wallet_txns:
                        print(f"  - {wtxn['txn_type']}: ₹{wtxn['amount']} (Balance: ₹{wtxn['balance_after']})")
                        print(f"    {wtxn['description']}")
                        print(f"    {wtxn['created_at']}")
                else:
                    print(f"  ⚠️  No wallet transactions found (wallet not credited yet)")
    
    finally:
        conn.close()
    
    print(f"\n{'='*100}")
    print("TO SEE WHAT AIRPAY SENT:")
    print(f"{'='*100}")
    print("\n1. Check server logs for Airpay callbacks:")
    print("   sudo journalctl -u moneyone-backend --since '2 hours ago' | grep -A 50 'Airpay V4 Payin Callback'")
    
    print("\n2. Check callback log file:")
    print("   cat /var/www/moneyone/moneyone/backend/logs/airpay_callbacks_*.log 2>/dev/null | tail -100")
    
    print("\n3. Search for specific order in logs:")
    if transactions:
        print(f"   sudo journalctl -u moneyone-backend | grep '{transactions[0]['order_id']}' | tail -50")
    
    print("\n4. Check raw callback data:")
    print("   cat /var/www/moneyone/moneyone/backend/logs/airpay_callbacks_*.log | grep -A 100 'TIMESTAMP'")

if __name__ == '__main__':
    check_transactions()
