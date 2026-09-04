#!/usr/bin/env python3
"""
Test ViyonaPay Service Integration
Tests the actual service implementation to verify it works correctly
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from viyonapay_service import viyonapay_service
from datetime import datetime
import json

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ViyonaPay Service Integration Test".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Generate Access Token
    print_header("TEST 1: Generate Access Token")
    
    token = viyonapay_service.generate_access_token()
    
    if token:
        print(f"✅ Token generated successfully")
        print(f"   Token: {token[:50]}...")
    else:
        print(f"❌ Token generation failed")
        return
    
    # Test 2: Create Payment Intent
    print_header("TEST 2: Create Payment Intent")
    
    # Prepare test order data
    order_data = {
        'amount': '100.00',
        'orderid': f'TEST_ORDER_{int(datetime.now().timestamp())}',
        'payee_fname': 'Test',
        'payee_lname': 'Customer',
        'payee_email': 'test@example.com',
        'payee_mobile': '9999999999',
        'productinfo': 'Test Payment'
    }
    
    print(f"\n📦 Order Details:")
    print(f"   Order ID: {order_data['orderid']}")
    print(f"   Amount: ₹{order_data['amount']}")
    print(f"   Customer: {order_data['payee_fname']} {order_data['payee_lname']}")
    print(f"   Email: {order_data['payee_email']}")
    print(f"   Phone: {order_data['payee_mobile']}")
    
    # Use a test merchant ID (you can change this)
    test_merchant_id = '9000000001'
    
    print(f"\n🔄 Creating payment intent for merchant: {test_merchant_id}")
    
    result = viyonapay_service.create_payin_order(test_merchant_id, order_data)
    
    print(f"\n📥 Result:")
    print(json.dumps(result, indent=2))
    
    if result.get('success'):
        print(f"\n✅ Payment intent created successfully!")
        print(f"   Transaction ID: {result.get('txn_id')}")
        print(f"   Payment Intent ID: {result.get('payment_intent_id')}")
        print(f"   Payment URL: {result.get('payment_url')}")
        print(f"   Amount: ₹{result.get('amount')}")
        print(f"   Charge: ₹{result.get('charge_amount')}")
        print(f"   Net Amount: ₹{result.get('net_amount')}")
    else:
        print(f"\n❌ Payment intent creation failed")
        print(f"   Error: {result.get('message')}")
    
    # Summary
    print_header("Test Summary")
    print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if result.get('success'):
        print("\n✅ All tests passed!")
        print(f"\n💡 Next Steps:")
        print(f"   1. Open the payment URL in browser")
        print(f"   2. Complete the UPI payment")
        print(f"   3. Check webhook for status updates")
    else:
        print("\n❌ Tests failed - check error messages above")

if __name__ == "__main__":
    main()
