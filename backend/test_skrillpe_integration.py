"""
Test SkrillPe Integration
Tests QR generation and status check
"""

from skrillpe_service import skrillpe_service
import json

def test_qr_generation():
    """Test SkrillPe QR generation"""
    print("=" * 80)
    print("Testing SkrillPe QR Generation")
    print("=" * 80)
    
    # Test order data
    order_data = {
        'amount': 100,
        'orderid': 'TEST_ORDER_001',
        'payee_fname': 'Test',
        'payee_lname': 'Customer',
        'payee_mobile': '9876543210',
        'payee_email': 'test@example.com'
    }
    
    # Assuming merchant_id 9000000001 exists
    merchant_id = '9000000001'
    
    print(f"\n📝 Test Order Data:")
    print(json.dumps(order_data, indent=2))
    
    result = skrillpe_service.create_payin_order(merchant_id, order_data)
    
    print(f"\n📊 Result:")
    print(json.dumps(result, indent=2))
    
    if result.get('success'):
        print("\n✓ QR Generation Successful!")
        print(f"Transaction ID: {result.get('txn_id')}")
        print(f"QR Code URL: {result.get('qr_code_url')}")
        print(f"VPA: {result.get('vpa')}")
        return result.get('txn_id')
    else:
        print(f"\n✗ QR Generation Failed: {result.get('message')}")
        return None

def test_status_check(txn_id):
    """Test SkrillPe status check"""
    print("\n" + "=" * 80)
    print("Testing SkrillPe Status Check")
    print("=" * 80)
    
    print(f"\n🔍 Checking status for: {txn_id}")
    
    result = skrillpe_service.check_payment_status(txn_id)
    
    print(f"\n📊 Status Result:")
    print(json.dumps(result, indent=2))
    
    if result.get('success'):
        print(f"\n✓ Status Check Successful!")
        print(f"Status: {result.get('status')}")
        print(f"Amount: {result.get('amount')}")
        print(f"RRN: {result.get('rrn')}")
    else:
        print(f"\n✗ Status Check Failed: {result.get('message')}")

if __name__ == '__main__':
    print("\n🚀 Starting SkrillPe Integration Tests\n")
    
    # Test 1: QR Generation
    txn_id = test_qr_generation()
    
    # Test 2: Status Check (if QR generation was successful)
    if txn_id:
        test_status_check(txn_id)
    
    print("\n" + "=" * 80)
    print("✓ Tests Complete!")
    print("=" * 80)
    print("\nNote: To test the full flow:")
    print("1. Use the QR code URL to make a payment")
    print("2. Run status check again after payment")
    print("3. Check the callback endpoint receives the webhook")
