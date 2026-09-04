#!/usr/bin/env python3
"""
Test PayTouch2 callback endpoint directly
"""

import requests
import json
from datetime import datetime

print("=" * 80)
print("TESTING PAYTOUCH2 CALLBACK ENDPOINT")
print("=" * 80)

# Test data
test_payload = {
    "transaction_id": "PT2_DIRECT_TEST_" + datetime.now().strftime("%Y%m%d%H%M%S"),
    "external_ref": "REF_DIRECT_TEST",
    "status": "SUCCESS",
    "utr_no": "UTR" + datetime.now().strftime("%Y%m%d%H%M%S"),
    "amount": 1000.0,
    "message": "Direct test transaction",
    "timestamp": datetime.now().isoformat()
}

print("\n1. Testing localhost:5000 (direct to Gunicorn)")
print("-" * 80)
print(f"Payload: {json.dumps(test_payload, indent=2)}")

try:
    response = requests.post(
        "http://localhost:5000/api/callback/paytouch2/payout",
        json=test_payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS - Endpoint is working!")
    elif response.status_code == 404:
        print("\n❌ 404 ERROR - Route not found!")
        print("This means the route is NOT accessible even though it's registered.")
    else:
        print(f"\n⚠️  Unexpected status code: {response.status_code}")
        
except requests.exceptions.ConnectionError as e:
    print(f"\n❌ CONNECTION ERROR: {e}")
    print("Gunicorn might not be running or not listening on port 5000")
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 80)
print("\n2. Testing via public API (through load balancer)")
print("-" * 80)

test_payload["transaction_id"] = "PT2_PUBLIC_TEST_" + datetime.now().strftime("%Y%m%d%H%M%S")

try:
    response = requests.post(
        "https://api.moneyone.co.in/api/callback/paytouch2/payout",
        json=test_payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
        verify=True
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS - Public endpoint is working!")
    elif response.status_code == 404:
        print("\n❌ 404 ERROR - Route not found via load balancer!")
    else:
        print(f"\n⚠️  Unexpected status code: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
