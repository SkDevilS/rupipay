#!/usr/bin/env python3
"""
Delete a PayIN transaction but keep the admin wallet credit
This removes it from PayIN reports while maintaining admin balance
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def delete_payin_keep_credit(txn_id):
    """Delete PayIN transaction but keep admin wallet credit"""
    print("\n" + "=" * 80)
    print("DELETE PAYIN - KEEP ADMIN CREDIT")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if PayIN transaction exists
            print(f"\n1. Checking PayIN transaction: {txn_id}")
            cursor.execute("""
                SELECT txn_id, merchant_id, amount, order_id, status
                FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            payin = cursor.fetchone()
            if not payin:
                print(f"   ❌ PayIN transaction {txn_id} not found")
                conn.close()
                return False
            
            print(f"   ✓ Found PayIN transaction")
            print(f"   Merchant: {payin['merchant_id']}")
            print(f"   Amount: ₹{float(payin['amount']):,.2f}")
            print(f"   Order ID: {payin['order_id']}")
            print(f"   Status: {payin['status']}")
            
            # Check if admin wallet transaction exists
            print(f"\n2. Checking admin wallet transaction...")
            cursor.execute("""
                SELECT txn_id, amount, description
                FROM admin_wallet_transactions
                WHERE reference_id = %s
            """, (txn_id,))
            
            admin_txn = cursor.fetchone()
            if admin_txn:
                print(f"   ✓ Found admin wallet transaction: {admin_txn['txn_id']}")
                print(f"   Amount: ₹{float(admin_txn['amount']):,.2f}")
                print(f"   Description: {admin_txn['description']}")
                print(f"   This will be KEPT (not deleted)")
            else:
                print(f"   ⚠️  No admin wallet transaction found with reference to this PayIN")
            
            # Delete the PayIN transaction
            print(f"\n3. Deleting PayIN transaction...")
            cursor.execute("""
                DELETE FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            print(f"   ✓ Deleted PayIN transaction")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - PayIN deleted, admin credit kept")
            print("=" * 80)
            print(f"\nDeleted PayIN: {txn_id}")
            print(f"Amount: ₹{float(payin['amount']):,.2f}")
            print(f"\n✓ Admin wallet credit remains intact")
            print(f"✓ Balance calculation will still include this credit")
            print(f"✓ PayIN will NOT appear in reports")
            
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
    if len(sys.argv) < 2:
        print("Usage: python3 delete_payin_keep_admin_credit.py <txn_id>")
        print("Example: python3 delete_payin_keep_admin_credit.py PAYIN20260303003956236")
        sys.exit(1)
    
    txn_id = sys.argv[1]
    
    print(f"\n⚠️  WARNING: This will DELETE the PayIN transaction {txn_id}")
    print("The admin wallet credit will be kept, so balance remains correct")
    print("But the PayIN will no longer appear in reports")
    
    confirm = input("\nProceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled")
        sys.exit(0)
    
    success = delete_payin_keep_credit(txn_id)
    sys.exit(0 if success else 1)
