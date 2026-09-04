#!/usr/bin/env python3
"""
Add reference_id column to fund_requests table
"""

import pymysql
from database import get_db_connection

def add_reference_id_column():
    """Add reference_id column to fund_requests table if it doesn't exist"""
    
    print("=" * 60)
    print("Adding reference_id column to fund_requests table")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if column already exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'fund_requests' 
                AND COLUMN_NAME = 'reference_id'
            """)
            
            if cursor.fetchone():
                print("✅ Column 'reference_id' already exists in fund_requests table")
                conn.close()
                return True
            
            # Add the column
            print("\n📝 Adding reference_id column...")
            cursor.execute("""
                ALTER TABLE fund_requests 
                ADD COLUMN reference_id VARCHAR(100) NULL AFTER request_id
            """)
            conn.commit()
            print("✅ Column added successfully")
            
            # Update existing rows to use request_id as reference_id
            print("\n📝 Updating existing rows...")
            cursor.execute("""
                UPDATE fund_requests 
                SET reference_id = request_id 
                WHERE reference_id IS NULL
            """)
            conn.commit()
            print(f"✅ Updated {cursor.rowcount} rows")
            
            # Verify the column was added
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'fund_requests' 
                AND COLUMN_NAME = 'reference_id'
            """)
            
            result = cursor.fetchone()
            if result:
                print("\n✅ Verification successful:")
                print(f"   Column: {result['COLUMN_NAME']}")
                print(f"   Type: {result['COLUMN_TYPE']}")
                print(f"   Nullable: {result['IS_NULLABLE']}")
            
        conn.close()
        print("\n" + "=" * 60)
        print("✅ Successfully added reference_id column to fund_requests")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    add_reference_id_column()
