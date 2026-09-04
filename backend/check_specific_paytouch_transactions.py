#!/usr/bin/env python3
"""
Check Specific PayTouch Transactions
Checks the specific transactions: TXN55B24F6EE079 and TXNFE9EDCDDBD58
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from paytouch_service import PayTouchService
from datetime import datetime
import json

def check_specific_transactions():
    """
    Check the specific transactions provided by the user
    """
    
    # The specific transaction IDs provided
    target_txn_ids = [
        'TXN55B24F6EE079',
        'TXNFE9EDCDDBD58'
    ]
    
    print("=" * 80)
    print(f"Specific PayTouch Transaction Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"Checking transactions: {', '.join(target_txn_ids)}")
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    paytouch_service = PayTouchService()
    
    try:
        with conn.cursor() as cursor:
            
            for txn_id in target_txn_ids:
                print(f"\n{'='*60}")
                print(f"Checking Transaction: {txn_id}")
                print(f"{'='*60}")
                
                # Get transaction details from database
                cursor.execute("""
                    SELECT txn_id, pg_txn_id, reference_id, status, merchant_id, admin_id,
                           amount, net_amount, charge_amount, utr, pg_partner,
                           created_at, updated_at, completed_at, error_message,
                           beneficiary_name, beneficiary_account, beneficiary_ifsc
                    FROM payout_transactions
                    WHERE txn_id = %s
                """, (txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Transaction {txn_id} not found in database")
                    continue
                
                print(f"📊 Database Details:")
                print(f"   TXN ID: {txn['txn_id']}")
                print(f"   PG TXN ID: {txn['pg_txn_id']}")
                print(f"   Reference ID: {txn['reference_id']}")
                print(f"   Status: {txn['status']}")
                print(f"   PG Partner: {txn['pg_partner']}")
                print(f"   Merchant ID: {txn['merchant_id']}")
                print(f"   Admin ID: {txn['admin_id']}")
                print(f"   Amount: ₹{txn['amount']}")
                print(f"   Net Amount: ₹{txn['net_amount']}")
                print(f"   Charges: ₹{txn['charge_amount']}")
                print(f"   UTR: {txn['utr']}")
                print(f"   Created: {txn['created_at']}")
                print(f"   Updated: {txn['updated_at']}")
                print(f"   Completed: {txn['completed_at']}")
                print(f"   Error: {txn['error_message']}")
                print(f"   Beneficiary: {txn['beneficiary_name']}")
                print(f"   Account: {txn['beneficiary_account']}")
                print(f"   IFSC: {txn['beneficiary_ifsc']}")
                
                # Check if this is actually a PayTouch transaction
                if txn['pg_partner'] != 'PayTouch':
                    print(f"⚠️  WARNING: This transaction uses '{txn['pg_partner']}', not PayTouch!")
                    continue
                
                # Check wallet transactions
                print(f"\n💰 Wallet Transaction History:")
                cursor.execute("""
                    SELECT txn_type, amount, description, created_at, balance_before, balance_after
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    for wtxn in wallet_txns:
                        print(f"   {wtxn['created_at']}: {wtxn['txn_type']} ₹{wtxn['amount']} - {wtxn['description']}")
                        print(f"     Balance: ₹{wtxn['balance_before']} → ₹{wtxn['balance_after']}")
                else:
                    print("   No wallet transactions found")
                
                # Now check with PayTouch API using both transaction_id and external_ref
                print(f"\n🔍 PayTouch API Status Check:")
                print("-" * 40)
                
                # Test with pg_txn_id as both transaction_id and external_ref
                if txn['pg_txn_id']:
                    print(f"Testing with PG TXN ID: {txn['pg_txn_id']}")
                    
                    status_result = paytouch_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['pg_txn_id']
                    )
                    
                    if status_result['success']:
                        print(f"✅ PayTouch API Response:")
                        print(f"   Status: {status_result['status']}")
                        print(f"   UTR: {status_result.get('utr', 'None')}")
                        print(f"   Message: {status_result.get('message', 'None')}")
                        
                        # Compare with database status
                        if status_result['status'] != txn['status']:
                            print(f"⚠️  STATUS MISMATCH!")
                            print(f"   Database: {txn['status']}")
                            print(f"   PayTouch: {status_result['status']}")
                        else:
                            print(f"✅ Status matches between database and PayTouch")
                    else:
                        print(f"❌ PayTouch API Error: {status_result['message']}")
                
                # Also test with reference_id if different from pg_txn_id
                if txn['reference_id'] and txn['reference_id'] != txn['pg_txn_id']:
                    print(f"\nTesting with Reference ID: {txn['reference_id']}")
                    
                    status_result = paytouch_service.check_payout_status(
                        transaction_id=txn['reference_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if status_result['success']:
                        print(f"✅ PayTouch API Response (Reference ID):")
                        print(f"   Status: {status_result['status']}")
                        print(f"   UTR: {status_result.get('utr', 'None')}")
                        print(f"   Message: {status_result.get('message', 'None')}")
                    else:
                        print(f"❌ PayTouch API Error (Reference ID): {status_result['message']}")
                
                # Analysis
                print(f"\n📋 Transaction Analysis:")
                
                if txn['status'] == 'FAILED' and not txn['completed_at']:
                    print(f"   ❌ Transaction failed before reaching PayTouch (no completion time)")
                elif txn['status'] == 'FAILED' and txn['completed_at']:
                    print(f"   ❌ Transaction failed after PayTouch response (has completion time)")
                elif txn['status'] == 'SUCCESS' and txn['utr']:
                    print(f"   ✅ Transaction successful with UTR")
                elif txn['status'] == 'SUCCESS' and not txn['utr']:
                    print(f"   ⚠️  Transaction marked successful but no UTR")
                elif txn['status'] in ['QUEUED', 'INPROCESS']:
                    print(f"   ⏳ Transaction still in progress")
                
                if txn['error_message']:
                    print(f"   ❌ Error Message: {txn['error_message']}")
                
                # Check if wallet was deducted
                wallet_deducted = any(wtxn['txn_type'] == 'DEBIT' for wtxn in wallet_txns)
                if txn['status'] == 'SUCCESS' and not wallet_deducted:
                    print(f"   ⚠️  Transaction is SUCCESS but wallet was not debited!")
                elif txn['status'] == 'FAILED' and wallet_deducted:
                    print(f"   ⚠️  Transaction is FAILED but wallet was debited!")
                elif txn['status'] == 'SUCCESS' and wallet_deducted:
                    print(f"   ✅ Transaction is SUCCESS and wallet was properly debited")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print(f"\n{'='*80}")
    print("SUMMARY & RECOMMENDATIONS")
    print(f"{'='*80}")
    
    print("Based on the analysis above:")
    print("1. 🔍 Check if transactions were actually sent to PayTouch")
    print("2. 📋 If PayTouch API says 'not found', transactions may not have been sent")
    print("3. 🔧 If status mismatch found, update database status")
    print("4. 💰 Verify wallet deductions match transaction status")
    print("5. 📞 Contact PayTouch support if transactions should exist but API says 'not found'")
    
    print(f"\nNext Actions:")
    print("1. Run the comprehensive API test: python3 test_paytouch_api_comprehensive.py")
    print("2. Check PayTouch dashboard manually for these transactions")
    print("3. Review payout initiation logs for these specific transactions")
    print("4. If needed, manually update transaction status based on PayTouch API response")

if __name__ == "__main__":
    check_specific_transactions()