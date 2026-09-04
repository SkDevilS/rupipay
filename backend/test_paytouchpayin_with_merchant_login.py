#!/usr/bin/env python3
"""
Test Paytouchpayin Integration via Merchant API
Tests the complete flow: Login → Create Order → Verify Response
"""

import requests
import json
import time

print("=" * 70)
print("PAYTOUCHPAYIN MERCHANT API TEST")
print("=" * 70)
print()

# Configuration
BASE_URL = "https://api.moneyone.co.in"
MERCHANT_ID = "7679022140"
PASSWORD = "So@080903"

print("Configuration:")
print(f"  Base URL: {BASE_URL}")
print(f"  Merchant ID: {MERCHANT_ID}")
print(f"  Password: {'*' * len(PASSWORD)}")
print()

# Step 1: Login
print("-" * 70)
print("STEP 1: Merchant Login")
print("-" * 70)
print()

login_url = f"{BASE_URL}/api/merchant/login"
login_payload = {
    "merchantId": MERCHANT_ID,  # Note: camelCase, not snake_case
    "password": PASSWORD
}

print(f"Request URL: {login_url}")
print(f"Request Payload:")
print(json.dumps(login_payload, indent=2))
print()

try:
    print("Sending login request...")
    login_response = requests.post(
        login_url,
        json=login_payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"Response Status: {login_response.status_code}")
    print(f"Response Body:")
    print(json.dumps(login_response.json(), indent=2))
    print()
    
    if login_response.status_code == 200:
        login_data = login_response.json()
        
        if login_data.get('success'):
            token = login_data.get('token')
            print(f"✅ Login successful!")
            print(f"Token: {token[:50]}...")
            print()
        else:
            print(f"❌ Login failed: {login_data.get('message')}")
            exit(1)
    else:
        print(f"❌ Login failed with HTTP {login_response.status_code}")
        exit(1)
        
except Exception as e:
    print(f"❌ Login error: {e}")
    exit(1)

# Step 2: Create Payin Order
print("-" * 70)
print("STEP 2: Create Payin Order (Paytouchpayin)")
print("-" * 70)
print()

order_url = f"{BASE_URL}/api/payin/order/create"

# Generate unique order ID
order_id = f"TEST{int(time.time())}"

order_payload = {
    "amount": "100",
    "orderid": order_id,
    "payee_fname": "Test Customer",
    "payee_mobile": "9876543210",
    "payee_email": "test@example.com"
}

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

print(f"Request URL: {order_url}")
print(f"Request Headers:")
print(f"  Authorization: Bearer {token[:30]}...")
print(f"Request Payload:")
print(json.dumps(order_payload, indent=2))
print()

try:
    print("Sending create order request...")
    order_response = requests.post(
        order_url,
        json=order_payload,
        headers=headers,
        timeout=30
    )
    
    print(f"Response Status: {order_response.status_code}")
    print(f"Response Body:")
    
    try:
        response_json = order_response.json()
        print(json.dumps(response_json, indent=2))
        print()
        
        if order_response.status_code == 200:
            if response_json.get('success'):
                print("✅ Order created successfully!")
                print()
                print("Order Details:")
                print(f"  - Order ID: {response_json.get('order_id')}")
                print(f"  - Transaction ID: {response_json.get('txn_id')}")
                print(f"  - PG Transaction ID: {response_json.get('pg_txn_id')}")
                print(f"  - Amount: ₹{response_json.get('amount')}")
                print(f"  - Charge: ₹{response_json.get('charge')}")
                print(f"  - Final Amount: ₹{response_json.get('final_amount')}")
                print(f"  - Payment Link: {response_json.get('payment_link')}")
                print()
                
                # Verify Paytouchpayin specific fields
                print("Paytouchpayin Integration Verification:")
                if response_json.get('pg_txn_id'):
                    print("  ✓ PG Transaction ID (apitxnid) received")
                if response_json.get('payment_link'):
                    print("  ✓ Payment Link (redirect_url) received")
                if 'shreefintechsolutions.com' in response_json.get('payment_link', ''):
                    print("  ✓ Payment link is from Paytouchpayin domain")
                print()
                
                print("✅ PAYTOUCHPAYIN INTEGRATION TEST PASSED!")
                print()
                print("Next Steps:")
                print("  1. Open the payment link in browser to test QR payment")
                print("  2. Check callback handling after payment")
                print("  3. Verify transaction status update")
                
            else:
                print(f"❌ Order creation failed: {response_json.get('message')}")
                print()
                print("Error Details:")
                if 'error' in response_json:
                    print(f"  Error: {response_json.get('error')}")
        else:
            print(f"❌ Order creation failed with HTTP {order_response.status_code}")
            print(f"Message: {response_json.get('message', 'Unknown error')}")
            
    except json.JSONDecodeError:
        print("Response (not JSON):")
        print(order_response.text)
        print()
        print(f"❌ Invalid JSON response")
        
except requests.exceptions.Timeout:
    print("❌ Request timeout")
except requests.exceptions.RequestException as e:
    print(f"❌ Request error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
