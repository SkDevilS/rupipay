#!/usr/bin/env python3
"""
Diagnose Rang RefID length issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
import json

def diagnose_refid_issue():
    """Diagnose the RefID length issue"""
    print("=" * 60)
    print("DIAGNOSING RANG REFID ISSUE")
    print("=" * 60)
    
    rang_service = RangService()
    
    # Test with the exact same data that's failing
    merchant_id = "9000000001"
    order_data = {
        'orderid': 'TEST_RANG_001',
        'amount': '100',
        'payee_fname': 'Test Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'scheme_id': 1
    }
    
    print("Original failing case:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Order ID: {order_data['orderid']}")
    
    # Generate RefID with new method
    ref_id = rang_service.generate_txn_id(merchant_id, order_data['orderid'])
    print(f"  New RefID: {ref_id}")
    print(f"  RefID Length: {len(ref_id)} characters")
    
    # Test different RefID lengths to find the limit
    print("\n" + "=" * 40)
    print("TESTING DIFFERENT REFID LENGTHS")
    print("=" * 40)
    
    test_refids = [
        "RNG001",           # 6 chars
        "RNG12345",         # 9 chars  
        "RNG1234567890",    # 14 chars
        "RNG123456789012345", # 19 chars
        ref_id              # Our generated RefID
    ]
    
    for test_ref in test_refids:
        print(f"\nTesting RefID: {test_ref} (Length: {len(test_ref)})")
        
        # Manually create the payload to test
        payload = {
            "RefID": test_ref,
            "Amount": "100",
            "Customer_Name": "Test Customer",
            "Customer_Mobile": "9876543210",
            "Customer_Email": "test@example.com"
        }
        
        print(f"  Payload: {json.dumps(payload, indent=2)}")
        
        # Test token generation first
        print("  Testing token generation...")
        token_result = rang_service.generate_token()
        
        if token_result:
            print("  ✅ Token generated successfully")
            
            # Test API call
            print("  Testing API call...")
            try:
                import requests
                
                url = f"{rang_service.base_url}/api/Payin/create-order"
                headers = rang_service.get_headers(include_auth=True)
                
                print(f"  URL: {url}")
                print(f"  Headers: {headers}")
                
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                print(f"  Response Status: {response.status_code}")
                print(f"  Response Body: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 1:
                        print(f"  ✅ SUCCESS with RefID length {len(test_ref)}")
                    else:
                        print(f"  ❌ FAILED: {data.get('message')}")
                        if "length" in data.get('message', '').lower():
                            print(f"  🔍 Length issue confirmed with {len(test_ref)} chars")
                else:
                    print(f"  ❌ HTTP Error: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Exception: {str(e)}")
        else:
            print("  ❌ Token generation failed")
        
        print("-" * 40)

if __name__ == "__main__":
    diagnose_refid_issue()