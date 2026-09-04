"""
Test PayTouchPayin Response Format
Verify that payment_link is copied to all payment-related fields
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paytouchpayin_service import PaytouchpayinService
import json

def test_response_format():
    """Test that payment_link is copied to all fields"""
    
    print("=" * 80)
    print("Testing PayTouchPayin Response Format")
    print("=" * 80)
    
    service = PaytouchpayinService()
    
    # Test order data
    order_data = {
        'amount': 1.0,
        'orderid': 'TEST' + str(int(__import__('time').time())),
        'payee_fname': 'Test Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com',
        'callbackurl': 'https://example.com/callback'
    }
    
    print("\n📤 Creating test order...")
    print(f"Order Data: {json.dumps(order_data, indent=2)}")
    
    # Use a test merchant ID (replace with actual merchant ID)
    merchant_id = '7679022140'
    
    result = service.create_payin_order(merchant_id, order_data)
    
    print("\n" + "=" * 80)
    print("📥 RESPONSE FORMAT CHECK")
    print("=" * 80)
    
    if result.get('success'):
        print("\n✅ Order created successfully!")
        print("\n📋 Response Fields:")
        
        # Check all payment-related fields
        payment_fields = [
            'qr_string',
            'qr_code_url',
            'upi_link',
            'payment_link',
            'intent_url',
            'tiny_url',
            'redirect_url'
        ]
        
        payment_link_value = result.get('payment_link', '')
        
        print(f"\n🔗 payment_link value:")
        print(f"   {payment_link_value}")
        
        print(f"\n📊 Checking if all fields have the same value:")
        all_same = True
        for field in payment_fields:
            field_value = result.get(field, '')
            is_same = field_value == payment_link_value
            status = "✅" if is_same else "❌"
            print(f"   {status} {field}: {field_value[:50]}{'...' if len(field_value) > 50 else ''}")
            if not is_same:
                all_same = False
        
        print("\n" + "=" * 80)
        if all_same:
            print("✅ SUCCESS: All payment fields have the same value!")
        else:
            print("❌ FAILED: Some fields have different values!")
        print("=" * 80)
        
        print("\n📦 Full Response:")
        print(json.dumps(result, indent=2))
        
    else:
        print(f"\n❌ Order creation failed:")
        print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_response_format()
