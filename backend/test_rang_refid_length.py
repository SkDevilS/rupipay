#!/usr/bin/env python3
"""
Test Rang RefID length generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
import json

def test_refid_generation():
    """Test RefID generation and length"""
    print("=" * 60)
    print("TESTING RANG REFID LENGTH")
    print("=" * 60)
    
    rang_service = RangService()
    
    # Test different scenarios
    test_cases = [
        {"merchant_id": "9000000001", "order_id": "TEST001"},
        {"merchant_id": "9000000001", "order_id": "VERY_LONG_ORDER_ID_123456789"},
        {"merchant_id": "1234567890", "order_id": "SHORT"},
        {"merchant_id": "9000000001", "order_id": "ORDER_12345"},
    ]
    
    print("Testing RefID generation:")
    print("-" * 60)
    
    for i, case in enumerate(test_cases, 1):
        merchant_id = case["merchant_id"]
        order_id = case["order_id"]
        
        # Generate RefID
        ref_id = rang_service.generate_txn_id(merchant_id, order_id)
        
        print(f"Test {i}:")
        print(f"  Merchant ID: {merchant_id}")
        print(f"  Order ID: {order_id}")
        print(f"  Generated RefID: {ref_id}")
        print(f"  RefID Length: {len(ref_id)} characters")
        
        # Check if length is acceptable (most APIs prefer 20 chars or less)
        if len(ref_id) <= 20:
            print(f"  ✅ Length OK (≤20 chars)")
        elif len(ref_id) <= 25:
            print(f"  ⚠️  Length borderline (21-25 chars)")
        else:
            print(f"  ❌ Length too long (>25 chars)")
        
        print()

def test_rang_api_call():
    """Test actual API call with new RefID"""
    print("=" * 60)
    print("TESTING RANG API WITH NEW REFID")
    print("=" * 60)
    
    rang_service = RangService()
    
    # Test data with shorter order ID
    merchant_id = "9000000001"
    order_data = {
        'orderid': 'TST001',  # Shorter order ID
        'amount': '100',
        'payee_fname': 'Test Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'scheme_id': 1
    }
    
    print(f"Testing with:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Order data: {json.dumps(order_data, indent=2)}")
    
    # Generate RefID to see what will be sent
    ref_id = rang_service.generate_txn_id(merchant_id, order_data['orderid'])
    print(f"  Generated RefID: {ref_id} (Length: {len(ref_id)})")
    
    try:
        print("\nCalling Rang API...")
        result = rang_service.create_payin_order(merchant_id, order_data)
        
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ API call successful!")
        else:
            print("❌ API call failed!")
            print(f"Error: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refid_generation()
    test_rang_api_call()