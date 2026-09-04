#!/usr/bin/env python3
"""
IP Security Tables Setup Script
Automatically creates IP security tables in RDS database using credentials from config.py
"""

import sys
import pymysql
from config import Config

def get_column_type(cursor, table_name, column_name):
    """Get the exact column type from a table"""
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    for col in columns:
        if col['Field'] == column_name:
            return col['Type']
    return None

def get_table_charset_collation(cursor, table_name):
    """Get the character set and collation of a table"""
    cursor.execute(f"SHOW CREATE TABLE {table_name}")
    result = cursor.fetchone()
    create_statement = list(result.values())[1]
    
    charset = None
    collation = None
    
    # Extract character set
    if 'CHARSET=' in create_statement:
        charset = create_statement.split('CHARSET=')[1].split()[0]
    elif 'CHARACTER SET ' in create_statement:
        charset = create_statement.split('CHARACTER SET ')[1].split()[0]
    
    # Extract collation
    if 'COLLATE=' in create_statement:
        collation = create_statement.split('COLLATE=')[1].split()[0]
    elif 'COLLATE ' in create_statement:
        collation = create_statement.split('COLLATE ')[1].split()[0]
    
    return charset, collation

def create_ip_security_tables():
    """Create IP security tables in the database"""
    
    print("=" * 60)
    print("IP Security Tables Setup")
    print("=" * 60)
    print()
    
    # Display connection info (without password)
    print(f"Database Host: {Config.DB_HOST}")
    print(f"Database Name: {Config.DB_NAME}")
    print(f"Database User: {Config.DB_USER}")
    print()
    
    try:
        # Connect to database
        print("Connecting to database...")
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✓ Connected successfully")
        print()
        
        with connection.cursor() as cursor:
            # Get actual column types from parent tables
            print("Detecting column types from parent tables...")
            merchant_id_type = get_column_type(cursor, 'merchants', 'merchant_id')
            admin_id_type = get_column_type(cursor, 'admin_users', 'admin_id')
            
            print(f"✓ merchants.merchant_id type: {merchant_id_type}")
            print(f"✓ admin_users.admin_id type: {admin_id_type}")
            
            # Get character set and collation from parent tables
            print("\nDetecting character set and collation...")
            merchant_charset, merchant_collation = get_table_charset_collation(cursor, 'merchants')
            admin_charset, admin_collation = get_table_charset_collation(cursor, 'admin_users')
            
            # Use merchants table charset/collation as primary (since it's the main foreign key)
            table_charset = merchant_charset or 'utf8mb4'
            table_collation = merchant_collation or 'utf8mb4_unicode_ci'
            
            print(f"✓ Using Character Set: {table_charset}")
            print(f"✓ Using Collation: {table_collation}")
            print()
            
            # Check if tables already exist
            print("Checking existing tables...")
            cursor.execute("SHOW TABLES LIKE 'merchant_ip_security'")
            ip_security_exists = cursor.fetchone()
            
            cursor.execute("SHOW TABLES LIKE 'ip_security_logs'")
            ip_logs_exists = cursor.fetchone()
            
            if ip_security_exists and ip_logs_exists:
                print("⚠ Tables already exist!")
                print()
                response = input("Do you want to drop and recreate them? (yes/no): ").lower()
                if response != 'yes':
                    print("Aborted. No changes made.")
                    return
                
                print()
                print("Dropping existing tables...")
                cursor.execute("DROP TABLE IF EXISTS ip_security_logs")
                print("✓ Dropped ip_security_logs")
                cursor.execute("DROP TABLE IF EXISTS merchant_ip_security")
                print("✓ Dropped merchant_ip_security")
                print()
            
            # Create merchant_ip_security table with correct column types and charset/collation
            print("Creating merchant_ip_security table...")
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS merchant_ip_security (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id {merchant_id_type} NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    description VARCHAR(255) DEFAULT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by {admin_id_type} NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
                    UNIQUE KEY unique_merchant_ip (merchant_id, ip_address)
                ) ENGINE=InnoDB DEFAULT CHARSET={table_charset} COLLATE={table_collation}
            """
            cursor.execute(create_table_sql)
            print("✓ Created merchant_ip_security table")
            
            # Create index for merchant_ip_security
            print("Creating index on merchant_ip_security...")
            cursor.execute("""
                CREATE INDEX idx_merchant_ip_active 
                ON merchant_ip_security(merchant_id, ip_address, is_active)
            """)
            print("✓ Created index idx_merchant_ip_active")
            
            # Create ip_security_logs table with correct column type and charset/collation
            print("Creating ip_security_logs table...")
            create_logs_sql = f"""
                CREATE TABLE IF NOT EXISTS ip_security_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id {merchant_id_type} NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    endpoint VARCHAR(255) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    status ENUM('ALLOWED', 'BLOCKED') NOT NULL,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET={table_charset} COLLATE={table_collation}
            """
            cursor.execute(create_logs_sql)
            print("✓ Created ip_security_logs table")
            
            # Create indexes for ip_security_logs
            print("Creating indexes on ip_security_logs...")
            cursor.execute("""
                CREATE INDEX idx_ip_logs_merchant 
                ON ip_security_logs(merchant_id, created_at DESC)
            """)
            print("✓ Created index idx_ip_logs_merchant")
            
            cursor.execute("""
                CREATE INDEX idx_ip_logs_status 
                ON ip_security_logs(status, created_at DESC)
            """)
            print("✓ Created index idx_ip_logs_status")
            
            # Commit changes
            connection.commit()
            print()
            print("=" * 60)
            print("✓ All tables and indexes created successfully!")
            print("=" * 60)
            print()
            
            # Verify tables
            print("Verifying tables...")
            cursor.execute("SHOW TABLES LIKE '%ip_security%'")
            tables = cursor.fetchall()
            print(f"Found {len(tables)} tables:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"  - {table_name}")
            print()
            
            # Show table structures
            print("Table Structures:")
            print("-" * 60)
            
            print("\n1. merchant_ip_security:")
            cursor.execute("DESCRIBE merchant_ip_security")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   {col['Field']:20} {col['Type']:20} {col['Null']:5} {col['Key']:5}")
            
            print("\n2. ip_security_logs:")
            cursor.execute("DESCRIBE ip_security_logs")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   {col['Field']:20} {col['Type']:20} {col['Null']:5} {col['Key']:5}")
            
            print()
            print("=" * 60)
            print("Setup Complete!")
            print("=" * 60)
            print()
            print("Next Steps:")
            print("1. Deploy backend code with IP security routes")
            print("2. Deploy frontend with IP Security page")
            print("3. Test IP whitelisting functionality")
            print()
            
    except pymysql.err.OperationalError as e:
        print(f"✗ Database connection error: {e}")
        print()
        print("Please check:")
        print("1. Database credentials in backend/.env")
        print("2. RDS security group allows your IP")
        print("3. Database is running and accessible")
        sys.exit(1)
        
    except pymysql.err.ProgrammingError as e:
        print(f"✗ SQL error: {e}")
        print()
        print("This might be due to:")
        print("1. Foreign key constraints (parent tables don't exist)")
        print("2. Syntax error in SQL")
        print("3. Insufficient permissions")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("Database connection closed.")

def verify_parent_tables():
    """Verify that parent tables (merchants, admin_users) exist"""
    
    print("Verifying parent tables...")
    
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check merchants table
            cursor.execute("SHOW TABLES LIKE 'merchants'")
            merchants_exists = cursor.fetchone()
            
            # Check admin_users table
            cursor.execute("SHOW TABLES LIKE 'admin_users'")
            admin_users_exists = cursor.fetchone()
            
            if not merchants_exists:
                print("✗ Error: 'merchants' table does not exist")
                print("  IP security requires the merchants table for foreign keys")
                return False
            
            if not admin_users_exists:
                print("✗ Error: 'admin_users' table does not exist")
                print("  IP security requires the admin_users table for foreign keys")
                return False
            
            print("✓ Parent tables exist (merchants, admin_users)")
            return True
            
    except Exception as e:
        print(f"✗ Error verifying parent tables: {e}")
        return False
        
    finally:
        if 'connection' in locals() and connection:
            connection.close()

def main():
    """Main execution function"""
    
    print()
    print("This script will create IP security tables in your RDS database")
    print("using credentials from backend/config.py")
    print()
    
    # Verify parent tables first
    if not verify_parent_tables():
        print()
        print("Cannot proceed without parent tables.")
        print("Please ensure your database is properly initialized.")
        sys.exit(1)
    
    print()
    response = input("Do you want to continue? (yes/no): ").lower()
    
    if response != 'yes':
        print("Aborted.")
        sys.exit(0)
    
    print()
    create_ip_security_tables()

if __name__ == "__main__":
    main()
