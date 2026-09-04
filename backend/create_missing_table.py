#!/usr/bin/env python3
"""Create missing merchant_wallet_transactions table"""

from database import get_db_connection

def create_missing_table():
    """Create merchant_wallet_transactions table if it doesn't exist"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'merchant_wallet_transactions'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("✓ Table merchant_wallet_transactions already exists")
                return True
            
            print("Creating merchant_wallet_transactions table...")
            
            # Create the table
            cursor.execute("""
                CREATE TABLE merchant_wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(20) NOT NULL,
                    transaction_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    balance_before DECIMAL(15, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description VARCHAR(500),
                    reference_id VARCHAR(100),
                    reference_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_reference (reference_id, reference_type),
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            print("✓ Table merchant_wallet_transactions created successfully")
            return True
            
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating missing database table...")
    print("-" * 50)
    
    if create_missing_table():
        print("-" * 50)
        print("✓ Success! Table created.")
    else:
        print("-" * 50)
        print("✗ Failed to create table.")
