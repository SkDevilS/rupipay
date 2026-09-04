"""
Test SkrillPe Status Check API and Callback Reception
This script checks the most recent SkrillPe transaction and verifies:
1. Status from SkrillPe API
2. Whether callback was received
3. Transaction status in database
4. Wallet credit status
"""

import sys
import os
from database import get_db_connection
from skrillpe_service import skrillpe_service
import json
from datetime import datetime

print("=" * 80)
print("SkrillPe Status Check & Callback Verification")
print("=" * 80)

conn = get_db_connection()
if not conn:
    print("ERROR: Database connection failed")
    sys.exit(1)

try:
    with conn.cursor() as cursor:
        # Get most recent SkrillPe transaction
        print("\n1. Finding Most Recent SkrillPe Transaction...")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                txn_id,
                merchant_id,
                order_id,
                amount,
                status,
                pg_txn_id,
                bank_ref_no as utr,
                created_at,
                updated_at,
                completed_at,
                remarks
            FROM payin_transactions
            WHERE pg_partner = 'SkrillPe'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        
        if not txn:
            print("✗ No SkrillPe transactions found in database")
            sys.exit(1)
        
        print(f"✓ Found Transaction:")
        print(f"  TXN ID: {txn['txn_id']}")
        print(f"  Order ID: {txn['order_id']}")
        print(f"  Merchant ID: {txn['merchant_id']}")
        print(f"  Amount: ₹{txn['amount']}")
        print(f"  Current Status: {txn['status']}")
        print(f"  PG TXN ID: {txn['pg_txn_id']}")
        print(f"  UTR: {txn['utr']}")
        print(f"  Created: {txn['created_at']}")
        print(f"  Updated: {txn['updated_at']}")
        print(f"  Completed: {txn['completed_at']}")
        
        # Check status via SkrillPe API
        print("\n2. Checking Status via SkrillPe API...")
        print("-" * 80)
        
        try:
            status_result = skrillpe_service.check_payment_status(txn['txn_id'])
            
            if status_result.get('success'):
                print(f"✓ SkrillPe API Response:")
                print(f"  Status: {status_result.get('status')}")
                print(f"  Amount: {status_result.get('amount')}")
                print(f"  RRN: {status_result.get('rrn')}")
                print(f"  Payer VPA: {status_result.get('payer_vpa')}")
                print(f"  Payer Name: {status_result.get('payer_name')}")
                print(f"  Payer Mobile: {status_result.get('payer_mobile')}")
                print(f"  Message: {status_result.get('message')}")
                print(f"  TXN DateTime: {status_result.get('txn_datetime')}")
                print(f"  Trans Ref ID: {status_result.get('trans_ref_id')}")
                
                api_status = status_result.get('status')
                db_status = txn['status']
                
                if api_status == db_status:
                    print(f"\n✓ Status Match: API and Database both show '{api_status}'")
                else:
                    print(f"\n⚠ Status Mismatch:")
                    print(f"  API Status: {api_status}")
                    print(f"  DB Status: {db_status}")
                    print(f"  → Callback may not have been received or processed")
            else:
                print(f"✗ SkrillPe API Error: {status_result.get('message')}")
                
        except Exception as e:
            print(f"✗ Error calling SkrillPe API: {e}")
            import traceback
            traceback.print_exc()
        
        # Check if callback was received (by checking wallet credit)
        print("\n3. Checking Callback Reception (Wallet Credit)...")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                txn_type,
                amount,
                balance_after,
                description,
                created_at
            FROM merchant_wallet_transactions
            WHERE reference_id = %s
            AND txn_type = 'UNSETTLED_CREDIT'
        """, (txn['txn_id'],))
        
        wallet_txn = cursor.fetchone()
        
        if wallet_txn:
            print(f"✓ Callback Received & Processed:")
            print(f"  Wallet credited: ₹{wallet_txn['amount']}")
            print(f"  Balance after: ₹{wallet_txn['balance_after']}")
            print(f"  Description: {wallet_txn['description']}")
            print(f"  Credited at: {wallet_txn['created_at']}")
            
            # Calculate time between transaction creation and wallet credit
            time_diff = wallet_txn['created_at'] - txn['created_at']
            print(f"  Time to credit: {time_diff}")
        else:
            print(f"✗ No Wallet Credit Found")
            print(f"  → Callback NOT received or NOT processed")
            print(f"  → Transaction status: {txn['status']}")
            
            if txn['status'] == 'INITIATED':
                print(f"\n  Possible reasons:")
                print(f"  1. Payment not completed yet")
                print(f"  2. Callback not sent by SkrillPe")
                print(f"  3. Callback URL not configured correctly")
                print(f"  4. Callback endpoint error")
        
        # Check merchant current wallet balance
        print("\n4. Checking Merchant Wallet Balance...")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                merchant_id,
                full_name,
                unsettled_wallet_balance,
                settled_wallet_balance
            FROM merchants
            WHERE merchant_id = %s
        """, (txn['merchant_id'],))
        
        merchant = cursor.fetchone()
        
        if merchant:
            print(f"Merchant: {merchant['full_name']} ({merchant['merchant_id']})")
            print(f"  Unsettled Balance: ₹{merchant['unsettled_wallet_balance']}")
            print(f"  Settled Balance: ₹{merchant['settled_wallet_balance']}")
        
        # Check server logs for callback activity
        print("\n5. Recent Callback Activity (Last 10 entries)...")
        print("-" * 80)
        print("Run this command to check server logs:")
        print(f"sudo journalctl -u moneyone-api --since '10 minutes ago' | grep -i 'skrillpe.*callback'")
        
        # Summary
        print("\n6. Summary & Recommendations...")
        print("-" * 80)
        
        if txn['status'] == 'SUCCESS' and wallet_txn:
            print("✓ Everything looks good!")
            print("  - Transaction is SUCCESS")
            print("  - Wallet has been credited")
            print("  - Callback was received and processed")
        elif txn['status'] == 'SUCCESS' and not wallet_txn:
            print("⚠ Transaction is SUCCESS but wallet NOT credited")
            print("  Action needed:")
            print("  1. Check if callback was received: sudo journalctl -u moneyone-api | grep -i skrillpe")
            print("  2. Manually credit wallet if needed")
        elif txn['status'] == 'INITIATED':
            print("⚠ Transaction still in INITIATED status")
            print("  Possible actions:")
            print("  1. Wait for customer to complete payment")
            print("  2. Check SkrillPe API status (shown above)")
            print("  3. Verify callback URL with SkrillPe team")
            print(f"  4. Monitor logs: sudo journalctl -u moneyone-api -f | grep -i skrillpe")
        elif txn['status'] == 'FAILED':
            print("✗ Transaction FAILED")
            print("  - Payment was not successful")
            print("  - No wallet credit expected")
        
        # Provide callback URL
        print("\n7. Callback Configuration...")
        print("-" * 80)
        print("Callback URL (should be configured with SkrillPe):")
        print("https://api.moneyone.co.in/api/callback/skrillpe/payin")
        print("\nTest callback endpoint:")
        print("curl -X POST https://api.moneyone.co.in/api/callback/skrillpe/payin \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -d '{\"test\": \"ping\"}'")

finally:
    conn.close()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
