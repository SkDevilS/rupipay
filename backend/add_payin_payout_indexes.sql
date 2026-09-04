-- Performance indexes for payin/payout APIs
-- Run this once to speed up queries

-- For payin status checks (txn_id + merchant_id)
CREATE INDEX IF NOT EXISTS idx_payin_txn_merchant 
ON payin_transactions(txn_id, merchant_id);

-- For payin list queries (merchant_id + date)
CREATE INDEX IF NOT EXISTS idx_payin_merchant_date 
ON payin_transactions(merchant_id, created_at DESC);

-- For payin status filter
CREATE INDEX IF NOT EXISTS idx_payin_merchant_status 
ON payin_transactions(merchant_id, status, created_at DESC);

-- For routing queries (most important!)
CREATE INDEX IF NOT EXISTS idx_routing_merchant_service_active 
ON service_routing(merchant_id, service_type, is_active, priority);

-- For payout status checks
CREATE INDEX IF NOT EXISTS idx_payout_txn_merchant 
ON payout_transactions(txn_id, merchant_id);

-- For payout list queries
CREATE INDEX IF NOT EXISTS idx_payout_merchant_date 
ON payout_transactions(merchant_id, created_at DESC);

-- For payout status filter
CREATE INDEX IF NOT EXISTS idx_payout_merchant_status 
ON payout_transactions(merchant_id, status, created_at DESC);

-- For wallet queries
CREATE INDEX IF NOT EXISTS idx_wallet_merchant 
ON merchant_wallet(merchant_id);

-- For wallet transactions
CREATE INDEX IF NOT EXISTS idx_wallet_txn_merchant 
ON wallet_transactions(merchant_id, created_at DESC);

-- Show created indexes
SHOW INDEX FROM payin_transactions;
SHOW INDEX FROM payout_transactions;
SHOW INDEX FROM service_routing;
