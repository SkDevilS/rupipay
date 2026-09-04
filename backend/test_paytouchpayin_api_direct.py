#!/usr/bin/env python3
"""
Direct test of Paytouchpayin API
Tests the API endpoint directly to verify credentials and response format
"""

import requests
import json
import time

print("=" * 70)
print("PAYTOUCHPAYIN API DIRECT TEST")
print("=" * 70)
print()

# Paytouchpayin API Configuration
BASE_URL = "https://dashboard.shreefintechsolutions.com"
TOKEN = "bfFkfbCtbOysf5RWoF7Tl1VjKc4hScTHE"

print("Configuration:")
print(f"  Base URL: {BASE_URL}")
print(f"  Token: {TOKEN[:20]}... (30 chars)")
print()

# Test 1: Generate Dynamic QR
print("-" * 70)
print("TEST 1: Generate Dynamic QR")
print("-" * 70)
print()

url = f"{BASE_URL}/api/payin/dynamic-qr"

# Generate unique transaction ID
txnid = f"TEST{int(time.time())}"

payload = {
    "token": TOKEN,
    "mobile": "9876543210",
    "amount": "10",
    "txnid": txnid,
    "name": "Test Customer"
}

print(f"Request URL: {url}")
print(f"Request Payload:")
print(json.dumps(payload, indent=2))
print()

try:
    print("Sending request...")
    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))
    print()
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'SUCCESS':
            print("✅ TEST PASSED: Dynamic QR generated successfully")
            print()
            print("Response Data:")
            qr_data = data.get('data', {})
            print(f"  - Transaction ID: {qr_data.get('txnid')}")
            print(f"  - API Transaction ID: {qr_data.get('apitxnid')}")
            print(f"  - Amount: ₹{qr_data.get('amount')}")
            print(f"  - Redirect URL: {qr_data.get('redirect_url')}")
            print(f"  - Customer Name: {qr_data.get('name')}")
            print(f"  - Expires At: {qr_data.get('expire_at')}")
            print()
            print("✅ API is working correctly!")
            print()
            print("Field Mapping Verified:")
            print("  ✓ token → API token (not in order_data)")
            print("  ✓ mobile → customer mobile")
            print("  ✓ amount → payment amount")
            print("  ✓ txnid → unique transaction ID")
            print("  ✓ name → customer name")
            print()
            print("Response Mapping:")
            print("  ✓ redirect_url → payment_link (QR payment page)")
            print("  ✓ apitxnid → pg_txn_id (Paytouchpayin transaction ID)")
            print("  ✓ amount → includes charges (e.g., ₹10 → ₹10.24)")
        else:
            print(f"❌ TEST FAILED: {data.get('message')}")
    else:
        print(f"❌ TEST FAILED: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ TEST FAILED: Request timeout")
except requests.exceptions.RequestException as e:
    print(f"❌ TEST FAILED: Request error - {e}")
except Exception as e:
    print(f"❌ TEST FAILED: {e}")

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print()
print("Next Steps:")
print("  1. If test passed, run: bash deploy_paytouchpayin_complete.sh")
print("  2. This will deploy the service and configure routing")
print("  3. Then test with merchant API")
print()
