"""
Add UNSETTLED_CREDIT and SETTLEMENT to the txn_type ENUM
"""

from database import get_db_connection

def add_unsettled_txn_types():
    """Add new transaction types to the ENUM"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check current ENUM values
            cursor.execute("""
                SHOW COLUMNS FROM merchant_wallet_transactions LIKE 'txn_type'
            """)
            column_info = cursor.fetchone()
            
            print("=" * 80)
            print("CURRENT TXN_TYPE ENUM")
            print("=" * 80)
            print(f"Type: {column_info['Type']}")
            print()
            
            # Check if already has the new types
            if 'UNSETTLED_CREDIT' in column_info['Type'] and 'SETTLEMENT' in column_info['Type']:
                print("✓ UNSETTLED_CREDIT and SETTLEMENT already exist in ENUM")
                return True
            
            print("Adding UNSETTLED_CREDIT and SETTLEMENT to ENUM...")
            
            # Modify the ENUM to include new types (preserve existing HOLD and RELEASE)
            cursor.execute("""
                ALTER TABLE merchant_wallet_transactions
                MODIFY COLUMN txn_type ENUM('CREDIT', 'DEBIT', 'HOLD', 'RELEASE', 'UNSETTLED_CREDIT', 'SETTLEMENT') NOT NULL
            """)
            
            conn.commit()
            
            # Verify the change
            cursor.execute("""
                SHOW COLUMNS FROM merchant_wallet_transactions LIKE 'txn_type'
            """)
            updated_column = cursor.fetchone()
            
            print()
            print("=" * 80)
            print("UPDATED TXN_TYPE ENUM")
            print("=" * 80)
            print(f"Type: {updated_column['Type']}")
            print()
            
            if 'UNSETTLED_CREDIT' in updated_column['Type'] and 'SETTLEMENT' in updated_column['Type']:
                print("✓ Successfully added new transaction types!")
                return True
            else:
                print("❌ Failed to add new transaction types")
                return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 80)
    print("ADD UNSETTLED TRANSACTION TYPES")
    print("=" * 80)
    print()
    
    success = add_unsettled_txn_types()
    
    print()
    print("=" * 80)
    if success:
        print("✓ COMPLETE!")
        print()
        print("You can now run:")
        print("  python3 fix_recent_transaction.py")
    else:
        print("❌ FAILED!")
    print("=" * 80)
