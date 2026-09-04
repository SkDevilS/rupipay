"""
Test PayTouch UTR Mapping
Check what fields PayTouch returns in their status response
"""

from paytouch_service import paytouch_service
import json

def test_paytouch_status_response():
    """Test PayTouch status check to see what fields are returned"""
    
    # Test with the transaction that had issues
    transaction_id = "DP202603062044589B36FB"
    external_ref = "DP202603062044589B36FB"
    
    print("=" * 80)
    print("Testing PayTouch Status Response")
    print("=" * 80)
    print(f"Transaction ID: {transaction_id}")
    print(f"External Ref: {external_ref}")
    print()
    
    # Call PayTouch status check
    result = paytouch_service.check_payout_status(
        transaction_id=transaction_id,
        external_ref=external_ref
    )
    
    print("\nPayTouch Service Response:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print("=" * 80)
    
    # Check what fields are available
    print("\nField Analysis:")
    print("-" * 80)
    
    if result.get('success'):
        print(f"✓ Status: {result.get('status')}")
        print(f"✓ Transaction ID: {result.get('transaction_id')}")
        print(f"✓ External Ref: {result.get('external_ref')}")
        print(f"✓ Amount: {result.get('amount')}")
        print(f"✓ Message: {result.get('message')}")
        
        # Check UTR field
        utr = result.get('utr')
        if utr:
            print(f"✅ UTR Found: {utr}")
        else:
            print(f"❌ UTR Not Found in response")
            print(f"   Available fields: {list(result.keys())}")
    else:
        print(f"❌ Status check failed: {result.get('message')}")
    
    print("\n" + "=" * 80)
    print("Recommendations:")
    print("=" * 80)
    
    if result.get('success'):
        if not result.get('utr'):
            print("⚠️  UTR field is missing from PayTouch response")
            print("   Possible reasons:")
            print("   1. PayTouch uses a different field name (check raw response)")
            print("   2. UTR is only available for SUCCESS status")
            print("   3. PayTouch doesn't provide UTR in status check API")
            print()
            print("   Solutions:")
            print("   1. Check PayTouch API documentation for correct field name")
            print("   2. Contact PayTouch support to confirm UTR field")
            print("   3. Use callback data instead (callbacks usually have UTR)")
        else:
            print("✅ UTR mapping is working correctly")
    
    return result

if __name__ == '__main__':
    test_paytouch_status_response()
