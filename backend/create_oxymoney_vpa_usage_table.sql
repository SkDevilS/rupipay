-- Create table for tracking Oxymoney VPA usage
-- This table tracks daily usage per VPA to enforce 9 Lakh limit

CREATE TABLE IF NOT EXISTS oxymoney_vpa_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vpa VARCHAR(100) NOT NULL COMMENT 'VPA used for transaction',
    amount DECIMAL(15, 2) NOT NULL COMMENT 'Transaction amount',
    txn_id VARCHAR(100) NOT NULL COMMENT 'Transaction ID reference',
    merchant_id VARCHAR(50) NOT NULL COMMENT 'Merchant ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Transaction timestamp',
    INDEX idx_vpa_date (vpa, created_at),
    INDEX idx_txn_id (txn_id),
    INDEX idx_merchant_id (merchant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tracks Oxymoney VPA usage for daily limit enforcement';
