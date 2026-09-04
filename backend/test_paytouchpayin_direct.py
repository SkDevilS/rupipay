"""
Direct Paytouchpayin API Test - Minimal Test
Simple direct API call without any framework dependencies
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://dashboard.shreefintechsolutions.com"
TOKEN = "bfFkfbCtbOysf5RWoF7Tl1VjKc4hScTHE"

def test_api():
    """Test the Paytouchpayin API directly"""
    
    print("="*80)
    print("PAYTOUCHPAYIN API DIRECT TEST")
    print("="*80)
    
    # API endpoint
    url = f"{BASE_URL}/api/payin/dynamic-qr"
    
    # Generate unique transaction ID
    txnid = f"TEST{int(time.time())}"
    
    # Request payload
    payload = {
        'token': TOKEN,
        'mobile': '9876543210',
        'amount': '10',
        'txnid': txnid,
        'name': 'Test User'
    }
    
    print(f"\n📤 Request Details:")
    print(f"URL: {url}")
    print(f"Method: POST")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Moneyone-Test/1.0'
    }
    
    print(f"\nHeaders:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    print(f"\n🚀 Sending request...")
    print("-"*80)
    
    try:
        # Send request
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"\n📥 Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
        
        print(f"\nResponse Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        print(response.text)
        
        # Try to parse JSON
        try:
            response_data = response.json()
            print(f"\nParsed JSON:")
            print(json.dumps(response_data, indent=2))
            
            # Check status
            if response_data.get('status') == 'SUCCESS':
                print(f"\n✅ SUCCESS!")
                data = response_data.get('data', {})
                print(f"\nQR Details:")
                print(f"  TxnID: {data.get('txnid')}")
                print(f"  API TxnID: {data.get('apitxnid')}")
                print(f"  Amount: ₹{data.get('amount')}")
                print(f"  QR URL: {data.get('redirect_url')}")
                print(f"  Expires At: {data.get('expire_at')}")
            else:
                print(f"\n❌ FAILED")
                print(f"  Status: {response_data.get('status')}")
                print(f"  Message: {response_data.get('message')}")
                
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON")
            print(f"Error: {str(e)}")
        
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout (30s)")
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection error")
        print(f"Error: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ Unexpected error")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)

if __name__ == '__main__':
    test_api()
