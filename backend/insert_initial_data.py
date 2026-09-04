"""
Insert Initial Data Script
Part 2 of database setup - inserts initial data after tables are created
"""

import pymysql
import bcrypt
import secrets
import hashlib
from config import Config

def insert_initial_data():
    """Insert initial data into database"""
    try:
        print("=" * 80)
        print("Inserting Initial Data")
        print("=" * 80)
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
            # Step 1: Create admin user
            print("Step 1: Creating admin user...")
            admin_id = "6239572985"
            password = "Admin@123"
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
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
            print("✅ Admin wallet created (Balance: ₹100,000)")
            print()
            
            # Step 3: Create default commercial scheme
            print("Step 3: Creating default commercial scheme...")
            cursor.execute("""
                INSERT INTO commercial_schemes (scheme_name, is_active, created_by)
                VALUES ('Default Scheme', TRUE, %s)
                ON DUPLICATE KEY UPDATE scheme_name = scheme_name
            """, (admin_id,))
            connection.commit()
            
            cursor.execute("SELECT id FROM commercial_schemes WHERE scheme_name = 'Default Scheme'")
            scheme = cursor.fetchone()
            scheme_id = scheme['id']
            print(f"✅ Default scheme created (ID: {scheme_id})")
            print()
            
            # Step 4: Add default payout charges
            print("Step 4: Adding default payout charges...")
            payout_charges = [
                (scheme_id, 'PAYOUT', 'IMPS', 0.00, 25000.00, 5.00, 'FIXED'),
                (scheme_id, 'PAYOUT', 'NEFT', 0.00, 200000.00, 3.00, 'FIXED'),
                (scheme_id, 'PAYOUT', 'RTGS', 200000.00, 10000000.00, 25.00, 'FIXED'),
                (scheme_id, 'PAYOUT', 'UPI', 0.00, 100000.00, 2.00, 'FIXED')
            ]
            
            for charge in payout_charges:
                cursor.execute("""
                    INSERT INTO commercial_charges 
                    (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE charge_value = charge_value
                """, charge)
            connection.commit()
            print("✅ Payout charges added (IMPS, NEFT, RTGS, UPI)")
            print()
            
            # Step 5: Add default payin charges
            print("Step 5: Adding default payin charges...")
            payin_charges = [
                (scheme_id, 'PAYIN', 'UPI', 0.00, 100000.00, 2.00, 'PERCENTAGE'),
                (scheme_id, 'PAYIN', 'Card', 0.00, 200000.00, 2.50, 'PERCENTAGE'),
                (scheme_id, 'PAYIN', 'Net Banking', 0.00, 200000.00, 1.50, 'PERCENTAGE')
            ]
            
            for charge in payin_charges:
                cursor.execute("""
                    INSERT INTO commercial_charges 
                    (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE charge_value = charge_value
                """, charge)
            connection.commit()
            print("✅ Payin charges added (UPI, Card, Net Banking)")
            print()

            
            # Step 6: Create test merchant (optional)
            print("Step 6: Creating test merchant...")
            test_merchant_id = "TEST001"
            test_password = "Test@123"
            test_password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Generate credentials
            authorization_key = 'mk_live_' + secrets.token_hex(28)
            module_secret = 'sk_live_' + secrets.token_hex(12)
            aes_key = secrets.token_hex(13)
            aes_iv = secrets.token_urlsafe(12)[:16]
            
            cursor.execute("""
                INSERT INTO merchants (
                    merchant_id, password_hash, full_name, email, mobile,
                    aadhar_card, pan_no, pincode, state, city, address,
                    merchant_type, account_number, ifsc_code, gst_no,
                    scheme_id, authorization_key, module_secret, aes_key, aes_iv,
                    is_active, created_by
                ) VALUES (
                    %s, %s, 'Test Merchant', 'test@moneyone.co.in', '9876543210',
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
            print(f"✅ Test merchant created (ID: {test_merchant_id})")
            print()
            
            # Step 7: Create merchant wallets
            print("Step 7: Creating merchant wallets...")
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
            
            # Step 8: Create merchant documents entry
            print("Step 8: Creating merchant documents entry...")
            cursor.execute("""
                INSERT INTO merchant_documents (merchant_id)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE merchant_id = merchant_id
            """, (test_merchant_id,))
            connection.commit()
            print("✅ Merchant documents entry created")
            print()
            
            # Step 9: Create merchant callbacks entry
            print("Step 9: Creating merchant callbacks entry...")
            cursor.execute("""
                INSERT INTO merchant_callbacks (merchant_id)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE merchant_id = merchant_id
            """, (test_merchant_id,))
            connection.commit()
            print("✅ Merchant callbacks entry created")
            print()
            
        connection.close()
        
        # Print summary
        print("=" * 80)
        print("Initial Data Inserted Successfully!")
        print("=" * 80)
        print()
        print("ADMIN CREDENTIALS:")
        print(f"  Admin ID: {admin_id}")
        print(f"  Password: {password}")
        print(f"  Wallet Balance: ₹100,000")
        print()
        print("TEST MERCHANT CREDENTIALS:")
        print(f"  Merchant ID: {test_merchant_id}")
        print(f"  Password: {test_password}")
        print(f"  Wallet Balance: ₹50,000")
        print(f"  Authorization Key: {authorization_key}")
        print(f"  Module Secret: {module_secret}")
        print()
        print("COMMERCIAL SCHEME:")
        print(f"  Scheme ID: {scheme_id}")
        print(f"  Scheme Name: Default Scheme")
        print()
        print("PAYOUT CHARGES:")
        print("  IMPS: ₹5.00 (Fixed)")
        print("  NEFT: ₹3.00 (Fixed)")
        print("  RTGS: ₹25.00 (Fixed)")
        print("  UPI: ₹2.00 (Fixed)")
        print()
        print("PAYIN CHARGES:")
        print("  UPI: 2.00% (Percentage)")
        print("  Card: 2.50% (Percentage)")
        print("  Net Banking: 1.50% (Percentage)")
        print()
        print("=" * 80)
        print("⚠️  IMPORTANT: Change admin password after first login!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Data insertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    insert_initial_data()
