"""
Test script for Vega Payin Integration
Tests the Vega payment link generation
"""

from vega_service import VegaService
import json

def test_vega_payin():
    """Test Vega payin order creation"""
    
    print("=" * 80)
    print("Testing Vega Payin Integration")
    print("=" * 80)
    
    vega_service = VegaService()
    
    # Test data
    merchant_id = "9000000001"  # Replace with actual merchant ID
    
    order_data = {
        'amount': 100,
        'orderid': 'TEST_VEGA_001',
        'payee_fname': 'Test',
        'payee_lname': 'User',
        'payee_mobile': '9999999999',
        'payee_email': 'test@example.com',
        'address': 'Test Address',
        'city': 'Test City',
        'state': 'Test State',
        'zipCode': '123456',
        'productinfo': 'Test Payment'
    }
    
    print(f"\nTest Order Data:")
    print(json.dumps(order_data, indent=2))
    
    print(f"\nVega Configuration:")
    print(f"Base URL: {vega_service.base_url}")
    print(f"API Key: {vega_service.api_key[:20]}...")
    print(f"User ID: {vega_service.user_id}")
    print(f"Action Picker: {vega_service.action_picker}")
    
    print(f"\n{'=' * 80}")
    print("Creating Vega Payment Link...")
    print("=" * 80)
    
    result = vega_service.create_payin_order(merchant_id, order_data)
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2, default=str))
    
    if result.get('success'):
        print(f"\n{'✓' * 40}")
        print("SUCCESS - Vega Payment Link Generated!")
        print("✓" * 40)
        print(f"\nPayment URL: {result.get('payment_url')}")
        print(f"Track ID: {result.get('order_id')}")
        print(f"Amount: ₹{result.get('amount')}")
        print(f"Expires In: {result.get('expires_in')} seconds")
        print(f"\nTransaction Details:")
        print(f"  - TXN ID: {result.get('txn_id')}")
        print(f"  - Merchant Order ID: {result.get('merchant_order_id')}")
        print(f"  - Charge: ₹{result.get('charge_amount')}")
        print(f"  - Net Amount: ₹{result.get('net_amount')}")
    else:
        print(f"\n{'✗' * 40}")
        print("FAILED - Vega Payment Link Generation Failed")
        print("✗" * 40)
        print(f"\nError: {result.get('message')}")
    
    print(f"\n{'=' * 80}")
    print("Test Complete")
    print("=" * 80)

if __name__ == '__main__':
    test_vega_payin()
