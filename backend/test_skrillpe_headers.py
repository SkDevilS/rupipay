#!/usr/bin/env python3
"""
SkrillPe Headers Test Script
Test SkrillPe API with correct headers format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
import base64
from config import Config

def test_headers_format():
    """Test different header formats for SkrillPe API"""
    print("🔍 SkrillPe Headers Test")
    print("=" * 60)
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    auth_api_key = Config.SKRILLPE_AUTH_API_KEY
    auth_api_password = Config.SKRILLPE_AUTH_API_PASSWORD
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print(f"Base URL: {base_url}")
    print(f"Company Alias: {company_alias}")
    print(f"AUTH-API_KEY: {'Set' if auth_api_key else 'Not set'}")
    print(f"AUTH-API_PASSWORD: {'Set' if auth_api_password else 'Not set'}")
    print(f"Bearer Token: {'Set' if bearer_token else 'Not set'}")
    
    # Test payload
    payload = {
        'transactionId': f'TEST_HEADERS_{int(time.time())}',
        'amount': '350.00',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📦 Test Payload:")
    print(json.dumps(payload, indent=2))
    
    # API endpoint
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    print(f"\n🚀 API Endpoint: {url}")
    
    # Test 1: Current format (Bearer token)
    print(f"\n🧪 Test 1: Bearer Token Format")
    print("-" * 40)
    
    headers_bearer = {
        'Authorization': f'Bearer {bearer_token}',
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    
    print(f"Headers:")
    for key, value in headers_bearer.items():
        if 'Authorization' in key:
            print(f"  {key}: Bearer ***")
        elif 'API_KEY' in key or 'PASSWORD' in key:
            print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, headers=headers_bearer, json=payload, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            intent_url = data.get('intentUrl', '')
            tiny_url = data.get('tinyUrl', '')
            reason = data.get('reason', '')
            
            print(f"Success: {'Successful' in reason}")
            print(f"Has intentUrl: {bool(intent_url)}")
            print(f"Has tinyUrl: {bool(tiny_url)}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Basic Auth format
    print(f"\n🧪 Test 2: Basic Auth Format")
    print("-" * 40)
    
    # Create Basic Auth token
    auth_string = f"{auth_api_key}:{auth_api_password}"
    basic_auth_token = base64.b64encode(auth_string.encode()).decode()
    
    headers_basic = {
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Authorization': f'Basic {basic_auth_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"Headers:")
    for key, value in headers_basic.items():
        if 'Authorization' in key:
            print(f"  {key}: Basic ***")
        elif 'API_KEY' in key or 'PASSWORD' in key:
            print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, headers=headers_basic, json=payload, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            intent_url = data.get('intentUrl', '')
            tiny_url = data.get('tinyUrl', '')
            reason = data.get('reason', '')
            
            print(f"Success: {'Successful' in reason}")
            print(f"Has intentUrl: {bool(intent_url)}")
            print(f"Has tinyUrl: {bool(tiny_url)}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Only AUTH headers (no Authorization)
    print(f"\n🧪 Test 3: Only AUTH Headers")
    print("-" * 40)
    
    headers_auth_only = {
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    
    print(f"Headers:")
    for key, value in headers_auth_only.items():
        if 'API_KEY' in key or 'PASSWORD' in key:
            print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, headers=headers_auth_only, json=payload, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            intent_url = data.get('intentUrl', '')
            tiny_url = data.get('tinyUrl', '')
            reason = data.get('reason', '')
            
            print(f"Success: {'Successful' in reason}")
            print(f"Has intentUrl: {bool(intent_url)}")
            print(f"Has tinyUrl: {bool(tiny_url)}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_service_with_new_headers():
    """Test SkrillPe service with updated headers"""
    print(f"\n🧪 Test 4: Service with Updated Headers")
    print("-" * 40)
    
    try:
        from skrillpe_service import skrillpe_service
        
        # Test data
        merchant_id = "7679022140"
        order_data = {
            'amount': '350.00',
            'orderid': f'ORD{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"Testing with merchant ID: {merchant_id}")
        print(f"Amount: ₹{order_data['amount']}")
        
        # Call service
        result = skrillpe_service.create_payin_order(merchant_id, order_data)
        
        if result:
            print(f"\n📊 Service Result:")
            print(json.dumps(result, indent=2, default=str))
            
            if result.get('success'):
                # Check URL fields
                url_fields = ['payment_url', 'upi_link', 'intent_url', 'tiny_url', 'qr_string']
                has_urls = False
                
                print(f"\n🔍 URL Fields Check:")
                for field in url_fields:
                    value = result.get(field, '')
                    has_value = bool(value and value.strip())
                    if has_value:
                        has_urls = True
                    status = "✅" if has_value else "❌"
                    print(f"  {field}: {status} '{value}'")
                
                if has_urls:
                    print(f"\n✅ SUCCESS: Headers are working correctly!")
                else:
                    print(f"\n⚠️  Headers work but URLs still empty (SkrillPe issue)")
            else:
                print(f"\n❌ Service failed: {result.get('message')}")
        else:
            print(f"\n❌ No response from service")
            
    except Exception as e:
        print(f"💥 Service Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    print("🔍 SkrillPe Headers Authentication Test")
    print("=" * 80)
    print("Testing different header formats to find the correct one")
    print("=" * 80)
    
    # Test different header formats
    test_headers_format()
    
    # Test service with updated headers
    test_service_with_new_headers()
    
    # Summary
    print(f"\n" + "=" * 80)
    print("🎯 Headers Test Summary")
    print("=" * 80)
    
    print(f"📋 What we tested:")
    print(f"1. Bearer Token format (original)")
    print(f"2. Basic Auth format (your suggestion)")
    print(f"3. Only AUTH headers (no Authorization)")
    print(f"4. Service integration with updated headers")
    
    print(f"\n📋 Next Steps:")
    print(f"1. Check which header format works (returns 200)")
    print(f"2. If all return 200 but empty URLs, it's SkrillPe's issue")
    print(f"3. Contact SkrillPe team with working header format")
    print(f"4. Request fix for empty intentUrl/tinyUrl generation")

if __name__ == "__main__":
    main()