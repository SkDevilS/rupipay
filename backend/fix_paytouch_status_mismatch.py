"""
Fix PayTouch Status Mismatch
Manually update transaction status when callback was missed
Transaction: TXN986649FDE8C3
"""

from database import get_db_connection
from paytouch_service import paytouch_service
from wallet_service import wallet_service
import json

def fix_transaction(txn_id):
    """Fix a specific transaction by checking PayTouch status and updating"""
    
    print("=" * 80)
    print(f"Fixing PayTouch Transaction: {txn_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_partner, pg_txn_id, utr,
                    error_message, created_at, completed_at
                FROM payout_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"ERROR: Transaction {txn_id} not found")
                return
            
            print(f"\nCurrent Transaction Status:")
            print(f"  Transaction ID: {txn['txn_id']}")
            print(f"  Reference ID: {txn['reference_id']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  Admin ID: {txn['admin_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Charges: ₹{txn['charge_amount']}")
            print(f"  Net Amount: ₹{txn['net_amount']}")
            print(f"  Status: {txn['status']}")
            print(f"  PG Partner: {txn['pg_partner']}")
            print(f"  PG Transaction ID: {txn['pg_txn_id']}")
            print(f"  UTR: {txn['utr']}")
            
            if txn['pg_partner'] != 'PayTouch':
                print(f"\nERROR: This transaction is not a PayTouch transaction")
                return
            
            # Check status from PayTouch
            print(f"\nChecking status from PayTouch...")
            status_result = paytouch_service.check_payout_status(
                transaction_id=txn['pg_txn_id'],
                external_ref=txn['reference_id']
            )
            
            if not status_result.get('success'):
                print(f"ERROR: Failed to check PayTouch status: {status_result.get('message')}")
                return
            
            paytouch_status = status_result.get('status')
            paytouch_utr = status_result.get('utr')
            
            print(f"\nPayTouch Status Check Result:")
            print(f"  Status: {paytouch_status}")
            print(f"  UTR: {paytouch_utr}")
            print(f"  Full Response: {json.dumps(status_result, indent=2)}")
            
            # Map PayTouch status
            status_map = {
                'SUCCESS': 'SUCCESS',
                'PENDING': 'QUEUED',
                'FAILED': 'FAILED',
                'PROCESSING': 'INPROCESS'
            }
            mapped_status = status_map.get(paytouch_status, 'QUEUED')
            
            print(f"\nMapped Status: {mapped_status}")
            
            if mapped_status == txn['status']:
                print(f"\n✓ Status is already correct. No update needed.")
                return
            
            print(f"\n⚠️  Status mismatch detected!")
            print(f"   Database: {txn['status']}")
            print(f"   PayTouch: {mapped_status}")
            
            # Ask for confirmation
            print(f"\nDo you want to update the transaction status to {mapped_status}?")
            print(f"This will also handle wallet deduction if status is SUCCESS.")
            confirm = input("Type 'yes' to confirm: ")
            
            if confirm.lower() != 'yes':
                print("Update cancelled.")
                return
            
            # Update transaction status
            if mapped_status == 'SUCCESS':
                # Check if wallet was already debited
                if txn['merchant_id']:
                    # This is a merchant transaction - check if wallet needs to be debited
                    total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                    
                    print(f"\nChecking if wallet was already debited...")
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (txn['merchant_id'],))
                    wallet_exists = cursor.fetchone()['count'] > 0
                    
                    if wallet_exists:
                        # Debit wallet
                        print(f"Debiting merchant wallet: ₹{total_deduction}")
                        debit_result = wallet_service.debit_merchant_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=total_deduction,
                            description=f"Payout - {txn['reference_id']} (Manual Fix)",
                            reference_id=txn['txn_id']
                        )
                        
                        if debit_result['success']:
                            print(f"✅ WALLET DEBITED - Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                        else:
                            print(f"⚠️  WALLET DEBIT FAILED: {debit_result['message']}")
                            print(f"   You may need to manually adjust the wallet balance")
                    else:
                        print(f"⚠️  Merchant wallet not found. Skipping wallet debit.")
                
                # Update transaction to SUCCESS
                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, paytouch_utr, txn['txn_id']))
                
            elif mapped_status == 'FAILED':
                # Update to FAILED
                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = %s, error_message = %s, completed_at = NOW(), updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, 'Failed at PayTouch', txn['txn_id']))
                
            else:
                # Update to intermediate status
                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = %s, updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, txn['txn_id']))
            
            conn.commit()
            
            print(f"\n✅ Transaction updated successfully!")
            print(f"   New Status: {mapped_status}")
            
            # Verify the update
            cursor.execute("""
                SELECT status, utr, completed_at
                FROM payout_transactions
                WHERE txn_id = %s
            """, (txn['txn_id'],))
            
            updated_txn = cursor.fetchone()
            print(f"\nVerification:")
            print(f"  Status: {updated_txn['status']}")
            print(f"  UTR: {updated_txn['utr']}")
            print(f"  Completed: {updated_txn['completed_at']}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        txn_id = sys.argv[1]
    else:
        txn_id = 'TXN986649FDE8C3'  # Default transaction
    
    fix_transaction(txn_id)
