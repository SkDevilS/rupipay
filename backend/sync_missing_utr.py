"""
Script to sync missing UTR (bank_ref_no) for successful payin transactions
This will fetch UTR from Mudrape for all SUCCESS transactions that have NULL bank_ref_no
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from mudrape_service import MudrapeService
import time

def sync_missing_utr():
    """Sync missing UTR for successful Mudrape transactions"""
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find all SUCCESS transactions with NULL bank_ref_no
            cursor.execute("""
                SELECT txn_id, order_id, merchant_id, pg_partner, pg_txn_id, amount
                FROM payin_transactions
                WHERE status = 'SUCCESS' 
                AND bank_ref_no IS NULL
                AND pg_partner IN ('Mudrape', 'Tourquest')
                ORDER BY created_at DESC
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No transactions found with missing UTR")
                return
            
            print(f"Found {len(transactions)} transactions with missing UTR")
            print("=" * 80)
            
            mudrape_service = MudrapeService()
            updated_count = 0
            failed_count = 0
            
            for txn in transactions:
                print(f"\nProcessing: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  PG Partner: {txn['pg_partner']}")
                print(f"  Amount: {txn['amount']}")
                
                try:
                    if txn['pg_partner'] == 'Mudrape':
                        # Check status from Mudrape using order_id
                        status_result = mudrape_service.check_payment_status(txn['order_id'])
                        
                        if status_result.get('success'):
                            utr = status_result.get('utr')
                            pg_txn_id = status_result.get('txnId')
                            
                            if utr:
                                # Update the transaction with UTR
                                cursor.execute("""
                                    UPDATE payin_transactions
                                    SET bank_ref_no = %s, pg_txn_id = %s, updated_at = NOW()
                                    WHERE txn_id = %s
                                """, (utr, pg_txn_id, txn['txn_id']))
                                
                                conn.commit()
                                
                                print(f"  ✓ Updated UTR: {utr}")
                                print(f"  ✓ Updated PG TXN ID: {pg_txn_id}")
                                updated_count += 1
                            else:
                                print(f"  ⚠ No UTR found in Mudrape response")
                                failed_count += 1
                        else:
                            print(f"  ✗ Failed to fetch status: {status_result.get('message')}")
                            failed_count += 1
                    
                    elif txn['pg_partner'] == 'Tourquest':
                        # For Tourquest, we would need to implement status check
                        # For now, skip Tourquest transactions
                        print(f"  ⚠ Tourquest status check not implemented yet")
                        failed_count += 1
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    failed_count += 1
                    continue
            
            print("\n" + "=" * 80)
            print(f"Sync completed!")
            print(f"  Updated: {updated_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Total: {len(transactions)}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting UTR sync for missing bank_ref_no...")
    print("=" * 80)
    sync_missing_utr()
