#!/usr/bin/env python3
"""
Test script for Rang payin integration
"""

import requests
import json
import time
from rang_service import RangService

def test_rang_token_generation():
    """Test Rang token generation"""
    print("=== Testing Rang Token Generation ===")
    
    rang_service = RangService()
    result = rang_service.generate_token()
    
    if result:
        print("✅ Token generation successful")
        print(f"Token: {rang_service.token[:20]}...")
        print(f"Expires at: {rang_service.token_expires_at}")
    else:
        print("❌ Token generation failed")
    
    return result

def test_rang_order_creation():
    """Test Rang order creation"""
    print("\n=== Testing Rang Order Creation ===")
    
    rang_service = RangService()
    
    # Test order data with correct field names matching your system
    order_data = {
        'orderid': f'TEST{int(time.time())}',  # Changed from order_id
        'amount': '100',
        'payee_fname': 'Test Customer',  # Changed from customer_name
        'payee_email': 'test@example.com',  # Changed from customer_email
        'payee_mobile': '9876543210',  # Changed from customer_mobile
        'scheme_id': 1  # Assuming scheme ID 1 exists
    }
    
    result = rang_service.create_payin_order('TEST_MERCHANT', order_data)
    
    print(f"Order creation result: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ Order creation successful")
        return result.get('txn_id')
    else:
        print("❌ Order creation failed")
        return None

def test_rang_status_check(txn_id):
    """Test Rang status check"""
    print(f"\n=== Testing Rang Status Check for {txn_id} ===")
    
    rang_service = RangService()
    result = rang_service.check_payment_status(txn_id)
    
    print(f"Status check result: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ Status check successful")
    else:
        print("❌ Status check failed")

def test_rang_api_endpoints():
    """Test Rang API endpoints directly"""
    print("\n=== Testing Rang API Endpoints ===")
    
    base_url = "http://localhost:5000"  # Adjust if your Flask app runs on different port
    
    # Test create order endpoint
    print("Testing create order endpoint...")
    
    order_payload = {
        'merchant_id': 'TEST_MERCHANT',
        'orderid': f'API_TEST{int(time.time())}',  # Changed from order_id
        'amount': '50',
        'payee_fname': 'API Test Customer',  # Changed from customer_name
        'payee_email': 'apitest@example.com',  # Changed from customer_email
        'payee_mobile': '9876543210',  # Changed from customer_mobile
        'scheme_id': 1
    }
    
    try:
        response = requests.post(
            f"{base_url}/create-rang-order",
            json=order_payload,
            timeout=30
        )
        
        print(f"Create order response: {response.status_code}")
        print(f"Response data: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ API order creation successful")
                txn_id = data.get('txn_id')
                
                # Test status check endpoint
                print(f"\nTesting status check endpoint for {txn_id}...")
                
                status_response = requests.get(
                    f"{base_url}/check-rang-status/{txn_id}",
                    timeout=30
                )
                
                print(f"Status check response: {status_response.status_code}")
                print(f"Status data: {status_response.text}")
                
                if status_response.status_code == 200:
                    print("✅ API status check successful")
                else:
                    print("❌ API status check failed")
            else:
                print("❌ API order creation failed")
        else:
            print("❌ API request failed")
            
    except Exception as e:
        print(f"❌ API test error: {str(e)}")

def main():
    """Main test function"""
    print("🚀 Starting Rang Integration Tests")
    print("=" * 50)
    
    # Test 1: Token Generation
    token_success = test_rang_token_generation()
    
    if token_success:
        # Test 2: Order Creation
        txn_id = test_rang_order_creation()
        
        if txn_id:
            # Test 3: Status Check
            test_rang_status_check(txn_id)
    
    # Test 4: API Endpoints (requires Flask app to be running)
    test_rang_api_endpoints()
    
    print("\n" + "=" * 50)
    print("🏁 Rang Integration Tests Complete")

if __name__ == "__main__":
    main()