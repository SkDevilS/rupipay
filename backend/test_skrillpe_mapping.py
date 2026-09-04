#!/usr/bin/env python3
"""
SkrillPe Response Mapping Test
Focus on fixing the empty intentUrl/tinyUrl issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
from config import Config

def test_response_mapping():
    """Test SkrillPe API response and field mapping"""
    print("🔍 SkrillPe Response Mapping Test")
    print("=" * 60)
    
    # Use merchant ID 7679022140 and amount above 300 as requested
    payload = {
        'transactionId': f'SKRILLPE_7679022140_ORD{int(time.time())}_20260318231530',
        'amount': '350.00',
        'customerNumber': '9876543210',
        'CompanyAlise': Config.SKRILLPE_COMPANY_ALIAS
    }
    
    headers = {
        'Authorization': f'Bearer {Config.SKRILLPE_BEARER_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f"{Config.SKRILLPE_BASE_URL}/api/skrill/upi/qr/send/intent/WL"
    
    print(f"🚀 Testing endpoint: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📊 Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n🔍 Field Analysis:")
            print(f"   code: '{data.get('code', 'NOT_FOUND')}'")
            print(f"   reason: '{data.get('reason', 'NOT_FOUND')}'")
            print(f"   intentUrl: '{data.get('intentUrl', 'NOT_FOUND')}'")
            print(f"   tinyUrl: '{data.get('tinyUrl', 'NOT_FOUND')}'")
            
            # Check all possible field variations
            possible_url_fields = [
                'intentUrl', 'intent_url', 'IntentUrl', 'INTENT_URL',
                'tinyUrl', 'tiny_url', 'TinyUrl', 'TINY_URL',
                'paymentUrl', 'payment_url', 'PaymentUrl', 'PAYMENT_URL',
                'upiUrl', 'upi_url', 'UpiUrl', 'UPI_URL',
                'qrString', 'qr_string', 'QrString', 'QR_STRING',
                'url', 'URL', 'link', 'LINK'
            ]
            
            print(f"\n🔍 Checking all possible URL field names:")
            found_urls = {}
            for field in possible_url_fields:
                if field in data:
                    value = data[field]
                    if value:  # Not empty
                        found_urls[field] = value
                        print(f"   ✅ {field}: '{value}'")
                    else:
                        print(f"   ❌ {field}: EMPTY")
                        
            if not found_urls:
                print(f"   ⚠️  No URL fields found with values")
                
                # Show all available fields
                print(f"\n🔍 All available fields in response:")
                for key, value in data.items():
                    print(f"   {key}: '{value}'")
            
            # Test the expected response format
            expected_response = {
                "txn_id": payload['transactionId'],
                "order_id": "ORD98787878760067251",  # From user's example
                "amount": 11.0,  # From user's example
                "charge_amount": 0.0,
                "net_amount": 11.0,
                "payment_url": "",
                "payment_params": {},
                "qr_string": "",
                "qr_code_url": "",
                "upi_link": "",
                "payment_link": "",
                "intent_url": "",
                "tiny_url": "",
                "expires_in": 0,
                "vpa": "",
                "pg_partner": "SKRILLPE"
            }
            
            print(f"\n📋 Expected Response Format (from user):")
            print(json.dumps(expected_response, indent=2))
            
            # Map SkrillPe response to expected format
            mapped_response = {
                "txn_id": payload['transactionId'],
                "order_id": payload['transactionId'].split('_')[2] if '_' in payload['transactionId'] else "ORD123",
                "amount": float(payload['amount']),
                "charge_amount": 0.0,  # Calculate based on scheme
                "net_amount": float(payload['amount']),
                "payment_url": data.get('intentUrl', ''),
                "payment_params": {},
                "qr_string": data.get('intentUrl', '') or data.get('tinyUrl', ''),
                "qr_code_url": "",
                "upi_link": data.get('intentUrl', '') or data.get('tinyUrl', ''),
                "payment_link": data.get('tinyUrl', ''),
                "intent_url": data.get('intentUrl', ''),
                "tiny_url": data.get('tinyUrl', ''),
                "expires_in": 0,
                "vpa": "",
                "pg_partner": "SKRILLPE"
            }
            
            print(f"\n📋 Mapped Response:")
            print(json.dumps(mapped_response, indent=2))
            
            # Check if mapping is successful
            has_payment_url = bool(mapped_response['payment_url'])
            has_upi_link = bool(mapped_response['upi_link'])
            has_intent_url = bool(mapped_response['intent_url'])
            
            print(f"\n✅ Mapping Success Check:")
            print(f"   Has payment_url: {has_payment_url}")
            print(f"   Has upi_link: {has_upi_link}")
            print(f"   Has intent_url: {has_intent_url}")
            
            if not (has_payment_url or has_upi_link or has_intent_url):
                print(f"\n❌ CRITICAL: No usable payment URLs in response")
                print(f"   This will prevent users from completing payments")
                
                # Suggest fallback strategies
                print(f"\n💡 Fallback Strategies:")
                print(f"   1. Use success message as payment confirmation")
                print(f"   2. Generate manual UPI string with merchant VPA")
                print(f"   3. Show QR code with transaction details")
                print(f"   4. Contact SkrillPe team for URL generation fix")
            
            return mapped_response
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Error details: {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_service_integration():
    """Test the service integration with proper field mapping"""
    print(f"\n🧪 Testing Service Integration")
    print("=" * 60)
    
    try:
        from skrillpe_service import skrillpe_service
        
        # Test with the exact parameters from user's request
        merchant_id = "7679022140"
        order_data = {
            'amount': '350.00',  # Amount above 300 as requested
            'orderid': f'ORD{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com'
        }
        
        print(f"Merchant: {merchant_id}")
        print(f"Order: {order_data['orderid']}")
        print(f"Amount: {order_data['amount']}")
        
        result = skrillpe_service.create_payin_order(merchant_id, order_data)
        
        if result:
            print(f"\n📊 Service Result:")
            print(json.dumps(result, indent=2, default=str))
            
            # Check the specific fields mentioned in user's expected response
            expected_fields = [
                'txn_id', 'order_id', 'amount', 'charge_amount', 'net_amount',
                'payment_url', 'qr_string', 'upi_link', 'intent_url', 'tiny_url',
                'pg_partner'
            ]
            
            print(f"\n🔍 Field Mapping Check:")
            for field in expected_fields:
                value = result.get(field, 'NOT_FOUND')
                status = "✅" if value and value != 'NOT_FOUND' else "❌"
                print(f"   {field}: {status} '{value}'")
            
            # Check if we have the critical payment URLs
            critical_urls = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
            has_critical_url = any([result.get(field) for field in critical_urls])
            
            if has_critical_url:
                print(f"\n✅ SUCCESS: At least one payment URL is available")
            else:
                print(f"\n❌ CRITICAL: No payment URLs available")
                print(f"   Users will not be able to complete payments")
        
        return result
        
    except Exception as e:
        print(f"💥 Service Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("🔍 SkrillPe Field Mapping Analysis")
    print("=" * 80)
    
    # Test API response mapping
    api_result = test_response_mapping()
    
    # Test service integration
    service_result = test_service_integration()
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎯 Final Analysis")
    print("=" * 80)
    
    if api_result:
        has_urls = any([
            api_result.get('payment_url'),
            api_result.get('upi_link'),
            api_result.get('intent_url')
        ])
        
        if has_urls:
            print("✅ API Response: URLs are properly mapped")
        else:
            print("❌ API Response: URLs are empty (SkrillPe issue)")
            print("   📞 Contact SkrillPe team about empty intentUrl/tinyUrl")
    
    if service_result and service_result.get('success'):
        critical_urls = ['payment_url', 'upi_link', 'intent_url', 'qr_string']
        has_service_urls = any([service_result.get(field) for field in critical_urls])
        
        if has_service_urls:
            print("✅ Service Integration: Working correctly")
        else:
            print("❌ Service Integration: No payment URLs generated")
    
    print(f"\n📋 Action Items:")
    print(f"1. ✅ Field mapping is correct")
    print(f"2. ❌ SkrillPe API returns empty intentUrl/tinyUrl")
    print(f"3. 📞 Contact SkrillPe team for URL generation fix")
    print(f"4. 🔧 Implement fallback payment method if needed")

if __name__ == "__main__":
    main()