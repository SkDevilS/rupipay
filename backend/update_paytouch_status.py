"""
Script to manually check and update PayTouch payout status
"""

from database import get_db_connection
from paytouch_service import paytouch_service
import json

def update_pending_paytouch_transactions():
    """Check and update status for pending PayTouch transactions"""
    print("=" * 80)
    print("Updating Pending PayTouch Transactions")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get pending PayTouch transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    pg_txn_id,
                    status,
                    amount,
                    created_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND status IN ('INITIATED', 'QUEUED', 'PENDING', 'INPROCESS')
                ORDER BY created_at DESC
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo pending PayTouch transactions found")
                return
            
            print(f"\nFound {len(transactions)} pending transactions")
            print("=" * 80)
            
            for idx, txn in enumerate(transactions, 1):
                print(f"\n{idx}. Checking transaction:")
                print(f"   TXN ID: {txn['txn_id']}")
                print(f"   Reference ID: {txn['reference_id']}")
                print(f"   PG TXN ID: {txn['pg_txn_id']}")
                print(f"   Current Status: {txn['status']}")
                print(f"   Amount: ₹{txn['amount']}")
                print(f"   Created: {txn['created_at']}")
                
                # Check status from PayTouch
                print(f"\n   Checking status from PayTouch...")
                
                status_result = paytouch_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )
                
                print(f"   PayTouch Response: {json.dumps(status_result, indent=6)}")
                
                if status_result.get('success'):
                    new_status = status_result.get('status')
                    utr = status_result.get('utr')
                    
                    print(f"\n   ✓ Status from PayTouch: {new_status}")
                    print(f"   ✓ UTR: {utr}")
                    
                    # Update database if status changed
                    if new_status and new_status != txn['status']:
                        print(f"\n   Updating database: {txn['status']} -> {new_status}")
                        
                        if new_status in ['SUCCESS', 'FAILED']:
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (new_status, utr, txn['txn_id']))
                        else:
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET status = %s, utr = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (new_status, utr, txn['txn_id']))
                        
                        conn.commit()
                        print(f"   ✓ Database updated successfully")
                    else:
                        print(f"   Status unchanged: {new_status}")
                else:
                    print(f"   ✗ Failed to get status: {status_result.get('message')}")
                
                print("-" * 80)
    
    finally:
        conn.close()
    
    print("\n" + "=" * 80)
    print("Update Complete")
    print("=" * 80)

if __name__ == '__main__':
    update_pending_paytouch_transactions()
