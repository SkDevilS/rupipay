#!/usr/bin/env python3
"""
Check recent Rang transactions using Rang's check status API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from rang_service import RangService
from datetime import datetime, timedelta
import json

def get_recent_rang_transactions(hours=24):
    """Get recent Rang transactions from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, status, 
                bank_ref_no, pg_txn_id, callback_url,
                created_at, completed_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY created_at DESC
        """, (hours,))
        
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return transactions
        
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
        return []

def check_transaction_with_rang_api(transaction, rang_service):
    """Check transaction status using Rang API"""
    try:
        print(f"\n{'='*60}")
        print(f"CHECKING TRANSACTION: {transaction['txn_id']}")
        print(f"{'='*60}")
        
        print(f"Database Info:")
        print(f"  TXN ID: {transaction['txn_id']}")
        print(f"  Order ID (RefID): {transaction['order_id']}")
        print(f"  Merchant: {transaction['merchant_id']}")
        print(f"  Amount: ₹{transaction['amount']}")
        print(f"  Current Status: {transaction['status']}")
        print(f"  UTR: {transaction['bank_ref_no'] or 'None'}")
        print(f"  PG TXN ID: {transaction['pg_txn_id'] or 'None'}")
        print(f"  Created: {transaction['created_at']}")
        print(f"  Completed: {transaction['completed_at'] or 'None'}")
        
        print(f"\nChecking with Rang API...")
        print(f"Using RefID: {transaction['order_id']}")
        
        # Call Rang status check API
        result = rang_service.check_payment_status(transaction['order_id'])
        
        if result['success']:
            rang_data = result['data']
            print(f"\n✅ Rang API Response:")
            print(f"  Raw Response: {json.dumps(rang_data, indent=2)}")
            
            # Parse Rang response
            if isinstance(rang_data, dict):
                # Extract status information
                rang_status = rang_data.get('status', 'Unknown')
                rang_message = rang_data.get('message', '')
                rang_utr = rang_data.get('utr', rang_data.get('UTR', ''))
                rang_amount = rang_data.get('amount', rang_data.get('Amount', ''))
                rang_txn_id = rang_data.get('txn_id', rang_data.get('transaction_id', ''))
                
                print(f"\n📊 Parsed Rang Data:")
                print(f"  Status: {rang_status}")
                print(f"  Message: {rang_message}")
                print(f"  UTR: {rang_utr or 'None'}")
                print(f"  Amount: {rang_amount or 'None'}")
                print(f"  Rang TXN ID: {rang_txn_id or 'None'}")
                
                # Compare with database
                print(f"\n🔍 Status Comparison:")
                print(f"  Database Status: {transaction['status']}")
                print(f"  Rang Status: {rang_status}")
                
                if str(transaction['status']).upper() != str(rang_status).upper():
                    print(f"  ⚠️ STATUS MISMATCH DETECTED!")
                    
                    # Suggest action based on Rang status
                    if str(rang_status).upper() in ['SUCCESS', 'COMPLETED', 'PAID']:
                        print(f"  💡 Suggestion: Transaction is SUCCESS on Rang but {transaction['status']} in database")
                        print(f"     - Rang may not have sent callback yet")
                        print(f"     - Or callback processing failed")
                        print(f"     - Consider manual status update")
                    elif str(rang_status).upper() in ['FAILED', 'CANCELLED']:
                        print(f"  💡 Suggestion: Transaction FAILED on Rang but {transaction['status']} in database")
                        print(f"     - Update database status to FAILED")
                    else:
                        print(f"  💡 Suggestion: Check Rang documentation for status '{rang_status}'")
                else:
                    print(f"  ✅ Status matches between database and Rang")
                
                return {
                    'txn_id': transaction['txn_id'],
                    'order_id': transaction['order_id'],
                    'db_status': transaction['status'],
                    'rang_status': rang_status,
                    'rang_utr': rang_utr,
                    'rang_message': rang_message,
                    'status_match': str(transaction['status']).upper() == str(rang_status).upper(),
                    'rang_data': rang_data
                }
            else:
                print(f"  ⚠️ Unexpected response format from Rang")
                return None
                
        else:
            print(f"\n❌ Rang API Error: {result.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking transaction: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_summary_report(check_results):
    """Generate summary report of all checks"""
    print(f"\n{'='*80}")
    print(f"SUMMARY REPORT")
    print(f"{'='*80}")
    
    total_checked = len([r for r in check_results if r is not None])
    status_matches = len([r for r in check_results if r and r['status_match']])
    status_mismatches = len([r for r in check_results if r and not r['status_match']])
    api_errors = len([r for r in check_results if r is None])
    
    print(f"Total Transactions Checked: {len(check_results)}")
    print(f"Successfully Checked: {total_checked}")
    print(f"API Errors: {api_errors}")
    print(f"Status Matches: {status_matches}")
    print(f"Status Mismatches: {status_mismatches}")
    
    if status_mismatches > 0:
        print(f"\n⚠️ TRANSACTIONS WITH STATUS MISMATCHES:")
        for result in check_results:
            if result and not result['status_match']:
                print(f"  - {result['txn_id']}: DB={result['db_status']} | Rang={result['rang_status']}")
                if result['rang_utr']:
                    print(f"    UTR: {result['rang_utr']}")
                if result['rang_message']:
                    print(f"    Message: {result['rang_message']}")
    
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS:")
    print(f"{'='*80}")
    
    if status_mismatches > 0:
        print(f"1. Review transactions with status mismatches")
        print(f"2. For SUCCESS on Rang but INITIATED in DB:")
        print(f"   - Check if callback was received")
        print(f"   - Verify callback processing logs")
        print(f"   - Consider manual status update")
        print(f"3. For FAILED on Rang but INITIATED in DB:")
        print(f"   - Update database status to FAILED")
        print(f"4. Contact Rang team if callbacks are not being sent")
    else:
        print(f"✅ All transaction statuses are in sync!")
    
    if api_errors > 0:
        print(f"5. {api_errors} transactions had API errors - check Rang API connectivity")

def main():
    print("RANG TRANSACTION STATUS CHECKER")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get recent transactions
    print("Step 1: Getting recent Rang transactions...")
    transactions = get_recent_rang_transactions(24)  # Last 24 hours
    
    if not transactions:
        print("❌ No recent Rang transactions found")
        return
    
    print(f"✅ Found {len(transactions)} recent Rang transaction(s)")
    
    # Initialize Rang service
    print("\nStep 2: Initializing Rang service...")
    try:
        rang_service = RangService()
        print("✅ Rang service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Rang service: {e}")
        return
    
    # Check each transaction
    print(f"\nStep 3: Checking transactions with Rang API...")
    check_results = []
    
    for i, transaction in enumerate(transactions, 1):
        print(f"\n[{i}/{len(transactions)}] Processing transaction...")
        result = check_transaction_with_rang_api(transaction, rang_service)
        check_results.append(result)
        
        # Add delay between API calls to avoid rate limiting
        if i < len(transactions):
            import time
            time.sleep(2)
    
    # Generate summary
    generate_summary_report(check_results)
    
    print(f"\n{'='*80}")
    print(f"STATUS CHECK COMPLETED")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()