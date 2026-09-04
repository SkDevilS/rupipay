"""
Test SkrillPe Authentication with all headers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from skrillpe_service import SkrillPeService
import hashlib
import base64

def test_basic_auth_generation():
    """Test the Basic Auth token generation matches C# implementation"""
    print("=" * 60)
    print("Testing SkrillPe Basic Auth Token Generation")
    print("=" * 60)
    
    # Get credentials from config
    mid = Config.SKRILLPE_MID
    mobile_number = Config.SKRILLPE_MOBILE_NUMBER
    
    print(f"\n1. Input Credentials:")
    print(f"   MPIn (MID): {mid}")
    print(f"   Mobile Number: {mobile_number}")
    
    # Step 1: SHA1 hash of mobile number
    sha1_hash = hashlib.sha1(mobile_number.encode('utf-8')).digest()
    print(f"\n2. SHA1 Hash (raw bytes): {sha1_hash.hex()}")
    
    # Step 2: Base64 encode the hash
    password = base64.b64encode(sha1_hash).decode('utf-8')
    print(f"\n3. Base64 Encoded Hash (password): {password}")
    
    # Step 3: Combine MID:password
    credentials = f"{mid}:{password}"
    print(f"\n4. Combined Credentials: {credentials}")
    
    # Step 4: Base64 encode with ISO-8859-1
    basic_auth = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
    print(f"\n5. Final Base64 (ISO-8859-1): {basic_auth}")
    
    # Step 5: Add "Basic" prefix
    final_token = f"Basic {basic_auth}"
    print(f"\n6. Final Authorization Token: {final_token}")
    
    return final_token

def test_skrillpe_headers():
    """Test complete headers generation"""
    print("\n" + "=" * 60)
    print("Testing Complete SkrillPe Headers")
    print("=" * 60)
    
    service = SkrillPeService()
    headers = service.get_headers()
    
    print("\nGenerated Headers:")
    for key, value in headers.items():
        if key == 'Authorization':
            print(f"   {key}: {value}")
        elif 'AUTH' in key:
            # Mask sensitive data
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '*' * len(value)
            print(f"   {key}: {masked}")
        else:
            print(f"   {key}: {value}")
    
    return headers

def test_api_call():
    """Test actual API call with proper headers"""
    print("\n" + "=" * 60)
    print("Testing SkrillPe API Call")
    print("=" * 60)
    
    import requests
    import json
    
    service = SkrillPeService()
    
    # Test payload
    payload = {
        'transactionId': 'TEST_' + str(int(time.time())),
        'amount': '100',
        'customerNumber': '9999999999',
        'CompanyAlise': service.company_alias
    }
    
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    url = f"{service.base_url}/api/skrill/upi/qr/send/intent/WL"
    print(f"\nEndpoint: {url}")
    
    headers = service.get_headers()
    print(f"\nHeaders (masked):")
    for key, value in headers.items():
        if 'AUTH' in key or key == 'Authorization':
            masked = value[:10] + '...' + value[-10:] if len(value) > 20 else value
            print(f"   {key}: {masked}")
        else:
            print(f"   {key}: {value}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        return response
        
    except Exception as e:
        print(f"\nError: {e}")
        return None

if __name__ == '__main__':
    import time
    
    # Test 1: Basic Auth Generation
    token = test_basic_auth_generation()
    
    # Test 2: Complete Headers
    headers = test_skrillpe_headers()
    
    # Test 3: API Call (optional - uncomment to test)
    # test_api_call()
    
    print("\n" + "=" * 60)
    print("✓ Authentication tests completed!")
    print("=" * 60)
