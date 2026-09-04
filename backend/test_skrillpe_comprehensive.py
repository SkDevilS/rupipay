#!/usr/bin/env python3
"""
Comprehensive SkrillPe Test Script
Tests both direct API and service integration with proper error handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
from config import Config

def test_skrillpe_api_direct():
    """Test SkrillPe API directly with new endpoint"""
    print("🔍 SkrillPe Direct API Test")
    print("=" * 80)
    
    print("🧪 Testing SkrillPe API")
    print("=" * 50)
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print(f"Base URL: {base_url}")
    print(f"Company Alias: {company_alias}")
    print(f"Bearer Token: {'Set' if bearer_token else 'Not set'}")
    
    # Test payload with merchant ID 7679022140 and amount above 300
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
    
    # API call to new endpoint
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
                print(f"{key}: '{value}'")
            
            # Check for success indicators
            code = data.get('code', '')
            reason = data.get('reason', '')
            intent_url = data.get('intentUrl', '')
            tiny_url = data.get('tinyUrl', '')
            
            print(f"\n✅ Success Indicators:")
            print(f"Message contains 'Successful': {'Successful' in reason}")
            print(f"Has intentUrl: {bool(intent_url)}")
            print(f"Has tinyUrl: {bool(tiny_url)}")
            print(f"Has code: {bool(code)}")
            
            return data
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

def test_skrillpe_service():
    """Test SkrillPe service method"""
    print("\n🧪 Testing SkrillPe Service")
    print("=" * 50)
    
    try:
        from skrillpe_service import skrillpe_service
        
        # Test data with merchant ID 7679022140 and amount above 300
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
        
        print(f"\nSkrillPe QR Request: {json.dumps({
            'transactionId': f'SKRILLPE_{merchant_id}_{order_data[\"orderid\"]}_timestamp',
            'amount': order_data['amount'],
            'customerNumber': order_data['payee_mobile'],
            'CompanyAlise': Config.SKRILLPE_COMPANY_ALIAS
        }, indent=2)}")
        
        if result:
            print(f"SkrillPe Response Status: 200")
            if 'raw_response' in result:
                print(f"SkrillPe Response: {json.dumps(result['raw_response'], indent=2)}")
        
        print(f"\n📊 Service Result:")
        print(json.dumps(result, indent=2, default=str))
        
        # Check result with proper syntax
        if result and result.get('success'):
            print(f"\n✅ Service Success!")
            
            # Check URL fields
            url_fields = ['qr_string', 'upi_link', 'intent_url', 'tiny_url']
            for field in url_fields:
                value = result.get(field, '')
                status = "✅" if value else "❌"
                print(f"{field}: {status} '{value}'")
                
            # Check if we have any usable URLs
            has_urls = any([result.get(field) for field in url_fields])
            if not has_urls:
                print("\n⚠️  No usable URLs found in response")
        else:
            print(f"\n❌ Service Failed: {result.get('message') if result else 'No result'}")
        
        return result
        
    except Exception as e:
        print(f"💥 Service Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_different_amounts():
    """Test with different amounts to see if that affects URL generation"""
    print("\n🧪 Testing Different Amounts")
    print("=" * 50)
    
    amounts = ['100.00', '300.00', '350.00', '500.00', '1000.00']
    
    for amount in amounts:
        print(f"\n💰 Testing amount: ₹{amount}")
        
        payload = {
            'transactionId': f'TEST_AMT_{amount.replace(".", "")}_{int(time.time())}',
            'amount': amount,
            'customerNumber': '9876543210',
            'CompanyAlise': Config.SKRILLPE_COMPANY_ALIAS
        }
        
        headers = {
            'Authorization': f'Bearer {Config.SKRILLPE_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        url = f"{Config.SKRILLPE_BASE_URL}/api/skrill/upi/qr/send/intent/WL"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                intent_url = data.get('intentUrl', '')
                tiny_url = data.get('tinyUrl', '')
                reason = data.get('reason', '')
                
                print(f"   Status: {response.status_code}")
                print(f"   Reason: {reason}")
                print(f"   Intent URL: {'✅' if intent_url else '❌'} {intent_url}")
                print(f"   Tiny URL: {'✅' if tiny_url else '❌'} {tiny_url}")
            else:
                print(f"   Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   Exception: {e}")

def main():
    """Main test function"""
    print("🔍 SkrillPe Comprehensive Test")
    print("=" * 80)
    
    # Test API directly
    api_result = test_skrillpe_api_direct()
    
    # Test service method
    service_result = test_skrillpe_service()
    
    # Test different amounts
    test_different_amounts()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Summary")
    print("=" * 80)
    
    if api_result:
        print("✅ Direct API: Working")
        print(f"Fields: {list(api_result.keys())}")
        
        # Check if URLs are populated
        has_intent = bool(api_result.get('intentUrl'))
        has_tiny = bool(api_result.get('tinyUrl'))
        
        if not has_intent and not has_tiny:
            print("⚠️  ISSUE: Both intentUrl and tinyUrl are empty")
        else:
            print("✅ URLs are populated")
    else:
        print("❌ Direct API: Failed")
    
    if service_result and service_result.get('success'):
        print("✅ Service Method: Working")
        
        # Check if service has usable URLs
        url_fields = ['qr_string', 'upi_link', 'intent_url', 'tiny_url']
        has_urls = any([service_result.get(field) for field in url_fields])
        print(f"URLs Available: {'Yes' if has_urls else 'No'}")
        
        if not has_urls:
            print("⚠️  CRITICAL: No payment URLs available for frontend")
    else:
        print("❌ Service Method: Failed")
    
    print("\n📋 Next Steps:")
    if api_result and not api_result.get('intentUrl') and not api_result.get('tinyUrl'):
        print("1. Contact SkrillPe team about empty intentUrl/tinyUrl issue")
        print("2. Check if merchant account needs additional configuration")
        print("3. Verify if there are minimum amount requirements")
        print("4. Test with different merchant IDs if available")
    elif not api_result:
        print("1. Check SkrillPe API credentials and configuration")
        print("2. Verify network connectivity to SkrillPe servers")
        print("3. Check if API endpoint URL is correct")
    elif service_result and service_result.get('success'):
        url_fields = ['qr_string', 'upi_link', 'intent_url', 'tiny_url']
        has_urls = any([service_result.get(field) for field in url_fields])
        if not has_urls:
            print("1. Check URL field extraction from API response")
            print("2. Verify intentUrl mapping in service")
            print("3. Implement fallback URL generation if needed")
        else:
            print("✅ Everything looks good!")

if __name__ == "__main__":
    main()