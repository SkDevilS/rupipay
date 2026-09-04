-- PayTouch2 Service Routing Configuration
-- This script helps configure PayTouch2 as a payout service provider

-- ============================================
-- 1. Check existing service routing
-- ============================================
SELECT 
    id,
    merchant_id,
    service_type,
    routing_type,
    pg_partner,
    priority,
    is_active,
    created_at
FROM service_routing
WHERE service_type = 'PAYOUT'
ORDER BY routing_type, merchant_id, priority;

-- ============================================
-- 2. Configure PayTouch2 for ALL USERS (Default)
-- ============================================
-- This makes PayTouch2 the default payout gateway for all merchants
-- Uncomment to execute:

-- INSERT INTO service_routing (service_type, routing_type, pg_partner, priority, is_active)
-- VALUES ('PAYOUT', 'ALL_USERS', 'Paytouch2', 2, TRUE)
-- ON DUPLICATE KEY UPDATE is_active = TRUE, priority = 2;

-- ============================================
-- 3. Configure PayTouch2 for SPECIFIC MERCHANT
-- ============================================
-- Replace '9000000001' with actual merchant_id
-- Uncomment to execute:

-- INSERT INTO service_routing (merchant_id, service_type, routing_type, pg_partner, priority, is_active)
-- VALUES ('9000000001', 'PAYOUT', 'SINGLE_USER', 'Paytouch2', 1, TRUE)
-- ON DUPLICATE KEY UPDATE is_active = TRUE, priority = 1;

-- ============================================
-- 4. Disable other payout gateways for a merchant
-- ============================================
-- This ensures only PayTouch2 is active for the merchant
-- Replace '9000000001' with actual merchant_id
-- Uncomment to execute:

-- UPDATE service_routing
-- SET is_active = FALSE
-- WHERE merchant_id = '9000000001'
--   AND service_type = 'PAYOUT'
--   AND pg_partner != 'Paytouch2';

-- ============================================
-- 5. Switch from PayTouch to PayTouch2 for ALL USERS
-- ============================================
-- Uncomment to execute:

-- -- Disable PayTouch
-- UPDATE service_routing
-- SET is_active = FALSE
-- WHERE service_type = 'PAYOUT'
--   AND routing_type = 'ALL_USERS'
--   AND pg_partner = 'PayTouch';

-- -- Enable PayTouch2
-- INSERT INTO service_routing (service_type, routing_type, pg_partner, priority, is_active)
-- VALUES ('PAYOUT', 'ALL_USERS', 'Paytouch2', 1, TRUE)
-- ON DUPLICATE KEY UPDATE is_active = TRUE, priority = 1;

-- ============================================
-- 6. Check PG Partners table (if exists)
-- ============================================
-- This table may store available payment gateway partners
-- Uncomment to check:

-- SELECT * FROM pg_partners WHERE supports LIKE '%PAYOUT%';

-- ============================================
-- 7. Verify PayTouch2 configuration
-- ============================================
SELECT 
    'PayTouch2 Routing Configuration' as info,
    COUNT(*) as total_routes,
    SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_routes,
    SUM(CASE WHEN routing_type = 'ALL_USERS' THEN 1 ELSE 0 END) as all_users_routes,
    SUM(CASE WHEN routing_type = 'SINGLE_USER' THEN 1 ELSE 0 END) as single_user_routes
FROM service_routing
WHERE service_type = 'PAYOUT' AND pg_partner = 'Paytouch2';

-- ============================================
-- 8. List merchants using PayTouch2
-- ============================================
SELECT 
    sr.merchant_id,
    m.full_name,
    m.email,
    sr.routing_type,
    sr.priority,
    sr.is_active,
    sr.created_at
FROM service_routing sr
LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
WHERE sr.service_type = 'PAYOUT' 
  AND sr.pg_partner = 'Paytouch2'
  AND sr.is_active = TRUE
ORDER BY sr.routing_type, sr.merchant_id;

-- ============================================
-- 9. Check recent PayTouch2 transactions
-- ============================================
SELECT 
    txn_id,
    merchant_id,
    admin_id,
    reference_id,
    amount,
    charge_amount,
    status,
    pg_txn_id,
    utr,
    created_at,
    completed_at
FROM payout_transactions
WHERE pg_partner = 'Paytouch2'
ORDER BY created_at DESC
LIMIT 20;

-- ============================================
-- 10. Check PayTouch2 callback logs
-- ============================================
SELECT 
    cl.id,
    cl.merchant_id,
    cl.txn_id,
    cl.callback_url,
    cl.response_code,
    cl.created_at,
    pt.status as transaction_status,
    pt.pg_partner
FROM callback_logs cl
LEFT JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
WHERE pt.pg_partner = 'Paytouch2'
ORDER BY cl.created_at DESC
LIMIT 20;

-- ============================================
-- EXAMPLE: Complete setup for a new merchant
-- ============================================
-- Replace values as needed:
-- - merchant_id: '9000000001'
-- - merchant_name: 'Test Merchant'

/*
-- Step 1: Verify merchant exists
SELECT merchant_id, full_name, email, is_active, scheme_id
FROM merchants
WHERE merchant_id = '9000000001';

-- Step 2: Configure PayTouch2 routing for this merchant
INSERT INTO service_routing (merchant_id, service_type, routing_type, pg_partner, priority, is_active)
VALUES ('9000000001', 'PAYOUT', 'SINGLE_USER', 'Paytouch2', 1, TRUE)
ON DUPLICATE KEY UPDATE is_active = TRUE, priority = 1;

-- Step 3: Disable other payout gateways for this merchant
UPDATE service_routing
SET is_active = FALSE
WHERE merchant_id = '9000000001'
  AND service_type = 'PAYOUT'
  AND pg_partner != 'Paytouch2';

-- Step 4: Verify configuration
SELECT * FROM service_routing
WHERE merchant_id = '9000000001' AND service_type = 'PAYOUT';
*/

-- ============================================
-- NOTES
-- ============================================
-- 1. Service routing priority:
--    - SINGLE_USER routing takes precedence over ALL_USERS
--    - Lower priority number = higher priority (1 is highest)
--
-- 2. Only ONE payout gateway should be active per merchant
--    - System uses the first active route found
--    - Order: SINGLE_USER (by priority) → ALL_USERS (by priority)
--
-- 3. PayTouch2 callback URL must be configured:
--    https://api.moneyone.co.in/api/callback/paytouch2/payout
--
-- 4. Wallet deduction happens via callback when status = SUCCESS
--    - Admin personal payouts: NO wallet deduction
--    - Merchant payouts: Wallet deducted on SUCCESS callback