"""
Setup Oxymoney_Barringer Database Tables
Creates the VPA usage tracking table
"""

from database import get_db_connection

def setup_oxymoney_barringer_tables():
    """Create Oxymoney_Barringer VPA usage table"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor()
        
        # Create VPA usage table
        print("Creating oxymoney_barringer_vpa_usage table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oxymoney_barringer_vpa_usage (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vpa VARCHAR(255) NOT NULL,
                amount DECIMAL(15, 2) NOT NULL,
                txn_id VARCHAR(255) NOT NULL,
                merchant_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_vpa_date (vpa, created_at),
                INDEX idx_txn_id (txn_id),
                INDEX idx_merchant_id (merchant_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        print("✅ oxymoney_barringer_vpa_usage table created successfully")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 80)
    print("Oxymoney_Barringer Database Setup")
    print("=" * 80)
    
    success = setup_oxymoney_barringer_tables()
    
    if success:
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Add Oxymoney_Barringer credentials to .env file")
        print("2. Register routes in app.py")
        print("3. Add to service routing")
    else:
        print("\n❌ Database setup failed!")
