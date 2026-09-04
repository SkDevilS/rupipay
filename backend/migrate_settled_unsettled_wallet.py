"""
Database Migration Script for Settled/Unsettled Wallet Feature
This script adds settled_balance and unsettled_balance columns to merchant_wallet table
and creates settlement_transactions table
"""

import pymysql
from config import Config
import sys

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"""
        SELECT COUNT(*) as count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{Config.DB_NAME}'
        AND TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = '{column_name}'
    """)
    result = cursor.fetchone()
    return result['count'] > 0

def check_table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute(f"""
        SELECT COUNT(*) as count
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{Config.DB_NAME}'
        AND TABLE_NAME = '{table_name}'
    """)
    result = cursor.fetchone()
    return result['count'] > 0

def migrate_database():
    """Run the database migration"""
    print("=" * 80)
    print("SETTLED/UNSETTLED WALLET DATABASE MIGRATION")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Step 1: Check if merchant_wallet table exists
            print("Step 1: Checking merchant_wallet table...")
            if not check_table_exists(cursor, 'merchant_wallet'):
                print("❌ merchant_wallet table does not exist!")
                return False
            print("✓ merchant_wallet table exists")
            print()
            
            # Step 2: Add settled_balance column
            print("Step 2: Adding settled_balance column...")
            if check_column_exists(cursor, 'merchant_wallet', 'settled_balance'):
                print("⚠ settled_balance column already exists, skipping...")
            else:
                cursor.execute("""
                    ALTER TABLE merchant_wallet 
                    ADD COLUMN settled_balance DECIMAL(15, 2) DEFAULT 0.00 
                    COMMENT 'Settled amount - available for payout'
                    AFTER balance
                """)
                print("✓ Added settled_balance column")
            print()
            
            # Step 3: Add unsettled_balance column
            print("Step 3: Adding unsettled_balance column...")
            if check_column_exists(cursor, 'merchant_wallet', 'unsettled_balance'):
                print("⚠ unsettled_balance column already exists, skipping...")
            else:
                cursor.execute("""
                    ALTER TABLE merchant_wallet 
                    ADD COLUMN unsettled_balance DECIMAL(15, 2) DEFAULT 0.00 
                    COMMENT 'Unsettled amount - pending admin approval'
                    AFTER settled_balance
                """)
                print("✓ Added unsettled_balance column")
            print()
            
            # Step 4: Migrate existing balance to settled_balance
            print("Step 4: Migrating existing balance to settled_balance...")
            cursor.execute("""
                UPDATE merchant_wallet 
                SET settled_balance = balance, 
                    unsettled_balance = 0.00
                WHERE settled_balance = 0.00
            """)
            affected_rows = cursor.rowcount
            print(f"✓ Migrated {affected_rows} wallet records")
            print()
            
            # Step 5: Get column types for foreign keys
            print("Step 5: Getting column types for foreign keys...")
            cursor.execute("""
                SELECT COLUMN_TYPE, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'merchants'
                AND COLUMN_NAME = 'merchant_id'
            """, (Config.DB_NAME,))
            merchant_col = cursor.fetchone()
            merchant_id_type = merchant_col['COLUMN_TYPE']
            merchant_collation = merchant_col['COLLATION_NAME']
            
            cursor.execute("""
                SELECT COLUMN_TYPE, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'admin_users'
                AND COLUMN_NAME = 'admin_id'
            """, (Config.DB_NAME,))
            admin_col = cursor.fetchone()
            admin_id_type = admin_col['COLUMN_TYPE']
            admin_collation = admin_col['COLLATION_NAME']
            
            print(f"  merchant_id: {merchant_id_type} COLLATE {merchant_collation}")
            print(f"  admin_id: {admin_id_type} COLLATE {admin_collation}")
            print()
            
            # Step 6: Create settlement_transactions table
            print("Step 6: Creating settlement_transactions table...")
            if check_table_exists(cursor, 'settlement_transactions'):
                print("⚠ settlement_transactions table already exists")
                print("  Dropping and recreating to ensure correct structure...")
                cursor.execute("DROP TABLE IF EXISTS settlement_transactions")
                print("  ✓ Dropped existing table")
            
            # Create table without foreign keys first
            create_table_sql = f"""
                CREATE TABLE settlement_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    settlement_id VARCHAR(100) UNIQUE NOT NULL,
                    merchant_id {merchant_id_type} COLLATE {merchant_collation} NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    settled_by {admin_id_type} COLLATE {admin_collation} NOT NULL,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
            """
            cursor.execute(create_table_sql)
            print("  ✓ Created settlement_transactions table")
            
            # Add foreign keys separately
            print("  Adding foreign key constraints...")
            try:
                cursor.execute("""
                    ALTER TABLE settlement_transactions
                    ADD CONSTRAINT fk_settlement_merchant
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                """)
                print("    ✓ Added merchant_id foreign key")
            except Exception as e:
                print(f"    ⚠ Could not add merchant_id foreign key: {e}")
            
            try:
                cursor.execute("""
                    ALTER TABLE settlement_transactions
                    ADD CONSTRAINT fk_settlement_admin
                    FOREIGN KEY (settled_by) REFERENCES admin_users(admin_id)
                """)
                print("    ✓ Added settled_by foreign key")
            except Exception as e:
                print(f"    ⚠ Could not add settled_by foreign key: {e}")
            
            print("✓ settlement_transactions table created successfully")
            print()
            
            # Step 7: Update balance column comment
            print("Step 7: Updating balance column comment...")
            cursor.execute("""
                ALTER TABLE merchant_wallet 
                MODIFY COLUMN balance DECIMAL(15, 2) DEFAULT 0.00 
                COMMENT 'Legacy balance - use settled_balance instead'
            """)
            print("✓ Updated balance column comment")
            print()
            
            # Commit all changes
            conn.commit()
            
            # Step 8: Verify migration
            print("Step 8: Verifying migration...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_wallets,
                    SUM(balance) as total_balance,
                    SUM(settled_balance) as total_settled,
                    SUM(unsettled_balance) as total_unsettled
                FROM merchant_wallet
            """)
            stats = cursor.fetchone()
            
            print(f"✓ Total wallets: {stats['total_wallets']}")
            print(f"✓ Total balance: ₹{float(stats['total_balance']):.2f}")
            print(f"✓ Total settled: ₹{float(stats['total_settled']):.2f}")
            print(f"✓ Total unsettled: ₹{float(stats['total_unsettled']):.2f}")
            print()
            
            # Check settlement_transactions table
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM settlement_transactions
            """)
            settlement_count = cursor.fetchone()['count']
            print(f"✓ Settlement transactions: {settlement_count}")
            print()
            
        conn.close()
        
        print("=" * 80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("Summary:")
        print("1. ✓ Added settled_balance column to merchant_wallet")
        print("2. ✓ Added unsettled_balance column to merchant_wallet")
        print("3. ✓ Migrated existing balance to settled_balance")
        print("4. ✓ Detected column types for foreign keys")
        print("5. ✓ Created settlement_transactions table")
        print("6. ✓ Updated column comments")
        print()
        print("Next steps:")
        print("1. Restart backend: pkill -f 'python.*app.py' && nohup python app.py > backend.log 2>&1 &")
        print("2. Test payin flow - verify unsettled wallet is credited")
        print("3. Test settlement flow - admin can transfer unsettled to settled")
        print("4. Verify dashboard displays are correct")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False

def rollback_migration():
    """Rollback the migration (remove added columns and table)"""
    print("=" * 80)
    print("ROLLING BACK SETTLED/UNSETTLED WALLET MIGRATION")
    print("=" * 80)
    print()
    
    response = input("⚠ WARNING: This will remove settled_balance, unsettled_balance columns and settlement_transactions table. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Rollback cancelled.")
        return False
    
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Drop settlement_transactions table
            print("Dropping settlement_transactions table...")
            cursor.execute("DROP TABLE IF EXISTS settlement_transactions")
            print("✓ Dropped settlement_transactions table")
            
            # Remove unsettled_balance column
            print("Removing unsettled_balance column...")
            if check_column_exists(cursor, 'merchant_wallet', 'unsettled_balance'):
                cursor.execute("ALTER TABLE merchant_wallet DROP COLUMN unsettled_balance")
                print("✓ Removed unsettled_balance column")
            else:
                print("⚠ unsettled_balance column does not exist")
            
            # Remove settled_balance column
            print("Removing settled_balance column...")
            if check_column_exists(cursor, 'merchant_wallet', 'settled_balance'):
                cursor.execute("ALTER TABLE merchant_wallet DROP COLUMN settled_balance")
                print("✓ Removed settled_balance column")
            else:
                print("⚠ settled_balance column does not exist")
            
            conn.commit()
        
        conn.close()
        
        print()
        print("✅ ROLLBACK COMPLETED SUCCESSFULLY!")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False

def show_current_status():
    """Show current database status"""
    print("=" * 80)
    print("CURRENT DATABASE STATUS")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check columns
            print("Checking merchant_wallet table columns...")
            has_settled = check_column_exists(cursor, 'merchant_wallet', 'settled_balance')
            has_unsettled = check_column_exists(cursor, 'merchant_wallet', 'unsettled_balance')
            
            print(f"  settled_balance: {'✓ EXISTS' if has_settled else '✗ NOT FOUND'}")
            print(f"  unsettled_balance: {'✓ EXISTS' if has_unsettled else '✗ NOT FOUND'}")
            print()
            
            # Check table
            print("Checking settlement_transactions table...")
            has_table = check_table_exists(cursor, 'settlement_transactions')
            print(f"  settlement_transactions: {'✓ EXISTS' if has_table else '✗ NOT FOUND'}")
            print()
            
            # Show wallet stats if columns exist
            if has_settled and has_unsettled:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_wallets,
                        SUM(balance) as total_balance,
                        SUM(settled_balance) as total_settled,
                        SUM(unsettled_balance) as total_unsettled
                    FROM merchant_wallet
                """)
                stats = cursor.fetchone()
                
                print("Wallet Statistics:")
                print(f"  Total wallets: {stats['total_wallets']}")
                print(f"  Total balance: ₹{float(stats['total_balance']):.2f}")
                print(f"  Total settled: ₹{float(stats['total_settled']):.2f}")
                print(f"  Total unsettled: ₹{float(stats['total_unsettled']):.2f}")
                print()
            
            # Show settlement stats if table exists
            if has_table:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_settlements,
                        COALESCE(SUM(amount), 0) as total_amount
                    FROM settlement_transactions
                """)
                settlement_stats = cursor.fetchone()
                
                print("Settlement Statistics:")
                print(f"  Total settlements: {settlement_stats['total_settlements']}")
                print(f"  Total amount settled: ₹{float(settlement_stats['total_amount']):.2f}")
                print()
            
            # Migration status
            print("Migration Status:")
            if has_settled and has_unsettled and has_table:
                print("  ✅ MIGRATION COMPLETED")
            elif not has_settled and not has_unsettled and not has_table:
                print("  ⚠ MIGRATION NOT RUN")
            else:
                print("  ⚠ PARTIAL MIGRATION (incomplete)")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "migrate":
            success = migrate_database()
            sys.exit(0 if success else 1)
        elif command == "rollback":
            success = rollback_migration()
            sys.exit(0 if success else 1)
        elif command == "status":
            show_current_status()
            sys.exit(0)
        else:
            print("Invalid command. Use: migrate, rollback, or status")
            sys.exit(1)
    else:
        print("=" * 80)
        print("SETTLED/UNSETTLED WALLET MIGRATION SCRIPT")
        print("=" * 80)
        print()
        print("Usage:")
        print("  python migrate_settled_unsettled_wallet.py migrate   - Run migration")
        print("  python migrate_settled_unsettled_wallet.py rollback  - Rollback migration")
        print("  python migrate_settled_unsettled_wallet.py status    - Check current status")
        print()
        print("Examples:")
        print("  python migrate_settled_unsettled_wallet.py migrate")
        print("  python migrate_settled_unsettled_wallet.py status")
        print()
        sys.exit(0)
