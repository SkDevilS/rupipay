"""
Database Verification Script
Checks if all required tables exist and creates default admin user
"""

import pymysql
import bcrypt
from config import Config

def verify_database():
    """Verify all database tables exist"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            print("=" * 60)
            print("Database Verification")
            print("=" * 60)
            print()
            
            # List of all required tables
            required_tables = [
                'admin_users',
                'admin_activity_logs',
                'commercial_schemes',
                'commercial_charges',
                'merchants',
                'merchant_documents',
                'merchant_ip_whitelist',
                'merchant_callbacks',
                'merchant_banks',
                'admin_banks',
                'payin_transactions',
                'merchant_wallet',
                'wallet_transactions',
                'callback_logs',
                'service_routing',
                'payout_transactions',
                'fund_requests',
                'merchant_unsettled_wallet',
                'admin_wallet',
                'admin_wallet_transactions',
                'payu_webhook_config',
                'payu_webhook_logs',
                'payu_tokens'
            ]
            
            print("Checking tables...")
            missing_tables = []
            
            for table in required_tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                result = cursor.fetchone()
                if result:
                    print(f"✅ {table}")
                else:
                    print(f"❌ {table} - MISSING")
                    missing_tables.append(table)
            
            print()
            
            if missing_tables:
                print(f"⚠️  {len(missing_tables)} table(s) missing!")
                print("Please run: python database.py")
                return False
            else:
                print(f"✅ All {len(required_tables)} tables exist!")
            
            print()
            print("-" * 60)
            print("Checking default admin user...")
            print()
            
            # Check if admin user exists
            cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = 'admin'")
            admin = cursor.fetchone()
            
            if not admin:
                print("Creating default admin user...")
                # Create default admin user
                password = "Admin@123"
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                cursor.execute("""
                    INSERT INTO admin_users (admin_id, password_hash, is_active)
                    VALUES (%s, %s, %s)
                """, ('admin', password_hash, True))
                
                connection.commit()
                print("✅ Default admin user created")
                print(f"   Username: admin")
                print(f"   Password: {password}")
            else:
                print("✅ Admin user exists")
            
            print()
            print("-" * 60)
            print("Checking admin wallet...")
            print()
            
            # Check if admin wallet exists
            cursor.execute("SELECT * FROM admin_wallet WHERE admin_id = 'admin'")
            wallet = cursor.fetchone()
            
            if not wallet:
                print("Creating admin wallet...")
                cursor.execute("""
                    INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                    VALUES ('admin', 0.00, 0.00)
                """)
                connection.commit()
                print("✅ Admin wallet created")
            else:
                print(f"✅ Admin wallet exists")
                print(f"   Main Balance: ₹{wallet['main_balance']}")
                print(f"   Unsettled Balance: ₹{wallet['unsettled_balance']}")
            
            print()
            print("=" * 60)
            print("Database verification completed!")
            print("=" * 60)
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Database verification failed: {e}")
        return False

if __name__ == "__main__":
    verify_database()
