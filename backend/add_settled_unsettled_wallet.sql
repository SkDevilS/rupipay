-- Migration: Add settled and unsettled balance columns to merchant_wallet table
-- This enables the settled/unsettled wallet feature

-- Add columns to merchant_wallet table
ALTER TABLE merchant_wallet 
ADD COLUMN settled_balance DECIMAL(15, 2) DEFAULT 0.00 AFTER balance,
ADD COLUMN unsettled_balance DECIMAL(15, 2) DEFAULT 0.00 AFTER settled_balance;

-- Migrate existing balance to settled_balance
UPDATE merchant_wallet 
SET settled_balance = balance, 
    unsettled_balance = 0.00;

-- Create settlement transactions table to track admin settlements
CREATE TABLE IF NOT EXISTS settlement_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    settlement_id VARCHAR(100) UNIQUE NOT NULL,
    merchant_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    settled_by VARCHAR(50) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    FOREIGN KEY (settled_by) REFERENCES admin_users(admin_id),
    INDEX idx_merchant_id (merchant_id),
    INDEX idx_created_at (created_at)
);

-- Add comment to columns
ALTER TABLE merchant_wallet 
MODIFY COLUMN balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Legacy balance - use settled_balance instead',
MODIFY COLUMN settled_balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Settled amount - available for payout',
MODIFY COLUMN unsettled_balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Unsettled amount - pending admin approval';
