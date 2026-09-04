"""
Test Mudrape Payout API
"""
import requests
import json
from config import Config

def test_mudrape_payout():
    """Test Mudrape IMPS payout API"""
    
    print("=" * 60)
    print("Testing Mudrape Payout API")
    print("=" * 60)
    
    # Configuration
    base_url = Config.MUDRAPE_BASE_URL
    api_key = Config.MUDRAPE_API_KEY
    api_secret = Config.MUDRAPE_API_SECRET
    
    print(f"\nBase URL: {base_url}")
    print(f"API Key: {api_key[:20]}...")
    print(f"API Secret: {api_secret[:20]}...")
    
    # Test IMPS Payout
    url = f"{base_url}/api/payout/imps"
    
    headers = {
        'x-api-key': api_key,
        'x-api-secret': api_secret,
        'Content-Type': 'application/json'
    }
    
    payload = {
        'p1': '123456852634',  # Account Number (test)
        'p2': 'IBKL0006235',   # IFSC Code (test)
        'p3': f'TEST{int(time.time())}',  # Unique Client Transaction ID
        'p4': '1',  # Amount (₹1 test)
        'p5': 'Test User'  # Beneficiary Name
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request Headers: {json.dumps({k: v[:20] + '...' if len(v) > 20 else v for k, v in headers.items()}, indent=2)}")
    print(f"Request Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("\n✓ Payout API call successful!")
            print(f"Status: {data.get('status')}")
            print(f"Transaction ID: {data.get('txnId')}")
            print(f"Message: {data.get('message')}")
        else:
            print("\n✗ Payout API call failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import time
    test_mudrape_payout()
