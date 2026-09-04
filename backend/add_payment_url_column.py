#!/usr/bin/env python3
"""
Add payment_url column to payin_transactions table
Required for ViyonaPay integration
"""

from database import get_db_connection

def add_payment_url_column():
    """Add payment_url column if it doesn't exist"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payin_transactions'
                AND COLUMN_NAME = 'payment_url'
            """)
            
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("✓ payment_url column already exists")
                return True
            
            # Add the column
            print("Adding payment_url column...")
            cursor.execute("""
                ALTER TABLE payin_transactions 
                ADD COLUMN payment_url TEXT AFTER product_info
            """)
            
            conn.commit()
            print("✅ payment_url column added successfully")
            
            # Verify
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payin_transactions'
                AND COLUMN_NAME = 'payment_url'
            """)
            
            column_info = cursor.fetchone()
            if column_info:
                print(f"   Column: {column_info['COLUMN_NAME']}")
                print(f"   Type: {column_info['DATA_TYPE']}")
                print(f"   Nullable: {column_info['IS_NULLABLE']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*80)
    print("  Add payment_url Column to payin_transactions")
    print("="*80)
    
    success = add_payment_url_column()
    
    if success:
        print("\n✅ Migration completed successfully")
    else:
        print("\n❌ Migration failed")
