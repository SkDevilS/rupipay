"""
Test Paytouchpayin API directly with the correct token
"""

import requests
import json
import time

# API Configuration (from documentation)
BASE_URL = "https://dashboard.shreefintechsolutions.com"
TOKEN = "izrfvcnddMzlf5B142yDH4PDkkoDUMPP"

def test_dynamic_qr_generation():
    """Test Dynamic QR generation with the API"""
    
    url = f"{BASE_URL}/api/payin/dynamic-qr"
    
    # Generate unique transaction ID
    txn_id = f"TEST{int(time.time())}"
    
    # Prepare payload exactly as per documentation
    payload = {
        "token": TOKEN,
        "mobile": "9876543210",
        "amount": "10",
        "txnid": txn_id,
        "name": "Test Customer"
    }
    
    print(f"🚀 Testing Paytouchpayin Dynamic QR API")
    print(f"📤 URL: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"\n{'='*80}\n")
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        print(f"📥 Response Body: {response.text}")
        print(f"\n{'='*80}\n")
        
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get('status') == 'SUCCESS':
                print(f"✅ SUCCESS!")
                print(f"📋 Response Data:")
                print(json.dumps(response_data, indent=2))
                
                data = response_data.get('data', {})
                print(f"\n🔑 Key Information:")
                print(f"  - Transaction ID: {data.get('txnid')}")
                print(f"  - API Transaction ID: {data.get('apitxnid')}")
                print(f"  - Amount: ₹{data.get('amount')}")
                print(f"  - Redirect URL: {data.get('redirect_url')}")
                print(f"  - Expires At: {data.get('expire_at')}")
                
                return True
            else:
                print(f"❌ API returned error status")
                print(f"Message: {response_data.get('message')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"PAYTOUCHPAYIN API DIRECT TEST")
    print(f"{'='*80}\n")
    
    success = test_dynamic_qr_generation()
    
    print(f"\n{'='*80}")
    if success:
        print(f"✅ TEST PASSED - API is working correctly")
    else:
        print(f"❌ TEST FAILED - Check the error messages above")
    print(f"{'='*80}\n")
