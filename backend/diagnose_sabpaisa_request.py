#!/usr/bin/env python3
"""
Diagnose Sabpaisa Request - Check what we're sending vs what they expect
"""

import requests
import json
import hmac
import hashlib
import time
from datetime import datetime

# Sabpaisa Credentials
SABPAISA_BASE_URL = "https://merchant-api.sabpaisa.in"
CLIENT_CODE = "GROS1"
API_KEY = "sp_VnZyfhBwunpPlq2-OqZdzGx-jwtW7e4ma5oFJZyzC-g"
SECRET_KEY = "sec_nO_3BmCMpUOSRcvABZylNmac7g5LumG4zAamrNgmbPQ"

def generate_checksum(merchant_id, merchant_txn_id, amount, currency, timestamp, secret_key):
    """Generate HMAC-SHA256 checksum"""
    message = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature.lower()

print("="*70)
print("SABPAISA REQUEST DIAGNOSIS")
print("="*70)

# Test with ₹500 (50000 paise)
amount_rupees = 500
amount_paise = int(amount_rupees * 100)

print(f"\n1. Amount Conversion:")
print(f"   Amount in Rupees: ₹{amount_rupees}")
print(f"   Amount in Paise: {amount_paise}")
print(f"   Type: {type(amount_paise)}")

# Generate transaction ID
timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
merchant_txn_id = f"SBP_GROS_TEST_{timestamp_str}"

print(f"\n2. Transaction ID:")
print(f"   {merchant_txn_id}")

# Generate timestamp
timestamp = int(time.time())

print(f"\n3. Timestamp:")
print(f"   {timestamp}")

# Generate checksum
checksum = generate_checksum(
    CLIENT_CODE,
    merchant_txn_id,
    amount_paise,
    "INR",
    timestamp,
    SECRET_KEY
)

print(f"\n4. Checksum:")
print(f"   {checksum}")

# Prepare payload
payload = {
    'merchantId': CLIENT_CODE,
    'merchantTxnId': merchant_txn_id,
    'amount': amount_paise,
    'currency': 'INR',
    'customerName': 'Test Customer',
    'customerEmail': 'test@example.com',
    'customerPhone': '9876543210',
    'paymentMode': 'UPI_INTENT',
    'timestamp': timestamp,
    'checksum': checksum,
    'description': 'Test Payment',
    'upiExpiryMinutes': 5
}

print(f"\n5. Request Payload:")
print(json.dumps(payload, indent=2))

# Prepare headers
headers = {
    'Content-Type': 'application/json',
    'X-Api-Key': API_KEY,
    'X-Merchant-Id': CLIENT_CODE
}

print(f"\n6. Request Headers:")
for key, value in headers.items():
    if key == 'X-Api-Key':
        print(f"   {key}: {value[:20]}...")
    else:
        print(f"   {key}: {value}")

url = f"{SABPAISA_BASE_URL}/api/v1/payments/s2s"

print(f"\n7. Request URL:")
print(f"   {url}")

print(f"\n8. Sending Request...")
print("-"*70)

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"\n9. Response Status: {response.status_code}")
    
    print(f"\n10. Response Headers:")
    for key, value in response.headers.items():
        print(f"    {key}: {value}")
    
    print(f"\n11. Response Body:")
    try:
        result = response.json()
        print(json.dumps(result, indent=2))
    except:
        print(response.text)
    
    print("\n" + "="*70)
    print("DIAGNOSIS COMPLETE")
    print("="*70)
    
    if response.status_code == 500:
        print("\n❌ INTERNAL_ERROR received")
        print("\nPossible causes:")
        print("1. Amount format issue (should be in paise)")
        print("2. Invalid customer details")
        print("3. Invalid merchant credentials")
        print("4. API endpoint issue")
        print("\nChecking our payload:")
        print(f"✓ Amount is integer: {isinstance(payload['amount'], int)}")
        print(f"✓ Amount in paise: {payload['amount']}")
        print(f"✓ Customer phone length: {len(payload['customerPhone'])}")
        print(f"✓ Customer email valid: {'@' in payload['customerEmail']}")
        print(f"✓ Checksum length: {len(payload['checksum'])}")
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")
    import traceback
    traceback.print_exc()
