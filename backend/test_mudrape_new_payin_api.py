"""
Test script for Mudrape new payin API endpoint
Updated: March 2026 - New endpoint and parameter format
"""

import requests
import os
from datetime import datetime
from config import Config

def test_mudrape_new_payin_endpoint():
    """Test the new Mudrape payin API endpoint with updated parameters"""
    
    print("=" * 60)
    print("Testing Mudrape New Payin API Endpoint")
    print("=" * 60)
    
    # Configuration
    base_url = Config.MUDRAPE_BASE_URL
    api_key = Config.MUDRAPE_API_KEY
    api_secret = Config.MUDRAPE_API_SECRET
    user_id = Config.MUDRAPE_USER_ID
    
    print(f"\n1. Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   API Key: {api_key[:20]}...")
    print(f"   User ID: {user_id}")
    
    # Step 1: Generate token
    print(f"\n2. Generating authentication token...")
    token_url = f"{base_url}/api/api-mudrape/genrate-token"
    
    token_payload = {
        'mid': Config.MUDRAPE_MERCHANT_MID,
        'email': Config.MUDRAPE_MERCHANT_EMAIL,
        'secretkey': Config.MUDRAPE_MERCHANT_SECRET
    }
    
    headers = {
        'x-api-key': api_key,
        'x-api-secret': api_secret,
        'Content-Type': 'application/json'
    }
    
    try:
        token_response = requests.post(token_url, headers=headers, json=token_payload, timeout=30)
        print(f"   Token Response Status: {token_response.status_code}")
        
        if token_response.status_code in [200, 201]:
            token_data = token_response.json()
            if token_data.get('success'):
                token = token_data.get('token')
                print(f"   ✓ Token generated successfully")
                print(f"   Token: {token[:30]}...")
            else:
                print(f"   ✗ Token generation failed: {token_data.get('message')}")
                return
        else:
            print(f"   ✗ Token request failed: {token_response.text}")
            return
            
    except Exception as e:
        print(f"   ✗ Token generation error: {e}")
        return
    
    # Step 2: Test new payin endpoint with new parameters
    print(f"\n3. Testing new payin endpoint...")
    print(f"   Endpoint: /api/api-mudrape/create-order")
    
    # Generate test reference ID (20 digits)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    import random
    random_part = str(random.randint(100000, 999999))
    ref_id = f"{timestamp}{random_part}"
    
    # New payload format as per Mudrape team update
    payin_payload = {
        'refId': ref_id,  # lowercase 'refId'
        'amount': 300,  # integer amount (not string)
        'name': 'Jhon',  # 'name' instead of 'Customer_Name'
        'mobile': '7857024383',  # 'mobile' instead of 'Customer_Mobile'
        'email': 'john@example.com',  # 'email' instead of 'Customer_Email'
        'userId': user_id
    }
    
    print(f"\n   Payload:")
    print(f"   {payin_payload}")
    
    # Add Bearer token to headers
    payin_headers = headers.copy()
    payin_headers['Authorization'] = f'Bearer {token}'
    
    payin_url = f"{base_url}/api/api-mudrape/create-order"
    
    try:
        payin_response = requests.post(payin_url, headers=payin_headers, json=payin_payload, timeout=30)
        print(f"\n   Response Status: {payin_response.status_code}")
        print(f"   Response Body:")
        
        try:
            response_json = payin_response.json()
            import json
            print(json.dumps(response_json, indent=2))
            
            if payin_response.status_code in [200, 201]:
                if response_json.get('success'):
                    print(f"\n   ✓ Payin order created successfully!")
                    data = response_json.get('data', {})
                    print(f"\n   Order Details:")
                    print(f"   - Transaction ID: {data.get('txnId', 'N/A')}")
                    print(f"   - QR String: {'Present' if data.get('qrString') else 'Missing'}")
                    print(f"   - UPI Link: {'Present' if data.get('upiLink') else 'Missing'}")
                else:
                    print(f"\n   ✗ Order creation failed: {response_json.get('message')}")
            else:
                print(f"\n   ✗ API request failed with status {payin_response.status_code}")
                
        except Exception as e:
            print(f"   Response Text: {payin_response.text}")
            print(f"   ✗ Failed to parse JSON: {e}")
            
    except Exception as e:
        print(f"   ✗ Payin request error: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == '__main__':
    test_mudrape_new_payin_endpoint()
