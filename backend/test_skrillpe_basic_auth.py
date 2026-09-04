"""
Test SkrillPE Basic Authentication
Tests the authentication token generation and API call
"""

import hashlib
import base64
import requests
import json
from config import Config

def generate_basic_auth_token(mid, mobile_number):
    """
    Generate Basic Authentication token as per SkrillPE specification
    """
    try:
        # Step 1: SHA1 hash of mobile number
        sha1_hash = hashlib.sha1(mobile_number.encode('utf-8')).digest()
        
        # Step 2: Base64 encode the hash
        password = base64.b64encode(sha1_hash).decode('utf-8')
        
        # Step 3: Combine MID:password
        credentials = f"{mid}:{password}"
        
        # Step 4: Base64 encode with ISO-8859-1
        basic_auth = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
        
        # Step 5: Return with "Basic" prefix
        return f"Basic {basic_auth}"
        
    except Exception as e:
        print(f"Error generating Basic Auth token: {e}")
        return None

def test_skrillpe_auth():
    """Test SkrillPE authentication and API call"""
    
    mid = Config.SKRILLPE_MID
    mobile_number = Config.SKRILLPE_MOBILE_NUMBER
    base_url = Config.SKRILLPE_BASE_URL
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    print("=" * 60)
    print("SKRILLPE BASIC AUTHENTICATION TEST")
    print("=" * 60)
    
    print(f"\n📋 Configuration:")
    print(f"   MID: {mid}")
    print(f"   Mobile: {mobile_number}")
    print(f"   Base URL: {base_url}")
    print(f"   Company Alias: {company_alias}")
    
    # Generate auth token
    auth_token = generate_basic_auth_token(mid, mobile_number)
    
    print(f"\n🔐 Generated Auth Token:")
    print(f"   {auth_token}")
    
    # Test API call
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    
    headers = {
        'Authorization': auth_token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        'transactionId': f'TEST_{int(__import__("time").time())}',
        'amount': '100',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"\n📤 API Request:")
    print(f"   URL: {url}")
    print(f"   Headers: {json.dumps(headers, indent=6)}")
    print(f"   Payload: {json.dumps(payload, indent=6)}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n📥 API Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"   Intent URL: {data.get('intentUrl', 'NOT FOUND')}")
            print(f"   Tiny URL: {data.get('tinyUrl', 'NOT FOUND')}")
            print(f"   Code: {data.get('code', 'NOT FOUND')}")
            print(f"   Reason: {data.get('reason', 'NOT FOUND')}")
            
            if data.get('intentUrl'):
                print(f"\n🎉 Intent URL is populated!")
            else:
                print(f"\n⚠️  Intent URL is empty - check with SkrillPE team")
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_skrillpe_auth()
