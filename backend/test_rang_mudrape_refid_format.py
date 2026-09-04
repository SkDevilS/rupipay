#!/usr/bin/env python3
"""
Test Rang RefID format matches Mudrape format exactly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
from mudrape_service import MudrapeService
import json

def test_refid_format_comparison():
    """Compare Rang and Mudrape RefID formats"""
    print("=" * 60)
    print("COMPARING RANG AND MUDRAPE REFID FORMATS")
    print("=" * 60)
    
    rang_service = RangService()
    mudrape_service = MudrapeService()
    
    # Test data
    merchant_id = "9000000001"
    order_id = "TEST001"
    
    print("Generating RefIDs with same parameters:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Order ID: {order_id}")
    print()
    
    # Generate multiple RefIDs to see the pattern
    print("Sample RefID Generation:")
    print("-" * 40)
    
    for i in range(5):
        rang_ref = rang_service.generate_txn_id(merchant_id, f"ORDER{i}")
        mudrape_ref = mudrape_service.generate_txn_id(merchant_id, f"ORDER{i}")
        
        print(f"Test {i+1}:")
        print(f"  Rang RefID:    {rang_ref} (Length: {len(rang_ref)})")
        print(f"  Mudrape RefID: {mudrape_ref} (Length: {len(mudrape_ref)})")
        
        # Check if formats match
        if len(rang_ref) == len(mudrape_ref):
            print(f"  ✅ Length matches: {len(rang_ref)} digits")
        else:
            print(f"  ❌ Length mismatch: Rang={len(rang_ref)}, Mudrape={len(mudrape_ref)}")
        
        # Check if both are numeric
        if rang_ref.isdigit() and mudrape_ref.isdigit():
            print(f"  ✅ Both are numeric")
        else:
            print(f"  ❌ Format issue: Rang numeric={rang_ref.isdigit()}, Mudrape numeric={mudrape_ref.isdigit()}")
        
        print()

def test_rang_api_with_mudrape_format():
    """Test Rang API with Mudrape-style RefID"""
    print("=" * 60)
    print("TESTING RANG API WITH MUDRAPE-STYLE REFID")
    print("=" * 60)
    
    rang_service = RangService()
    
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
    
    # Generate RefID
    ref_id = rang_service.generate_txn_id(merchant_id, order_data['orderid'])
    print(f"Generated RefID: {ref_id}")
    print(f"RefID Length: {len(ref_id)} digits")
    print(f"RefID Format: {'✅ Numeric' if ref_id.isdigit() else '❌ Non-numeric'}")
    print(f"RefID Pattern: YYYYMMDDHHMMSS + 6-digit random")
    
    # Parse the RefID to show structure
    if len(ref_id) == 20 and ref_id.isdigit():
        timestamp_part = ref_id[:14]
        random_part = ref_id[14:]
        print(f"  Timestamp part: {timestamp_part} (14 digits)")
        print(f"  Random part: {random_part} (6 digits)")
        
        # Try to parse timestamp
        try:
            from datetime import datetime
            parsed_time = datetime.strptime(timestamp_part, '%Y%m%d%H%M%S')
            print(f"  Parsed time: {parsed_time}")
            print(f"  ✅ Valid timestamp format")
        except:
            print(f"  ❌ Invalid timestamp format")
    
    print("\nTesting API call...")
    try:
        result = rang_service.create_payin_order(merchant_id, order_data)
        
        print(f"API Result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ API call successful with Mudrape-style RefID!")
        else:
            print("❌ API call failed!")
            error_msg = result.get('message', '')
            if 'length' in error_msg.lower():
                print(f"🔍 Still a length issue: {error_msg}")
            else:
                print(f"🔍 Different error: {error_msg}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refid_format_comparison()
    test_rang_api_with_mudrape_format()