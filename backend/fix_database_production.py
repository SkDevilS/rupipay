"""
Quick Fix Script for Production Database Setup
Run this on production server to fix the foreign key constraint issue
"""

import pymysql
import bcrypt
from config import Config

def fix_database():
    """Fix database by creating admin user first, then commercial scheme"""
    try:
        print("=" * 60)
        print("Production Database Fix")
        print("=" * 60)
        print()
        
        # Connect to database
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Step 1: Create admin user FIRST
            print("Step 1: Creating admin user...")
            admin_id = "6239572985"
            password = "Admin@123"
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            cursor.execute("""
                INSERT INTO admin_users (admin_id, password_hash, is_active, must_change_password)
                VALUES (%s, %s, TRUE, FALSE)
                ON DUPLICATE KEY UPDATE 
                    password_hash = %s,
                    is_active = TRUE,
                    must_change_password = FALSE,
                    login_attempts = 0,
                    locked_until = NULL
            """, (admin_id, password_hash, password_hash))
            connection.commit()
            print(f"✅ Admin user created (ID: {admin_id})")
            print()
            
            # Step 2: Create admin wallet
            print("Step 2: Creating admin wallet...")
            cursor.execute("""
                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                VALUES (%s, 100000.00, 0.00)
                ON DUPLICATE KEY UPDATE admin_id = admin_id
            """, (admin_id,))
            connection.commit()
            print("✅ Admin wallet created")
            print()
            
            # Step 3: Now create commercial scheme (admin user exists)
            print("Step 3: Creating default commercial scheme...")
            cursor.execute("""
                INSERT INTO commercial_schemes (scheme_name, is_active, created_by)
                VALUES ('Default Scheme', TRUE, %s)
                ON DUPLICATE KEY UPDATE scheme_name = scheme_name
            """, (admin_id,))
            connection.commit()
            
            # Get scheme ID
            cursor.execute("SELECT id FROM commercial_schemes WHERE scheme_name = 'Default Scheme'")
            scheme = cursor.fetchone()
            scheme_id = scheme['id']
            print(f"✅ Default scheme created (ID: {scheme_id})")
            print()
            
            # Step 4: Add default payout charges
            print("Step 4: Adding default payout charges...")
            cursor.execute("""
                INSERT INTO commercial_charges 
                (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type)
                VALUES 
                (%s, 'PAYOUT', 'IMPS', 0.00, 25000.00, 5.00, 'FIXED'),
                (%s, 'PAYOUT', 'NEFT', 0.00, 200000.00, 3.00, 'FIXED'),
                (%s, 'PAYOUT', 'RTGS', 200000.00, 10000000.00, 25.00, 'FIXED'),
                (%s, 'PAYOUT', 'UPI', 0.00, 100000.00, 2.00, 'FIXED')
                ON DUPLICATE KEY UPDATE charge_value = charge_value
            """, (scheme_id, scheme_id, scheme_id, scheme_id))
            connection.commit()
            print("✅ Payout charges added")
            print()
            
            # Step 5: Add default payin charges
            print("Step 5: Adding default payin charges...")
            cursor.execute("""
                INSERT INTO commercial_charges 
                (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type)
                VALUES 
                (%s, 'PAYIN', 'UPI', 0.00, 100000.00, 2.00, 'PERCENTAGE'),
                (%s, 'PAYIN', 'Card', 0.00, 200000.00, 2.50, 'PERCENTAGE'),
                (%s, 'PAYIN', 'Net Banking', 0.00, 200000.00, 1.50, 'PERCENTAGE')
                ON DUPLICATE KEY UPDATE charge_value = charge_value
            """, (scheme_id, scheme_id, scheme_id))
            connection.commit()
            print("✅ Payin charges added")
            print()
            
        connection.close()
        
        print("=" * 60)
        print("Database Fix Complete!")
        print("=" * 60)
        print()
        print("Admin Credentials:")
        print(f"  Admin ID: {admin_id}")
        print(f"  Password: {password}")
        print()
        print("You can now run: python setup_complete_database.py")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_database()
