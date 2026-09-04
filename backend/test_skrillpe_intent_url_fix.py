"""
Test SkrillPE Intent URL Fix
Tests the corrected endpoint path
"""

import requests
import json
from config import Config

def test_skrillpe_intent_url():
    """Test SkrillPE with corrected endpoint"""
    
    base_url = Config.SKRILLPE_BASE_URL
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    auth_api_key = Config.SKRILLPE_AUTH_API_KEY
    auth_api_password = Config.SKRILLPE_AUTH_API_PASSWORD
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print("=" * 60)
    print("SKRILLPE INTENT URL FIX TEST")
    print("=" * 60)
    
    # Test with corrected endpoint
    url = f"{base_url}/api/skrill/upi/qr/get/intent/WL"
    
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'AUTH-API_KEY': auth_api_key,
        'AUTH-API_PASSWORD': auth_api_password,
        'Content-Type': 'application/json'
    }
    
    payload = {
        'transactionId': 'TEST_SKRILLPE_' + str(int(time.time())),
        'amount': '100',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📤 Request URL: {url}")
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        print(f"📥 Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"   Intent URL: {data.get('intentUrl', 'NOT FOUND')}")
            print(f"   Tiny URL: {data.get('tinyUrl', 'NOT FOUND')}")
            print(f"   Code: {data.get('code', 'NOT FOUND')}")
            print(f"   Reason: {data.get('reason', 'NOT FOUND')}")
            
            if data.get('intentUrl'):
                print(f"\n🎉 Intent URL is now populated!")
            else:
                print(f"\n⚠️  Intent URL still empty - may need to contact SkrillPE team")
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import time
    test_skrillpe_intent_url()
