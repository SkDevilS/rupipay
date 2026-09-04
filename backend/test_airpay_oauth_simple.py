#!/usr/bin/env python3
"""
Test Airpay OAuth2 with Simple Approach
"""

import requests
from config import Config

def test_simple_oauth():
    """Test OAuth2 without encryption"""
    
    print("🧪 Testing Simple OAuth2 (No Encryption)")
    print("=" * 50)
    
    base_url = Config.AIRPAY_BASE_URL
    client_id = Config.AIRPAY_CLIENT_ID
    client_secret = Config.AIRPAY_CLIENT_SECRET
    merchant_id = Config.AIRPAY_MERCHANT_ID
    
    url = f"{base_url}/airpay/pay/v4/api/oauth2"
    
    # Try simple form data without encryption
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'merchant_id': int(merchant_id),
        'grant_type': 'client_credentials'
    }
    
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    print()
    
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=payload,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_json = response.json()
            
            # Check if it's a direct success response
            if response_json.get('status_code') == '200':
                print("✅ Direct OAuth2 success!")
                token = response_json.get('data', {}).get('access_token')
                print(f"Token: {token}")
                return True
            
            # Check if response is encrypted
            elif 'response' in response_json:
                print("📦 Response is encrypted - need to decrypt")
                return False
            
            else:
                print("❌ Unexpected response format")
                return False
        else:
            print("❌ HTTP error")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_simple_oauth()