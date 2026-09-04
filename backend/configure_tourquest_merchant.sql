-- Configure Tourquest for a Specific Merchant
-- Replace 'YOUR_MERCHANT_ID' with the actual merchant ID

-- Step 1: Check current routing for the merchant
SELECT sr.*, m.full_name 
FROM service_routing sr
LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
WHERE sr.merchant_id = 'YOUR_MERCHANT_ID' 
AND sr.service_type = 'PAYIN';

-- Step 2: Deactivate all other PAYIN gateways for this merchant
UPDATE service_routing
SET is_active = FALSE
WHERE merchant_id = 'YOUR_MERCHANT_ID' 
AND service_type = 'PAYIN';

-- Step 3: Insert or update Tourquest routing for this merchant
INSERT INTO service_routing (
    merchant_id, 
    service_type, 
    routing_type, 
    pg_partner, 
    priority, 
    is_active,
    created_by
) VALUES (
    'YOUR_MERCHANT_ID',  -- Replace with actual merchant ID
    'PAYIN',
    'SINGLE_USER',
    'Tourquest',
    1,
    TRUE,
    'admin'  -- Replace with actual admin ID if needed
)
ON DUPLICATE KEY UPDATE
    is_active = TRUE,
    priority = 1,
    updated_at = CURRENT_TIMESTAMP;

-- Step 4: Verify the configuration
SELECT sr.*, m.full_name 
FROM service_routing sr
LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
WHERE sr.merchant_id = 'YOUR_MERCHANT_ID' 
AND sr.service_type = 'PAYIN'
AND sr.is_active = TRUE;

-- Alternative: Configure Tourquest for ALL merchants (ALL_USERS)
-- Use this if you want all merchants to use Tourquest by default

-- Deactivate all other ALL_USERS PAYIN gateways
UPDATE service_routing
SET is_active = FALSE
WHERE merchant_id IS NULL 
AND service_type = 'PAYIN'
AND routing_type = 'ALL_USERS';

-- Insert or update Tourquest as default for all users
INSERT INTO service_routing (
    merchant_id, 
    service_type, 
    routing_type, 
    pg_partner, 
    priority, 
    is_active,
    created_by
) VALUES (
    NULL,  -- NULL means ALL_USERS
    'PAYIN',
    'ALL_USERS',
    'Tourquest',
    1,
    TRUE,
    'admin'
)
ON DUPLICATE KEY UPDATE
    is_active = TRUE,
    priority = 1,
    updated_at = CURRENT_TIMESTAMP;

-- Verify ALL_USERS configuration
SELECT * FROM service_routing 
WHERE merchant_id IS NULL 
AND service_type = 'PAYIN'
AND routing_type = 'ALL_USERS'
AND is_active = TRUE;
