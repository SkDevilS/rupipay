#!/usr/bin/env python3
"""
SkrillPe Payin Test Script
Test SkrillPe payin integration with merchant ID 7679022140 and amount above 300
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
from config import Config

def test_skrillpe_payin():
    """Test SkrillPe payin with specific requirements"""
    print("🔍 SkrillPe Payin Test")
    print("=" * 50)
    
    # Use merchant ID 7679022140 and amount above 300 as requested
    merchant_id = "7679022140"
    amount = "350.00"  # Above 300 as requested
    
    print(f"Merchant ID: {merchant_id}")
    print(f"Amount: ₹{amount}")
    
    try:
        from skrillpe_service import skrillpe_service
        
        # Test order data
        order_data = {
            'amount': amount,
            'orderid': f'ORD{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"Order ID: {order_data['orderid']}")
        print(f"Customer: {order_data['payee_fname']} {order_data['payee_lname']}")
        print(f"Mobile: {order_data['payee_mobile']}")
        
        # Call SkrillPe service
        print(f"\n🚀 Calling SkrillPe service...")
        result = skrillpe_service.create_payin_order(merchant_id, order_data)
        
        if result:
            print(f"\n📊 Response received:")
            print(json.dumps(result, indent=2, default=str))
            
            if result.get('success'):
                print(f"\n✅ Payin created successfully!")
                
                # Check the expected response format
                expected_fields = {
                    'txn_id': result.get('txn_id'),
                    'order_id': result.get('order_id'),
                    'amount': result.get('amount'),
                    'charge_amount': result.get('charge_amount'),
                    'net_amount': result.get('net_amount'),
                    'payment_url': result.get('payment_url'),
                    'payment_params': result.get('payment_params', {}),
                    'qr_string': result.get('qr_string'),
                    'qr_code_url': result.get('qr_code_url'),
                    'upi_link': result.get('upi_link'),
                    'payment_link': result.get('payment_link'),
                    'intent_url': result.get('intent_url'),
                    'tiny_url': result.get('tiny_url'),
                    'expires_in': result.get('expires_in'),
                    'vpa': result.get('vpa'),
                    'pg_partner': result.get('pg_partner')
                }
                
                print(f"\n📋 Mapped Response (Expected Format):")
                print(json.dumps(expected_fields, indent=2, default=str))
                
                # Check critical fields
                critical_urls = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
                url_status = {}
                
                print(f"\n🔍 URL Field Analysis:")
                for field in critical_urls:
                    value = result.get(field, '')
                    has_value = bool(value and value.strip())
                    url_status[field] = has_value
                    status = "✅" if has_value else "❌"
                    print(f"   {field}: {status} '{value}'")
                
                # Overall status
                has_any_url = any(url_status.values())
                if has_any_url:
                    print(f"\n✅ SUCCESS: Payment URLs are available")
                    print(f"   Users can proceed with payment")
                else:
                    print(f"\n❌ CRITICAL ISSUE: No payment URLs available")
                    print(f"   This is the empty intentUrl/tinyUrl issue")
                    print(f"   Users cannot complete payments")
                    
                    # Show the raw SkrillPe response for debugging
                    if 'raw_response' in result:
                        print(f"\n🔍 Raw SkrillPe Response:")
                        print(json.dumps(result['raw_response'], indent=2))
                
            else:
                print(f"\n❌ Payin creation failed:")
                print(f"   Error: {result.get('message')}")
                
                if 'raw_response' in result:
                    print(f"\n🔍 Raw SkrillPe Response:")
                    print(json.dumps(result['raw_response'], indent=2))
        else:
            print(f"\n❌ No response from service")
            
        return result
        
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_direct_api():
    """Test SkrillPe API directly"""
    print(f"\n🧪 Direct API Test")
    print("=" * 50)
    
    # Direct API call with the new endpoint
    payload = {
        'transactionId': f'TEST_7679022140_{int(time.time())}',
        'amount': '350.00',
        'customerNumber': '9876543210',
        'CompanyAlise': Config.SKRILLPE_COMPANY_ALIAS
    }
    
    headers = {
        'Authorization': f'Bearer {Config.SKRILLPE_BEARER_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f"{Config.SKRILLPE_BASE_URL}/api/skrill/upi/qr/send/intent/WL"
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check the key fields
            code = data.get('code', '')
            reason = data.get('reason', '')
            intent_url = data.get('intentUrl', '')
            tiny_url = data.get('tinyUrl', '')
            
            print(f"\n🔍 Key Fields:")
            print(f"   code: '{code}'")
            print(f"   reason: '{reason}'")
            print(f"   intentUrl: '{intent_url}'")
            print(f"   tinyUrl: '{tiny_url}'")
            
            # Check if this is the empty URL issue
            if reason and 'Successful' in reason and not intent_url and not tiny_url:
                print(f"\n❌ CONFIRMED: Empty intentUrl/tinyUrl issue")
                print(f"   SkrillPe says success but provides no URLs")
                print(f"   This needs to be reported to SkrillPe team")
            elif intent_url or tiny_url:
                print(f"\n✅ SUCCESS: URLs are provided")
            else:
                print(f"\n⚠️  Unclear response - check with SkrillPe team")
            
            return data
        else:
            print(f"\n❌ API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"💥 API Error: {e}")
        return None

def main():
    """Main test function"""
    print("🔍 SkrillPe Payin Integration Test")
    print("=" * 80)
    print("Testing with:")
    print("- Merchant ID: 7679022140")
    print("- Amount: ₹350.00 (above 300 as requested)")
    print("- New API endpoint: /api/skrill/upi/qr/send/intent/WL")
    print("=" * 80)
    
    # Test service integration
    service_result = test_skrillpe_payin()
    
    # Test direct API
    api_result = test_direct_api()
    
    # Summary
    print(f"\n" + "=" * 80)
    print("🎯 Test Summary")
    print("=" * 80)
    
    if service_result and service_result.get('success'):
        # Check if we have usable URLs
        critical_urls = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
        has_urls = any([service_result.get(field) for field in critical_urls])
        
        if has_urls:
            print("✅ Service Integration: WORKING")
            print("✅ Payment URLs: AVAILABLE")
            print("✅ Status: Ready for production")
        else:
            print("✅ Service Integration: WORKING")
            print("❌ Payment URLs: EMPTY (SkrillPe issue)")
            print("⚠️  Status: Blocked by SkrillPe empty URL issue")
    else:
        print("❌ Service Integration: FAILED")
    
    if api_result:
        intent_url = api_result.get('intentUrl', '')
        tiny_url = api_result.get('tinyUrl', '')
        reason = api_result.get('reason', '')
        
        if intent_url or tiny_url:
            print("✅ Direct API: URLs provided")
        elif 'Successful' in reason:
            print("❌ Direct API: Success message but empty URLs")
        else:
            print("❌ Direct API: No success indication")
    
    print(f"\n📋 Next Steps:")
    if service_result and service_result.get('success'):
        critical_urls = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
        has_urls = any([service_result.get(field) for field in critical_urls])
        
        if has_urls:
            print("1. ✅ Integration is ready")
            print("2. ✅ Deploy to production")
            print("3. ✅ Test with real payments")
        else:
            print("1. 📞 Contact SkrillPe team about empty intentUrl/tinyUrl")
            print("2. 🔧 Request fix for URL generation in new API")
            print("3. 🧪 Test with different amounts/merchants if suggested")
            print("4. ⏳ Wait for SkrillPe team response")
    else:
        print("1. 🔧 Fix service integration issues")
        print("2. 🧪 Debug API connectivity")
        print("3. 📞 Contact SkrillPe team if API issues persist")

if __name__ == "__main__":
    main()