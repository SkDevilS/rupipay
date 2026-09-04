-- Add payment_url column to payin_transactions table for ViyonaPay integration

ALTER TABLE payin_transactions 
ADD COLUMN IF NOT EXISTS payment_url TEXT AFTER product_info;

-- Verify the column was added
DESCRIBE payin_transactions;
