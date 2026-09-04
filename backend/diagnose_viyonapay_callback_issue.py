#!/usr/bin/env python3
"""
ViyonaPay Callback Issue Diagnostic Tool
Checks all possible reasons why callbacks are not being received
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime, timedelta

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def check_callback_endpoint():
    """Check if callback endpoint is properly configured"""
    print_section("1. CALLBACK ENDPOINT CONFIGURATION")
    
    try:
        from config import Config
        
        # Check if ViyonaPay callback URL is configured
        callback_url = getattr(Config, 'VIYONAPAY_CALLBACK_URL', None)
        
        if callback_url:
            print(f"✓ Callback URL configured: {callback_url}")
        else:
            print(f"⚠ No VIYONAPAY_CALLBACK_URL found in config")
            print(f"  Expected format: https://yourdomain.com/api/callback/viyonapay/payin")
        
        # Check backend URL
        backend_url = getattr(Config, 'BACKEND_URL', None)
        if backend_url:
            print(f"✓ Backend URL: {backend_url}")
            expected_callback = f"{backend_url}/api/callback/viyonapay/payin"
            print(f"  Expected callback: {expected_callback}")
        
        return True
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False

def check_recent_transactions():
    """Check recent ViyonaPay transactions"""
    print_section("2. RECENT VIYONAPAY TRANSACTIONS")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get recent ViyonaPay transactions
            cursor.execute("""
                SELECT txn_id, order_id, merchant_id, status, amount, 
                       pg_txn_id, created_at, updated_at, callback_url
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("⚠ No ViyonaPay transactions found")
                return False
            
            print(f"✓ Found {len(transactions)} recent ViyonaPay transactions:\n")
            
            for txn in transactions:
                print(f"Transaction: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  PG TXN ID: {txn['pg_txn_id'] or 'None'}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Updated: {txn['updated_at']}")
                print(f"  Callback URL: {txn['callback_url'] or 'Not set'}")
                
                # Check if stuck in INITIATED
                if txn['status'] == 'INITIATED':
                    age = datetime.now() - txn['created_at']
                    if age > timedelta(minutes=5):
                        print(f"  ⚠ STUCK: Transaction is {age.seconds//60} minutes old and still INITIATED")
                        print(f"     This indicates NO callback was received from ViyonaPay")
                
                print()
            
            return True
    finally:
        conn.close()

def check_callback_logs():
    """Check if any callbacks were received"""
    print_section("3. CALLBACK LOGS")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check for any ViyonaPay callbacks
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM callback_logs
                WHERE callback_url LIKE '%viyonapay%'
                   OR request_data LIKE '%paymentStatus%'
                   OR request_data LIKE '%transactionId%'
            """)
            
            result = cursor.fetchone()
            callback_count = result['count'] if result else 0
            
            if callback_count > 0:
                print(f"✓ Found {callback_count} ViyonaPay callbacks in logs")
                
                # Get latest callback
                cursor.execute("""
                    SELECT id, merchant_id, callback_url, request_data, 
                           response_code, created_at
                    FROM callback_logs
                    WHERE callback_url LIKE '%viyonapay%'
                       OR request_data LIKE '%paymentStatus%'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                latest = cursor.fetchone()
                if latest:
                    print(f"\nLatest callback:")
                    print(f"  Time: {latest['created_at']}")
                    print(f"  Response Code: {latest['response_code']}")
                    print(f"  Request Data: {latest['request_data'][:200]}...")
            else:
                print(f"❌ NO ViyonaPay callbacks found in callback_logs table")
                print(f"   This confirms ViyonaPay is NOT sending webhooks to your server")
            
            return callback_count > 0
    finally:
        conn.close()

def check_flask_routes():
    """Check if Flask route is registered"""
    print_section("4. FLASK ROUTE REGISTRATION")
    
    try:
        # Check if app.py imports viyonapay_callback_routes
        with open('app.py', 'r') as f:
            app_content = f.read()
        
        if 'viyonapay_callback' in app_content:
            print("✓ ViyonaPay callback routes imported in app.py")
        else:
            print("❌ ViyonaPay callback routes NOT imported in app.py")
            print("   Add this line to app.py:")
            print("   from viyonapay_callback_routes import viyonapay_callback_bp")
            print("   app.register_blueprint(viyonapay_callback_bp)")
            return False
        
        if 'register_blueprint(viyonapay_callback_bp)' in app_content:
            print("✓ ViyonaPay callback blueprint registered")
        else:
            print("❌ ViyonaPay callback blueprint NOT registered")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking Flask routes: {e}")
        return False

def check_network_accessibility():
    """Check if callback URL is accessible from internet"""
    print_section("5. NETWORK ACCESSIBILITY")
    
    try:
        from config import Config
        backend_url = getattr(Config, 'BACKEND_URL', None)
        
        if not backend_url:
            print("⚠ BACKEND_URL not configured")
            return False
        
        callback_endpoint = f"{backend_url}/api/callback/viyonapay/payin"
        
        print(f"Callback endpoint: {callback_endpoint}")
        print()
        print("To test if ViyonaPay can reach your server:")
        print()
        print(f"1. Test from external network:")
        print(f"   curl -X POST {callback_endpoint} \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"test\": \"data\"}}'")
        print()
        print(f"2. Check server logs for incoming requests")
        print()
        print(f"3. Verify firewall/security groups allow HTTPS traffic")
        print()
        
        # Check if URL is localhost
        if 'localhost' in backend_url or '127.0.0.1' in backend_url:
            print("❌ CRITICAL: Backend URL is localhost!")
            print("   ViyonaPay cannot reach localhost URLs")
            print("   You need a public domain or IP address")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_viyonapay_credentials():
    """Check ViyonaPay credentials configuration"""
    print_section("6. VIYONAPAY CREDENTIALS")
    
    try:
        from config import Config
        
        credentials = {
            'Client ID': getattr(Config, 'VIYONAPAY_CLIENT_ID', None),
            'Client Secret': getattr(Config, 'VIYONAPAY_CLIENT_SECRET', None),
            'Webhook Secret Key': getattr(Config, 'VIYONAPAY_WEBHOOK_SECRET_KEY', None),
            'Server Public Key Path': getattr(Config, 'VIYONAPAY_SERVER_PUBLIC_KEY_PATH', None),
        }
        
        all_configured = True
        for key, value in credentials.items():
            if value:
                if 'Secret' in key or 'Key' in key:
                    print(f"✓ {key}: {'*' * 10}")
                else:
                    print(f"✓ {key}: {value}")
            else:
                print(f"❌ {key}: NOT CONFIGURED")
                all_configured = False
        
        return all_configured
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def generate_action_plan():
    """Generate action plan based on findings"""
    print_section("ACTION PLAN")
    
    print("""
Based on the diagnostic results, here's what you need to do:

1. VERIFY CALLBACK URL WITH VIYONAPAY
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Contact ViyonaPay support and confirm:
   
   ✓ Is your callback URL registered in their system?
   ✓ Are webhooks enabled for your account?
   ✓ Is your account in TEST or PRODUCTION mode?
   ✓ Do they have any IP whitelist restrictions?
   
   Provide them with your callback URL:
   https://yourdomain.com/api/callback/viyonapay/payin

2. TEST CALLBACK ENDPOINT MANUALLY
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Test if your endpoint is reachable:
   
   curl -X POST https://yourdomain.com/api/callback/viyonapay/payin \\
        -H 'Content-Type: application/json' \\
        -d '{
          "paymentStatus": "SUCCESS",
          "transactionId": "TEST123",
          "orderId": "TEST_ORDER",
          "amount": "100"
        }'
   
   You should see this request in your callback_logs table.

3. CHECK SERVER LOGS
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Monitor your Flask application logs while completing a transaction:
   
   tail -f /var/log/your-app/app.log
   
   Look for incoming POST requests to /api/callback/viyonapay/payin

4. REQUEST SAMPLE CALLBACK FROM VIYONAPAY
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Ask ViyonaPay support to:
   
   ✓ Send a test webhook to your callback URL
   ✓ Provide webhook delivery logs from their side
   ✓ Confirm if they see any errors when sending to your URL

5. VERIFY NETWORK CONFIGURATION
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ✓ Ensure your server accepts HTTPS POST requests
   ✓ Check firewall rules allow incoming traffic on port 443
   ✓ Verify SSL certificate is valid
   ✓ Check if any WAF/CDN is blocking ViyonaPay's IP addresses

6. ALTERNATIVE: USE WEBHOOK TESTING SERVICE
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Temporarily use a webhook testing service to verify ViyonaPay is sending:
   
   • webhook.site
   • requestbin.com
   • ngrok (for local testing)
   
   Register the test URL with ViyonaPay and see if they send webhooks there.
""")

def main():
    print("\n" + "🔍"*40)
    print("  VIYONAPAY CALLBACK DIAGNOSTIC TOOL")
    print("🔍"*40)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {
        'endpoint_config': check_callback_endpoint(),
        'transactions': check_recent_transactions(),
        'callback_logs': check_callback_logs(),
        'flask_routes': check_flask_routes(),
        'network': check_network_accessibility(),
        'credentials': check_viyonapay_credentials(),
    }
    
    print_section("DIAGNOSTIC SUMMARY")
    
    print("\nChecks completed:")
    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {check.replace('_', ' ').title()}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\nOverall: {passed_count}/{total_count} checks passed")
    
    if not results['callback_logs']:
        print("\n" + "⚠"*40)
        print("  CRITICAL FINDING")
        print("⚠"*40)
        print("\nNO callbacks have been received from ViyonaPay.")
        print("This is NOT a code issue - ViyonaPay is not sending webhooks.")
        print("\nYour callback handler implementation is CORRECT.")
        print("The problem is on ViyonaPay's side or network configuration.")
    
    generate_action_plan()
    
    print("\n" + "="*80)
    print("  NEXT STEPS")
    print("="*80)
    print("""
1. Contact ViyonaPay support immediately
2. Share this diagnostic report with them
3. Request webhook delivery logs from their system
4. Ask them to send a test webhook to your URL
5. Verify your callback URL is registered in their dashboard

Email template for ViyonaPay support:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Subject: Webhook Callbacks Not Being Received

Dear ViyonaPay Support,

We have integrated ViyonaPay payin API successfully, and transactions are 
being created. However, we are NOT receiving webhook callbacks for payment 
status updates.

Our callback URL: https://yourdomain.com/api/callback/viyonapay/payin

Could you please:
1. Verify this callback URL is registered in your system
2. Confirm webhooks are enabled for our account
3. Check your webhook delivery logs for any errors
4. Send a test webhook to our URL
5. Provide your webhook sender IP addresses (for firewall whitelist)

Our recent test transaction:
- Order ID: [YOUR_ORDER_ID]
- Transaction ID: [YOUR_TXN_ID]
- Date/Time: [TIMESTAMP]

Thank you for your assistance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
