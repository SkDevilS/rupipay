#!/usr/bin/env python3
"""
Debug specific PayTouch transaction from screenshot
Transaction ID: QRP2024031021816F4NRE
"""

from database import get_db_connection
from paytouch_service import PayTouchService
import json
from datetime import datetime

def debug_paytouch_transaction():
    """Debug the specific PayTouch transaction showing as failed"""
    
    # Transaction details from screenshot
    transaction_ref = "QRP2024031021816F4NRE"
    
    print("=" * 80)
    print(f"Debugging PayTouch Transaction: {transaction_ref}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find the transaction in database
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, utr, error_message,
                    created_at, updated_at, completed_at
                FROM payout_transactions
                WHERE reference_id = %s OR pg_txn_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (transaction_ref, transaction_ref))
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print(f"❌ Transaction not found: {transaction_ref}")
                return
            
            print(f"Found {len(transactions)} transaction(s):")
            print("-" * 80)
            
            for i, txn in enumerate(transactions, 1):
                print(f"\n{i}. Transaction Details:")
                print(f"   TXN ID: {txn['txn_id']}")
                print(f"   Reference: {txn['reference_id']}")
                print(f"   PG TXN ID: {txn['pg_txn_id']}")
                print(f"   Status: {txn['status']}")
                print(f"   Amount: ₹{txn['amount']}")
                print(f"   Net Amount: ₹{txn['net_amount']}")
                print(f"   Charges: ₹{txn['charge_amount']}")
                print(f"   UTR: {txn['utr']}")
                print(f"   Error: {txn['error_message']}")
                print(f"   Created: {txn['created_at']}")
                print(f"   Updated: {txn['updated_at']}")
                print(f"   Completed: {txn['completed_at']}")
                
                # Check wallet transactions for this payout
                cursor.execute("""
                    SELECT 
                        txn_type, amount, balance_before, balance_after,
                        description, created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    print(f"\n   Wallet Transactions:")
                    for w_txn in wallet_txns:
                        print(f"     - {w_txn['txn_type']}: ₹{w_txn['amount']} | {w_txn['balance_before']} → {w_txn['balance_after']} | {w_txn['description']}")
                else:
                    print(f"   ⚠️  No wallet transactions found")
                
                # Check PayTouch status via API
                print(f"\n   Checking PayTouch API Status...")
                
                paytouch_service = PayTouchService()
                status_result = paytouch_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )
                
                if status_result.get('success'):
                    print(f"   PayTouch API Status: {status_result.get('status')}")
                    print(f"   PayTouch UTR: {status_result.get('utr')}")
                    print(f"   PayTouch Message: {status_result.get('message')}")
                    
                    # Compare with database status
                    api_status = status_result.get('status')
                    db_status = txn['status']
                    
                    if api_status != db_status:
                        print(f"   🔥 STATUS MISMATCH: DB={db_status}, API={api_status}")
                        
                        if api_status == 'SUCCESS' and db_status == 'FAILED':
                            print(f"   💡 ISSUE FOUND: PayTouch shows SUCCESS but DB shows FAILED")
                            print(f"   💡 This indicates callback was not processed correctly")
                    else:
                        print(f"   ✅ Status matches between DB and PayTouch API")
                        
                else:
                    print(f"   ❌ PayTouch API Error: {status_result.get('message')}")
            
            # Check callback logs for this transaction
            print(f"\n" + "-" * 80)
            print("Checking Callback Logs...")
            
            for txn in transactions:
                cursor.execute("""
                    SELECT 
                        callback_url, request_data, response_code, response_data,
                        created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (txn['txn_id'],))
                
                callback_logs = cursor.fetchall()
                
                if callback_logs:
                    print(f"\nCallback logs for {txn['txn_id']}:")
                    for log in callback_logs:
                        print(f"  - {log['created_at']}: {log['response_code']} to {log['callback_url']}")
                        if log['request_data']:
                            try:
                                req_data = json.loads(log['request_data'])
                                print(f"    Request: {json.dumps(req_data, indent=6)}")
                            except:
                                print(f"    Request: {log['request_data'][:200]}...")
                else:
                    print(f"No callback logs found for {txn['txn_id']}")
            
            print("\n" + "=" * 80)
            print("DIAGNOSIS COMPLETE")
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    debug_paytouch_transaction()