#!/usr/bin/env python3
"""
Search for a specific payout transaction by any identifier
"""

import sys
from database import get_db_connection

def search_transaction(search_term):
    """Search for transaction by txn_id, reference_id, order_id, or pg_txn_id"""
    print("=" * 80)
    print(f"SEARCHING FOR TRANSACTION: {search_term}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Search across all identifier fields
            cursor.execute("""
                SELECT 
                    pt.*,
                    m.full_name as merchant_name,
                    m.mobile as merchant_mobile,
                    m.email as merchant_email
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.txn_id LIKE %s
                OR pt.reference_id LIKE %s
                OR pt.order_id LIKE %s
                OR pt.pg_txn_id LIKE %s
                OR pt.bank_ref_no LIKE %s
                OR pt.utr LIKE %s
                ORDER BY pt.created_at DESC
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", 
                  f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            
            results = cursor.fetchall()
            
            if not results:
                print(f"\n❌ No transactions found matching: {search_term}")
                print("\nTry searching with:")
                print("  - Transaction ID (TXN...)")
                print("  - Reference ID (DP...)")
                print("  - Order ID")
                print("  - PG Transaction ID")
                print("  - Bank Reference Number")
                print("  - UTR Number")
            else:
                print(f"\n✅ Found {len(results)} transaction(s):")
                print("=" * 80)
                
                for i, txn in enumerate(results, 1):
                    print(f"\n{'='*80}")
                    print(f"TRANSACTION #{i}")
                    print(f"{'='*80}")
                    print(f"TXN ID: {txn['txn_id']}")
                    print(f"Reference ID: {txn['reference_id']}")
                    print(f"Order ID: {txn['order_id']}")
                    print(f"Merchant ID: {txn['merchant_id']}")
                    print(f"Merchant Name: {txn['merchant_name']}")
                    print(f"Merchant Mobile: {txn['merchant_mobile']}")
                    print(f"Merchant Email: {txn['merchant_email']}")
                    print(f"\nPayout Details:")
                    print(f"  Amount: ₹{txn['amount']:.2f}")
                    print(f"  Charge: ₹{txn['charge_amount']:.2f}")
                    print(f"  Net Amount: ₹{txn['net_amount']:.2f}")
                    print(f"  Status: {txn['status']}")
                    print(f"\nBeneficiary Details:")
                    print(f"  Name: {txn['bene_name']}")
                    print(f"  Bank: {txn['bene_bank']}")
                    print(f"  Account: {txn['account_no']}")
                    print(f"  IFSC: {txn['ifsc_code']}")
                    print(f"  Mobile: {txn['bene_mobile']}")
                    print(f"  Email: {txn['bene_email']}")
                    print(f"\nPayment Gateway Details:")
                    print(f"  PG Partner: {txn['pg_partner']}")
                    print(f"  PG Transaction ID: {txn['pg_txn_id']}")
                    print(f"  Bank Ref No: {txn['bank_ref_no']}")
                    print(f"  UTR: {txn['utr']}")
                    print(f"  Payment Type: {txn['payment_type']}")
                    print(f"\nTimestamps:")
                    print(f"  Created: {txn['created_at']}")
                    print(f"  Updated: {txn['updated_at']}")
                    print(f"  Completed: {txn['completed_at']}")
                    
                    if txn['error_message']:
                        print(f"\n⚠️  Error Message: {txn['error_message']}")
                    
                    if txn['remarks']:
                        print(f"Remarks: {txn['remarks']}")
                    
                    # Check if this is an orphaned record
                    if txn['merchant_id'] and not txn['merchant_name']:
                        print(f"\n⚠️  WARNING: This is an ORPHANED record!")
                        print(f"   merchant_id '{txn['merchant_id']}' not found in merchants table")
                        print(f"   This is likely an admin personal payout stored incorrectly")
                
                print(f"\n{'='*80}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_payout_transaction.py <search_term>")
        print("\nExample:")
        print("  python search_payout_transaction.py DP2026030417553292BE6E")
        print("  python search_payout_transaction.py TXN6B52F88DCA32")
        print("  python search_payout_transaction.py ORD0987865271002")
        sys.exit(1)
    
    search_term = sys.argv[1]
    search_transaction(search_term)
