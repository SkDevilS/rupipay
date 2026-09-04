-- Add UNIQUE Constraints to Prevent Duplicate Transactions
-- This prevents the same transaction from being inserted multiple times

-- Step 1: First, we need to clean existing duplicates before adding constraints
-- Run the Python script first: python3 fix_duplicate_status_transactions.py --execute

-- Step 2: Add UNIQUE constraint on txn_id
-- This ensures each transaction ID is unique
ALTER TABLE payout_transactions 
ADD UNIQUE KEY unique_txn_id (txn_id);

-- Step 3: Add UNIQUE constraint on reference_id  
-- This ensures each reference ID is unique
ALTER TABLE payout_transactions 
ADD UNIQUE KEY unique_reference_id (reference_id);

-- Step 4: Add UNIQUE constraint on order_id per merchant
-- This prevents duplicate order_ids for the same merchant
ALTER TABLE payout_transactions 
ADD UNIQUE KEY unique_merchant_order (merchant_id, order_id);

-- Step 5: Verify constraints were added
SHOW INDEX FROM payout_transactions WHERE Key_name LIKE 'unique%';

-- Step 6: Test that duplicates are now prevented
-- This should fail with duplicate key error:
-- INSERT INTO payout_transactions (txn_id, reference_id, ...) 
-- VALUES ('existing_txn_id', 'existing_ref_id', ...);
