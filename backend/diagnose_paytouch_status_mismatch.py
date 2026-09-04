"""
Diagnose PayTouch Status Mismatch
Check why admin shows SUCCESS but merchant shows FAILED
Transaction: TXN986649FDE8C3
Reference: DP202603062044589B36FB
"""

from database import get_db_connection
import json

def diagnose_status_mismatch():
    txn_id = 'TXN986649FDE8C3'
    reference_id = 'DP202603062044589B36FB'
    
    print("=" * 80)
    print("PayTouch Status Mismatch Diagnosis")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            print(f"\n1. Transaction Details for {txn_id}")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_partner, pg_txn_id, utr,
                    error_message, created_at, completed_at, updated_at
                FROM payout_transactions
                WHERE txn_id = %s OR reference_id = %s
            """, (txn_id, reference_id))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"ERROR: Transaction not found")
                return
            
            print(f"Transaction ID: {txn['txn_id']}")
            print(f"Reference ID: {txn['reference_id']}")
            print(f"Merchant ID: {txn['merchant_id']}")
            print(f"Admin ID: {txn['admin_id']}")
            print(f"Amount: ₹{txn['amount']}")
            print(f"Charges: ₹{txn['charge_amount']}")
            print(f"Net Amount: ₹{txn['net_amount']}")
            print(f"Status: {txn['status']}")
            print(f"PG Partner: {txn['pg_partner']}")
            print(f"PG Transaction ID: {txn['pg_txn_id']}")
            print(f"UTR: {txn['utr']}")
            print(f"Error Message: {txn['error_message']}")
            print(f"Created: {txn['created_at']}")
            print(f"Completed: {txn['completed_at']}")
            print(f"Updated: {txn['updated_at']}")
            
            # Check callback logs
            print(f"\n2. Callback Logs")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    id, callback_url, request_data, response_code, 
                    response_data, created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (txn['txn_id'],))
            
            callbacks = cursor.fetchall()
            
            if callbacks:
                for i, cb in enumerate(callbacks, 1):
                    print(f"\nCallback #{i}:")
                    print(f"  URL: {cb['callback_url']}")
                    print(f"  Time: {cb['created_at']}")
                    print(f"  Response Code: {cb['response_code']}")
                    print(f"  Request Data: {cb['request_data']}")
                    print(f"  Response: {cb['response_data'][:200] if cb['response_data'] else 'None'}")
            else:
                print("No callback logs found")
            
            # Check wallet transactions
            print(f"\n3. Wallet Transactions")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    id, merchant_id, txn_type, amount, 
                    balance_before, balance_after, description,
                    reference_id, created_at
                FROM wallet_transactions
                WHERE reference_id = %s OR description LIKE %s
                ORDER BY created_at DESC
            """, (txn['txn_id'], f"%{txn['reference_id']}%"))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                for wt in wallet_txns:
                    print(f"\nWallet Transaction:")
                    print(f"  Merchant: {wt['merchant_id']}")
                    print(f"  Type: {wt['txn_type']}")
                    print(f"  Amount: ₹{wt['amount']}")
                    print(f"  Balance: ₹{wt['balance_before']} → ₹{wt['balance_after']}")
                    print(f"  Description: {wt['description']}")
                    print(f"  Time: {wt['created_at']}")
            else:
                print("No wallet transactions found")
            
            # Check if there are duplicate transactions
            print(f"\n4. Check for Duplicate Transactions")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, status, pg_txn_id, created_at
                FROM payout_transactions
                WHERE reference_id = %s OR pg_txn_id = %s
                ORDER BY created_at
            """, (txn['reference_id'], txn['pg_txn_id']))
            
            duplicates = cursor.fetchall()
            
            if len(duplicates) > 1:
                print(f"⚠️  Found {len(duplicates)} transactions with same reference/pg_txn_id:")
                for dup in duplicates:
                    print(f"  - {dup['txn_id']}: {dup['status']} (Created: {dup['created_at']})")
            else:
                print("No duplicates found")
            
            # Analysis
            print(f"\n5. Analysis")
            print("=" * 80)
            
            if txn['status'] == 'FAILED':
                print("❌ Transaction is marked as FAILED")
                print(f"   Error: {txn['error_message']}")
                
                if txn['utr']:
                    print(f"⚠️  BUT UTR exists: {txn['utr']}")
                    print("   This suggests payment was successful at PayTouch")
                    print("   Possible causes:")
                    print("   1. Callback received with FAILED status incorrectly")
                    print("   2. Status mapping issue in callback handler")
                    print("   3. Wallet debit failed, causing transaction to be marked FAILED")
                
                if txn['completed_at']:
                    print(f"⚠️  Completed timestamp exists: {txn['completed_at']}")
                    print("   This suggests the transaction went through")
            
            elif txn['status'] == 'SUCCESS':
                print("✅ Transaction is marked as SUCCESS")
                
                if not wallet_txns:
                    print("⚠️  BUT no wallet debit found")
                    print("   Merchant wallet may not have been debited")
            
            print("\n" + "=" * 80)
            print("Recommendation:")
            print("=" * 80)
            
            if txn['status'] == 'FAILED' and txn['utr']:
                print("1. Check PayTouch dashboard to confirm actual status")
                print("2. If PayTouch shows SUCCESS, update transaction status manually")
                print("3. Ensure wallet was debited correctly")
                print("\nTo fix manually:")
                print(f"   UPDATE payout_transactions")
                print(f"   SET status = 'SUCCESS', error_message = NULL")
                print(f"   WHERE txn_id = '{txn['txn_id']}';")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_status_mismatch()
