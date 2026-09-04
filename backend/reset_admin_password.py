"""
Reset Admin Password Script
"""

import pymysql
import bcrypt
from config import Config

def reset_admin_password():
    """Reset admin password to default"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # New password
            password = "Admin@123"
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Update admin password
            cursor.execute("""
                UPDATE admin_users 
                SET password_hash = %s, 
                    must_change_password = FALSE,
                    login_attempts = 0,
                    locked_until = NULL
                WHERE admin_id = 'admin'
            """, (password_hash,))
            
            connection.commit()
            
            print("=" * 60)
            print("Admin Password Reset Successful!")
            print("=" * 60)
            print()
            print("Login Credentials:")
            print(f"  Username: admin")
            print(f"  Password: {password}")
            print()
            print("You can now login to the admin panel.")
            print("=" * 60)
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Password reset failed: {e}")
        return False

if __name__ == "__main__":
    reset_admin_password()
