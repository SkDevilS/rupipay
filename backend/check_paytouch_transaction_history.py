#!/usr/bin/env python3
"""
Check PayTouch Transaction History
Checks if the transactions were actually sent to PayTouch and their complete history
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime
import json

def check_paytouch_transaction_history():
    """
    Check the complete history of PayTouch transactions
    """
    
    print("=" * 80)
    print(f"PayTouch Transaction History Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # The specific transactions from the issue
    target_transactions = [
        'ADMIN20260310182521A6904E',
        'ADMIN20260310182131FF1C8D'
    ]
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            
            print("🔍 Checking specific transactions...")
            print("-" * 60)
            
            for pg_txn_id in target_transactions:
                print(f"\nTransaction: {pg_txn_id}")
                print("=" * 40)
                
                # Get complete transaction details
                cursor.execute("""
                    SELECT txn_id, pg_txn_id, reference_id, status, merchant_id, admin_id,
                           amount, net_amount, charge_amount, utr, pg_partner,
                           created_at, updated_at, completed_at, error_message,
                           beneficiary_name, beneficiary_account, beneficiary_ifsc
                    FROM payout_transactions
                    WHERE pg_txn_id = %s
                """, (pg_txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Transaction not found in database")
                    continue
                
                print(f"📊 Transaction Details:")
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
                
                # Check if this was actually sent to PayTouch
                if txn['pg_partner'] != 'PayTouch':
                    print(f"⚠️  WARNING: PG Partner is '{txn['pg_partner']}', not 'PayTouch'")
                
                # Check wallet transactions for this payout
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
                
                # Check if there are any logs related to this transaction
                print(f"\n📋 Transaction Analysis:")
                
                # Check creation time vs current time
                created_time = txn['created_at']
                current_time = datetime.now()
                time_diff = current_time - created_time
                
                print(f"   Age: {time_diff}")
                
                if txn['status'] == 'FAILED' and not txn['completed_at']:
                    print(f"   ❌ Status is FAILED but no completion time - likely never sent to PayTouch")
                elif txn['status'] == 'FAILED' and txn['completed_at']:
                    print(f"   ❌ Status is FAILED with completion time - PayTouch responded with failure")
                elif txn['status'] == 'QUEUED':
                    print(f"   ⏳ Status is QUEUED - waiting for processing")
                elif txn['status'] == 'INPROCESS':
                    print(f"   🔄 Status is INPROCESS - being processed by PayTouch")
                elif txn['status'] == 'SUCCESS':
                    print(f"   ✅ Status is SUCCESS")
                
                if not txn['utr']:
                    print(f"   ⚠️  No UTR - transaction likely not completed by PayTouch")
                
                if txn['error_message']:
                    print(f"   ❌ Error Message: {txn['error_message']}")
            
            # Check overall PayTouch transaction patterns
            print(f"\n{'='*60}")
            print("PayTouch Transaction Patterns (Last 7 Days)")
            print(f"{'='*60}")
            
            cursor.execute("""
                SELECT 
                    DATE(created_at) as txn_date,
                    COUNT(*) as total_txns,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count,
                    COUNT(CASE WHEN status = 'QUEUED' THEN 1 END) as queued_count,
                    COUNT(CASE WHEN status = 'INPROCESS' THEN 1 END) as inprocess_count,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_count,
                    COUNT(CASE WHEN utr IS NOT NULL AND utr != '' THEN 1 END) as utr_count
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
                GROUP BY DATE(created_at)
                ORDER BY txn_date DESC
            """)
            
            patterns = cursor.fetchall()
            
            if patterns:
                for pattern in patterns:
                    print(f"\nDate: {pattern['txn_date']}")
                    print(f"  Total: {pattern['total_txns']}")
                    print(f"  Success: {pattern['success_count']}")
                    print(f"  Failed: {pattern['failed_count']}")
                    print(f"  Queued: {pattern['queued_count']}")
                    print(f"  In Process: {pattern['inprocess_count']}")
                    print(f"  Completed: {pattern['completed_count']}")
                    print(f"  With UTR: {pattern['utr_count']}")
                    
                    if pattern['total_txns'] > 0:
                        success_rate = (pattern['success_count'] / pattern['total_txns']) * 100
                        completion_rate = (pattern['completed_count'] / pattern['total_txns']) * 100
                        print(f"  Success Rate: {success_rate:.1f}%")
                        print(f"  Completion Rate: {completion_rate:.1f}%")
            else:
                print("No PayTouch transactions found in last 7 days")
            
            # Check recent successful PayTouch transactions for comparison
            print(f"\n{'='*60}")
            print("Recent Successful PayTouch Transactions (for comparison)")
            print(f"{'='*60}")
            
            cursor.execute("""
                SELECT pg_txn_id, amount, utr, created_at, completed_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status = 'SUCCESS'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAYS)
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            successful_txns = cursor.fetchall()
            
            if successful_txns:
                for stxn in successful_txns:
                    print(f"  {stxn['pg_txn_id']}: ₹{stxn['amount']} - UTR: {stxn['utr']}")
                    print(f"    Created: {stxn['created_at']}, Completed: {stxn['completed_at']}")
            else:
                print("  No successful PayTouch transactions found in last 30 days")
                print("  ⚠️  This suggests PayTouch integration may have issues")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print(f"\n{'='*80}")
    print("CONCLUSIONS & RECOMMENDATIONS")
    print(f"{'='*80}")
    
    print("1. 🔍 Check if transactions were actually sent to PayTouch")
    print("2. 📋 Review payout initiation logs for these specific transactions")
    print("3. 🔧 If transactions show FAILED without completion_at, they likely failed before reaching PayTouch")
    print("4. 📞 If transactions should have been sent but PayTouch API says 'not found', contact PayTouch support")
    print("5. ⚠️  Consider implementing better error handling and retry logic for PayTouch API calls")
    
    print(f"\nNext Steps:")
    print("1. Run: python3 test_paytouch_api_comprehensive.py")
    print("2. Check PayTouch dashboard manually for these transaction IDs")
    print("3. Review application logs during the time these transactions were created")
    print("4. Consider setting up a cron job to sync PayTouch transaction statuses")

if __name__ == "__main__":
    check_paytouch_transaction_history()