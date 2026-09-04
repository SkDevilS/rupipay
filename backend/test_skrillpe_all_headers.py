#!/usr/bin/env python3
"""
Complete SkrillPe API Test Script
Tests all header combinations and generates orders with merchant ID 7679022140 and amount 300+
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
import base64
from config import Config

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"🔍 {title}")
    print(f"{'='*80}")

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-'*60}")
    print(f"🧪 {title}")
    print(f"{'-'*60}")

def test_header_combination(test_name, headers, payload, url):
    """Test a specific header combination"""
    print(f"\n📋 {test_name}")
    print("Headers:")
    for key, value in headers.items():
        if 'Authorization' in key or 'TOKEN' in key or 'PASSWORD' in key or 'KEY' in key:
            if 'Basic' in str(value):
                print(f"  {key}: Basic ***")
            elif 'Bearer' in str(value):
                print(f"  {key}: Bearer ***")
            else:
                print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    try:
        print(f"\n🚀 Making API call...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        print(f"📊 Response Body: {response.text}")
        
        # Analyze response
        success = False
        has_urls = False
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check success indicators
                code = data.get('code', '')
                reason = data.get('reason', '')
                message = data.get('message', '')
                intent_url = data.get('intentUrl', '')
                tiny_url = data.get('tinyUrl', '')
                
                # Determine success
                success_indicators = [
                    'Successful' in reason,
                    'successful' in reason.lower(),
                    'Successful' in message,
                    'successful' in message.lower(),
                    code == '0',
                    code == 0
                ]
                
                success = any(success_indicators)
                has_urls = bool(intent_url or tiny_url)
                
                print(f"\n🔍 Response Analysis:")
                print(f"  code: '{code}'")
                print(f"  reason: '{reason}'")
                print(f"  message: '{message}'")
                print(f"  intentUrl: '{intent_url}'")
                print(f"  tinyUrl: '{tiny_url}'")
                print(f"  Success: {success}")
                print(f"  Has URLs: {has_urls}")
                
                if success and has_urls:
                    print(f"✅ PERFECT: Success with URLs!")
                elif success and not has_urls:
                    print(f"⚠️  SUCCESS but empty URLs (SkrillPe issue)")
                elif not success:
                    print(f"❌ FAILED: No success indication")
                
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response")
                
        elif response.status_code == 401:
            print(f"❌ AUTHENTICATION FAILED")
        elif response.status_code == 403:
            print(f"❌ AUTHORIZATION FAILED")
        else:
            print(f"❌ API ERROR: {response.status_code}")
        
        return {
            'status_code': response.status_code,
            'success': success,
            'has_urls': has_urls,
            'response_text': response.text
        }
        
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return {
            'status_code': 0,
            'success': False,
            'has_urls': False,
            'error': str(e)
        }

def test_all_header_combinations():
    """Test all possible header combinations"""
    print_section("SkrillPe API Header Combinations Test")
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    auth_api_key = Config.SKRILLPE_AUTH_API_KEY
    auth_api_password = Config.SKRILLPE_AUTH_API_PASSWORD
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print(f"📋 Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Company Alias: {company_alias}")
    print(f"  AUTH-API_KEY: {'Set' if auth_api_key else 'Not set'}")
    print(f"  AUTH-API_PASSWORD: {'Set' if auth_api_password else 'Not set'}")
    print(f"  Bearer Token: {'Set' if bearer_token else 'Not set'}")
    
    # Test payload with merchant ID 7679022140 and amount above 300
    payload = {
        'transactionId': f'TEST_ALL_HEADERS_{int(time.time())}',
        'amount': '350.00',  # Above 300 as requested
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📦 Test Payload:")
    print(json.dumps(payload, indent=2))
    
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    print(f"\n🚀 API Endpoint: {url}")
    
    # Create Basic Auth token
    auth_string = f"{auth_api_key}:{auth_api_password}"
    basic_auth_token = base64.b64encode(auth_string.encode()).decode()
    
    # Test results storage
    test_results = []
    
    print_subsection("Testing All Header Combinations")
    
    # Test 1: Bearer Token + AUTH headers (Current implementation)
    headers1 = {
        'Authorization': f'Bearer {bearer_token}',
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    result1 = test_header_combination("Test 1: Bearer + AUTH Headers", headers1, payload, url)
    test_results.append(('Bearer + AUTH', result1))
    
    # Test 2: Basic Auth + AUTH headers (Your suggestion)
    headers2 = {
        'Authorization': f'Basic {basic_auth_token}',
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    result2 = test_header_combination("Test 2: Basic Auth + AUTH Headers", headers2, payload, url)
    test_results.append(('Basic + AUTH', result2))
    
    # Test 3: Only AUTH headers (No Authorization)
    headers3 = {
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    result3 = test_header_combination("Test 3: Only AUTH Headers", headers3, payload, url)
    test_results.append(('Only AUTH', result3))
    
    # Test 4: Only Bearer Token
    headers4 = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    result4 = test_header_combination("Test 4: Only Bearer Token", headers4, payload, url)
    test_results.append(('Only Bearer', result4))
    
    # Test 5: Only Basic Auth
    headers5 = {
        'Authorization': f'Basic {basic_auth_token}',
        'Content-Type': 'application/json'
    }
    result5 = test_header_combination("Test 5: Only Basic Auth", headers5, payload, url)
    test_results.append(('Only Basic', result5))
    
    # Test 6: Alternative header names (in case SkrillPe uses different names)
    headers6 = {
        'X-API-KEY': auth_api_key,
        'X-API-PASSWORD': auth_api_password,
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    result6 = test_header_combination("Test 6: X-API Headers + Bearer", headers6, payload, url)
    test_results.append(('X-API + Bearer', result6))
    
    # Test 7: API Key in Authorization header
    api_key_auth = base64.b64encode(f"{auth_api_key}:".encode()).decode()
    headers7 = {
        'Authorization': f'Basic {api_key_auth}',
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    result7 = test_header_combination("Test 7: API Key in Auth + Password", headers7, payload, url)
    test_results.append(('API Key Auth', result7))
    
    return test_results

def test_service_integration():
    """Test the service integration with updated headers"""
    print_section("Service Integration Test")
    
    try:
        from skrillpe_service import skrillpe_service
        
        # Test data with merchant ID 7679022140 and amount above 300
        merchant_id = "7679022140"
        order_data = {
            'amount': '350.00',  # Above 300 as requested
            'orderid': f'ORD{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"📋 Test Parameters:")
        print(f"  Merchant ID: {merchant_id}")
        print(f"  Order ID: {order_data['orderid']}")
        print(f"  Amount: ₹{order_data['amount']}")
        print(f"  Customer: {order_data['payee_fname']} {order_data['payee_lname']}")
        print(f"  Mobile: {order_data['payee_mobile']}")
        
        print(f"\n🚀 Calling skrillpe_service.create_payin_order...")
        result = skrillpe_service.create_payin_order(merchant_id, order_data)
        
        if result:
            print(f"\n📊 Service Response:")
            print(json.dumps(result, indent=2, default=str))
            
            if result.get('success'):
                print(f"\n✅ Service call successful!")
                
                # Check all URL fields
                url_fields = [
                    'payment_url', 'upi_link', 'intent_url', 'tiny_url', 
                    'qr_string', 'payment_link', 'qr_code_url'
                ]
                
                print(f"\n🔍 URL Fields Analysis:")
                has_any_url = False
                for field in url_fields:
                    value = result.get(field, '')
                    has_value = bool(value and value.strip())
                    if has_value:
                        has_any_url = True
                    status = "✅" if has_value else "❌"
                    print(f"  {field}: {status} '{value}'")
                
                if has_any_url:
                    print(f"\n🎉 SUCCESS: Service integration working with URLs!")
                else:
                    print(f"\n⚠️  Service works but no URLs (SkrillPe empty URL issue)")
                
                # Check raw response
                if 'raw_response' in result:
                    print(f"\n🔍 Raw SkrillPe API Response:")
                    print(json.dumps(result['raw_response'], indent=2))
                
                return result
            else:
                print(f"\n❌ Service failed: {result.get('message')}")
                return result
        else:
            print(f"\n❌ No response from service")
            return None
            
    except Exception as e:
        print(f"💥 Service Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_different_amounts():
    """Test with different amounts to see if amount affects URL generation"""
    print_section("Amount Variation Test")
    
    amounts = ['300.00', '350.00', '500.00', '1000.00', '2000.00']
    
    # Use the best header combination (we'll determine this from previous tests)
    auth_api_key = Config.SKRILLPE_AUTH_API_KEY
    auth_api_password = Config.SKRILLPE_AUTH_API_PASSWORD
    basic_auth_token = base64.b64encode(f"{auth_api_key}:{auth_api_password}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {basic_auth_token}',
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    
    url = f"{Config.SKRILLPE_BASE_URL}/api/skrill/upi/qr/send/intent/WL"
    
    for amount in amounts:
        print(f"\n💰 Testing Amount: ₹{amount}")
        
        payload = {
            'transactionId': f'AMT_TEST_{amount.replace(".", "")}_{int(time.time())}',
            'amount': amount,
            'customerNumber': '9876543210',
            'CompanyAlise': Config.SKRILLPE_COMPANY_ALIAS
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                code = data.get('code', '')
                reason = data.get('reason', '')
                intent_url = data.get('intentUrl', '')
                tiny_url = data.get('tinyUrl', '')
                
                success = 'Successful' in reason or code == '0'
                has_urls = bool(intent_url or tiny_url)
                
                print(f"  Status: {response.status_code}")
                print(f"  Success: {success}")
                print(f"  Has URLs: {has_urls}")
                print(f"  Reason: {reason}")
                
                if success and has_urls:
                    print(f"  ✅ PERFECT: This amount works!")
                elif success and not has_urls:
                    print(f"  ⚠️  Success but empty URLs")
                else:
                    print(f"  ❌ Failed")
            else:
                print(f"  ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"  💥 Error: {e}")

def generate_summary(test_results):
    """Generate a summary of all test results"""
    print_section("Test Results Summary")
    
    print(f"📊 Header Combination Results:")
    print(f"{'Test Name':<20} {'Status':<10} {'Success':<10} {'Has URLs':<10} {'Result'}")
    print(f"{'-'*70}")
    
    working_combinations = []
    
    for test_name, result in test_results:
        status = result.get('status_code', 0)
        success = result.get('success', False)
        has_urls = result.get('has_urls', False)
        
        if status == 200:
            status_str = "✅ 200"
        elif status == 401:
            status_str = "❌ 401"
        elif status == 403:
            status_str = "❌ 403"
        else:
            status_str = f"❌ {status}"
        
        success_str = "✅ Yes" if success else "❌ No"
        urls_str = "✅ Yes" if has_urls else "❌ No"
        
        if success and has_urls:
            result_str = "🎉 PERFECT"
            working_combinations.append(test_name)
        elif success and not has_urls:
            result_str = "⚠️  Empty URLs"
        elif status == 200:
            result_str = "⚠️  No Success"
        else:
            result_str = "❌ Failed"
        
        print(f"{test_name:<20} {status_str:<10} {success_str:<10} {urls_str:<10} {result_str}")
    
    print(f"\n🎯 Conclusions:")
    
    if working_combinations:
        print(f"✅ Working header combinations:")
        for combo in working_combinations:
            print(f"  - {combo}")
        print(f"✅ Use any of these combinations for production")
    else:
        # Check if any returned 200 with success
        success_combinations = [name for name, result in test_results 
                              if result.get('status_code') == 200 and result.get('success')]
        
        if success_combinations:
            print(f"⚠️  Header combinations that work but return empty URLs:")
            for combo in success_combinations:
                print(f"  - {combo}")
            print(f"⚠️  This confirms the SkrillPe empty URL issue")
            print(f"📞 Contact SkrillPe team about empty intentUrl/tinyUrl")
        else:
            print(f"❌ No working header combinations found")
            print(f"🔧 Check SkrillPe credentials and API configuration")
    
    print(f"\n📋 Next Steps:")
    if working_combinations:
        print(f"1. ✅ Use working header combination in production")
        print(f"2. ✅ Deploy updated SkrillPe integration")
        print(f"3. 🧪 Test with real payments")
    elif any(result.get('success') for _, result in test_results):
        print(f"1. 📞 Contact SkrillPe team about empty intentUrl/tinyUrl issue")
        print(f"2. 🔧 Request fix for URL generation in new API endpoint")
        print(f"3. 🧪 Test with different merchant configurations if suggested")
        print(f"4. ⏳ Wait for SkrillPe team response and fix")
    else:
        print(f"1. 🔧 Verify SkrillPe API credentials")
        print(f"2. 📞 Contact SkrillPe team for correct authentication method")
        print(f"3. 🧪 Test API access with SkrillPe support")

def main():
    """Main test function"""
    print_section("Complete SkrillPe API Test Suite")
    print(f"🎯 Testing with:")
    print(f"  - Merchant ID: 7679022140")
    print(f"  - Amount: ₹350.00 (above 300 as requested)")
    print(f"  - All possible header combinations")
    print(f"  - Service integration")
    print(f"  - Different amount variations")
    
    # Test all header combinations
    test_results = test_all_header_combinations()
    
    # Test service integration
    service_result = test_service_integration()
    
    # Test different amounts
    test_different_amounts()
    
    # Generate summary
    generate_summary(test_results)
    
    # Final recommendation
    print_section("Final Recommendation")
    
    if service_result and service_result.get('success'):
        url_fields = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
        has_urls = any([service_result.get(field) for field in url_fields])
        
        if has_urls:
            print(f"🎉 READY FOR PRODUCTION!")
            print(f"✅ SkrillPe integration is working correctly")
            print(f"✅ Headers are properly configured")
            print(f"✅ URLs are being generated")
        else:
            print(f"⚠️  INTEGRATION WORKS BUT BLOCKED BY SKRILLPE ISSUE")
            print(f"✅ Headers and authentication are correct")
            print(f"✅ API calls are successful")
            print(f"❌ SkrillPe is not generating intentUrl/tinyUrl")
            print(f"📞 Contact SkrillPe team immediately")
    else:
        print(f"❌ INTEGRATION NEEDS FIXING")
        print(f"🔧 Check configuration and credentials")
        print(f"📞 Contact SkrillPe team for support")

if __name__ == "__main__":
    main()