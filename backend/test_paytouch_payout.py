"""
Test script for PayTouch payout integration
"""

from paytouch_service import paytouch_service
import json

def test_initiate_payout():
    """Test PayTouch payout initiation"""
    print("=" * 80)
    print("Testing PayTouch Payout Initiation")
    print("=" * 80)
    
    # Test payout data
    payout_data = {
        'reference_id': 'TEST123456',
        'amount': 100.00,
        'bene_name': 'Test Beneficiary',
        'bene_account': '1234567890',
        'bene_ifsc': 'SBIN0001234',
        'payment_mode': 'IMPS',
        'bank_name': 'State Bank of India',
        'bank_branch': 'Test Branch',
        'narration': 'Test payout transaction',
        'bene_mobile': '9876543210',
        'bene_email': 'test@example.com'
    }
    
    print(f"\nTest Payout Data:")
    print(json.dumps(payout_data, indent=2))
    
    # Note: This will fail without a valid merchant_id in database
    # For actual testing, use a real merchant_id
    merchant_id = '9000000001'  # Replace with actual merchant ID
    
    print(f"\nMerchant ID: {merchant_id}")
    print("\nInitiating payout...")
    
    result = paytouch_service.initiate_payout(merchant_id, payout_data)
    
    print("\n" + "=" * 80)
    print("Result:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    
    return result

def test_check_status():
    """Test PayTouch status check"""
    print("\n" + "=" * 80)
    print("Testing PayTouch Status Check")
    print("=" * 80)
    
    # Replace with actual transaction ID from PayTouch
    transaction_id = "TEST_TXN_ID"
    external_ref = "TEST123456"
    
    print(f"\nTransaction ID: {transaction_id}")
    print(f"External Ref: {external_ref}")
    print("\nChecking status...")
    
    result = paytouch_service.check_payout_status(
        transaction_id=transaction_id,
        external_ref=external_ref
    )
    
    print("\n" + "=" * 80)
    print("Result:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == '__main__':
    print("\nPayTouch Payout Service Test")
    print("=" * 80)
    
    # Test 1: Initiate payout
    print("\n1. Testing Payout Initiation")
    print("-" * 80)
    initiate_result = test_initiate_payout()
    
    # Test 2: Check status (only if initiation was successful)
    if initiate_result.get('success'):
        print("\n2. Testing Status Check")
        print("-" * 80)
        test_check_status()
    else:
        print("\nSkipping status check test (initiation failed)")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
