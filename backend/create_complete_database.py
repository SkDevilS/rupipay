"""
Complete Database Creation Script
Creates entire database from scratch with all tables, indexes, and initial data
Run this script to set up a fresh MoneyOne database
"""

import pymysql
import bcrypt
import secrets
import hashlib
from config import Config

def create_complete_database():
    """Create complete database with all tables and initial data"""
    try:
        print("=" * 80)
        print("MoneyOne Complete Database Creation")
        print("=" * 80)
        print()
        
        # Step 1: Connect to MySQL server (without database)
        print("Step 1: Connecting to MySQL server...")
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Step 2: Create database if not exists
            print("Step 2: Creating database...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {Config.DB_NAME}")
            connection.commit()
            print(f"✅ Database '{Config.DB_NAME}' created/verified")
            print()
            
            # Step 3: Create admin_users table
            print("Step 3: Creating admin_users table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    admin_id VARCHAR(50) PRIMARY KEY,
                    password_hash VARCHAR(255) NOT NULL,
                    pin_hash VARCHAR(255) DEFAULT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    must_change_password BOOLEAN DEFAULT FALSE,
                    login_attempts INT DEFAULT 0,
                    locked_until DATETIME DEFAULT NULL,
                    last_login DATETIME DEFAULT NULL,
                    password_changed_at DATETIME DEFAULT NULL,
                    pin_changed_at DATETIME DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_is_active (is_active),
                    INDEX idx_last_login (last_login)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ admin_users table created")
            
            # Step 4: Create admin_activity_logs table
            print("Step 4: Creating admin_activity_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_activity_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE,
                    INDEX idx_admin_id (admin_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_action (action)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ admin_activity_logs table created")
            
            # Step 5: Create commercial_schemes table
            print("Step 5: Creating commercial_schemes table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commercial_schemes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    scheme_name VARCHAR(100) NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
                    INDEX idx_is_active (is_active),
                    INDEX idx_scheme_name (scheme_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ commercial_schemes table created")
            
            # Step 6: Create commercial_charges table
            print("Step 6: Creating commercial_charges table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commercial_charges (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    scheme_id INT NOT NULL,
                    service_type ENUM('PAYIN', 'PAYOUT') NOT NULL,
                    product_name VARCHAR(100) NOT NULL,
                    min_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    max_amount DECIMAL(15, 2) NOT NULL,
                    charge_value DECIMAL(10, 2) NOT NULL,
                    charge_type ENUM('FIXED', 'PERCENTAGE') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (scheme_id) REFERENCES commercial_schemes(id) ON DELETE CASCADE,
                    INDEX idx_scheme_service (scheme_id, service_type),
                    INDEX idx_product (product_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ commercial_charges table created")
            
            # Step 7: Create merchants table
            print("Step 7: Creating merchants table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchants (
                    merchant_id VARCHAR(50) PRIMARY KEY,
                    password_hash VARCHAR(255) NOT NULL,
                    pin_hash VARCHAR(255) DEFAULT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    mobile VARCHAR(15) NOT NULL,
                    aadhar_card VARCHAR(12) NOT NULL,
                    pan_no VARCHAR(10) NOT NULL,
                    pincode VARCHAR(10) NOT NULL,
                    state VARCHAR(100) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    address TEXT NOT NULL,
                    merchant_type ENUM('PAYIN', 'PAYOUT', 'BOTH') NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(11) NOT NULL,
                    gst_no VARCHAR(15),
                    scheme_id INT NOT NULL,
                    authorization_key VARCHAR(255) NOT NULL UNIQUE,
                    module_secret VARCHAR(255) NOT NULL UNIQUE,
                    aes_key VARCHAR(255) NOT NULL,
                    aes_iv VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    last_login DATETIME DEFAULT NULL,
                    password_changed_at DATETIME DEFAULT NULL,
                    pin_changed_at DATETIME DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (scheme_id) REFERENCES commercial_schemes(id),
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
                    INDEX idx_email (email),
                    INDEX idx_mobile (mobile),
                    INDEX idx_is_active (is_active),
                    INDEX idx_merchant_type (merchant_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchants table created")

            
            # Step 8: Create merchant_documents table
            print("Step 8: Creating merchant_documents table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL UNIQUE,
                    aadhar_front_path VARCHAR(500),
                    aadhar_back_path VARCHAR(500),
                    pan_card_path VARCHAR(500),
                    gst_certificate_path VARCHAR(500),
                    cancelled_cheque_path VARCHAR(500),
                    shop_photo_path VARCHAR(500),
                    profile_photo_path VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_documents table created")
            
            # Step 9: Create merchant_ip_whitelist table
            print("Step 9: Creating merchant_ip_whitelist table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_ip_whitelist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_merchant_ip (merchant_id, ip_address),
                    INDEX idx_merchant_id (merchant_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_ip_whitelist table created")
            
            # Step 10: Create merchant_callbacks table
            print("Step 10: Creating merchant_callbacks table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_callbacks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL UNIQUE,
                    payin_callback_url VARCHAR(500),
                    payout_callback_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_callbacks table created")
            
            # Step 11: Create merchant_banks table
            print("Step 11: Creating merchant_banks table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_banks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    bank_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(11) NOT NULL,
                    account_holder_name VARCHAR(255) NOT NULL,
                    account_type ENUM('SAVINGS', 'CURRENT') NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_banks table created")
            
            # Step 12: Create admin_banks table
            print("Step 12: Creating admin_banks table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_banks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bank_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(11) NOT NULL,
                    account_holder_name VARCHAR(255) NOT NULL,
                    account_type ENUM('SAVINGS', 'CURRENT') NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ admin_banks table created")
            
            # Step 13: Create payin_transactions table
            print("Step 13: Creating payin_transactions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payin_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    txn_id VARCHAR(100) NOT NULL UNIQUE,
                    merchant_id VARCHAR(50) NOT NULL,
                    merchant_order_id VARCHAR(100) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    customer_name VARCHAR(255) NOT NULL,
                    customer_email VARCHAR(255) NOT NULL,
                    customer_mobile VARCHAR(15) NOT NULL,
                    product_info VARCHAR(500),
                    udf1 VARCHAR(255),
                    udf2 VARCHAR(255),
                    udf3 VARCHAR(255),
                    udf4 VARCHAR(255),
                    udf5 VARCHAR(255),
                    status ENUM('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED') DEFAULT 'PENDING',
                    payment_mode VARCHAR(50),
                    pg_txn_id VARCHAR(100),
                    pg_response TEXT,
                    callback_sent BOOLEAN DEFAULT FALSE,
                    callback_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_merchant_order_id (merchant_order_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ payin_transactions table created")

            
            # Step 14: Create payout_transactions table
            print("Step 14: Creating payout_transactions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payout_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    txn_id VARCHAR(100) NOT NULL UNIQUE,
                    merchant_id VARCHAR(50) NOT NULL,
                    merchant_order_id VARCHAR(100) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    beneficiary_name VARCHAR(255) NOT NULL,
                    beneficiary_account VARCHAR(50) NOT NULL,
                    beneficiary_ifsc VARCHAR(11) NOT NULL,
                    beneficiary_mobile VARCHAR(15),
                    beneficiary_email VARCHAR(255),
                    transfer_mode ENUM('IMPS', 'NEFT', 'RTGS', 'UPI') NOT NULL,
                    purpose VARCHAR(500),
                    status ENUM('PENDING', 'QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED') DEFAULT 'PENDING',
                    pg_txn_id VARCHAR(100),
                    pg_response TEXT,
                    utr_number VARCHAR(100),
                    callback_sent BOOLEAN DEFAULT FALSE,
                    callback_response TEXT,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_merchant_order_id (merchant_order_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ payout_transactions table created")
            
            # Step 15: Create merchant_wallet table
            print("Step 15: Creating merchant_wallet table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL UNIQUE,
                    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_balance (balance)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_wallet table created")
            
            # Step 16: Create merchant_unsettled_wallet table
            print("Step 16: Creating merchant_unsettled_wallet table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_unsettled_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL UNIQUE,
                    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_balance (balance)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ merchant_unsettled_wallet table created")
            
            # Step 17: Create admin_wallet table
            print("Step 17: Creating admin_wallet table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL UNIQUE,
                    main_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    unsettled_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE,
                    INDEX idx_main_balance (main_balance)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ admin_wallet table created")
            
            # Step 18: Create wallet_transactions table
            print("Step 18: Creating wallet_transactions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    transaction_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    balance_before DECIMAL(15, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description TEXT NOT NULL,
                    reference_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_transaction_type (transaction_type),
                    INDEX idx_created_at (created_at),
                    INDEX idx_reference_id (reference_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ wallet_transactions table created")
            
            # Step 19: Create admin_wallet_transactions table
            print("Step 19: Creating admin_wallet_transactions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL,
                    transaction_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    balance_before DECIMAL(15, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description TEXT NOT NULL,
                    reference_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE,
                    INDEX idx_admin_id (admin_id),
                    INDEX idx_transaction_type (transaction_type),
                    INDEX idx_created_at (created_at),
                    INDEX idx_reference_id (reference_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ admin_wallet_transactions table created")

            
            # Step 20: Create fund_requests table
            print("Step 20: Creating fund_requests table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id VARCHAR(100) NOT NULL UNIQUE,
                    merchant_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    bank_id INT NOT NULL,
                    utr_number VARCHAR(100) NOT NULL,
                    deposit_date DATE NOT NULL,
                    deposit_slip_path VARCHAR(500),
                    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
                    admin_remarks TEXT,
                    processed_by VARCHAR(50),
                    processed_at DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    FOREIGN KEY (bank_id) REFERENCES admin_banks(id),
                    FOREIGN KEY (processed_by) REFERENCES admin_users(admin_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ fund_requests table created")
            
            # Step 21: Create service_routing table
            print("Step 21: Creating service_routing table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_routing (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    service_type ENUM('PAYIN', 'PAYOUT') NOT NULL,
                    routing_type ENUM('MERCHANT', 'GLOBAL') NOT NULL,
                    merchant_id VARCHAR(50),
                    pg_partner VARCHAR(100) NOT NULL,
                    priority INT NOT NULL DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
                    INDEX idx_service_routing (service_type, routing_type),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ service_routing table created")
            
            # Step 22: Create callback_logs table
            print("Step 22: Creating callback_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS callback_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    transaction_id VARCHAR(100) NOT NULL,
                    transaction_type ENUM('PAYIN', 'PAYOUT') NOT NULL,
                    callback_url VARCHAR(500) NOT NULL,
                    request_payload TEXT,
                    response_status INT,
                    response_body TEXT,
                    attempt_number INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_transaction_id (transaction_id),
                    INDEX idx_transaction_type (transaction_type),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ callback_logs table created")
            
            # Step 23: Create payu_webhook_config table
            print("Step 23: Creating payu_webhook_config table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_webhook_config (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    webhook_url VARCHAR(500) NOT NULL,
                    secret_key VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ payu_webhook_config table created")
            
            # Step 24: Create payu_webhook_logs table
            print("Step 24: Creating payu_webhook_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_webhook_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    payload TEXT NOT NULL,
                    signature VARCHAR(500),
                    is_verified BOOLEAN DEFAULT FALSE,
                    processed BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_event_type (event_type),
                    INDEX idx_processed (processed),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ payu_webhook_logs table created")
            
            # Step 25: Create payu_tokens table
            print("Step 25: Creating payu_tokens table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    token_type VARCHAR(50) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ payu_tokens table created")
            
            connection.commit()
            print()
            print("=" * 80)
            print("All 25 tables created successfully!")
            print("=" * 80)
            print()

        connection.close()
        
        print("Step 26: Inserting initial data...")
        print()
        
        # Import and run initial data insertion
        from insert_initial_data import insert_initial_data
        if insert_initial_data():
            print()
            print("=" * 80)
            print("✅ DATABASE SETUP COMPLETE!")
            print("=" * 80)
            print()
            print("Your MoneyOne database is ready to use!")
            print()
            print("Next steps:")
            print("  1. Login to admin dashboard with provided credentials")
            print("  2. Change admin password immediately")
            print("  3. Configure PayU credentials in .env file")
            print("  4. Start the backend API: python app.py")
            print("  5. Access admin panel: https://admin.moneyone.co.in")
            print()
            print("=" * 80)
            return True
        else:
            print("\n❌ Initial data insertion failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Database creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_complete_database()
    exit(0 if success else 1)
