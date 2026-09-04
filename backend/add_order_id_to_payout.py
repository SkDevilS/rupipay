#!/usr/bin/env python3
"""
Add order_id column to payout_transactions table
"""

import pymysql
from config import Config

def add_order_id_column():
    """Add order_id column to payout_transactions table"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check if column already exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'payout_transactions'
                AND COLUMN_NAME = 'order_id'
            """, (Config.DB_NAME,))
            
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("Adding order_id column to payout_transactions table...")
                
                # Add order_id column (nullable initially for existing records)
                cursor.execute("""
                    ALTER TABLE payout_transactions
                    ADD COLUMN order_id VARCHAR(100) NULL AFTER reference_id
                """)
                
                # Add index on order_id for faster lookups
                cursor.execute("""
                    ALTER TABLE payout_transactions
                    ADD INDEX idx_order_id (order_id)
                """)
                
                connection.commit()
                print("✓ Successfully added order_id column with index")
                
                # Update existing records with order_id = reference_id for backward compatibility
                print("Updating existing records with order_id...")
                cursor.execute("""
                    UPDATE payout_transactions
                    SET order_id = reference_id
                    WHERE order_id IS NULL
                """)
                connection.commit()
                print(f"✓ Updated {cursor.rowcount} existing records")
                
            else:
                print("✓ order_id column already exists")
        
        connection.close()
        print("\n✓ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Adding order_id column to payout_transactions table")
    print("=" * 60)
    add_order_id_column()
