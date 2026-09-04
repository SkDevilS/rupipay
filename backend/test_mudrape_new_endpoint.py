#!/usr/bin/env python3
"""
Test script for Mudrape new endpoint and parameter changes
Updated: March 2026
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mudrape_service import MudrapeService
import json

def test_new_endpoint():
    """Test the new Mudrape endpoint with updated parameters"""
    
    print("=" * 60)
    print("Testing Mudrape New Endpoint & Parameters")
    print("=" * 60)
    
    # Initialize service
    service = MudrapeService()
    
    print("\n1. Checking configuration...")
    print(f"   Base URL: {service.base_url}")
    print(f"   API Key: {service.api_key[:20]}..." if service.api_key else "   API Key: NOT SET")
    print(f"   User ID: {service.user_id}")
    
    # Test merchant ID (use a real one from your system)
    test_merchant_id = "9000000001"
    
    # Test order data
    test_order = {
        'amount': 100,
        'orderid': f'TEST_{int(time.time())}',
        'payee_fname': 'Test',
        'payee_lname': 'User',
        'payee_mobile': '9999999999',
        'payee_email': 'test@example.com',
        'productinfo': 'Test Payment'
    }
    
    print("\n2. Test Order Data:")
    print(f"   Merchant ID: {test_merchant_id}")
    print(f"   Amount: ₹{test_order['amount']}")
    print(f"   Order ID: {test_order['orderid']}")
    print(f"   Customer: {test_order['payee_fname']} {test_order['payee_lname']}")
    print(f"   Mobile: {test_order['payee_mobile']}")
    print(f"   Email: {test_order['payee_email']}")
    
    print("\n3. Expected API Call:")
    print("   Endpoint: /api/api-mudrape/create-order")
    print("   Parameters:")
    print("   - refId: (20-digit unique ID)")
    print("   - amount: (integer)")
    print("   - name: (customer name)")
    print("   - mobile: (customer mobile)")
    print("   - email: (customer email)")
    print("   - userId: (Mudrape user ID)")
    
    print("\n4. Creating test order...")
    print("   NOTE: This will make a real API call to Mudrape")
    
    response = input("\n   Proceed with API call? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n   Test cancelled by user")
        return
    
    result = service.create_payin_order(test_merchant_id, test_order)
    
    print("\n5. API Response:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)
    
    if result.get('success'):
        print("\n✓ SUCCESS: Order created successfully!")
        print(f"  Transaction ID: {result.get('txn_id')}")
        print(f"  Order ID: {result.get('order_id')}")
        print(f"  Amount: ₹{result.get('amount')}")
        print(f"  Charge: ₹{result.get('charge_amount')}")
        print(f"  Net Amount: ₹{result.get('net_amount')}")
        
        if result.get('qr_string'):
            print(f"  QR Code: Available ({len(result.get('qr_string'))} chars)")
        
        if result.get('upi_link'):
            print(f"  UPI Link: {result.get('upi_link')[:50]}...")
    else:
        print("\n✗ FAILED: Order creation failed")
        print(f"  Error: {result.get('message')}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_new_endpoint()
