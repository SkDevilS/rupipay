#!/usr/bin/env python3
"""
Update the merchant_id for a specific PayIN transaction
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def update_payin_merchant(txn_id, new_merchant_id):
    """Update merchant_id for a PayIN transaction"""
    print("\n" + "=" * 80)
    print("UPDATE PAYIN MERCHANT ID")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if transaction exists
            print(f"\n1. Checking transaction: {txn_id}")
            cursor.execute("""
                SELECT txn_id, merchant_id, amount, order_id, status
                FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            if not txn:
                print(f"   ❌ Transaction {txn_id} not found")
                conn.close()
                return False
            
            print(f"   ✓ Found transaction")
            print(f"   Current Merchant: {txn['merchant_id']}")
            print(f"   Amount: ₹{float(txn['amount']):,.2f}")
            print(f"   Order ID: {txn['order_id']}")
            print(f"   Status: {txn['status']}")
            
            # Check if new merchant exists
            print(f"\n2. Checking new merchant: {new_merchant_id}")
            cursor.execute("""
                SELECT merchant_id, full_name
                FROM merchants
                WHERE merchant_id = %s
            """, (new_merchant_id,))
            
            merchant = cursor.fetchone()
            if not merchant:
                print(f"   ❌ Merchant {new_merchant_id} not found in database")
                print(f"   Please use an existing merchant_id")
                conn.close()
                return False
            else:
                print(f"   ✓ Merchant exists: {merchant['full_name']}")
            
            # Update the transaction
            print(f"\n3. Updating transaction merchant_id...")
            cursor.execute("""
                UPDATE payin_transactions
                SET merchant_id = %s
                WHERE txn_id = %s
            """, (new_merchant_id, txn_id))
            
            print(f"   ✓ Updated transaction")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - Merchant ID updated")
            print("=" * 80)
            print(f"\nTransaction: {txn_id}")
            print(f"Old Merchant: {txn['merchant_id']}")
            print(f"New Merchant: {new_merchant_id}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 update_payin_merchant.py <txn_id> <new_merchant_id>")
        print("Example: python3 update_payin_merchant.py PAYIN20260303012 TEST_MERCHANT")
        sys.exit(1)
    
    txn_id = sys.argv[1]
    new_merchant_id = sys.argv[2]
    
    print(f"\nYou are about to update transaction {txn_id}")
    print(f"New merchant ID will be: {new_merchant_id}")
    
    confirm = input("\nProceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled")
        sys.exit(0)
    
    success = update_payin_merchant(txn_id, new_merchant_id)
    sys.exit(0 if success else 1)
