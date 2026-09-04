#!/usr/bin/env python3
"""
Test script for Skrillpe UPI QR Intent API
Generates Basic Auth token using SHA1 hashing and tests the API endpoint
"""

import requests
import hashlib
import base64
import json
from datetime import datetime

# Configuration
MOBILE_NUMBER = "7376582857"
MPIN = "28619924"
API_KEY = "F8D12F51-1732-4787-B8DD-7858A41E396F"  # Replace with actual API key
API_PASSWORD = "8DB03D51BB9A4CFDB8F35B1E7572433A"  # Replace with actual API password
BASE_URL = "https://clientapisrv.skrillpe.com/poutsaps"  # Replace with actual base URL
ENDPOINT = "/api/skrill/upi/qr/get/intent/WL"

def generate_basic_auth_token(mobile_number, mpin):
    """
    Generate Basic Authentication token using SHA1 hashing
    Following the C# implementation provided
    """
    try:
        # Step 1: Hash the MPIN using SHA1
        password_bytes = mpin.encode('utf-8')
        sha1_hash = hashlib.sha1(password_bytes).digest()
        password_base64 = base64.b64encode(sha1_hash).decode('utf-8')
        
        print(f"[DEBUG] MPIN: {mpin}")
        print(f"[DEBUG] SHA1 Hash (Base64): {password_base64}")
        
        # Step 2: Combine mobile number and hashed password
        credentials = f"{mobile_number}:{password_base64}"
        print(f"[DEBUG] Credentials String: {credentials}")
        
        # Step 3: Encode using ISO-8859-1 and then Base64
        credentials_bytes = credentials.encode('iso-8859-1')
        final_basic_auth = base64.b64encode(credentials_bytes).decode('utf-8')
        
        # Step 4: Format as "Basic <token>"
        auth_token = f"Basic {final_basic_auth}"
        print(f"[DEBUG] Final Basic Auth Token: {auth_token}")
        
        return auth_token
        
    except Exception as ex:
        print(f"[ERROR] Failed to generate auth token: {ex}")
        return None

def test_skrillpe_qr_intent():
    """
    Test the Skrillpe UPI QR Intent API endpoint
    """
    print("=" * 80)
    print("SKRILLPE UPI QR INTENT API TEST")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Generate Basic Auth token
    print("[STEP 1] Generating Basic Auth Token...")
    basic_auth_token = generate_basic_auth_token(MOBILE_NUMBER, MPIN)
    
    if not basic_auth_token:
        print("[ERROR] Failed to generate Basic Auth token. Exiting.")
        return
    
    print("[SUCCESS] Basic Auth token generated successfully")
    print()
    
    # Prepare headers
    print("[STEP 2] Preparing API Headers...")
    headers = {
        'Authorization': basic_auth_token,
        'AUTH-API_KEY': API_KEY,
        'AUTH-API_PASSWORD': API_PASSWORD,
        'Content-Type': 'application/json'
    }
    
    print("Headers:")
    for key, value in headers.items():
        if key == 'Authorization':
            print(f"  {key}: {value[:20]}... (truncated)")
        else:
            # Mask sensitive data
            masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '*' * len(value)
            print(f"  {key}: {masked_value}")
    print()
    
    # Prepare request payload
    print("[STEP 3] Preparing Request Payload...")
    payload = {
        "transactionId": f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "amount": "100.00",
        "customerNumber": "9876543210",
        "CompanyAlise": "TESTCOMPANY"
    }
    
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    # Make API request
    print("[STEP 4] Making API Request...")
    url = f"{BASE_URL}{ENDPOINT}"
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print("[STEP 5] Response Received")
        print("-" * 80)
        print(f"Status Code: {response.status_code}")
        print(f"Status Text: {response.reason}")
        print()
        
        print("Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()
        
        print("Response Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except:
            print(response.text)
        print("-" * 80)
        
        # Analyze response
        print()
        print("[STEP 6] Response Analysis")
        if response.status_code == 200:
            print("[SUCCESS] ✓ API call successful (200 OK)")
            try:
                data = response.json()
                if 'intentUrl' in data or 'qrCode' in data or 'paymentUrl' in data:
                    print("[SUCCESS] ✓ Response contains payment data")
                else:
                    print("[WARNING] ⚠ Response structure unexpected")
            except:
                print("[WARNING] ⚠ Response is not JSON")
        elif response.status_code == 401:
            print("[ERROR] ✗ Authentication failed (401 Unauthorized)")
            print("  - Check if API_KEY and API_PASSWORD are correct")
            print("  - Verify Basic Auth token generation")
        elif response.status_code == 403:
            print("[ERROR] ✗ Access forbidden (403 Forbidden)")
            print("  - Check if your IP/domain is whitelisted")
        elif response.status_code == 400:
            print("[ERROR] ✗ Bad request (400)")
            print("  - Check payload format and required fields")
        else:
            print(f"[ERROR] ✗ Unexpected status code: {response.status_code}")
        
    except requests.exceptions.Timeout:
        print("[ERROR] ✗ Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError:
        print("[ERROR] ✗ Connection error - check if API URL is correct")
    except Exception as ex:
        print(f"[ERROR] ✗ Unexpected error: {ex}")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    print()
    print("IMPORTANT: Update the following variables before running:")
    print("  - API_KEY: Your Skrillpe API Key")
    print("  - API_PASSWORD: Your Skrillpe API Password")
    print("  - BASE_URL: Skrillpe API base URL")
    print()
    
    test_skrillpe_qr_intent()
    
    print("After updating credentials, uncomment the test_skrillpe_qr_intent() call")
    print()
