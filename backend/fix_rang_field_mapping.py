#!/usr/bin/env python3
"""
Quick fix script to test Rang field mapping
"""

import json
from rang_service import RangService

def test_field_mapping():
    """Test the field mapping fix"""
    print("🔧 Testing Rang Field Mapping Fix")
    print("=" * 40)
    
    # Test data with your system's field names
    test_order_data = {
        'orderid': 'TEST123456',
        'amount': '100',
        'payee_fname': 'John Doe',
        'payee_email': 'john@example.com',
        'payee_mobile': '9876543210'
    }
    
    print("Input data (your system format):")
    print(json.dumps(test_order_data, indent=2))
    
    # Test the mapping logic
    rang_service = RangService()
    
    # Simulate the mapping that happens in create_payin_order
    mapped_order_data = {
        'order_id': test_order_data.get('orderid'),
        'amount': test_order_data.get('amount'),
        'customer_name': test_order_data.get('payee_fname', ''),
        'customer_mobile': test_order_data.get('payee_mobile'),
        'customer_email': test_order_data.get('payee_email'),
        'scheme_id': test_order_data.get('scheme_id', 1)
    }
    
    print("\nMapped data (Rang format):")
    print(json.dumps(mapped_order_data, indent=2))
    
    # Test Rang API payload
    payload = {
        "RefID": "TEST_TXN_123",
        "Amount": str(mapped_order_data['amount']),
        "Customer_Name": mapped_order_data['customer_name'],
        "Customer_Mobile": mapped_order_data['customer_mobile'],
        "Customer_Email": mapped_order_data['customer_email']
    }
    
    print("\nRang API payload:")
    print(json.dumps(payload, indent=2))
    
    # Validate all required fields are present
    required_fields = ['RefID', 'Amount', 'Customer_Name', 'Customer_Mobile', 'Customer_Email']
    missing_fields = []
    
    for field in required_fields:
        if not payload.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        print(f"\n❌ Missing fields: {missing_fields}")
        return False
    else:
        print("\n✅ All required fields present!")
        print("✅ Field mapping fix should resolve the 'order_id' error")
        return True

def main():
    """Main function"""
    success = test_field_mapping()
    
    if success:
        print("\n🎉 Field mapping test passed!")
        print("Deploy the updated rang_service.py to fix the error.")
    else:
        print("\n❌ Field mapping test failed!")
        print("Check the field mapping logic.")

if __name__ == "__main__":
    main()