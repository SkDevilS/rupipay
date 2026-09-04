#!/usr/bin/env python3
"""
Test Airpay QR Generation with Domain Debugging
"""
import os
import sys
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service

print("=" * 60)
print("AIRPAY QR GENERATION TEST - DOMAIN DEBUGGING")
print("=" * 60)

# Check configuration
print("\nStep 1: Check domain configuration...")
backend_url = os.getenv('BACKEND_URL', 'https://api.moneyone.co.in')
frontend_url = os.getenv('FRONTEND_URL', 'https://client.moneyone.co.in')
merchant_id = os.getenv('AIRPAY_MERCHANT_ID')

print(f"Backend URL: {backend_url}")
print(f"Frontend URL: {frontend_url}")
print(f"Merchant ID: {merchant_id}")

# Encode mer_dom
mer_dom = base64.b64encode(frontend_url.encode()).decode()
print(f"\nMerchant Domain (mer_dom):")
print(f"  Original: {frontend_url}")
print(f"  Base64: {mer_dom}")
print(f"  Decoded: {base64.b64decode(mer_dom).decode()}")

# Prepare test order data
print("\nStep 2: Prepare test order...")
test_order = {
    'orderid': 'TEST_QR_001',
    'amount': '100.00',
    'tid': '12345678',
    'buyer_email': 'test@example.com',
    'buyer_phone': '9876543210',
    'mer_dom': mer_dom,
    'customvar': 'test_merchant_id=TEST001|test_txn_id=TXN001',
    'call_type': 'upiqr'
}

print(f"Order data:")
for key, value in test_order.items():
    if key == 'mer_dom':
        print(f"  {key}: {value} (decoded: {base64.b64decode(value).decode()})")
    else:
        print(f"  {key}: {value}")

# Generate QR
print("\nStep 3: Generate QR code...")
print("-" * 60)
result = airpay_service.generate_qr(test_order)
print("-" * 60)

# Display result
print("\nStep 4: Result...")
if result.get('success'):
    print("✅ SUCCESS!")
    print(f"QR String: {result.get('qrcode_string', 'N/A')[:50]}...")
    print(f"Transaction ID: {result.get('ap_transactionid', 'N/A')}")
else:
    print("❌ FAILED!")
    print(f"Message: {result.get('message', 'Unknown error')}")
    if 'details' in result:
        import json
        print(f"Details: {json.dumps(result['details'], indent=2)}")

print("\n" + "=" * 60)
print("DOMAIN INFORMATION FOR AIRPAY SUPPORT")
print("=" * 60)
print(f"""
Please whitelist the following domains for Merchant ID: {merchant_id}

1. API Domain (for making API calls):
   {backend_url}

2. Merchant Domain (mer_dom parameter):
   {frontend_url}
   Base64 Encoded: {mer_dom}

3. Callback URL:
   {backend_url}/api/callback/airpay/payin

All three domains need to be registered in Airpay's system.
""")
print("=" * 60)
