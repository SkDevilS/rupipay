-- Cleanup Extra Wallet Tables
-- Remove duplicate/unused wallet tables

-- Step 1: Backup data before dropping (optional)
-- Uncomment if you want to keep a backup

-- CREATE TABLE merchant_unsettled_wallet_backup AS SELECT * FROM merchant_unsettled_wallet;
-- CREATE TABLE wallet_transactions_backup AS SELECT * FROM wallet_transactions;

-- Step 2: Check if tables exist and show their data
SELECT 'merchant_unsettled_wallet' as table_name, COUNT(*) as row_count 
FROM merchant_unsettled_wallet;

SELECT 'wallet_transactions' as table_name, COUNT(*) as row_count 
FROM wallet_transactions;

-- Step 3: Drop the extra tables
-- These are duplicates and not used in current code

DROP TABLE IF EXISTS merchant_unsettled_wallet;
DROP TABLE IF EXISTS wallet_transactions;

-- Step 4: Verify tables are dropped
SELECT 
    TABLE_NAME,
    TABLE_COMMENT
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('merchant_unsettled_wallet', 'wallet_transactions', 'merchant_wallet', 'merchant_wallet_transactions');

-- Step 5: Show remaining wallet tables (should only see these)
-- Expected tables:
-- - admin_wallet
-- - admin_wallet_transactions
-- - merchant_wallet
-- - merchant_wallet_transactions
-- - settlement_transactions

SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    UPDATE_TIME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME LIKE '%wallet%'
ORDER BY TABLE_NAME;
