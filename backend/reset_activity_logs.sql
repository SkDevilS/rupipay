-- ============================================================================
-- Reset Activity Logs SQL Script
-- ============================================================================

-- Option 1: View current activity logs count
SELECT COUNT(*) as total_logs FROM admin_activity_logs;

-- Option 2: View activity logs by admin
SELECT 
    admin_id,
    COUNT(*) as log_count,
    MIN(created_at) as first_log,
    MAX(created_at) as last_log
FROM admin_activity_logs
GROUP BY admin_id
ORDER BY log_count DESC;

-- Option 3: View recent activity logs (last 10)
SELECT 
    id,
    admin_id,
    action,
    status,
    ip_address,
    created_at
FROM admin_activity_logs
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================================
-- RESET OPTIONS (Uncomment the one you want to use)
-- ============================================================================

-- Option A: Delete ALL activity logs
-- WARNING: This will delete all activity logs permanently!
-- DELETE FROM admin_activity_logs;
-- ALTER TABLE admin_activity_logs AUTO_INCREMENT = 1;

-- Option B: Delete activity logs for a specific admin
-- Replace 'ADMIN_ID_HERE' with actual admin ID
-- DELETE FROM admin_activity_logs WHERE admin_id = 'ADMIN_ID_HERE';

-- Option C: Delete activity logs older than 30 days
-- DELETE FROM admin_activity_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Option D: Delete activity logs older than 90 days
-- DELETE FROM admin_activity_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Option E: Keep only last 100 logs per admin
-- DELETE FROM admin_activity_logs 
-- WHERE id NOT IN (
--     SELECT id FROM (
--         SELECT id FROM admin_activity_logs 
--         ORDER BY created_at DESC 
--         LIMIT 100
--     ) as keep_logs
-- );

-- ============================================================================
-- Verify deletion
-- ============================================================================
-- SELECT COUNT(*) as remaining_logs FROM admin_activity_logs;
