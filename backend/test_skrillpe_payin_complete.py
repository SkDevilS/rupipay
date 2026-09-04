#!/usr/bin/env python3
"""
Complete SkrillPe Payin Test Script
Tests the entire flow from API call to response mapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
from config import Config
from skrillpe_service import skrillpe_service

def test_skrillpe_api_direct():
    """Test SkrillPe API directly to see raw response"""
    print("🔍 Step 1: Testing SkrillPe API Directly")
    print("=" * 60)
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print(f"Base URL: {base_url}")
    print(f"Company Alias: {company_alias}")
    print(f"Bearer Token: {bearer_token[:20]}..." if bearer_token else "Bearer Token: Not set")
    
    # Headers
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    
    # Test payload with exact mapping
    payload = {
        'transactionId': f'TEST_TXN_{int(time.time())}',
        'amount': '11.00',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📦 Request Payload:")
    print(json.dumps(payload, indent=2))
    
    # Make API call
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    
    try:
        print(f"\n🚀 Calling: {url}")
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n📊 Response Details:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n✅ Parsed JSON Response:")
                print(json.dumps(data, indent=2))
                
                # Analyze each field
                print(f"\n🔍 Field Analysis:")
                for key, value in data.items():
                    print(f"  {key}: '{value}' (type: {type(value).__name__})")
                
                return data
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                return None
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Request Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_skrillpe_service():
    """Test SkrillPe service method"""
    print("\n🔍 Step 2: Testing SkrillPe Service Method")
    print("=" * 60)
    
    # Test data
    merchant_id = "9000000001"
    order_data = {
        'amount': '11.00',
        'orderid': f'ORD{int(time.time())}',
        'payee_fname': 'Test',
        'payee_lname': 'Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com'
    }
    
    print(f"Merchant ID: {merchant_id}")
    print(f"Order Data:")
    print(json.dumps(order_data, indent=2))
    
    # Call service
    print(f"\n🚀 Calling skrillpe_service.create_payin_order...")
    result = skrillpe_service.create_payin_order(merchant_id, order_data)
    
    print(f"\n📊 Service Response:")
    print(json.dumps(result, indent=2, default=str))
    
    # Analyze response
    print(f"\n🔍 Response Analysis:")
    if result.get('success'):
        print("✅ Success: True")
        
        # Check each URL field
        url_fields = ['qr_string', 'upi_link', 'intent_url', 'tiny_url']
        for field in url_fields:
            value = result.get(field, '')
            status = "✅ Present" if value else "❌ Empty"
            print(f"  {field}: {status} - '{value}'")
    else:
        print(f"❌ Success: False")
        print(f"❌ Message: {result.get('message')}")
    
    return result

def test_payin_routes_simulation():
    """Simulate how payin routes would handle the response"""
    print("\n🔍 Step 3: Testing Payin Routes Response Mapping")
    print("=" * 60)
    
    # Get service result
    service_result = test_skrillpe_service()
    
    if not service_result.get('success'):
        print("❌ Service failed, cannot test routes mapping")
        return
    
    # Simulate payin routes response mapping
    response_data = {
        'txn_id': service_result['txn_id'],
        'order_id': service_result['order_id'],
        'amount': service_result['amount'],
        'charge_amount': service_result.get('charge_amount', 0),
        'net_amount': service_result.get('net_amount', service_result['amount']),
        'payment_url': service_result.get('payment_url', ''),
        'payment_params': service_result.get('payment_params', {}),
        'qr_string': service_result.get('qr_string', ''),
        'qr_code_url': service_result.get('qr_code_url', ''),
        'upi_link': service_result.get('upi_link', ''),
        'payment_link': service_result.get('payment_link', ''),
        'intent_url': service_result.get('intent_url', ''),
        'tiny_url': service_result.get('tiny_url', ''),
        'expires_in': service_result.get('expires_in', 0),
        'vpa': service_result.get('vpa', ''),
        'pg_partner': 'SKRILLPE'
    }
    
    print(f"📊 Final Response Data (what frontend receives):")
    print(json.dumps(response_data, indent=2))
    
    # Check if any payment method is available
    payment_methods = [
        response_data.get('intent_url'),
        response_data.get('upi_link'),
        response_data.get('qr_string'),
        response_data.get('payment_url')
    ]
    
    available_methods = [method for method in payment_methods if method]
    
    print(f"\n🎯 Payment Methods Available: {len(available_methods)}")
    for i, method in enumerate(available_methods, 1):
        print(f"  {i}. {method}")
    
    if not available_methods:
        print("❌ No payment methods available for frontend!")
    
    return response_data

def debug_configuration():
    """Debug SkrillPe configuration"""
    print("\n🔍 Step 4: Configuration Debug")
    print("=" * 60)
    
    config_items = [
        ('SKRILLPE_BASE_URL', Config.SKRILLPE_BASE_URL),
        ('SKRILLPE_BEARER_TOKEN', Config.SKRILLPE_BEARER_TOKEN),
        ('SKRILLPE_AUTH_API_KEY', Config.SKRILLPE_AUTH_API_KEY),
        ('SKRILLPE_AUTH_API_PASSWORD', Config.SKRILLPE_AUTH_API_PASSWORD),
        ('SKRILLPE_COMPANY_ALIAS', Config.SKRILLPE_COMPANY_ALIAS),
    ]
    
    print("Configuration Status:")
    for name, value in config_items:
        if value:
            display_value = f"{value[:20]}..." if len(str(value)) > 20 else value
            print(f"  ✅ {name}: {display_value}")
        else:
            print(f"  ❌ {name}: Not set")

def main():
    """Run complete test suite"""
    print("🧪 SkrillPe Complete Integration Test")
    print("=" * 80)
    
    try:
        # Step 1: Debug configuration
        debug_configuration()
        
        # Step 2: Test API directly
        api_response = test_skrillpe_api_direct()
        
        # Step 3: Test service method
        service_response = test_skrillpe_service()
        
        # Step 4: Test routes mapping
        routes_response = test_payin_routes_simulation()
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 Test Summary")
        print("=" * 80)
        
        if api_response:
            print("✅ Direct API call: Success")
            print(f"   Response fields: {list(api_response.keys())}")
        else:
            print("❌ Direct API call: Failed")
        
        if service_response and service_response.get('success'):
            print("✅ Service method: Success")
            has_urls = any([
                service_response.get('qr_string'),
                service_response.get('upi_link'),
                service_response.get('intent_url')
            ])
            print(f"   URLs available: {'Yes' if has_urls else 'No'}")
        else:
            print("❌ Service method: Failed")
        
        if routes_response:
            payment_available = any([
                routes_response.get('intent_url'),
                routes_response.get('upi_link'),
                routes_response.get('qr_string')
            ])
            print(f"✅ Routes mapping: Success")
            print(f"   Payment methods: {'Available' if payment_available else 'None'}")
        else:
            print("❌ Routes mapping: Failed")
        
        # Recommendations
        print("\n📋 Recommendations:")
        if not api_response:
            print("  1. Check SkrillPe API credentials and endpoint")
            print("  2. Verify network connectivity to SkrillPe servers")
        elif api_response and not service_response.get('success'):
            print("  1. Check service response parsing logic")
            print("  2. Verify success condition detection")
        elif service_response.get('success') and not any([service_response.get('qr_string'), service_response.get('intent_url')]):
            print("  1. Check API response field mapping")
            print("  2. Verify intentUrl extraction from API response")
        else:
            print("  ✅ Integration appears to be working correctly!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()