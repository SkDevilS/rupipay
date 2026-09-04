#!/usr/bin/env python3
"""
Test Paytouchpayin service after cursor fix
"""

import sys
import json

# Test the service
from paytouchpayin_service import PaytouchpayinService

print("=" * 80)
print("TESTING PAYTOUCHPAYIN SERVICE - CURSOR FIX")
print("=" * 80)

# Initialize service
service = PaytouchpayinService()

# Test data
merchant_id = "7679022140"
order_data = {
    "amount": 100,
    "orderid": "TEST_CURSOR_FIX_123",
    "payee_fname": "Test Customer",
    "payee_mobile": "9876543210",
    "payee_email": "test@example.com"
}

print(f"\n📋 Testing with:")
print(f"  Merchant ID: {merchant_id}")
print(f"  Order Data: {json.dumps(order_data, indent=2)}")

print("\n" + "=" * 80)
print("CREATING PAYIN ORDER")
print("=" * 80)

result = service.create_payin_order(merchant_id, order_data)

print("\n" + "=" * 80)
print("RESULT:")
print("=" * 80)
print(json.dumps(result, indent=2))

if result.get('success'):
    print("\n✅ SUCCESS!")
    print(f"  Transaction ID: {result.get('txn_id')}")
    print(f"  PG Transaction ID: {result.get('pg_txn_id')}")
    print(f"  Amount: ₹{result.get('amount')}")
    print(f"  Charge: ₹{result.get('charge')}")
    print(f"  Final Amount: ₹{result.get('final_amount')}")
    print(f"  Payment URL: {result.get('payment_link')}")
else:
    print(f"\n❌ FAILED!")
    print(f"  Error: {result.get('error')}")
    sys.exit(1)
