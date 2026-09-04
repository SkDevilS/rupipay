#!/usr/bin/env python3
"""
Test Rang with simple RefID format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
import json

def test_simple_refid():
    """Test with simple RefID format"""
    print("=" * 60)
    print("TESTING RANG WITH SIMPLE REFID")
    print("=" * 60)
    
    rang_service = RangService()
    
    # Generate a few RefIDs to see the format
    print("Sample RefID generation:")
    for i in range(5):
        ref_id = rang_service.generate_txn_id("9000000001", f"TEST{i}")
        print(f"  RefID {i+1}: {ref_id} (Length: {len(ref_id)})")
    
    print("\n" + "=" * 40)
    print("TESTING API CALL")
    print("=" * 40)
    
    # Test data
    merchant_id = "9000000001"
    order_data = {
        'orderid': 'TST001',
        'amount': '100',
        'payee_fname': 'Test Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'scheme_id': 1
    }
    
    ref_id = rang_service.generate_txn_id(merchant_id, order_data['orderid'])
    print(f"Generated RefID: {ref_id} (Length: {len(ref_id)})")
    
    try:
        print("\nTesting Rang order creation...")
        result = rang_service.create_payin_order(merchant_id, order_data)
        
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ Order creation successful!")
        else:
            print("❌ Order creation failed!")
            error_msg = result.get('message', '')
            if 'length' in error_msg.lower():
                print(f"🔍 Still a length issue: {error_msg}")
                print("💡 Suggestion: Try even shorter RefID or check Rang documentation")
            else:
                print(f"🔍 Different error: {error_msg}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_refid()