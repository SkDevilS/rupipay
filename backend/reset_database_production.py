#!/usr/bin/env python3
"""
Reset Production Database and Create Admin User
WARNING: This will DROP and RECREATE the entire database!
"""

import pymysql
import bcrypt
import sys
from database import get_db_connection

# Admin credentials
ADMIN_ID = "6239572985"
ADMIN_PASSWORD = "Admin@123"

def confirm_reset():
    """Ask for confirmation before proceeding"""
    print("\n" + "=" * 70)
    print("⚠️  WARNING: DATABASE RESET")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. DROP the entire moneyone_db database")
    print("  2. CREATE a fresh moneyone_db database")
    print("  3. Import all tables from moneyone_db.sql")
    print("  4. Create admin user with ID: 6239572985")
    print("\n⚠️  ALL EXISTING DATA WILL BE LOST!")
    print("=" * 70)
    
    response = input("\nType 'YES' to continue or anything else to cancel: ")
    return response.strip().upper() == "YES"

def reset_database():
    """Reset database and import schema"""
    
    if not confirm_reset():
        print("\n❌ Database reset cancelled by user")
        return False
    
    print("\n" + "=" * 70)
    print("Starting Database Reset...")
    print("=" * 70)
    
    # Connect to MySQL without selecting a database
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Update if you have a root password
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ Connected to MySQL server")
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        print("\nTry running manually:")
        print("  mysql -u root -p < moneyone_db.sql")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Drop existing database
            print("\n📝 Dropping existing database...")
            cursor.execute("DROP DATABASE IF EXISTS moneyone_db")
            print("✅ Database dropped")
            
            # Create fresh database
            print("\n📝 Creating fresh database...")
            cursor.execute("CREATE DATABASE moneyone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✅ Database created")
            
            # Select the database
            cursor.execute("USE moneyone_db")
            
            # Read and execute SQL file
            print("\n📝 Importing schema from moneyone_db.sql...")
            try:
                with open('moneyone_db.sql', 'r', encoding='utf8') as f:
                    sql_content = f.read()
                    
                # Split by semicolons and execute each statement
                statements = sql_content.split(';')
                executed = 0
                
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                            executed += 1
                        except Exception as e:
                            # Skip errors for statements that might not apply
                            if 'already exists' not in str(e).lower():
                                print(f"  ⚠️  Skipped statement: {str(e)[:100]}")
                
                conn.commit()
                print(f"✅ Executed {executed} SQL statements")
                
            except FileNotFoundError:
                print("❌ moneyone_db.sql file not found!")
                print("   Make sure the file exists in the backend directory")
                conn.close()
                return False
            
            # Create admin user
            print("\n📝 Creating admin user...")
            password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO admin_users (admin_id, password_hash, is_active, must_change_password)
                VALUES (%s, %s, TRUE, FALSE)
                ON DUPLICATE KEY UPDATE 
                    password_hash = VALUES(password_hash),
                    is_active = TRUE,
                    must_change_password = FALSE,
                    login_attempts = 0,
                    locked_until = NULL
            """, (ADMIN_ID, password_hash))
            
            print(f"✅ Admin user created: {ADMIN_ID}")
            
            # Create admin wallet
            print("\n📝 Creating admin wallet...")
            cursor.execute("""
                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                VALUES (%s, 0.00, 0.00)
                ON DUPLICATE KEY UPDATE admin_id = admin_id
            """, (ADMIN_ID,))
            
            print("✅ Admin wallet created")
            
            # Verify tables
            print("\n📝 Verifying tables...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_count = len(tables)
            
            print(f"✅ Found {table_count} tables:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"   - {table_name}")
            
            conn.commit()
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ DATABASE RESET COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nAdmin Login Credentials:")
        print(f"  Admin ID: {ADMIN_ID}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print("\nNext Steps:")
        print("  1. Restart backend: sudo supervisorctl restart moneyone-api")
        print("  2. Login at: https://admin.moneyone.co.in")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during database reset: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
