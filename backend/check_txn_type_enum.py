"""
Check the txn_type ENUM values in merchant_wallet_transactions table
"""

from database import get_db_connection

def check_txn_type_enum():
    """Check what values are allowed for txn_type"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get column definition
            cursor.execute("""
                SHOW COLUMNS FROM merchant_wallet_transactions LIKE 'txn_type'
            """)
            column_info = cursor.fetchone()
            
            print("=" * 80)
            print("TXN_TYPE COLUMN DEFINITION")
            print("=" * 80)
            print(f"Field: {column_info['Field']}")
            print(f"Type: {column_info['Type']}")
            print(f"Null: {column_info['Null']}")
            print(f"Default: {column_info['Default']}")
            print()
            
            # Check if UNSETTLED_CREDIT is in the ENUM
            if 'UNSETTLED_CREDIT' in column_info['Type']:
                print("✓ UNSETTLED_CREDIT is already in the ENUM")
            else:
                print("❌ UNSETTLED_CREDIT is NOT in the ENUM")
                print()
                print("Need to add it with:")
                print("ALTER TABLE merchant_wallet_transactions")
                print("MODIFY COLUMN txn_type ENUM('CREDIT', 'DEBIT', 'UNSETTLED_CREDIT', 'SETTLEMENT') NOT NULL;")
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_txn_type_enum()
