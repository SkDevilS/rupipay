#!/usr/bin/env python3
"""
Test Rang integration after fixing database column issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
import json

def test_rang_integration():
    """Test Rang payin integration"""
    print("=" * 60)
    print("TESTING RANG INTEGRATION (FIXED)")
    print("=" * 60)
    
    rang_service = RangService()
    
    # Test data
    merchant_id = "9000000001"
    order_data = {
        'orderid': 'TEST_RANG_001',
        'amount': '100',
        'payee_fname': 'Test Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'scheme_id': 1
    }
    
    print(f"Testing with merchant_id: {merchant_id}")
    print(f"Order data: {json.dumps(order_data, indent=2)}")
    
    try:
        # Test order creation
        print("\n1. Testing order creation...")
        result = rang_service.create_payin_order(merchant_id, order_data)
        
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ Order creation successful!")
            
            # Test status check
            print("\n2. Testing status check...")
            txn_id = result.get('txn_id')
            if txn_id:
                status_result = rang_service.check_payment_status(txn_id)
                print(f"Status check result: {json.dumps(status_result, indent=2)}")
            
        else:
            print("❌ Order creation failed!")
            print(f"Error: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rang_integration()