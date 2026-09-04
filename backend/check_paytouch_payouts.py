"""
Diagnostic script to check PayTouch payout transactions
"""

from database import get_db_connection
import json
from datetime import datetime, timedelta

def check_paytouch_transactions():
    """Check recent PayTouch payout transactions"""
    print("=" * 80)
    print("PayTouch Payout Transactions Diagnostic")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent PayTouch transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    admin_id,
                    amount,
                    charge_amount,
                    net_amount,
                    bene_name,
                    account_no,
                    ifsc_code,
                    status,
                    pg_partner,
                    pg_txn_id,
                    utr,
                    error_message,
                    created_at,
                    updated_at,
                    completed_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo PayTouch transactions found")
                return
            
            print(f"\nFound {len(transactions)} PayTouch transactions")
            print("=" * 80)
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{idx}. Transaction Details:")
                print(f"   TXN ID:        {txn['txn_id']}")
                print(f"   Reference ID:  {txn['reference_id']}")
                print(f"   Merchant ID:   {txn['merchant_id']}")
                print(f"   Admin ID:      {txn['admin_id']}")
                print(f"   Amount:        ₹{txn['amount']}")
                print(f"   Charge:        ₹{txn['charge_amount']}")
                print(f"   Net Amount:    ₹{txn['net_amount']}")
                print(f"   Beneficiary:   {txn['bene_name']}")
                print(f"   Account:       {txn['account_no']}")
                print(f"   IFSC:          {txn['ifsc_code']}")
                print(f"   Status:        {txn['status']}")
                print(f"   PG TXN ID:     {txn['pg_txn_id']}")
                print(f"   UTR:           {txn['utr']}")
                print(f"   Error:         {txn['error_message']}")
                print(f"   Created:       {txn['created_at']}")
                print(f"   Updated:       {txn['updated_at']}")
                print(f"   Completed:     {txn['completed_at']}")
                print("-" * 80)
            
            # Check for stuck transactions (pending for more than 5 minutes)
            print("\n" + "=" * 80)
            print("Checking for Stuck Transactions (Pending > 5 minutes)")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    status,
                    pg_txn_id,
                    created_at,
                    TIMESTAMPDIFF(MINUTE, created_at, NOW()) as minutes_pending
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status IN ('INITIATED', 'QUEUED', 'PENDING', 'INPROCESS')
                AND created_at < DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                ORDER BY created_at DESC
            """)
            
            stuck_txns = cursor.fetchall()
            
            if stuck_txns:
                print(f"\nFound {len(stuck_txns)} stuck transactions:")
                for idx, txn in enumerate(stuck_txns, 1):
                    print(f"\n{idx}. TXN ID: {txn['txn_id']}")
                    print(f"   Reference ID: {txn['reference_id']}")
                    print(f"   Status: {txn['status']}")
                    print(f"   PG TXN ID: {txn['pg_txn_id']}")
                    print(f"   Created: {txn['created_at']}")
                    print(f"   Minutes Pending: {txn['minutes_pending']}")
            else:
                print("\nNo stuck transactions found")
            
            # Check callback logs
            print("\n" + "=" * 80)
            print("Checking Callback Logs")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    cl.id,
                    cl.txn_id,
                    cl.callback_url,
                    cl.request_data,
                    cl.response_code,
                    cl.response_data,
                    cl.created_at
                FROM callback_logs cl
                INNER JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
                WHERE pt.pg_partner = 'PayTouch'
                ORDER BY cl.created_at DESC
                LIMIT 10
            """)
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print(f"\nFound {len(callback_logs)} callback logs:")
                for idx, log in enumerate(callback_logs, 1):
                    print(f"\n{idx}. Callback Log:")
                    print(f"   TXN ID: {log['txn_id']}")
                    print(f"   URL: {log['callback_url']}")
                    print(f"   Response Code: {log['response_code']}")
                    print(f"   Created: {log['created_at']}")
                    try:
                        request_data = json.loads(log['request_data'])
                        print(f"   Request Data: {json.dumps(request_data, indent=6)}")
                    except:
                        print(f"   Request Data: {log['request_data']}")
                    print(f"   Response: {log['response_data'][:200]}")
            else:
                print("\nNo callback logs found for PayTouch transactions")
    
    finally:
        conn.close()
    
    print("\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)

if __name__ == '__main__':
    check_paytouch_transactions()
