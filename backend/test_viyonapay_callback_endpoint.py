#!/usr/bin/env python3
"""
Test ViyonaPay Callback Endpoint
Simulates a ViyonaPay webhook to verify your endpoint is reachable and working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime
import time

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_callback_endpoint():
    """Test the ViyonaPay callback endpoint with sample data"""
    
    print("\n" + "🧪"*40)
    print("  VIYONAPAY CALLBACK ENDPOINT TESTER")
    print("🧪"*40)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get backend URL
    try:
        from config import Config
        backend_url = getattr(Config, 'BACKEND_URL', None)
        
        if not backend_url:
            print("⚠️  BACKEND_URL not configured in config.py")
            print("   Using default: https://api.moneyone.co.in")
            backend_url = "https://api.moneyone.co.in"
        
        callback_url = f"{backend_url}/api/callback/viyonapay/payin"
        
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        print("   Using default: https://api.moneyone.co.in")
        callback_url = "https://api.moneyone.co.in/api/callback/viyonapay/payin"
    
    print_section("1. ENDPOINT CONFIGURATION")
    print(f"Testing callback URL: {callback_url}")
    print()
    
    # Prepare test webhook payload (matching ViyonaPay format)
    test_payloads = [
        {
            "name": "SUCCESS - UPI Payment",
            "data": {
                "paymentStatus": "SUCCESS",
                "transactionId": "TEST_VIYONA_" + str(int(time.time())),
                "paymentMode": "UPI",
                "cardType": "",
                "cardMasked": "",
                "orderId": "TEST_ORDER_" + str(int(time.time())),
                "customerName": "Test Customer",
                "customerEmail": "test@example.com",
                "customerPhoneNumber": "9999999999",
                "amount": "100",
                "bankRefId": "TEST_UTR_" + str(int(time.time()))
            }
        },
        {
            "name": "SUCCESS - Card Payment",
            "data": {
                "paymentStatus": "SUCCESS",
                "transactionId": "TEST_VIYONA_CARD_" + str(int(time.time())),
                "paymentMode": "CARD",
                "cardType": "CREDIT",
                "cardMasked": "4111XXXXXXXX1234",
                "orderId": "TEST_ORDER_CARD_" + str(int(time.time())),
                "customerName": "Test Customer",
                "customerEmail": "test@example.com",
                "customerPhoneNumber": "9999999999",
                "amount": "500",
                "bankRefId": "TEST_BANK_REF_" + str(int(time.time()))
            }
        },
        {
            "name": "FAILED - Payment Failed",
            "data": {
                "paymentStatus": "FAILED",
                "transactionId": "TEST_VIYONA_FAIL_" + str(int(time.time())),
                "paymentMode": "UPI",
                "cardType": "",
                "cardMasked": "",
                "orderId": "TEST_ORDER_FAIL_" + str(int(time.time())),
                "customerName": "Test Customer",
                "customerEmail": "test@example.com",
                "customerPhoneNumber": "9999999999",
                "amount": "200",
                "bankRefId": ""
            }
        },
        {
            "name": "PENDING - Payment Processing",
            "data": {
                "paymentStatus": "PENDING",
                "transactionId": "TEST_VIYONA_PEND_" + str(int(time.time())),
                "paymentMode": "NETBANKING",
                "cardType": "",
                "cardMasked": "",
                "orderId": "TEST_ORDER_PEND_" + str(int(time.time())),
                "customerName": "Test Customer",
                "customerEmail": "test@example.com",
                "customerPhoneNumber": "9999999999",
                "amount": "300",
                "bankRefId": ""
            }
        }
    ]
    
    print_section("2. RUNNING TESTS")
    
    results = []
    
    for i, test_case in enumerate(test_payloads, 1):
        print(f"\nTest {i}/{len(test_payloads)}: {test_case['name']}")
        print("-" * 80)
        
        payload = test_case['data']
        
        print(f"Payload:")
        print(json.dumps(payload, indent=2))
        print()
        
        try:
            # Send POST request to callback endpoint
            print(f"Sending POST request to: {callback_url}")
            
            response = requests.post(
                callback_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'X-TIMESTAMP': str(int(time.time())),
                    'X-Request-Id': f"TEST_REQ_{int(time.time())}",
                    'User-Agent': 'ViyonaPay-Webhook-Test/1.0'
                },
                timeout=10
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body:")
            
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))
            except:
                print(response.text[:500])
            
            if response.status_code == 200:
                print(f"\n✅ Test PASSED - Endpoint is reachable and responding")
                results.append({
                    'test': test_case['name'],
                    'status': 'PASS',
                    'code': response.status_code
                })
            elif response.status_code == 404:
                print(f"\n❌ Test FAILED - Endpoint not found (404)")
                print(f"   Check if viyonapay_callback_routes is registered in app.py")
                results.append({
                    'test': test_case['name'],
                    'status': 'FAIL',
                    'code': response.status_code,
                    'error': 'Endpoint not found'
                })
            else:
                print(f"\n⚠️  Test WARNING - Unexpected status code: {response.status_code}")
                results.append({
                    'test': test_case['name'],
                    'status': 'WARNING',
                    'code': response.status_code
                })
            
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ Test FAILED - Connection Error")
            print(f"   Cannot connect to {callback_url}")
            print(f"   Error: {e}")
            print(f"\n   Possible reasons:")
            print(f"   1. Backend server is not running")
            print(f"   2. Wrong URL configured")
            print(f"   3. Firewall blocking the connection")
            results.append({
                'test': test_case['name'],
                'status': 'FAIL',
                'error': 'Connection refused'
            })
            
        except requests.exceptions.Timeout:
            print(f"\n❌ Test FAILED - Request Timeout")
            print(f"   Server took too long to respond")
            results.append({
                'test': test_case['name'],
                'status': 'FAIL',
                'error': 'Timeout'
            })
            
        except Exception as e:
            print(f"\n❌ Test FAILED - Unexpected Error")
            print(f"   Error: {e}")
            results.append({
                'test': test_case['name'],
                'status': 'FAIL',
                'error': str(e)
            })
        
        print()
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print_section("3. TEST SUMMARY")
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    warnings = sum(1 for r in results if r['status'] == 'WARNING')
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")
    print()
    
    for result in results:
        status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
        print(f"{status_icon} {result['test']}")
        if 'code' in result:
            print(f"   Status Code: {result['code']}")
        if 'error' in result:
            print(f"   Error: {result['error']}")
    
    print_section("4. VERIFICATION")
    
    if passed > 0:
        print("""
✅ Your callback endpoint IS REACHABLE and responding!

Now check your database to verify the test callbacks were logged:

1. Check callback_logs table:
   
   SELECT * FROM callback_logs 
   WHERE callback_url LIKE '%viyonapay%' 
   ORDER BY created_at DESC 
   LIMIT 5;

2. If you see the test callbacks in the logs, your endpoint is working correctly.

3. The issue is that ViyonaPay is NOT sending real webhooks to your server.

NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Contact ViyonaPay Support:
   - Confirm your callback URL is registered: {callback_url}
   - Ask them to enable webhooks for your account
   - Request webhook delivery logs from their side
   - Ask them to send a test webhook

2. Verify Network Configuration:
   - Ensure your server accepts HTTPS POST requests
   - Check firewall rules allow incoming traffic
   - Verify SSL certificate is valid
   - Check if any WAF/CDN is blocking ViyonaPay's IPs

3. Test from External Network:
   Run this command from a different server/network:
   
   curl -X POST {callback_url} \\
        -H 'Content-Type: application/json' \\
        -d '{{"paymentStatus":"SUCCESS","transactionId":"TEST123","orderId":"TEST_ORDER","amount":"100"}}'
""".format(callback_url=callback_url))
    else:
        print("""
❌ Your callback endpoint is NOT REACHABLE!

TROUBLESHOOTING STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Check if backend server is running:
   
   ps aux | grep python
   
   or
   
   systemctl status your-backend-service

2. Verify Flask route is registered:
   
   Check app.py contains:
   from viyonapay_callback_routes import viyonapay_callback_bp
   app.register_blueprint(viyonapay_callback_bp)

3. Check server logs for errors:
   
   tail -f /var/log/your-app/app.log

4. Test locally first:
   
   If testing on same server, try:
   curl -X POST http://localhost:5000/api/callback/viyonapay/payin \\
        -H 'Content-Type: application/json' \\
        -d '{{"paymentStatus":"SUCCESS","transactionId":"TEST123","orderId":"TEST_ORDER","amount":"100"}}'

5. Check firewall rules:
   
   sudo ufw status
   sudo iptables -L

6. Verify BACKEND_URL in config.py is correct
""")
    
    print("\n" + "="*80 + "\n")
    
    return passed > 0

if __name__ == "__main__":
    success = test_callback_endpoint()
    sys.exit(0 if success else 1)
