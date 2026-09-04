"""
Create Admin User Script
Creates a new admin user with specified credentials
"""

import pymysql
import bcrypt
from config import Config

def create_admin_user(admin_id, password):
    """Create a new admin user"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check if admin already exists
            cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = %s", (admin_id,))
            existing_admin = cursor.fetchone()
            
            if existing_admin:
                print(f"⚠️  Admin user '{admin_id}' already exists!")
                print("Updating password...")
                
                # Update existing admin password
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("""
                    UPDATE admin_users 
                    SET password_hash = %s, 
                        is_active = TRUE,
                        must_change_password = FALSE,
                        login_attempts = 0,
                        locked_until = NULL
                    WHERE admin_id = %s
                """, (password_hash, admin_id))
                
                connection.commit()
                print(f"✅ Admin user '{admin_id}' password updated!")
            else:
                # Create new admin user
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                cursor.execute("""
                    INSERT INTO admin_users (admin_id, password_hash, is_active, must_change_password)
                    VALUES (%s, %s, %s, %s)
                """, (admin_id, password_hash, True, False))
                
                connection.commit()
                print(f"✅ Admin user '{admin_id}' created successfully!")
            
            # Create admin wallet if it doesn't exist
            cursor.execute("SELECT * FROM admin_wallet WHERE admin_id = %s", (admin_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                cursor.execute("""
                    INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00)
                """, (admin_id,))
                connection.commit()
                print(f"✅ Admin wallet created for '{admin_id}'")
            
            print()
            print("=" * 60)
            print("Admin User Details")
            print("=" * 60)
            print(f"  Admin ID: {admin_id}")
            print(f"  Password: {password}")
            print(f"  Status: Active")
            print("=" * 60)
            print()
            print("You can now login to the admin panel with these credentials.")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False

if __name__ == "__main__":
    # Create admin user with ID 6239572985 and password Admin@123
    admin_id = "6239572985"
    password = "Admin@123"
    
    print("=" * 60)
    print("Creating Admin User")
    print("=" * 60)
    print()
    
    create_admin_user(admin_id, password)
