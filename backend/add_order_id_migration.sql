-- Migration: Add order_id column to payout_transactions table
-- Date: 2026-02-27
-- Description: Add order_id field for duplicate detection in merchant payouts

-- Add order_id column (nullable initially for existing records)
ALTER TABLE payout_transactions
ADD COLUMN IF NOT EXISTS order_id VARCHAR(100) NULL AFTER reference_id;

-- Add index on order_id for faster lookups
ALTER TABLE payout_transactions
ADD INDEX IF NOT EXISTS idx_order_id (order_id);

-- Update existing records with order_id = reference_id for backward compatibility
UPDATE payout_transactions
SET order_id = reference_id
WHERE order_id IS NULL;

-- Verify the changes
SELECT 
    'Migration completed successfully' as status,
    COUNT(*) as total_records,
    COUNT(order_id) as records_with_order_id
FROM payout_transactions;
