import pymysql
from config import Config

def get_db_connection():
    """Create and return a database connection with proper isolation level"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False  # Explicit transaction control
        )
        
        # Set timezone and isolation level separately
        with connection.cursor() as cursor:
            cursor.execute("SET time_zone='+05:30'")
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database and create tables"""
    try:
        # Connect without database to create it
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
            cursor.execute(f"USE {Config.DB_NAME}")
            
            # Create admin table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    pin_hash VARCHAR(255) NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    login_attempts INT DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    password_changed_at TIMESTAMP NULL,
                    pin_changed_at TIMESTAMP NULL,
                    must_change_password BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create activity logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_activity_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    status VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id)
                )
            """)
            
            # Create commercial schemes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commercial_schemes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    scheme_name VARCHAR(100) UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id)
                )
            """)
            
            # Create commercial charges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commercial_charges (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    scheme_id INT NOT NULL,
                    service_type ENUM('PAYOUT', 'PAYIN') NOT NULL,
                    product_name VARCHAR(100) NOT NULL,
                    min_amount DECIMAL(10, 2) NOT NULL,
                    max_amount DECIMAL(10, 2) NOT NULL,
                    charge_value DECIMAL(10, 4) NOT NULL,
                    charge_type ENUM('PERCENTAGE', 'FIXED') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (scheme_id) REFERENCES commercial_schemes(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_scheme_product (scheme_id, service_type, product_name)
                )
            """)
            
            # Create merchants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    pin_hash VARCHAR(255) NULL,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    mobile VARCHAR(20) NOT NULL,
                    dob DATE,
                    aadhar_card VARCHAR(20) NOT NULL,
                    pan_no VARCHAR(20) NOT NULL,
                    pincode VARCHAR(10) NOT NULL,
                    state VARCHAR(100) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    house_number VARCHAR(100),
                    address TEXT NOT NULL,
                    landmark VARCHAR(255),
                    merchant_type ENUM('PAYIN', 'PAYOUT', 'BOTH') NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(20) NOT NULL,
                    gst_no VARCHAR(50) NOT NULL,
                    scheme_id INT,
                    authorization_key VARCHAR(255) UNIQUE NOT NULL,
                    module_secret VARCHAR(255) UNIQUE NOT NULL,
                    aes_iv VARCHAR(255) NOT NULL,
                    aes_key VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    password_changed_at TIMESTAMP NULL,
                    pin_changed_at TIMESTAMP NULL,
                    FOREIGN KEY (scheme_id) REFERENCES commercial_schemes(id),
                    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id)
                )
            """)
            
            # Create merchant documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
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
                )
            """)
            
            # Create merchant IP whitelist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_ip_whitelist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_merchant_ip (merchant_id, ip_address)
                )
            """)
            
            # Create merchant callback URLs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_callbacks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) UNIQUE NOT NULL,
                    payin_callback_url VARCHAR(500),
                    payout_callback_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                )
            """)
            
            # Create merchant banks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_banks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    bank_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(20) NOT NULL,
                    branch_name VARCHAR(255),
                    account_holder_name VARCHAR(255) NOT NULL,
                    tpin_hash VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                )
            """)
            
            # Create admin banks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_banks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL,
                    bank_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(50) NOT NULL,
                    ifsc_code VARCHAR(20) NOT NULL,
                    branch_name VARCHAR(255),
                    account_holder_name VARCHAR(255) NOT NULL,
                    tpin_hash VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE
                )
            """)
            
            # Create payin transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payin_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    txn_id VARCHAR(100) UNIQUE NOT NULL,
                    merchant_id VARCHAR(50) NOT NULL,
                    order_id VARCHAR(100) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    charge_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    charge_type ENUM('PERCENTAGE', 'FIXED') NOT NULL DEFAULT 'FIXED',
                    net_amount DECIMAL(15, 2) NOT NULL,
                    payee_name VARCHAR(255),
                    payee_email VARCHAR(255),
                    payee_mobile VARCHAR(20),
                    product_info VARCHAR(500),
                    status ENUM('INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'CANCELLED') NOT NULL DEFAULT 'INITIATED',
                    pg_partner VARCHAR(50) DEFAULT 'PayU',
                    pg_txn_id VARCHAR(100),
                    bank_ref_no VARCHAR(100),
                    payment_mode VARCHAR(50),
                    error_message TEXT,
                    remarks TEXT,
                    callback_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            # Create merchant wallet table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) UNIQUE NOT NULL,
                    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                )
            """)
            
            # Create wallet transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    txn_id VARCHAR(100) NOT NULL,
                    txn_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    balance_before DECIMAL(15, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            # Create callback logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS callback_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NOT NULL,
                    txn_id VARCHAR(100) NOT NULL,
                    callback_url VARCHAR(500),
                    request_data TEXT,
                    response_code INT,
                    response_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_txn_id (txn_id)
                )
            """)
            
            # Create PayU webhook configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_webhook_config (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    webhook_url VARCHAR(500) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_event (event_type)
                )
            """)
            
            # Create PayU webhook logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_webhook_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    merchant_ref_id VARCHAR(100),
                    payu_ref_id VARCHAR(100),
                    payload TEXT,
                    status ENUM('RECEIVED', 'PROCESSED', 'FAILED') NOT NULL DEFAULT 'RECEIVED',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    INDEX idx_event_type (event_type),
                    INDEX idx_merchant_ref_id (merchant_ref_id),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            # Create PayU token storage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payu_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_type VARCHAR(50),
                    expires_at TIMESTAMP NOT NULL,
                    user_uuid VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create service routing table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_routing (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50),
                    service_type ENUM('PAYIN', 'PAYOUT') NOT NULL,
                    routing_type ENUM('SINGLE_USER', 'ALL_USERS') NOT NULL,
                    pg_partner VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    priority INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_routing (merchant_id, service_type, routing_type, pg_partner)
                )
            """)
            
            # Create payout transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payout_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    txn_id VARCHAR(100) UNIQUE NOT NULL,
                    merchant_id VARCHAR(50) NOT NULL,
                    reference_id VARCHAR(100) NOT NULL,
                    order_id VARCHAR(100) NULL,
                    batch_id VARCHAR(100),
                    amount DECIMAL(15, 2) NOT NULL,
                    charge_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    charge_type ENUM('PERCENTAGE', 'FIXED') NOT NULL DEFAULT 'FIXED',
                    net_amount DECIMAL(15, 2) NOT NULL,
                    bene_name VARCHAR(255) NOT NULL,
                    bene_email VARCHAR(255),
                    bene_mobile VARCHAR(20),
                    bene_bank VARCHAR(255),
                    ifsc_code VARCHAR(20),
                    account_no VARCHAR(50),
                    vpa VARCHAR(100),
                    payment_type ENUM('IMPS', 'NEFT', 'RTGS', 'UPI') NOT NULL DEFAULT 'IMPS',
                    purpose VARCHAR(500),
                    status ENUM('INITIATED', 'QUEUED', 'INPROCESS', 'SUCCESS', 'FAILED', 'REVERSED') NOT NULL DEFAULT 'INITIATED',
                    pg_partner VARCHAR(50) DEFAULT 'PayU',
                    pg_txn_id VARCHAR(100),
                    bank_ref_no VARCHAR(100),
                    utr VARCHAR(100),
                    name_with_bank VARCHAR(255),
                    name_match_score INT,
                    error_message TEXT,
                    remarks TEXT,
                    callback_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_reference_id (reference_id),
                    INDEX idx_order_id (order_id)
                )
            """)
            
            # Create fund requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id VARCHAR(100) UNIQUE NOT NULL,
                    merchant_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    request_type ENUM('TOPUP', 'SETTLEMENT') NOT NULL,
                    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
                    remarks TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    processed_by VARCHAR(50),
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
                    FOREIGN KEY (processed_by) REFERENCES admin_users(admin_id),
                    INDEX idx_merchant_id (merchant_id),
                    INDEX idx_status (status)
                )
            """)
            
            # Create merchant unsettled wallet table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_unsettled_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) UNIQUE NOT NULL,
                    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                )
            """)
            
            # Create admin wallet table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) UNIQUE NOT NULL,
                    main_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    unsettled_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE
                )
            """)
            
            # Create admin wallet transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    admin_id VARCHAR(50) NOT NULL,
                    txn_id VARCHAR(100) NOT NULL,
                    wallet_type ENUM('MAIN', 'UNSETTLED') NOT NULL,
                    txn_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    balance_before DECIMAL(15, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admin_users(admin_id) ON DELETE CASCADE,
                    INDEX idx_admin_id (admin_id),
                    INDEX idx_wallet_type (wallet_type),
                    INDEX idx_created_at (created_at)
                )
            """)
            
        connection.commit()
        connection.close()
        print("Database initialized successfully!")
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False
