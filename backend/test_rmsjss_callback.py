"""
Test RMS_JSS Callback Handler
Tests the callback endpoint with sample data
"""

import requests
import json

# Test callback URL
CALLBACK_URL = "https://api.moneyone.co.in/api/callback/rmsjss/payin"

# Test data based on RMS sample
test_data = {
    'payid': '15234',
    'client_id': 'P202605201430259876',
    'operator_ref': 'UTR9876543210',
    'status': 'success'
}

print("=" * 80)
print("Testing RMS_JSS Callback Handler")
print("=" * 80)

# Test 1: GET request with query parameters (most likely format)
print("\n1. Testing GET request with query parameters...")
print(f"URL: {CALLBACK_URL}")
print(f"Parameters: {test_data}")

try:
    response = requests.get(CALLBACK_URL, params=test_data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: POST request with query parameters
print("\n2. Testing POST request with query parameters...")
try:
    response = requests.post(CALLBACK_URL, params=test_data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: POST request with JSON body
print("\n3. Testing POST request with JSON body...")
try:
    response = requests.post(
        CALLBACK_URL, 
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: POST request with form data
print("\n4. Testing POST request with form data...")
try:
    response = requests.post(
        CALLBACK_URL, 
        data=test_data,
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
