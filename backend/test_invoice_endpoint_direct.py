#!/usr/bin/env python3

import requests
import json

def test_invoice_endpoint():
    """
    Test the invoice endpoint directly with proper headers
    """
    
    # Test transaction ID from the error
    txn_id = "VY_BAR_9000000001_TRD8CA027267488D0_20260414155514"
    
    # API endpoint
    url = f"https://api.moneyone.co.in/api/payin/admin/create-invoice/{txn_id}"
    
    print("=" * 80)
    print(f"🧪 TESTING INVOICE ENDPOINT DIRECTLY")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Method: POST")
    
    # Test without authentication first
    print("\n1️⃣ Testing without authentication...")
    try:
        response = requests.post(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        try:
            response_data = response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with basic headers
    print("\n2️⃣ Testing with basic headers...")
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        try:
            response_data = response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with fake JWT token
    print("\n3️⃣ Testing with fake JWT token...")
    headers_with_auth = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer fake_token_123'
    }
    
    try:
        response = requests.post(url, headers=headers_with_auth, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        try:
            response_data = response.json()
            print(f"Response Data: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_invoice_endpoint()