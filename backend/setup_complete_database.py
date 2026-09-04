"""
Complete Database Setup Script
Sets up all tables, default data, and configurations
"""

import pymysql
import bcrypt
from config import Config
from database import init_database

def setup_complete_database():
    """Complete database setup with all required data"""
    try:
        print("=" * 60)
        print("Complete Database Setup")
        print("=" * 60)
        print()
        
        # Step 1: Initialize database and create all tables
        print("Step 1: Initializing database and creating tables...")
        init_database()
        print("✅ Database initialized")
        print()
        
        # Step 2: Connect to database
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Step 3: Create/Update admin user FIRST (required for foreign key)
            print("Step 2: Setting up admin user...")
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
            print(f"✅ Admin user created/updated (ID: {admin_id})")
            print()
            
            # Step 4: Create admin wallet
            print("Step 3: Setting up admin wallet...")
            cursor.execute("""
                INSERT INTO admin_wallet (admin_id, main_balance, unsettled_balance)
                VALUES (%s, 100000.00, 0.00)
                ON DUPLICATE KEY UPDATE admin_id = admin_id
            """, (admin_id,))
            connection.commit()
            print("✅ Admin wallet created (Balance: ₹100,000)")
            print()
            
            # Step 5: Create default commercial scheme (NOW admin user exists)
            print("Step 4: Creating default commercial scheme...")
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
            
            # Step 6: Add default charges for PAYOUT
            print("Step 5: Adding default payout charges...")
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
            print("✅ Default payout charges added")
            print()
            
            # Step 7: Add default charges for PAYIN
            print("Step 6: Adding default payin charges...")
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
            print("✅ Default payin charges added")
            print()
            
            # Step 8: Create a test merchant with the default scheme
            print("Step 7: Creating test merchant...")
            test_merchant_id = "TEST001"
            test_password_hash = bcrypt.hashpw("Test@123".encode('utf-8'), bcrypt.gensalt())
            
            # Generate required keys
            import secrets
            import hashlib
            
            authorization_key = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
            module_secret = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
            aes_key = secrets.token_hex(16)
            aes_iv = secrets.token_hex(8)
            
            cursor.execute("""
                INSERT INTO merchants (
                    merchant_id, password_hash, full_name, email, mobile,
                    aadhar_card, pan_no, pincode, state, city, address,
                    merchant_type, account_number, ifsc_code, gst_no,
                    scheme_id, authorization_key, module_secret, aes_key, aes_iv,
                    is_active, created_by
                ) VALUES (
                    %s, %s, 'Test Merchant', 'test@example.com', '9876543210',
                    '123456789012', 'ABCDE1234F', '110001', 'Delhi', 'New Delhi', 'Test Address',
                    'BOTH', '1234567890', 'HDFC0001234', '29ABCDE1234F1Z5',
                    %s, %s, %s, %s, %s,
                    TRUE, %s
                )
                ON DUPLICATE KEY UPDATE scheme_id = %s
            """, (
                test_merchant_id, test_password_hash, scheme_id,
                authorization_key, module_secret, aes_key, aes_iv,
                admin_id, scheme_id
            ))
            connection.commit()
            print(f"✅ Test merchant created (ID: {test_merchant_id}, Password: Test@123)")
            print()
            
            # Step 9: Create merchant wallet
            print("Step 8: Setting up merchant wallet...")
            cursor.execute("""
                INSERT INTO merchant_wallet (merchant_id, balance)
                VALUES (%s, 50000.00)
                ON DUPLICATE KEY UPDATE merchant_id = merchant_id
            """, (test_merchant_id,))
            
            cursor.execute("""
                INSERT INTO merchant_unsettled_wallet (merchant_id, balance)
                VALUES (%s, 0.00)
                ON DUPLICATE KEY UPDATE merchant_id = merchant_id
            """, (test_merchant_id,))
            connection.commit()
            print("✅ Merchant wallets created (Balance: ₹50,000)")
            print()
            
            # Step 10: Verify all tables
            print("Step 9: Verifying all tables...")
            required_tables = [
                'admin_users', 'admin_activity_logs', 'commercial_schemes',
                'commercial_charges', 'merchants', 'merchant_documents',
                'merchant_ip_whitelist', 'merchant_callbacks', 'merchant_banks',
                'admin_banks', 'payin_transactions', 'merchant_wallet',
                'wallet_transactions', 'callback_logs', 'service_routing',
                'payout_transactions', 'fund_requests', 'merchant_unsettled_wallet',
                'admin_wallet', 'admin_wallet_transactions', 'payu_webhook_config',
                'payu_webhook_logs', 'payu_tokens'
            ]
            
            all_exist = True
            for table in required_tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if not cursor.fetchone():
                    print(f"❌ Table '{table}' missing")
                    all_exist = False
            
            if all_exist:
                print(f"✅ All {len(required_tables)} tables verified")
            print()
            
        connection.close()
        
        # Summary
        print("=" * 60)
        print("Database Setup Complete!")
        print("=" * 60)
        print()
        print("Admin Login Credentials:")
        print(f"  Admin ID: {admin_id}")
        print(f"  Password: {password}")
        print(f"  Wallet Balance: ₹100,000")
        print()
        print("Test Merchant Credentials:")
        print(f"  Merchant ID: {test_merchant_id}")
        print(f"  Password: Test@123")
        print(f"  Wallet Balance: ₹50,000")
        print()
        print("Default Commercial Scheme:")
        print(f"  Scheme ID: {scheme_id}")
        print(f"  Scheme Name: Default Scheme")
        print()
        print("Payout Charges:")
        print("  IMPS: ₹5.00 (Fixed)")
        print("  NEFT: ₹3.00 (Fixed)")
        print("  RTGS: ₹25.00 (Fixed)")
        print("  UPI: ₹2.00 (Fixed)")
        print()
        print("Payin Charges:")
        print("  UPI: 2.00% (Percentage)")
        print("  Card: 2.50% (Percentage)")
        print("  Net Banking: 1.50% (Percentage)")
        print()
        print("=" * 60)
        print("You can now:")
        print("  1. Login to admin panel")
        print("  2. Create payouts")
        print("  3. Manage merchants")
        print("  4. Configure service routing")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_complete_database()
