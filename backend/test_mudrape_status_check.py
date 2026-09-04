#!/usr/bin/env python3
"""
Test Mudrape status check with new endpoint
"""

import sys
from mudrape_service import mudrape_service

def test_status_check(identifier):
    """Test status check for a transaction"""
    print("=" * 60)
    print("Testing Mudrape Status Check")
    print("=" * 60)
    
    print(f"\nIdentifier: {identifier}")
    print("Endpoint: /api/api-mudrape/check-status")
    
    # Generate token first
    print("\nGenerating token...")
    token_result = mudrape_service.generate_token()
    
    if not token_result.get('success'):
        print(f"❌ Token generation failed: {token_result.get('message')}")
        return False
    
    print(f"✅ Token generated: {token_result['token'][:30]}...")
    
    # Check status
    print(f"\nChecking status for: {identifier}")
    result = mudrape_service.check_payment_status(identifier)
    
    if result.get('success'):
        print("\n✅ Status check successful!")
        print(f"\nStatus: {result.get('status')}")
        print(f"TxnID: {result.get('txnId')}")
        print(f"RefID: {result.get('refId')}")
        print(f"Amount: {result.get('amount')}")
        print(f"UTR: {result.get('utr')}")
        print(f"Payment Mode: {result.get('payment_mode')}")
        print(f"Created: {result.get('created_at')}")
        print(f"Completed: {result.get('completed_at')}")
        return True
    else:
        print(f"\n❌ Status check failed!")
        print(f"Error: {result.get('message')}")
        if result.get('note'):
            print(f"Note: {result.get('note')}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_mudrape_status_check.py <refId_or_txnId>")
        print("\nExamples:")
        print("  python test_mudrape_status_check.py 20241234567890123456")
        print("  python test_mudrape_status_check.py MPAY70861522689")
        sys.exit(1)
    
    identifier = sys.argv[1]
    success = test_status_check(identifier)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Status Check Test Passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Status Check Test Failed!")
        print("=" * 60)
        sys.exit(1)
