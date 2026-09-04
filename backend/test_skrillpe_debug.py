"""
Debug SkrillPe API Integration
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from skrillpe_service import SkrillPeService
import json

print("=" * 60)
print("SkrillPe API Debug Test")
print("=" * 60)

# Initialize service
service = SkrillPeService()

print("\n1. Configuration Check:")
print(f"   Base URL: {service.base_url}")
print(f"   MID: {service.mid}")
print(f"   Mobile: {service.mobile_number}")
print(f"   Company Alias: {service.company_alias}")
print(f"   Auth API Key: {service.auth_api_key[:10]}..." if service.auth_api_key else "   Auth API Key: NOT SET")
print(f"   Auth API Password: {service.auth_api_password[:10]}..." if service.auth_api_password else "   Auth API Password: NOT SET")

print("\n2. Generate Basic Auth Token:")
token = service.generate_basic_auth_token()
if token:
    print(f"   ✓ Token generated: {token[:30]}...")
else:
    print("   ✗ Token generation failed")

print("\n3. Get Headers:")
headers = service.get_headers()
print(f"   Headers:")
for key, value in headers.items():
    if key == 'Authorization':
        print(f"     {key}: {value[:30]}..." if value else f"     {key}: None")
    else:
        print(f"     {key}: {value[:20]}..." if len(str(value)) > 20 else f"     {key}: {value}")

print("\n4. Test API Call:")
import requests

url = f"{service.base_url}/api/skrill/upi/qr/send/intent/WL"
payload = {
    'transactionId': 'TEST_TXN_123456',
    'amount': '100',
    'customerNumber': '9999999999',
    'CompanyAlise': service.company_alias
}

print(f"   URL: {url}")
print(f"   Payload: {json.dumps(payload, indent=6)}")
print(f"   Headers: {json.dumps({k: v[:30]+'...' if k == 'Authorization' and v else v for k, v in headers.items()}, indent=6)}")

try:
    print("\n   Making API call...")
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print(f"\n5. Response:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    print(f"   Body: {response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\n   Parsed JSON:")
            print(f"   {json.dumps(data, indent=6)}")
        except:
            print(f"   Could not parse as JSON")
    
except requests.exceptions.Timeout:
    print("   ✗ Request timed out")
except requests.exceptions.ConnectionError as e:
    print(f"   ✗ Connection error: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
