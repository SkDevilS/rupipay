-- Fix Admin Wallet Schema
-- Add settled_balance column and update structure

-- Step 1: Add settled_balance column
ALTER TABLE admin_wallet 
ADD COLUMN IF NOT EXISTS settled_balance DECIMAL(15, 2) DEFAULT 0.00 AFTER unsettled_balance;

-- Step 2: Add comments to columns
ALTER TABLE admin_wallet 
MODIFY COLUMN main_balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Legacy balance - deprecated',
MODIFY COLUMN unsettled_balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Unsettled amount from payin charges - pending settlement',
MODIFY COLUMN settled_balance DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Settled amount - available for admin operations';

-- Step 3: Update admin_wallet_transactions to remove wallet_type (no longer needed)
-- First check if column exists
SET @col_exists = (SELECT COUNT(*) 
                   FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'admin_wallet_transactions' 
                   AND COLUMN_NAME = 'wallet_type');

SET @sql = IF(@col_exists > 0, 
    'ALTER TABLE admin_wallet_transactions DROP COLUMN wallet_type',
    'SELECT "Column wallet_type does not exist" AS message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 4: Update txn_type ENUM to include UNSETTLED_CREDIT and SETTLEMENT
ALTER TABLE admin_wallet_transactions
MODIFY COLUMN txn_type ENUM('CREDIT', 'DEBIT', 'UNSETTLED_CREDIT', 'SETTLEMENT', 'UNSETTLED_DEBIT') NOT NULL;

-- Step 5: Verify the changes
SELECT 
    'admin_wallet' as table_name,
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'admin_wallet'
ORDER BY ORDINAL_POSITION;

SELECT 
    'admin_wallet_transactions' as table_name,
    COLUMN_NAME,
    COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'admin_wallet_transactions'
AND COLUMN_NAME = 'txn_type';
