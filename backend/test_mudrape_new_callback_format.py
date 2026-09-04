#!/usr/bin/env python3
"""
Test script for new Mudrape callback format
Tests the updated parameter handling
"""

import requests
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:5000"  # Change to your backend URL
CALLBACK_ENDPOINT = f"{BACKEND_URL}/mudrape/payin/callback"

def test_new_callback_format():
    """Test with new Mudrape callback format"""
    print("=" * 80)
    print("Testing New Mudrape Callback Format")
    print("=" * 80)
    
    # New format from Mudrape team
    callback_data = {
        "utr": "TEST123456789",
        "amount": 100.00,
        "ref_id": "ORD20260305001",
        "source": "Mudrape",
        "status": "SUCCESS",
        "txn_id": "MUD987654321",
        "payeeVpa": "merchant@paytm",
        "timestamp": datetime.now().isoformat()
    }
    
    print("\nSending callback data:")
    print(json.dumps(callback_data, indent=2))
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Callback processed successfully")
            return True
        else:
            print("\n✗ Callback processing failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility with old format"""
    print("\n" + "=" * 80)
    print("Testing Backward Compatibility (Old Format)")
    print("=" * 80)
    
    # Old format (should still work)
    callback_data = {
        "refId": "ORD20260305002",
        "txnId": "MUD111222333",
        "status": "SUCCESS",
        "UTR": "OLD123456789",
        "amount": 200.00
    }
    
    print("\nSending old format callback data:")
    print(json.dumps(callback_data, indent=2))
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Old format still works (backward compatible)")
            return True
        else:
            print("\n✗ Old format failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

def test_failed_transaction():
    """Test FAILED status callback"""
    print("\n" + "=" * 80)
    print("Testing FAILED Transaction Callback")
    print("=" * 80)
    
    callback_data = {
        "utr": "",
        "amount": 150.00,
        "ref_id": "ORD20260305003",
        "source": "Mudrape",
        "status": "FAILED",
        "txn_id": "MUD444555666",
        "payeeVpa": "",
        "timestamp": datetime.now().isoformat()
    }
    
    print("\nSending FAILED callback data:")
    print(json.dumps(callback_data, indent=2))
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ FAILED callback processed successfully")
            return True
        else:
            print("\n✗ FAILED callback processing failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MUDRAPE NEW CALLBACK FORMAT TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("New Format", test_new_callback_format()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    results.append(("Failed Transaction", test_failed_transaction()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. Check logs for details.")
    
    print("=" * 80)
