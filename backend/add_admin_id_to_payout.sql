-- Add admin_id column to payout_transactions table
-- This allows us to distinguish between merchant payouts and admin personal payouts

-- Step 1: Add admin_id column (nullable for existing records)
ALTER TABLE payout_transactions
ADD COLUMN IF NOT EXISTS admin_id VARCHAR(50) NULL AFTER merchant_id;

-- Step 2: Add index on admin_id for faster lookups
ALTER TABLE payout_transactions
ADD INDEX IF NOT EXISTS idx_admin_id (admin_id);

-- Step 3: Migrate existing admin payouts
-- Update records where merchant_id is actually an admin_id (not in merchants table)
UPDATE payout_transactions pt
LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
SET pt.admin_id = pt.merchant_id,
    pt.merchant_id = NULL
WHERE m.merchant_id IS NULL 
AND pt.merchant_id IS NOT NULL
AND pt.merchant_id != '';

-- Step 4: Verify migration
SELECT 
    COUNT(*) as total_payouts,
    SUM(CASE WHEN merchant_id IS NOT NULL THEN 1 ELSE 0 END) as merchant_payouts,
    SUM(CASE WHEN admin_id IS NOT NULL THEN 1 ELSE 0 END) as admin_payouts
FROM payout_transactions;

-- Expected result: admin_payouts should show records that were previously using admin_id in merchant_id field
