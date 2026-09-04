-- IP Security Configuration Table
CREATE TABLE IF NOT EXISTS merchant_ip_security (
    id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    description VARCHAR(255) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES admin_users(admin_id),
    UNIQUE KEY unique_merchant_ip (merchant_id, ip_address)
);

-- Index for faster lookups
CREATE INDEX idx_merchant_ip_active ON merchant_ip_security(merchant_id, ip_address, is_active);

-- IP Security Logs Table
CREATE TABLE IF NOT EXISTS ip_security_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    status ENUM('ALLOWED', 'BLOCKED') NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
);

-- Index for log queries
CREATE INDEX idx_ip_logs_merchant ON ip_security_logs(merchant_id, created_at DESC);
CREATE INDEX idx_ip_logs_status ON ip_security_logs(status, created_at DESC);
