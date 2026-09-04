#!/usr/bin/env python3
"""
Extract complete payout flow with all requests, responses, and timestamps
"""

import pymysql
from config import Config
from datetime import datetime
import json

# Reference IDs to extract
REFERENCE_IDS = [
    "DP202603211123227D557A",
    "DP2026032111230879694C",
    "DP20260321112021D5DFE0",
    "DP20260321111935565DB1",
    "DP2026032111191828B4E8",
    "DP202603211117295EF78D",
    "DP202603211116582EA094",
    "DP20260321110813AC31E9",
    "DP202603211102490B25BF",
    "DP202603211102228BEE47",
    "DP202603211102088F7A3E",
    "DP20260321105452D21C4F",
    "DP20260321105102FC67AE"
]

def get_db_connection():
    """Get database connection"""
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def format_timestamp(ts):
    """Format timestamp for display"""
    if ts:
        return ts.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def main():
    print("\n" + "=" * 100)
    print("COMPLETE PAYOUT TRANSACTION FLOW EXTRACTION")
    print("=" * 100)
    print(f"\nExtracting complete flow for {len(REFERENCE_IDS)} reference IDs")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = get_db_connection()
    if not conn:
        return
    
    output_file = f'complete_payout_flow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("COMPLETE PAYOUT TRANSACTION FLOW\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 100 + "\n\n")
        
        try:
            with conn.cursor() as cursor:
                for ref_id in REFERENCE_IDS:
                    f.write("\n" + "=" * 100 + "\n")
                    f.write(f"REFERENCE ID: {ref_id}\n")
                    f.write("=" * 100 + "\n\n")
                    
                    # 1. Get payout transaction details
                    f.write("📋 STEP 1: PAYOUT TRANSACTION INITIATED\n")
                    f.write("-" * 100 + "\n")
                    
                    query = """
                        SELECT *
                        FROM payout_transactions
                        WHERE reference_id = %s OR order_id = %s OR txn_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cursor.execute(query, (ref_id, ref_id, ref_id))
                    payout = cursor.fetchone()
                    
                    if not payout:
                        f.write(f"❌ No payout transaction found for {ref_id}\n\n")
                        print(f"❌ No payout transaction found for {ref_id}")
                        continue
                    
                    print(f"✓ Found payout: {ref_id}")
                    
                    f.write(f"Transaction ID: {payout['txn_id']}\n")
                    f.write(f"Order ID: {payout['order_id']}\n")
                    f.write(f"Reference ID: {payout['reference_id']}\n")
                    f.write(f"Merchant ID: {payout['merchant_id']}\n")
                    f.write(f"Admin ID: {payout['admin_id']}\n")
                    f.write(f"Amount: ₹{payout['amount']}\n")
                    f.write(f"Charge: ₹{payout['charge_amount']} ({payout['charge_type']})\n")
                    f.write(f"Net Amount: ₹{payout['net_amount']}\n")
                    f.write(f"Payment Gateway: {payout['pg_partner']}\n")
                    f.write(f"Payment Type: {payout['payment_type']}\n")
                    f.write(f"Status: {payout['status']}\n")
                    f.write(f"Created At: {format_timestamp(payout['created_at'])}\n")
                    f.write(f"Updated At: {format_timestamp(payout['updated_at'])}\n")
                    if payout['completed_at']:
                        f.write(f"Completed At: {format_timestamp(payout['completed_at'])}\n")
                    f.write("\n")
                    
                    f.write("Beneficiary Details:\n")
                    f.write(f"  Name: {payout['bene_name']}\n")
                    f.write(f"  Mobile: {payout['bene_mobile']}\n")
                    f.write(f"  Bank: {payout['bene_bank']}\n")
                    f.write(f"  Account: {payout['account_no']}\n")
                    f.write(f"  IFSC: {payout['ifsc_code']}\n")
                    if payout['vpa']:
                        f.write(f"  UPI: {payout['vpa']}\n")
                    f.write("\n")
                    
                    # 2. Payment Gateway Response
                    f.write("📤 STEP 2: PAYMENT GATEWAY RESPONSE\n")
                    f.write("-" * 100 + "\n")
                    f.write(f"PG Transaction ID: {payout['pg_txn_id'] or 'Not received yet'}\n")
                    f.write(f"Bank Reference No: {payout['bank_ref_no'] or 'Not received yet'}\n")
                    f.write(f"UTR: {payout['utr'] or 'Not received yet'}\n")
                    if payout['name_with_bank']:
                        f.write(f"Name with Bank: {payout['name_with_bank']}\n")
                        f.write(f"Name Match Score: {payout['name_match_score']}\n")
                    if payout['error_message']:
                        f.write(f"Error Message: {payout['error_message']}\n")
                    if payout['remarks']:
                        f.write(f"Remarks: {payout['remarks']}\n")
                    f.write("\n")
                    
                    # 3. Merchant Wallet Deduction
                    f.write("💰 STEP 3: MERCHANT WALLET TRANSACTIONS\n")
                    f.write("-" * 100 + "\n")
                    
                    query = """
                        SELECT *
                        FROM merchant_wallet_transactions
                        WHERE reference_id = %s OR txn_id = %s
                        ORDER BY created_at ASC
                    """
                    cursor.execute(query, (ref_id, payout['txn_id']))
                    merchant_txns = cursor.fetchall()
                    
                    if merchant_txns:
                        for idx, txn in enumerate(merchant_txns, 1):
                            f.write(f"\nTransaction {idx}:\n")
                            f.write(f"  Type: {txn['txn_type']}\n")
                            f.write(f"  Amount: ₹{txn['amount']}\n")
                            f.write(f"  Balance Before: ₹{txn['balance_before']}\n")
                            f.write(f"  Balance After: ₹{txn['balance_after']}\n")
                            if txn['on_hold_before'] is not None:
                                f.write(f"  On Hold Before: ₹{txn['on_hold_before']}\n")
                                f.write(f"  On Hold After: ₹{txn['on_hold_after']}\n")
                            f.write(f"  Description: {txn['description']}\n")
                            f.write(f"  Timestamp: {format_timestamp(txn['created_at'])}\n")
                    else:
                        f.write("No merchant wallet transactions found\n")
                    f.write("\n")
                    
                    # 4. Admin Wallet Transactions
                    f.write("💼 STEP 4: ADMIN WALLET TRANSACTIONS\n")
                    f.write("-" * 100 + "\n")
                    
                    query = """
                        SELECT *
                        FROM admin_wallet_transactions
                        WHERE reference_id = %s OR txn_id = %s
                        ORDER BY created_at ASC
                    """
                    cursor.execute(query, (ref_id, payout['txn_id']))
                    admin_txns = cursor.fetchall()
                    
                    if admin_txns:
                        for idx, txn in enumerate(admin_txns, 1):
                            f.write(f"\nTransaction {idx}:\n")
                            f.write(f"  Wallet Type: {txn['wallet_type']}\n")
                            f.write(f"  Type: {txn['txn_type']}\n")
                            f.write(f"  Amount: ₹{txn['amount']}\n")
                            f.write(f"  Balance Before: ₹{txn['balance_before']}\n")
                            f.write(f"  Balance After: ₹{txn['balance_after']}\n")
                            f.write(f"  Description: {txn['description']}\n")
                            f.write(f"  Timestamp: {format_timestamp(txn['created_at'])}\n")
                    else:
                        f.write("No admin wallet transactions found\n")
                    f.write("\n")
                    
                    # 5. Callback Logs
                    f.write("📞 STEP 5: MERCHANT CALLBACK\n")
                    f.write("-" * 100 + "\n")
                    
                    query = """
                        SELECT *
                        FROM callback_logs
                        WHERE txn_id = %s
                        ORDER BY created_at ASC
                    """
                    cursor.execute(query, (payout['txn_id'],))
                    callbacks = cursor.fetchall()
                    
                    if callbacks:
                        for idx, cb in enumerate(callbacks, 1):
                            f.write(f"\nCallback Attempt {idx}:\n")
                            f.write(f"  Callback URL: {cb['callback_url']}\n")
                            f.write(f"  Request Data: {cb['request_data']}\n")
                            f.write(f"  Response Code: {cb['response_code']}\n")
                            f.write(f"  Response Data: {cb['response_data']}\n")
                            f.write(f"  Timestamp: {format_timestamp(cb['created_at'])}\n")
                    else:
                        f.write("No callback logs found\n")
                        if payout['callback_url']:
                            f.write(f"Callback URL configured: {payout['callback_url']}\n")
                    f.write("\n")
                    
                    # 6. Timeline Summary
                    f.write("⏱️  TIMELINE SUMMARY\n")
                    f.write("-" * 100 + "\n")
                    
                    timeline = []
                    timeline.append((payout['created_at'], "Transaction Created"))
                    if payout['updated_at'] and payout['updated_at'] != payout['created_at']:
                        timeline.append((payout['updated_at'], f"Status Updated to {payout['status']}"))
                    if payout['completed_at']:
                        timeline.append((payout['completed_at'], "Transaction Completed"))
                    
                    for txn in merchant_txns:
                        timeline.append((txn['created_at'], f"Merchant Wallet: {txn['txn_type']}"))
                    
                    for txn in admin_txns:
                        timeline.append((txn['created_at'], f"Admin Wallet: {txn['txn_type']}"))
                    
                    for cb in callbacks:
                        timeline.append((cb['created_at'], f"Callback Sent (Response: {cb['response_code']})"))
                    
                    timeline.sort(key=lambda x: x[0] if x[0] else datetime.min)
                    
                    for ts, event in timeline:
                        f.write(f"{format_timestamp(ts)} - {event}\n")
                    
                    f.write("\n")
                    
        finally:
            conn.close()
    
    print(f"\n✅ Complete flow extracted to: {output_file}")
    print(f"\nYou can view it with: cat {output_file}")
    print(f"Or search in it with: grep 'keyword' {output_file}\n")

if __name__ == '__main__':
    main()
