"""
Diagnose Paytouchpayin Error
Check what's actually failing in the service
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paytouchpayin_service import PaytouchpayinService
import json

def test_service():
    """Test the paytouchpayin service directly"""
    
    print("="*80)
    print("PAYTOUCHPAYIN SERVICE DIAGNOSTIC")
    print("="*80)
    print()
    
    service = PaytouchpayinService()
    
    # Test data
    merchant_id = "7679022140"
    order_data = {
        'amount': 100,
        'orderid': 'TEST123',
        'payee_fname': 'Test',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com'
    }
    
    print(f"Testing with:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Order Data: {json.dumps(order_data, indent=2)}")
    print()
    
    try:
        result = service.create_payin_order(merchant_id, order_data)
        
        print("="*80)
        print("RESULT:")
        print("="*80)
        print(json.dumps(result, indent=2))
        print()
        
        if result.get('success'):
            print("✅ SUCCESS!")
        else:
            print("❌ FAILED!")
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print("="*80)
        print("EXCEPTION OCCURRED:")
        print("="*80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_service()
