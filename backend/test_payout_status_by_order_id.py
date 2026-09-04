"""
Test script for payout status check by order ID endpoint
Similar to MoneyStake API pattern
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Change to your server URL
MERCHANT_ID = "9000000001"  # Replace with your test merchant ID
PASSWORD = "Test@123"  # Replace with your test password
ORDER_ID = "ORD20260415123456ABCD1234"  # Replace with an actual order ID from your database

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_response(response):
    """Print formatted response"""
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))

def test_payout_status_check():
    """Test the complete flow: login + status check"""
    
    print_section("STEP 1: MERCHANT LOGIN")
    
    # Step 1: Login
    login_url = f"{BASE_URL}/api/merchant/login"
    login_payload = {
        "merchantId": MERCHANT_ID,
        "password": PASSWORD
    }
    
    print(f"\nEndpoint: POST {login_url}")
    print(f"Payload: {json.dumps(login_payload, indent=2)}")
    
    try:
        login_response = requests.post(login_url, json=login_payload)
        print_response(login_response)
        
        if login_response.status_code != 200:
            print("\n❌ Login failed!")
            return
        
        login_data = login_response.json()
        if not login_data.get('success'):
            print(f"\n❌ Login failed: {login_data.get('message')}")
            return
        
        token = login_data.get('token')
        print(f"\n✅ Login successful!")
        print(f"Token: {token[:50]}...")
        
        # Step 2: Check status by order ID
        print_section("STEP 2: CHECK STATUS BY ORDER ID")
        
        status_url = f"{BASE_URL}/api/payout/client/check-status-by-order-id/{ORDER_ID}"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print(f"\nEndpoint: GET {status_url}")
        print(f"Headers: Authorization: Bearer {token[:30]}...")
        
        status_response = requests.get(status_url, headers=headers)
        print_response(status_response)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data.get('success'):
                print("\n✅ Status check successful!")
                
                # Print formatted transaction details
                print_section("TRANSACTION DETAILS")
                data = status_data.get('data', {})
                
                print(f"\nOrder ID:        {data.get('order_id')}")
                print(f"Transaction ID:  {data.get('txn_id')}")
                print(f"Reference ID:    {data.get('reference_id')}")
                print(f"Status:          {data.get('status')}")
                print(f"Amount:          ₹{data.get('amount')}")
                print(f"Charge:          ₹{data.get('charge_amount')}")
                print(f"Net Amount:      ₹{data.get('net_amount')}")
                print(f"UTR:             {data.get('utr')}")
                print(f"PG Partner:      {data.get('pg_partner')}")
                print(f"PG Txn ID:       {data.get('pg_txn_id')}")
                print(f"Beneficiary:     {data.get('bene_name')}")
                print(f"Account No:      {data.get('account_no')}")
                print(f"IFSC Code:       {data.get('ifsc_code')}")
                print(f"Payment Type:    {data.get('payment_type')}")
                print(f"Created At:      {data.get('created_at')}")
                print(f"Completed At:    {data.get('completed_at')}")
                
            else:
                print(f"\n❌ Status check failed: {status_data.get('message')}")
        elif status_response.status_code == 404:
            print("\n❌ Transaction not found or unauthorized")
        elif status_response.status_code == 401:
            print("\n❌ Invalid or expired token")
        else:
            print(f"\n❌ Status check failed with status code {status_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection error: Could not connect to {BASE_URL}")
        print("Make sure the backend server is running!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def test_invalid_order_id():
    """Test with invalid order ID"""
    
    print_section("TEST: INVALID ORDER ID")
    
    # Login first
    login_url = f"{BASE_URL}/api/merchant/login"
    login_payload = {
        "merchantId": MERCHANT_ID,
        "password": PASSWORD
    }
    
    try:
        login_response = requests.post(login_url, json=login_payload)
        if login_response.status_code != 200:
            print("❌ Login failed!")
            return
        
        token = login_response.json().get('token')
        
        # Try with invalid order ID
        invalid_order_id = "INVALID_ORDER_ID_12345"
        status_url = f"{BASE_URL}/api/payout/client/check-status-by-order-id/{invalid_order_id}"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print(f"\nTesting with invalid order ID: {invalid_order_id}")
        print(f"Endpoint: GET {status_url}")
        
        status_response = requests.get(status_url, headers=headers)
        print_response(status_response)
        
        if status_response.status_code == 404:
            print("\n✅ Correctly returned 404 for invalid order ID")
        else:
            print(f"\n⚠️ Expected 404, got {status_response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def test_without_token():
    """Test without authentication token"""
    
    print_section("TEST: WITHOUT AUTHENTICATION TOKEN")
    
    status_url = f"{BASE_URL}/api/payout/client/check-status-by-order-id/{ORDER_ID}"
    
    print(f"\nEndpoint: GET {status_url}")
    print("Headers: None (no Authorization header)")
    
    try:
        status_response = requests.get(status_url)
        print_response(status_response)
        
        if status_response.status_code == 401:
            print("\n✅ Correctly returned 401 for missing token")
        else:
            print(f"\n⚠️ Expected 401, got {status_response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print(" PAYOUT STATUS CHECK BY ORDER ID - TEST SUITE")
    print(" Similar to MoneyStake API Pattern")
    print("=" * 80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Merchant ID: {MERCHANT_ID}")
    print(f"Test Order ID: {ORDER_ID}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Normal flow
    test_payout_status_check()
    
    # Test 2: Invalid order ID
    test_invalid_order_id()
    
    # Test 3: Without token
    test_without_token()
    
    print_section("TEST SUITE COMPLETED")
    print("\n✅ All tests completed!")
    print("\nNOTE: Make sure to update the ORDER_ID variable with an actual order ID from your database.")

if __name__ == "__main__":
    main()
