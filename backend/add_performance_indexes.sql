-- Performance Indexes for MoneyOne Database
-- Run this script to add indexes for better query performance

USE moneyone_db;

-- Payin transactions indexes
ALTER TABLE payin_transactions 
ADD INDEX IF NOT EXISTS idx_merchant_status (merchant_id, status),
ADD INDEX IF NOT EXISTS idx_order_id (order_id),
ADD INDEX IF NOT EXISTS idx_pg_txn_id (pg_txn_id),
ADD INDEX IF NOT EXISTS idx_bank_ref_no (bank_ref_no);

-- Payout transactions indexes  
ALTER TABLE payout_transactions
ADD INDEX IF NOT EXISTS idx_merchant_status (merchant_id, status),
ADD INDEX IF NOT EXISTS idx_batch_id (batch_id),
ADD INDEX IF NOT EXISTS idx_pg_txn_id (pg_txn_id),
ADD INDEX IF NOT EXISTS idx_utr (utr);

-- Wallet transactions indexes
ALTER TABLE wallet_transactions
ADD INDEX IF NOT EXISTS idx_merchant_txn (merchant_id, txn_id),
ADD INDEX IF NOT EXISTS idx_txn_type (txn_type),
ADD INDEX IF NOT EXISTS idx_merchant_created (merchant_id, created_at);

-- Admin wallet transactions indexes
ALTER TABLE admin_wallet_transactions
ADD INDEX IF NOT EXISTS idx_admin_wallet (admin_id, wallet_type),
ADD INDEX IF NOT EXISTS idx_admin_created (admin_id, created_at);

-- Service routing index
ALTER TABLE service_routing
ADD INDEX IF NOT EXISTS idx_merchant_service (merchant_id, service_type, is_active),
ADD INDEX IF NOT EXISTS idx_routing_active (routing_type, service_type, is_active);

-- Merchants index
ALTER TABLE merchants
ADD INDEX IF NOT EXISTS idx_merchant_active (merchant_id, is_active),
ADD INDEX IF NOT EXISTS idx_authorization_key (authorization_key);

-- Merchant callbacks index
ALTER TABLE merchant_callbacks
ADD INDEX IF NOT EXISTS idx_merchant_id (merchant_id);

-- Fund requests indexes
ALTER TABLE fund_requests
ADD INDEX IF NOT EXISTS idx_merchant_status (merchant_id, status),
ADD INDEX IF NOT EXISTS idx_status_requested (status, requested_at);

-- Callback logs indexes
ALTER TABLE callback_logs
ADD INDEX IF NOT EXISTS idx_merchant_txn (merchant_id, txn_id),
ADD INDEX IF NOT EXISTS idx_created_at (created_at);

-- Show index statistics
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    SEQ_IN_INDEX,
    COLUMN_NAME,
    CARDINALITY
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'moneyone_db'
AND TABLE_NAME IN ('payin_transactions', 'payout_transactions', 'wallet_transactions', 'service_routing', 'merchants')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;
