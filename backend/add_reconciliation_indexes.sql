-- Add indexes for manual reconciliation performance optimization
-- These indexes will significantly speed up date range queries

-- Index for payin_transactions
-- Check if index exists first
SELECT COUNT(*) INTO @index_exists 
FROM information_schema.statistics 
WHERE table_schema = DATABASE() 
AND table_name = 'payin_transactions' 
AND index_name = 'idx_merchant_status_created';

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX idx_merchant_status_created ON payin_transactions(merchant_id, status, created_at)',
    'SELECT "Index idx_merchant_status_created already exists on payin_transactions"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index for payout_transactions
SELECT COUNT(*) INTO @index_exists 
FROM information_schema.statistics 
WHERE table_schema = DATABASE() 
AND table_name = 'payout_transactions' 
AND index_name = 'idx_merchant_status_created';

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX idx_merchant_status_created ON payout_transactions(merchant_id, status, created_at)',
    'SELECT "Index idx_merchant_status_created already exists on payout_transactions"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Show created indexes
SELECT 
    table_name,
    index_name,
    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns
FROM information_schema.statistics
WHERE table_schema = DATABASE()
AND table_name IN ('payin_transactions', 'payout_transactions')
AND index_name LIKE 'idx_merchant_status_created'
GROUP BY table_name, index_name;
