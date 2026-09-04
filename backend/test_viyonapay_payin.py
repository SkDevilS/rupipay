#!/usr/bin/env python3
"""
Test script for ViyonaPay Payin API
Tests the complete flow: Token generation -> Create Payment Intent -> Check Status
Uses UpiMasterMerchant with VPA: vfipl.188690284791@kvb
"""

import sys
import os
import json
import time
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from viyonapay_service import ViyonapayService
from config import Config

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_json(data, title=""):
    """Pretty print JSON data"""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2))

def test_token_generation():
    """Test 1: Generate Access Token"""
    print_section("TEST 1: Generate Access Token")
    
    try:
        service = ViyonapayService()
        print(f"✓ ViyonaPay service initialized")
        print(f"  - Base URL: {Config.VIYONAPAY_BASE_URL}")
        print(f"  - Client ID: {Config.VIYONAPAY_CLIENT_ID}")
        print(f"  - API Key: {Config.VIYONAPAY_API_KEY[:20]}..." if Config.VIYONAPAY_API_KEY else "  - API Key: Not set")
        
        print("\n⏳ Generating access token...")
        result = service.generate_access_token()
        
        if result.get('success'):
            print("✅ Token generation successful!")
            print_json(result, "Token Response")
            return result.get('access_token')
        else:
            print("❌ Token generation failed!")
            print_json(result, "Error Response")
            return None
            
    except Exception as e:
        print(f"❌ Exception during token generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_create_payment_intent(access_token):
    """Test 2: Create Payment Intent with UpiMasterMerchant"""
    print_section("TEST 2: Create Payment Intent (UpiMasterMerchant)")
    
    if not access_token:
        print("❌ Skipping - No access token available")
        return None
    
    try:
        service = ViyonapayService()
        
        # Generate unique order ID
        order_id = f"TEST_VIYONA_{int(time.time())}"
        
        # Payment intent data
        payment_data = {
            "orderId": order_id,
            "amount": "100.00",
            "currency": "INR",
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "9999999999",
            "payinType": ["upiMasterMerchant"],
            "vpa": "vfipl.188690284791@kvb",
            "note": "Test payment for ViyonaPay integration"
        }
        
        print("\n📋 Payment Intent Details:")
        print_json(payment_data)
        
        print("\n⏳ Creating payment intent...")
        result = service.create_payin_order(
            merchant_id="TEST_MERCHANT",  # This will be replaced with actual merchant_id
            order_data=payment_data
        )
        
        if result.get('success'):
            print("✅ Payment intent created successfully!")
            print_json(result, "Payment Intent Response")
            
            # Extract important details
            response_body = result.get('response_body', {})
            print("\n📌 Key Details:")
            print(f"  - Payment Intent ID: {response_body.get('payment_intent_id')}")
            print(f"  - Order ID: {response_body.get('order_id')}")
            print(f"  - Amount: {response_body.get('amount')} {response_body.get('currency')}")
            print(f"  - Status: {response_body.get('status')}")
            print(f"  - Payment URL: {response_body.get('payment_url')}")
            print(f"  - Expires At: {response_body.get('expires_at')}")
            
            return response_body.get('order_id')
        else:
            print("❌ Payment intent creation failed!")
            print_json(result, "Error Response")
            return None
            
    except Exception as e:
        print(f"❌ Exception during payment intent creation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_check_payment_status(order_id):
    """Test 3: Check Payment Status"""
    print_section("TEST 3: Check Payment Status")
    
    if not order_id:
        print("❌ Skipping - No order ID available")
        return None
    
    try:
        service = ViyonapayService()
        
        print(f"\n🔍 Checking status for Order ID: {order_id}")
        print("⏳ Fetching payment status...")
        
        result = service.check_payment_status(order_id)
        
        if result.get('success'):
            print("✅ Status check successful!")
            print_json(result, "Status Response")
            
            # Extract status details
            status_result = result.get('result', {})
            print("\n📌 Payment Status Details:")
            print(f"  - Status: {status_result.get('status')}")
            print(f"  - Transaction ID: {status_result.get('transaction_id')}")
            print(f"  - Payment Mode: {status_result.get('payment_mode')}")
            print(f"  - Order ID: {status_result.get('order_id')}")
            print(f"  - Amount: {status_result.get('amount')}")
            print(f"  - Bank Reference: {status_result.get('bank_reference_number')}")
            print(f"  - Message: {status_result.get('message')}")
            
            return status_result
        else:
            print("❌ Status check failed!")
            print_json(result, "Error Response")
            return None
            
    except Exception as e:
        print(f"❌ Exception during status check: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_raw_api_response():
    """Test 4: Display Raw API Responses"""
    print_section("TEST 4: Raw API Response Analysis")
    
    try:
        service = ViyonapayService()
        
        # Test token generation and capture raw response
        print("\n🔍 Testing Token Generation API...")
        print("⏳ Making API call...")
        
        import requests
        import uuid
        
        # Prepare token request
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        session_key = service._generate_session_key()
        encrypted_session_key = service._encrypt_session_key(session_key)
        
        aad = {
            "client_id": Config.VIYONAPAY_CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        data_to_encrypt = {
            "client_secret": Config.VIYONAPAY_CLIENT_SECRET,
            "scopes": ["PAYMENT_GATEWAY"]
        }
        
        encrypted_data = service._encrypt_data(data_to_encrypt, session_key, aad)
        
        request_body = {
            "client_id": Config.VIYONAPAY_CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = service._sign_request(request_body)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        print("\n📤 Request Headers:")
        print_json(headers)
        
        print("\n📤 Request Body (Encrypted):")
        print_json(request_body)
        
        # Make the API call
        url = f"{Config.VIYONAPAY_BASE_URL}/v1/auth/token"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status Code: {response.status_code}")
        print(f"📥 Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\n📥 Raw Response Body:")
        print(response.text)
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                print("\n📥 Parsed Response JSON:")
                print_json(response_json)
                
                # Try to decrypt if encrypted
                if 'encrypted_data' in response_json:
                    print("\n🔓 Attempting to decrypt response...")
                    decrypted = service._decrypt_data(
                        response_json['encrypted_data'],
                        session_key,
                        aad
                    )
                    if decrypted:
                        print("✅ Decrypted Response:")
                        print_json(decrypted)
                    else:
                        print("❌ Failed to decrypt response")
            except Exception as e:
                print(f"❌ Error parsing response: {str(e)}")
        
    except Exception as e:
        print(f"❌ Exception during raw API test: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main test execution"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  VIYONAPAY PAYIN API TEST SUITE".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check configuration
    print_section("Configuration Check")
    print(f"✓ Base URL: {Config.VIYONAPAY_BASE_URL}")
    print(f"✓ Client ID: {Config.VIYONAPAY_CLIENT_ID if Config.VIYONAPAY_CLIENT_ID else '❌ NOT SET'}")
    print(f"✓ Client Secret: {'***' + Config.VIYONAPAY_CLIENT_SECRET[-4:] if Config.VIYONAPAY_CLIENT_SECRET else '❌ NOT SET'}")
    print(f"✓ API Key: {'***' + Config.VIYONAPAY_API_KEY[-4:] if Config.VIYONAPAY_API_KEY else '❌ NOT SET'}")
    print(f"✓ Private Key Path: {Config.VIYONAPAY_CLIENT_PRIVATE_KEY_PATH}")
    print(f"✓ Public Key Path: {Config.VIYONAPAY_SERVER_PUBLIC_KEY_PATH}")
    
    if not all([Config.VIYONAPAY_CLIENT_ID, Config.VIYONAPAY_CLIENT_SECRET, Config.VIYONAPAY_API_KEY]):
        print("\n❌ ERROR: Missing required configuration!")
        print("Please set the following in your .env file:")
        print("  - VIYONAPAY_CLIENT_ID")
        print("  - VIYONAPAY_CLIENT_SECRET")
        print("  - VIYONAPAY_API_KEY")
        return
    
    # Run tests
    access_token = test_token_generation()
    
    if access_token:
        order_id = test_create_payment_intent(access_token)
        
        if order_id:
            # Wait a bit before checking status
            print("\n⏳ Waiting 2 seconds before status check...")
            time.sleep(2)
            test_check_payment_status(order_id)
    
    # Show raw API responses
    test_raw_api_response()
    
    # Summary
    print_section("Test Summary")
    print(f"⏰ Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✅ Test suite execution completed!")
    print("\n📝 Notes:")
    print("  - Payment Intent Type: upiMasterMerchant")
    print("  - VPA Used: vfipl.188690284791@kvb")
    print("  - Test Amount: ₹100.00")
    print("\n💡 Next Steps:")
    print("  1. Check the payment_url from the response")
    print("  2. Complete the payment using the URL")
    print("  3. Run status check again to verify payment completion")
    print("  4. Monitor webhook callbacks for real-time updates")

if __name__ == "__main__":
    main()
