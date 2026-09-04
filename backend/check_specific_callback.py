#!/usr/bin/env python3
"""
Script to check if a specific Mudrape callback was received
Based on the callback payload structure
"""

import sys
from database import get_db_connection
from datetime import datetime
import json

def format_datetime(dt):
    """Format datetime for display"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def check_callback_by_payload(ref_id=None, txn_id=None, amount=None):
    """
    Check if a specific callback was received based on payload data
    
    Expected callback format:
    {
        "amount": 300,
        "ref_id": "20260303133259143440",
        "source": "SUCCESS",
        "status": "SUCCESS",
        "txn_id": "MPAY80087485652",
        "payeeVpa": "9810244341.2@hdfc",
        "timestamp": "2026-03-03T08:03:35.668Z"
    }
    
    Args:
        ref_id: Mudrape ref_id (our order_id)
        txn_id: Mudrape txn_id (PG transaction ID)
        amount: Transaction amount
    """
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 100)
            print("MUDRAPE CALLBACK VERIFICATION")
            print("=" * 100)
            print(f"\nSearching for callback with:")
            if ref_id:
                print(f"  ref_id (order_id): {ref_id}")
            if txn_id:
                print(f"  txn_id (PG TXN ID): {txn_id}")
            if amount:
                print(f"  amount: ₹{amount}")
            print("")
            
            # Step 1: Find transaction in database
            print("STEP 1: Checking if transaction exists in database")
            print("-" * 100)
            
            query = """
                SELECT 
                    pt.txn_id,
                    pt.order_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.net_amount,
                    pt.charge_amount,
                    pt.status,
                    pt.pg_partner,
                    pt.pg_txn_id,
                    pt.bank_ref_no as utr,
                    pt.created_at,
                    pt.completed_at,
                    pt.updated_at,
                    m.full_name as merchant_name
                FROM payin_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE 1=1
            """
            params = []
            
            if ref_id:
                query += " AND pt.order_id = %s"
                params.append(ref_id)
            
            if txn_id:
                query += " AND pt.pg_txn_id = %s"
                params.append(txn_id)
            
            if amount:
                query += " AND pt.amount = %s"
                params.append(amount)
            
            cursor.execute(query, params)
            txn = cursor.fetchone()
            
            if not txn:
                print("❌ TRANSACTION NOT FOUND IN DATABASE")
                print("\nPossible reasons:")
                print("  1. Transaction was never created")
                print("  2. Wrong ref_id/order_id provided")
                print("  3. Transaction was deleted")
                print("\nPlease verify the ref_id and try again.")
                print("=" * 100)
                return
            
            print("✅ TRANSACTION FOUND")
            print(f"\n📋 Transaction Details:")
            print(f"   Our TXN ID:       {txn['txn_id']}")
            print(f"   Order ID:         {txn['order_id']} (ref_id in callback)")
            print(f"   Merchant:         {txn['merchant_name']} ({txn['merchant_id']})")
            print(f"   Amount:           ₹{float(txn['amount']):.2f}")
            print(f"   Net Amount:       ₹{float(txn['net_amount']):.2f}")
            print(f"   Charge:           ₹{float(txn['charge_amount']):.2f}")
            print(f"   Status:           {txn['status']}")
            print(f"   PG Partner:       {txn['pg_partner']}")
            print(f"   PG TXN ID:        {txn['pg_txn_id'] if txn['pg_txn_id'] else '❌ NOT SET'}")
            print(f"   UTR:              {txn['utr'] if txn['utr'] else '❌ NOT SET'}")
            print(f"   Created:          {format_datetime(txn['created_at'])}")
            print(f"   Completed:        {format_datetime(txn['completed_at'])}")
            print(f"   Last Updated:     {format_datetime(txn['updated_at'])}")
            
            # Step 2: Check if callback was received
            print(f"\n{'─' * 100}")
            print("STEP 2: Checking if Mudrape callback was received")
            print("-" * 100)
            
            # Check if PG TXN ID matches
            if txn_id and txn['pg_txn_id']:
                if txn['pg_txn_id'] == txn_id:
                    print(f"✅ PG TXN ID MATCHES: {txn_id}")
                    print("   This confirms callback was received and processed")
                else:
                    print(f"⚠️  PG TXN ID MISMATCH:")
                    print(f"   Expected: {txn_id}")
                    print(f"   Found:    {txn['pg_txn_id']}")
            elif txn_id and not txn['pg_txn_id']:
                print(f"❌ PG TXN ID NOT SET")
                print(f"   Expected: {txn_id}")
                print("   Callback may not have been received yet")
            
            # Check if amount matches
            if amount:
                if float(txn['amount']) == float(amount):
                    print(f"✅ AMOUNT MATCHES: ₹{amount}")
                else:
                    print(f"⚠️  AMOUNT MISMATCH:")
                    print(f"   Expected: ₹{amount}")
                    print(f"   Found:    ₹{float(txn['amount']):.2f}")
            
            # Step 3: Check wallet transactions
            print(f"\n{'─' * 100}")
            print("STEP 3: Checking wallet credit status")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    balance_before,
                    balance_after,
                    description,
                    created_at
                FROM merchant_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                print(f"✅ WALLET CREDITED ({len(wallet_txns)} transaction(s))")
                for idx, wtxn in enumerate(wallet_txns, 1):
                    print(f"\n   Transaction #{idx}:")
                    print(f"   Type:             {wtxn['txn_type']}")
                    print(f"   Amount:           ₹{float(wtxn['amount']):.2f}")
                    print(f"   Balance Before:   ₹{float(wtxn['balance_before']):.2f}")
                    print(f"   Balance After:    ₹{float(wtxn['balance_after']):.2f}")
                    print(f"   Description:      {wtxn['description']}")
                    print(f"   Time:             {format_datetime(wtxn['created_at'])}")
            else:
                print("❌ NO WALLET TRANSACTIONS FOUND")
                print("   Wallet was not credited - callback may not have been processed")
            
            # Step 4: Check callback logs
            print(f"\n{'─' * 100}")
            print("STEP 4: Checking callback forwarding logs")
            print("-" * 100)
            
            cursor.execute("""
                SELECT 
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print(f"✅ CALLBACK FORWARDING LOGS FOUND ({len(callback_logs)} attempt(s))")
                for idx, log in enumerate(callback_logs, 1):
                    print(f"\n   Attempt #{idx}:")
                    print(f"   URL:              {log['callback_url']}")
                    print(f"   Response Code:    {log['response_code']}")
                    print(f"   Time:             {format_datetime(log['created_at'])}")
                    
                    # Parse and display request data
                    try:
                        request_data = json.loads(log['request_data'])
                        print(f"   Request Data:")
                        print(f"      Status:        {request_data.get('status')}")
                        print(f"      Amount:        ₹{request_data.get('amount')}")
                        print(f"      Order ID:      {request_data.get('order_id')}")
                        print(f"      UTR:           {request_data.get('utr')}")
                        print(f"      PG TXN ID:     {request_data.get('pg_txn_id')}")
                    except:
                        print(f"   Request Data:     {log['request_data'][:100]}...")
                    
                    if log['response_data']:
                        print(f"   Response:         {log['response_data'][:200]}...")
            else:
                print("⚠️  NO CALLBACK FORWARDING LOGS")
                print("   Either merchant callback URL not configured or callback not sent")
            
            # Step 5: Check backend logs for this transaction
            print(f"\n{'─' * 100}")
            print("STEP 5: Summary and recommendations")
            print("-" * 100)
            
            # Determine callback status
            callback_received = bool(txn['pg_txn_id'])
            wallet_credited = bool(wallet_txns)
            
            print(f"\n📊 Status Summary:")
            print(f"   Transaction Exists:       ✅ YES")
            print(f"   Callback Received:        {'✅ YES' if callback_received else '❌ NO'}")
            print(f"   Wallet Credited:          {'✅ YES' if wallet_credited else '❌ NO'}")
            print(f"   Merchant Callback Sent:   {'✅ YES' if callback_logs else '⚠️  NO LOGS'}")
            
            # Provide recommendations
            print(f"\n💡 Recommendations:")
            
            if not callback_received:
                print("\n   ❌ CALLBACK NOT RECEIVED FROM MUDRAPE")
                print("   Actions to take:")
                print("   1. Check if Mudrape webhook is configured correctly")
                print("   2. Verify callback URL is accessible: /api/callback/mudrape/payin")
                print("   3. Check backend logs for incoming webhook attempts:")
                print(f"      sudo journalctl -u moneyone-api.service | grep '{txn['order_id']}'")
                print("   4. Contact Mudrape support to verify webhook configuration")
                print("   5. Manually trigger callback using status check API")
            elif not wallet_credited:
                print("\n   ⚠️  CALLBACK RECEIVED BUT WALLET NOT CREDITED")
                print("   Actions to take:")
                print("   1. Check backend logs for errors during callback processing:")
                print(f"      sudo journalctl -u moneyone-api.service | grep '{txn['order_id']}'")
                print("   2. Verify wallet credit logic in mudrape_callback_routes.py")
                print("   3. Manually credit wallet if needed")
            else:
                print("\n   ✅ EVERYTHING LOOKS GOOD")
                print("   Callback was received and processed successfully")
                print("   Wallet was credited properly")
            
            # Show expected callback payload
            print(f"\n{'─' * 100}")
            print("EXPECTED CALLBACK PAYLOAD:")
            print("-" * 100)
            expected_payload = {
                "amount": float(txn['amount']),
                "ref_id": txn['order_id'],
                "source": "SUCCESS",
                "status": "SUCCESS",
                "txn_id": txn_id if txn_id else "MPAY_XXXXXXXXXX",
                "payeeVpa": "merchant@upi",
                "timestamp": "2026-03-03T08:03:35.668Z"
            }
            print(json.dumps(expected_payload, indent=2))
            
            print("\n" + "=" * 100)
            
    finally:
        conn.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Check by ref_id (order_id):")
        print("    python3 check_specific_callback.py --ref-id <order_id>")
        print("")
        print("  Check by PG transaction ID:")
        print("    python3 check_specific_callback.py --txn-id <mudrape_txn_id>")
        print("")
        print("  Check by ref_id and verify PG TXN ID:")
        print("    python3 check_specific_callback.py --ref-id <order_id> --txn-id <mudrape_txn_id>")
        print("")
        print("  Check with all details:")
        print("    python3 check_specific_callback.py --ref-id <order_id> --txn-id <mudrape_txn_id> --amount <amount>")
        print("")
        print("Examples:")
        print("  python3 check_specific_callback.py --ref-id 20260303133259143440")
        print("  python3 check_specific_callback.py --ref-id 20260303133259143440 --txn-id MPAY80087485652")
        print("  python3 check_specific_callback.py --ref-id 20260303133259143440 --txn-id MPAY80087485652 --amount 300")
        sys.exit(1)
    
    # Parse arguments
    ref_id = None
    txn_id = None
    amount = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--ref-id' and i + 1 < len(sys.argv):
            ref_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--txn-id' and i + 1 < len(sys.argv):
            txn_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--amount' and i + 1 < len(sys.argv):
            amount = float(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    if not ref_id and not txn_id:
        print("ERROR: At least one of --ref-id or --txn-id must be provided")
        sys.exit(1)
    
    check_callback_by_payload(ref_id, txn_id, amount)

if __name__ == '__main__':
    main()
