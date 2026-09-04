#!/usr/bin/env python3
"""
MoneyOne Fresh Database Initialization
Creates all tables and one admin user only
No test data, no merchants, no schemes
"""

import pymysql
import bcrypt
from config import Config

def init_fresh_database():
    """Create all tables and admin user only"""
    try:
        print("=" * 80)
        print("MoneyOne Fresh Database Initialization")
        print("=" * 80)
        print()
        
        # Connect to MySQL server
        print("Connecting to MySQL server...")
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Create database
            print(f"Creating database: {Config.DB_NAME}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {Config.DB_NAME}")
            connection.commit()
            print("✅ Database created/verified")
            print()
            
            # Create all tables
            tables = [
                ("admin_users", """
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
                """),
                
                ("admin_activity_logs", """
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
                """),
                
                ("commercial_schemes", """
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
                """),
                
                ("commercial_charges", """
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
                """),
                
                ("merchants", """
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
                """),

                
                ("merchant_documents", """
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
                """),
                
                ("merchant_ip_whitelist", """
                    CREATE TABLE IF NOT EXISTS merchant_ip_whitelist (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        merchant_id VARCHAR(50) NOT NULL,
                        ip_address VARCHAR(45) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                        UNIQUE KEY unique_merchant_ip (merchant_id, ip_address),
                        INDEX idx_merchant_id (merchant_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("merchant_callbacks", """
                    CREATE TABLE IF NOT EXISTS merchant_callbacks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        merchant_id VARCHAR(50) NOT NULL UNIQUE,
                        payin_callback_url VARCHAR(500),
                        payout_callback_url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("merchant_banks", """
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
                """),

                
                ("admin_banks", """
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
                """),
                
                ("payin_transactions", """
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
                        udf1 VARCHAR(255), udf2 VARCHAR(255), udf3 VARCHAR(255), udf4 VARCHAR(255), udf5 VARCHAR(255),
                        status ENUM('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED') DEFAULT 'PENDING',
                        payment_mode VARCHAR(50),
                        pg_txn_id VARCHAR(100),
                        pg_response TEXT,
                        callback_sent BOOLEAN DEFAULT FALSE,
                        callback_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
                        INDEX idx_merchant_id (merchant_id), INDEX idx_status (status),
                        INDEX idx_created_at (created_at), INDEX idx_merchant_order_id (merchant_order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("payout_transactions", """
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
                        INDEX idx_merchant_id (merchant_id), INDEX idx_status (status),
                        INDEX idx_created_at (created_at), INDEX idx_merchant_order_id (merchant_order_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),

                
                ("merchant_wallet", """
                    CREATE TABLE IF NOT EXISTS merchant_wallet (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        merchant_id VARCHAR(50) NOT NULL UNIQUE,
                        balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                        INDEX idx_balance (balance)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("merchant_unsettled_wallet", """
                    CREATE TABLE IF NOT EXISTS merchant_unsettled_wallet (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        merchant_id VARCHAR(50) NOT NULL UNIQUE,
                        balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                        INDEX idx_balance (balance)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("admin_wallet", """
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
                """),
                
                ("wallet_transactions", """
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
                        INDEX idx_merchant_id (merchant_id), INDEX idx_transaction_type (transaction_type),
                        INDEX idx_created_at (created_at), INDEX idx_reference_id (reference_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("admin_wallet_transactions", """
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
                        INDEX idx_admin_id (admin_id), INDEX idx_transaction_type (transaction_type),
                        INDEX idx_created_at (created_at), INDEX idx_reference_id (reference_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),

                
                ("fund_requests", """
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
                        INDEX idx_merchant_id (merchant_id), INDEX idx_status (status), INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("service_routing", """
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
                        INDEX idx_merchant_id (merchant_id), INDEX idx_is_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("callback_logs", """
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
                        INDEX idx_transaction_id (transaction_id), INDEX idx_transaction_type (transaction_type),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("payu_webhook_config", """
                    CREATE TABLE IF NOT EXISTS payu_webhook_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        webhook_url VARCHAR(500) NOT NULL,
                        secret_key VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("payu_webhook_logs", """
                    CREATE TABLE IF NOT EXISTS payu_webhook_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        event_type VARCHAR(100) NOT NULL,
                        payload TEXT NOT NULL,
                        signature VARCHAR(500),
                        is_verified BOOLEAN DEFAULT FALSE,
                        processed BOOLEAN DEFAULT FALSE,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_event_type (event_type), INDEX idx_processed (processed), INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
                
                ("payu_tokens", """
                    CREATE TABLE IF NOT EXISTS payu_tokens (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        access_token TEXT NOT NULL,
                        token_type VARCHAR(50) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_expires_at (expires_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """),
            ]
            
            # Create all tables
            print("Creating tables...")
            for table_name, create_sql in tables:
                cursor.execute(create_sql)
                print(f"  ✅ {table_name}")
            
            connection.commit()
            print()
            print(f"✅ All {len(tables)} tables created successfully!")
            print()
            
            # Create admin user
            print("Creating admin user...")
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
            
        connection.close()
        
        # Success message
        print("=" * 80)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("=" * 80)
        print()
        print("Admin Login Credentials:")
        print(f"  Admin ID: {admin_id}")
        print(f"  Password: {password}")
        print()
        print("Database Summary:")
        print(f"  Database: {Config.DB_NAME}")
        print(f"  Tables: {len(tables)}")
        print(f"  Admin Users: 1")
        print()
        print("Next Steps:")
        print("  1. Login to admin dashboard")
        print("  2. Create commercial schemes")
        print("  3. Onboard merchants")
        print("  4. Configure service routing")
        print()
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_fresh_database()
    exit(0 if success else 1)
