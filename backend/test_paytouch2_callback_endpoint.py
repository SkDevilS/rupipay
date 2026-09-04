#!/usr/bin/env python3
"""
Test script for PayTouch2 payout callback endpoint
Usage: python test_paytouch2_callback_endpoint.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://api.moneyone.co.in"
CALLBACK_ENDPOINT = f"{BASE_URL}/api/callback/paytouch2/payout"

def test_callback(test_name, payload):
    """Send test callback and print response"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code, response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR: {str(e)}")
        return None, None

def main():
    """Run all test cases"""
    
    print("🧪 PayTouch2 Payout Callback Endpoint Test Suite")
    print(f"Endpoint: {CALLBACK_ENDPOINT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: SUCCESS callback
    test_callback(
        "SUCCESS Callback",
        {
            "transaction_id": "PT2_TEST_123456",
            "external_ref": "REF_TEST_001",
            "status": "SUCCESS",
            "utr_no": "UTR123456789012",
            "amount": 1000.00,
            "message": "Transaction successful",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Test 2: PENDING callback
    test_callback(
        "PENDING Callback",
        {
            "transaction_id": "PT2_TEST_123456",
            "external_ref": "REF_TEST_001",
            "status": "PENDING",
            "amount": 1000.00,
            "message": "Transaction pending",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Test 3: FAILED callback
    test_callback(
        "FAILED Callback",
        {
            "transaction_id": "PT2_TEST_123456",
            "external_ref": "REF_TEST_001",
            "status": "FAILED",
            "amount": 1000.00,
            "message": "Transaction failed - Invalid account",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Test 4: Alternative field names
    test_callback(
        "Alternative Field Names",
        {
            "transactionId": "PT2_TEST_789012",
            "request_id": "REF_TEST_002",
            "status": "SUCCESS",
            "bank_ref_no": "BRN987654321098",
            "amount": 2500.50,
            "message": "Payment processed successfully",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Test 5: Missing transaction ID (should fail)
    test_callback(
        "Missing Transaction ID (Expected: 400)",
        {
            "status": "SUCCESS",
            "amount": 1000.00,
            "message": "Transaction successful"
        }
    )
    
    # Test 6: Non-existent transaction (should fail)
    test_callback(
        "Non-Existent Transaction (Expected: 404)",
        {
            "transaction_id": "NONEXISTENT_TXN_999999",
            "external_ref": "NONEXISTENT_REF_999",
            "status": "SUCCESS",
            "utr_no": "UTR999999999999",
            "amount": 5000.00,
            "message": "Transaction successful"
        }
    )
    
    # Test 7: PROCESSING status
    test_callback(
        "PROCESSING Status",
        {
            "transaction_id": "PT2_TEST_123456",
            "external_ref": "REF_TEST_001",
            "status": "PROCESSING",
            "amount": 1000.00,
            "message": "Transaction is being processed",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Test 8: RRN field for UTR
    test_callback(
        "RRN Field for UTR",
        {
            "transaction_id": "PT2_TEST_123456",
            "external_ref": "REF_TEST_001",
            "status": "SUCCESS",
            "rrn": "RRN123456789012",
            "amount": 1500.00,
            "message": "Transaction successful with RRN",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    print(f"\n{'='*60}")
    print("✅ All tests completed!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
