-- Add PayTouch as a payout option for ADMIN personal payouts
-- This allows PayTouch to appear in the admin personal payout dropdown

INSERT INTO service_routing (
    merchant_id,
    service_type,
    routing_type,
    pg_partner,
    priority,
    is_active,
    created_at,
    updated_at
) VALUES (
    NULL,                    -- NULL for admin routing
    'PAYOUT',               -- Service type
    'ADMIN',                -- Routing type for admin personal payouts
    'PayTouch',             -- Payment gateway partner
    1,                      -- Priority
    TRUE,                   -- Active
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- Verify the insertion
SELECT * FROM service_routing 
WHERE routing_type = 'ADMIN' 
AND service_type = 'PAYOUT'
ORDER BY pg_partner;
