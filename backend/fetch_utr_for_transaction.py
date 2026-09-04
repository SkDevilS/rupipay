"""
Script to fetch and update UTR for a specific transaction from Mudrape
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from mudrape_service import MudrapeService
import json

def fetch_utr(order_id):
    """Fetch UTR from Mudrape for a specific transaction"""
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT 
                    txn_id, 
                    order_id, 
                    merchant_id, 
                    status, 
                    pg_partner,
                    pg_txn_id,
                    bank_ref_no,
                    amount
                FROM payin_transactions
                WHERE order_id = %s
            """, (order_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"ERROR: Transaction not found for order_id: {order_id}")
                return False
            
            print("=" * 80)
            print("Transaction Details:")
            print("=" * 80)
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant ID: {txn['merchant_id']}")
            print(f"Status: {txn['status']}")
            print(f"PG Partner: {txn['pg_partner']}")
            print(f"PG TXN ID: {txn['pg_txn_id']}")
            print(f"Current Bank Ref No: {txn['bank_ref_no']}")
            print(f"Amount: {txn['amount']}")
            
            if txn['pg_partner'] != 'Mudrape':
                print(f"\nERROR: This transaction is not from Mudrape (PG Partner: {txn['pg_partner']})")
                return False
            
            # Fetch status from Mudrape
            print("\n" + "=" * 80)
            print("Fetching status from Mudrape...")
            print("=" * 80)
            
            mudrape_service = MudrapeService()
            
            # Try with pg_txn_id first (txnId), then fall back to order_id (refId)
            identifier = txn.get('pg_txn_id') or txn['order_id']
            print(f"Using identifier: {identifier}")
            print(f"  Type: {'txnId (pg_txn_id)' if txn.get('pg_txn_id') else 'refId (order_id)'}")
            
            status_result = mudrape_service.check_payment_status(identifier)
            
            print(f"\nMudrape Response:")
            print(json.dumps(status_result, indent=2))
            
            if not status_result.get('success'):
                print(f"\nERROR: Failed to fetch status from Mudrape")
                print(f"Message: {status_result.get('message')}")
                return False
            
            # Extract UTR and other details
            utr = status_result.get('utr')
            pg_txn_id = status_result.get('txnId')
            status = status_result.get('status')
            payment_mode = status_result.get('payment_mode', 'UPI')
            
            print("\n" + "=" * 80)
            print("Extracted Data:")
            print("=" * 80)
            print(f"Status: {status}")
            print(f"UTR/Bank Ref No: {utr}")
            print(f"PG TXN ID: {pg_txn_id}")
            print(f"Payment Mode: {payment_mode}")
            
            if not utr:
                print("\n⚠ WARNING: No UTR found in Mudrape response")
                print("This could mean:")
                print("  1. Payment is still pending")
                print("  2. Mudrape hasn't received UTR from bank yet")
                print("  3. Transaction failed")
                return False
            
            # Update database
            print("\n" + "=" * 80)
            print("Updating Database...")
            print("=" * 80)
            
            cursor.execute("""
                UPDATE payin_transactions
                SET bank_ref_no = %s, pg_txn_id = %s, payment_mode = %s, updated_at = NOW()
                WHERE order_id = %s
            """, (utr, pg_txn_id, payment_mode, order_id))
            
            conn.commit()
            
            print(f"✓ Updated bank_ref_no: {utr}")
            print(f"✓ Updated pg_txn_id: {pg_txn_id}")
            print(f"✓ Updated payment_mode: {payment_mode}")
            
            # Verify update
            cursor.execute("""
                SELECT bank_ref_no, pg_txn_id, payment_mode
                FROM payin_transactions
                WHERE order_id = %s
            """, (order_id,))
            
            updated_txn = cursor.fetchone()
            
            print("\n" + "=" * 80)
            print("Verification:")
            print("=" * 80)
            print(f"Bank Ref No in DB: {updated_txn['bank_ref_no']}")
            print(f"PG TXN ID in DB: {updated_txn['pg_txn_id']}")
            print(f"Payment Mode in DB: {updated_txn['payment_mode']}")
            
            print("\n✓ SUCCESS: UTR updated successfully!")
            return True
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch and update UTR for a transaction')
    parser.add_argument('--order-id', required=True, help='Order ID of the transaction')
    
    args = parser.parse_args()
    
    print("Fetching UTR from Mudrape...")
    print("=" * 80)
    
    success = fetch_utr(args.order_id)
    
    if success:
        print("\n" + "=" * 80)
        print("Done! You can now verify the transaction:")
        print(f"  Order ID: {args.order_id}")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("Failed to fetch UTR. Please check the error messages above.")
        print("=" * 80)
        sys.exit(1)
