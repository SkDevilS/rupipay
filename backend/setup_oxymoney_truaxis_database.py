"""
Setup Oxymoney_Truaxis VPA Usage Tracking Table
Creates the table to track daily VPA usage for limit management
"""

from database import get_db_connection

def setup_oxymoney_truaxis_table():
    """Create oxymoney_truaxis_vpa_usage table"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Create table for VPA usage tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oxymoney_truaxis_vpa_usage (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vpa VARCHAR(100) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    txn_id VARCHAR(100) NOT NULL,
                    merchant_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_vpa_date (vpa, created_at),
                    INDEX idx_txn_id (txn_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            print("✅ oxymoney_truaxis_vpa_usage table created successfully")
            
            # Check if table exists and show structure
            cursor.execute("DESCRIBE oxymoney_truaxis_vpa_usage")
            columns = cursor.fetchall()
            
            print("\n📋 Table Structure:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 80)
    print("Setting up Oxymoney_Truaxis Database Tables")
    print("=" * 80)
    
    if setup_oxymoney_truaxis_table():
        print("\n✅ Database setup completed successfully")
        print("\n📝 Next Steps:")
        print("1. Add Oxymoney_Truaxis credentials to .env file")
        print("2. Register routes in app.py")
        print("3. Add service routing configuration")
        print("4. Test the integration")
    else:
        print("\n❌ Database setup failed")
