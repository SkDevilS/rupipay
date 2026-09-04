#!/usr/bin/env python3
"""
PayTouch Callback Endpoint Tester
Tests if the PayTouch callback endpoint is working properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def test_paytouch_callback_endpoint():
    """
    Test the PayTouch callback endpoint with sample data
    """
    
    print("=" * 80)
    print(f"PayTouch Callback Endpoint Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Test endpoint URL
    callback_url = "https://api.moneyone.co.in/api/callback/paytouch/payout"
    local_test_url = "http://localhost:5000/api/callback/paytouch/payout"
    
    # Sample callback data that PayTouch might send
    test_callbacks = [
        {
            "name": "Success Callback Test",
            "data": {
                "transaction_id": "TEST_TXN_SUCCESS_001",
                "external_ref": "TEST_REF_SUCCESS_001",
                "status": "SUCCESS",
                "amount": "100.00",
                "utr_no": "TEST_UTR_123456789",
                "message": "Transaction completed successfully"
            }
        },
        {
            "name": "Failed Callback Test",
            "data": {
                "transaction_id": "TEST_TXN_FAILED_001",
                "external_ref": "TEST_REF_FAILED_001",
                "status": "FAILED",
                "amount": "50.00",
                "message": "Insufficient balance"
            }
        },
        {
            "name": "Pending Callback Test",
            "data": {
                "transaction_id": "TEST_TXN_PENDING_001",
                "external_ref": "TEST_REF_PENDING_001",
                "status": "PENDING",
                "amount": "200.00",
                "message": "Transaction is being processed"
            }
        }
    ]
    
    # Test both local and production endpoints
    test_urls = [
        ("Local Endpoint", local_test_url),
        ("Production Endpoint", callback_url)
    ]
    
    for url_name, test_url in test_urls:
        print(f"\n🔍 Testing {url_name}: {test_url}")
        print("-" * 60)
        
        # First, test if endpoint is reachable
        try:
            # Test with GET request first (should return method not allowed)
            get_response = requests.get(test_url, timeout=10)
            print(f"GET Request Response: {get_response.status_code}")
            
            if get_response.status_code == 405:
                print("✅ Endpoint exists (Method Not Allowed for GET is expected)")
            elif get_response.status_code == 404:
                print("❌ Endpoint not found (404)")
                continue
            else:
                print(f"⚠️  Unexpected GET response: {get_response.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach endpoint: {e}")
            continue
        
        # Test with sample callback data
        for test_case in test_callbacks:
            print(f"\n📤 Testing: {test_case['name']}")
            print(f"Data: {json.dumps(test_case['data'], indent=2)}")
            
            try:
                response = requests.post(
                    test_url,
                    json=test_case['data'],
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"Response Status: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                
                try:
                    response_json = response.json()
                    print(f"Response Body: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"Response Body (text): {response.text}")
                
                if response.status_code == 200:
                    print("✅ Callback processed successfully")
                elif response.status_code == 404:
                    print("❌ Transaction not found (expected for test data)")
                elif response.status_code == 400:
                    print("⚠️  Bad request - check data format")
                elif response.status_code == 500:
                    print("❌ Server error - check logs")
                else:
                    print(f"⚠️  Unexpected response: {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed: {e}")
            
            print("-" * 40)
    
    # Test endpoint accessibility from external sources
    print(f"\n🌐 External Accessibility Test")
    print("-" * 60)
    
    print("Testing if PayTouch can reach your callback endpoint...")
    
    # Test with curl-like request
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'PayTouch-Webhook/1.0'
        }
        
        test_data = {
            "transaction_id": "EXTERNAL_TEST_001",
            "status": "SUCCESS",
            "message": "External accessibility test"
        }
        
        response = requests.post(
            callback_url,
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        print(f"External Test Response: {response.status_code}")
        
        if response.status_code in [200, 404]:  # 404 is OK for test data
            print("✅ Endpoint is externally accessible")
        else:
            print(f"⚠️  Potential accessibility issue: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ External accessibility test failed: {e}")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    
    print("1. ✅ Verify callback endpoint is accessible: https://api.moneyone.co.in/api/callback/paytouch/payout")
    print("2. 🔧 Check PayTouch dashboard callback configuration")
    print("3. 📋 Ensure PayTouch has the correct callback URL configured")
    print("4. 🔍 Monitor server logs for incoming callback requests")
    print("5. 📞 Contact PayTouch support to verify webhook setup")
    
    print(f"\n📋 PayTouch Callback URL Configuration:")
    print(f"   URL: https://api.moneyone.co.in/api/callback/paytouch/payout")
    print(f"   Method: POST")
    print(f"   Content-Type: application/json")
    
    print(f"\n🔍 To check if callbacks are being received:")
    print(f"   1. Monitor server access logs for POST requests to /api/callback/paytouch/payout")
    print(f"   2. Check application logs for callback processing messages")
    print(f"   3. Run: python3 check_paytouch_callback_activity.py")

if __name__ == "__main__":
    test_paytouch_callback_endpoint()