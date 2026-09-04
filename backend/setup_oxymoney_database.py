"""
Oxymoney_Grosmart Database Migration Script
Creates necessary tables for Oxymoney integration with VPA rotation logic

Run this script to set up the database:
    python backend/setup_oxymoney_database.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def create_oxymoney_tables():
    """Create Oxymoney VPA usage tracking table"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("=" * 80)
            print("OXYMONEY_GROSMART DATABASE MIGRATION")
            print("=" * 80)
            
            # Create oxymoney_vpa_usage table
            print("\n📋 Creating oxymoney_vpa_usage table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oxymoney_vpa_usage (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vpa VARCHAR(100) NOT NULL COMMENT 'VPA used for transaction',
                    amount DECIMAL(15,2) NOT NULL COMMENT 'Transaction amount',
                    txn_id VARCHAR(100) NOT NULL COMMENT 'Transaction ID from payin_transactions',
                    merchant_id VARCHAR(50) NOT NULL COMMENT 'Merchant ID',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_vpa_date (vpa, created_at),
                    INDEX idx_txn_id (txn_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Tracks VPA usage for daily limit management (9.6 Lakh per VPA)'
            """)
            print("✅ oxymoney_vpa_usage table created successfully")
            
            # Check if callback_logs table exists, if not create it
            print("\n📋 Checking callback_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS callback_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    txn_id VARCHAR(100) NOT NULL,
                    callback_url TEXT NOT NULL,
                    request_data TEXT,
                    response_code INT,
                    response_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_txn_id (txn_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Logs all callback attempts to merchants'
            """)
            print("✅ callback_logs table verified/created")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print("\n📊 Summary:")
            print("  ✓ oxymoney_vpa_usage table created")
            print("  ✓ callback_logs table verified")
            print("  ✓ All indexes created")
            print("\n🔧 Next Steps:")
            print("  1. Add environment variables to backend/.env")
            print("  2. Register routes in app.py")
            print("  3. Test the integration")
            print("\n")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

def verify_tables():
    """Verify that tables were created successfully"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        with conn.cursor() as cursor:
            print("\n🔍 Verifying tables...")
            
            # Check oxymoney_vpa_usage
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'oxymoney_vpa_usage'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("  ✓ oxymoney_vpa_usage table exists")
                
                # Show table structure
                cursor.execute("DESCRIBE oxymoney_vpa_usage")
                columns = cursor.fetchall()
                print("\n  Table Structure:")
                for col in columns:
                    print(f"    - {col['Field']}: {col['Type']}")
            else:
                print("  ✗ oxymoney_vpa_usage table not found")
                return False
            
            # Check callback_logs
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'callback_logs'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("\n  ✓ callback_logs table exists")
            else:
                print("\n  ✗ callback_logs table not found")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

def show_sample_queries():
    """Show sample queries for monitoring VPA usage"""
    print("\n" + "=" * 80)
    print("📊 USEFUL QUERIES FOR MONITORING")
    print("=" * 80)
    
    print("\n1. Check today's VPA usage:")
    print("""
    SELECT 
        vpa,
        COUNT(*) as transaction_count,
        SUM(amount) as total_amount,
        ROUND((SUM(amount) / 960000) * 100, 2) as usage_percentage
    FROM oxymoney_vpa_usage
    WHERE DATE(created_at) = CURDATE()
    GROUP BY vpa
    ORDER BY total_amount DESC;
    """)
    
    print("\n2. Check available VPA capacity:")
    print("""
    SELECT 
        vpa,
        960000 - COALESCE(SUM(amount), 0) as remaining_capacity
    FROM oxymoney_vpa_usage
    WHERE DATE(created_at) = CURDATE()
    GROUP BY vpa
    HAVING remaining_capacity > 0
    ORDER BY remaining_capacity DESC;
    """)
    
    print("\n3. View recent transactions:")
    print("""
    SELECT 
        vpa,
        amount,
        txn_id,
        merchant_id,
        created_at
    FROM oxymoney_vpa_usage
    ORDER BY created_at DESC
    LIMIT 10;
    """)
    
    print("\n4. Check callback logs:")
    print("""
    SELECT 
        merchant_id,
        txn_id,
        response_code,
        created_at
    FROM callback_logs
    WHERE txn_id LIKE 'OX_GROS_%'
    ORDER BY created_at DESC
    LIMIT 10;
    """)

if __name__ == "__main__":
    print("\n🚀 Starting Oxymoney_Grosmart Database Migration...\n")
    
    # Create tables
    if create_oxymoney_tables():
        # Verify tables
        if verify_tables():
            # Show sample queries
            show_sample_queries()
            print("\n✅ Migration completed successfully!\n")
            sys.exit(0)
        else:
            print("\n❌ Table verification failed\n")
            sys.exit(1)
    else:
        print("\n❌ Migration failed\n")
        sys.exit(1)
