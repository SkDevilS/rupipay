#!/usr/bin/env python3
"""
Simple SkrillPe Test Script
Quick test to check SkrillPe API response and mapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
from config import Config

def test_skrillpe_api():
    """Test SkrillPe API directly"""
    print("🧪 Testing SkrillPe API")
    print("=" * 50)
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print(f"Base URL: {base_url}")
    print(f"Company Alias: {company_alias}")
    print(f"Bearer Token: {'Set' if bearer_token else 'Not set'}")
    
    # Test payload
    payload = {
        'transactionId': f'TEST_{int(time.time())}',
        'amount': '350.00',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📦 Request:")
    print(json.dumps(payload, indent=2))
    
    # Headers
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    
    # API call
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    
    try:
        print(f"\n🚀 Calling: {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n📊 Response:")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔍 Parsed Response:")
            for key, value in data.items():
                print(f"  {key}: '{value}'")
            
            # Check for success indicators
            message = data.get('message', '')
            has_intent = bool(data.get('intentUrl'))
            has_tiny = bool(data.get('tinyUrl'))
            has_code = bool(data.get('code'))
            
            print(f"\n✅ Success Indicators:")
            print(f"  Message contains 'Successful': {'Successful' in message}")
            print(f"  Has intentUrl: {has_intent}")
            print(f"  Has tinyUrl: {has_tiny}")
            print(f"  Has code: {has_code}")
            
            return data
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

def test_service_method():
    """Test SkrillPe service method"""
    print("\n🧪 Testing SkrillPe Service")
    print("=" * 50)
    
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
        
        print(f"Merchant: {merchant_id}")
        print(f"Order: {order_data['orderid']}")
        print(f"Amount: {order_data['amount']}")
        
        # Call service
        result = skrillpe_service.create_payin_order(merchant_id, order_data)
        
        print(f"\n📊 Service Result:")
        print(json.dumps(result, indent=2, default=str))
        
        # Check result
        if result.get('success'):
            print(f"\n✅ Service Success!")
            
            # Check URL fields
            url_fields = ['qr_string', 'upi_link', 'intent_url', 'tiny_url']
            for field in url_fields:
                value = result.get(field, '')
                status = "✅" if value else "❌"
                print(f"  {field}: {status} '{value}'")
        else:
            print(f"\n❌ Service Failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        print(f"💥 Service Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("🔍 SkrillPe Simple Test")
    print("=" * 80)
    
    # Test API directly
    api_result = test_skrillpe_api()
    
    # Test service method
    service_result = test_service_method()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Summary")
    print("=" * 80)
    
    if api_result:
        print("✅ Direct API: Working")
        print(f"   Fields: {list(api_result.keys())}")
    else:
        print("❌ Direct API: Failed")
    
    if service_result and service_result.get('success'):
        print("✅ Service Method: Working")
        has_urls = any([
            service_result.get('qr_string'),
            service_result.get('upi_link'),
            service_result.get('intent_url')
        ])
        print(f"   URLs Available: {'Yes' if has_urls else 'No'}")
    else:
        print("❌ Service Method: Failed")
    
    print("\n📋 Next Steps:")
    if not api_result:
        print("  1. Check SkrillPe API credentials")
        print("  2. Verify API endpoint URL")
        print("  3. Check network connectivity")
    elif api_result and not (service_result and service_result.get('success')):
        print("  1. Check service response parsing")
        print("  2. Review success detection logic")
        print("  3. Check database connection")
    elif service_result and service_result.get('success'):
        has_urls = any([
            service_result.get('qr_string'),
            service_result.get('upi_link'),
            service_result.get('intent_url')
        ])
        if not has_urls:
            print("  1. Check URL field extraction from API response")
            print("  2. Verify intentUrl mapping")
        else:
            print("  ✅ Everything looks good!")

if __name__ == "__main__":
    main()