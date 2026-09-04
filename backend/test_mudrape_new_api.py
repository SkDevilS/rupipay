#!/usr/bin/env python3
"""
Test script for new Mudrape Payin API format
Updated endpoint: /api/api-mudrape/create-order (March 2026)
Updated parameters: refId, amount, name, mobile, email, userId
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mudrape_service import MudrapeService
from datetime import datetime

def test_new_payin_api():
    """Test the new Mudrape payin API with updated format"""
    
    print("=" * 60)
    print("Testing NEW Mudrape Payin API Format")
    print("=" * 60)
    
    service = MudrapeService()
    
    # Test merchant ID (use a real one from your database)
    test_merchant_id = "9000000001"
    
    # Test order data
    order_data = {
        'amount': '500',
        'orderid': f'TEST_{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'payee_fname': 'Test',
        'payee_lname': 'Customer',
        'payee_mobile': '8130055250',
        'payee_email': 'test@mudrape.com',
        'productinfo': 'Test Payment'
    }
    
    print(f"\n📋 Test Order Details:")
    print(f"   Merchant ID: {test_merchant_id}")
    print(f"   Amount: ₹{order_data['amount']}")
    print(f"   Order ID: {order_data['orderid']}")
    print(f"   Customer: {order_data['payee_fname']} {order_data['payee_lname']}")
    print(f"   Mobile: {order_data['payee_mobile']}")
    print(f"   Email: {order_data['payee_email']}")
    
    print(f"\n🔄 Creating payin order with NEW API format...")
    print(f"   Endpoint: /api/api-mudrape/create-order")
    print(f"   Fields: refId, amount, name, mobile, email, userId")
    
    result = service.create_payin_order(test_merchant_id, order_data)
    
    print(f"\n📊 Result:")
    print(f"   Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"   ✅ Order created successfully!")
        print(f"   Transaction ID: {result.get('txn_id')}")
        print(f"   Order ID (refId): {result.get('order_id')}")
        print(f"   Amount: ₹{result.get('amount')}")
        print(f"   Charge: ₹{result.get('charge_amount')}")
        print(f"   Net Amount: ₹{result.get('net_amount')}")
        print(f"   Mudrape TXN ID: {result.get('mudrape_txn_id')}")
        
        if result.get('qr_string'):
            print(f"   QR String: {result.get('qr_string')[:50]}...")
        
        if result.get('upi_link'):
            print(f"   UPI Link: {result.get('upi_link')[:80]}...")
    else:
        print(f"   ❌ Order creation failed!")
        print(f"   Error: {result.get('message')}")
    
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    test_new_payin_api()
