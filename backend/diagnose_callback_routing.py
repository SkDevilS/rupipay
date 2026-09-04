"""
Diagnose Callback Routing Issues After Instance Separation
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_app_routes(app_file):
    """Check which routes are registered in an app file"""
    print(f"\n{'='*80}")
    print(f"Checking routes in {app_file}")
    print('='*80)
    
    try:
        if app_file == 'app.py':
            from app import app
        else:
            from app_payin import app
        
        # Get all routes
        routes = []
        for rule in app.url_map.iter_rules():
            if 'callback' in rule.rule.lower():
                routes.append({
                    'path': rule.rule,
                    'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'}),
                    'endpoint': rule.endpoint
                })
        
        # Group by service
        services = {}
        for route in routes:
            service = route['path'].split('/')[3] if len(route['path'].split('/')) > 3 else 'unknown'
            if service not in services:
                services[service] = []
            services[service].append(route)
        
        # Print organized results
        for service, service_routes in sorted(services.items()):
            print(f"\n{service.upper()} Callbacks:")
            for route in service_routes:
                print(f"  ✓ {route['methods']:10} {route['path']}")
        
        print(f"\nTotal callback routes: {len(routes)}")
        return len(routes)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0


def check_gunicorn_status():
    """Check if Gunicorn is running"""
    print(f"\n{'='*80}")
    print("Checking Gunicorn Status")
    print('='*80)
    
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        gunicorn_processes = [line for line in result.stdout.split('\n') if 'gunicorn' in line.lower()]
        
        if gunicorn_processes:
            print(f"✓ Found {len(gunicorn_processes)} Gunicorn processes:")
            for proc in gunicorn_processes:
                print(f"  {proc}")
        else:
            print("✗ No Gunicorn processes found")
            print("  Run: sudo systemctl status gunicorn")
        
        return len(gunicorn_processes) > 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def check_recent_callbacks():
    """Check recent callback activity in database"""
    print(f"\n{'='*80}")
    print("Checking Recent Callback Activity (Last 24 Hours)")
    print('='*80)
    
    try:
        from database_pooled import get_db_connection
        
        conn = get_db_connection()
        if not conn:
            print("✗ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Check callback_logs table
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m-%d %H:00') as hour,
                    COUNT(*) as count,
                    SUM(CASE WHEN response_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN response_code NOT BETWEEN 200 AND 299 THEN 1 ELSE 0 END) as failed
                FROM callback_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY hour
                ORDER BY hour DESC
                LIMIT 10
            """)
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print("\nCallback Forwarding Activity:")
                print(f"{'Hour':<20} {'Total':>8} {'Success':>8} {'Failed':>8}")
                print("-" * 50)
                for log in callback_logs:
                    print(f"{log['hour']:<20} {log['count']:>8} {log['success']:>8} {log['failed']:>8}")
            else:
                print("✗ No callback forwarding activity in last 24 hours")
            
            # Check recent PayTouch2 payout callbacks
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status IN ('QUEUED', 'INITIATED', 'INPROCESS') THEN 1 ELSE 0 END) as pending,
                    MAX(updated_at) as last_update
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            paytouch2_stats = cursor.fetchone()
            
            print(f"\nPayTouch2 Payout Transactions (Last 24 Hours):")
            print(f"  Total: {paytouch2_stats['total']}")
            print(f"  Success: {paytouch2_stats['success']}")
            print(f"  Failed: {paytouch2_stats['failed']}")
            print(f"  Pending: {paytouch2_stats['pending']}")
            print(f"  Last Update: {paytouch2_stats['last_update']}")
            
            if paytouch2_stats['pending'] > 0:
                print(f"\n⚠️  WARNING: {paytouch2_stats['pending']} PayTouch2 transactions are still pending")
                print("   This suggests callbacks are not being received")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def check_load_balancer_config():
    """Provide instructions for checking load balancer"""
    print(f"\n{'='*80}")
    print("Load Balancer Configuration Check")
    print('='*80)
    
    print("""
To verify load balancer is routing callbacks correctly:

1. Check Target Group Health:
   - Go to AWS Console → EC2 → Target Groups
   - Verify all instances show "healthy" status
   - Check "Health check path" is correct

2. Check Listener Rules:
   - Go to Load Balancer → Listeners
   - Verify rules are routing traffic correctly
   - Ensure no path-based routing is blocking callbacks

3. Check Security Groups:
   - Verify load balancer security group allows inbound on port 443/80
   - Verify instance security group allows inbound from load balancer

4. Test Direct Instance Access:
   # SSH to instance and test locally
   curl -X POST http://localhost:5000/api/callback/paytouch2/payout \\
     -H "Content-Type: application/json" \\
     -d '{"transaction_id":"TEST","status":"SUCCESS"}'

5. Check Application Logs:
   sudo journalctl -u gunicorn -f
   # Look for callback requests
""")


def main():
    print("="*80)
    print("CALLBACK ROUTING DIAGNOSTIC TOOL")
    print("="*80)
    
    # Check which app file to use
    if os.path.exists('app_payin.py'):
        print("\n✓ Found app_payin.py - checking payin instance configuration")
        app_payin_routes = check_app_routes('app_payin.py')
    else:
        print("\n✗ app_payin.py not found")
        app_payin_routes = 0
    
    if os.path.exists('app.py'):
        print("\n✓ Found app.py - checking main instance configuration")
        app_routes = check_app_routes('app.py')
    else:
        print("\n✗ app.py not found")
        app_routes = 0
    
    # Check Gunicorn
    gunicorn_running = check_gunicorn_status()
    
    # Check recent callbacks
    check_recent_callbacks()
    
    # Load balancer instructions
    check_load_balancer_config()
    
    # Summary
    print(f"\n{'='*80}")
    print("DIAGNOSTIC SUMMARY")
    print('='*80)
    
    issues = []
    
    if app_payin_routes == 0:
        issues.append("✗ No callback routes found in app_payin.py")
    else:
        print(f"✓ app_payin.py has {app_payin_routes} callback routes registered")
    
    if not gunicorn_running:
        issues.append("✗ Gunicorn is not running")
    else:
        print("✓ Gunicorn is running")
    
    if issues:
        print("\n⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print("\nRecommended Actions:")
        print("1. Restart Gunicorn: sudo systemctl restart gunicorn")
        print("2. Check logs: sudo journalctl -u gunicorn -n 100")
        print("3. Verify load balancer target health in AWS Console")
    else:
        print("\n✓ All checks passed")
        print("\nIf callbacks still not working:")
        print("1. Check load balancer configuration (see instructions above)")
        print("2. Verify payment gateway callback URLs are correct")
        print("3. Check application logs for incoming requests")


if __name__ == '__main__':
    main()
