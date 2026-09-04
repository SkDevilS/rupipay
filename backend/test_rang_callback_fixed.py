#!/usr/bin/env python3
"""
Test Rang callback processing after fixing database column issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_rang_callback():
    """Test Rang callback endpoint"""
    print("=" * 60)
    print("TESTING RANG CALLBACK (FIXED)")
    print("=" * 60)
    
    # Test callback data (simulating Rang callback)
    callback_data = {
        'status_id': '1',  # Success
        'amount': '100',
        'utr': 'TEST_UTR_123456',
        'client_id': 'RNG9000000001TEST_RANG_0011710000000',  # Example txn_id
        'message': 'Payment successful'
    }
    
    print(f"Test callback data: {json.dumps(callback_data, indent=2)}")
    
    try:
        # Test callback endpoint
        url = "http://localhost:5000/rang-payin-callback"
        
        print(f"\nSending callback to: {url}")
        
        response = requests.post(
            url,
            data=callback_data,  # Send as form data (as per Rang documentation)
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Callback processing successful!")
        else:
            print("❌ Callback processing failed!")
            
    except Exception as e:
        print(f"❌ Callback test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_rang_test_callback():
    """Test Rang test callback endpoint"""
    print("\n" + "=" * 60)
    print("TESTING RANG TEST CALLBACK ENDPOINT")
    print("=" * 60)
    
    callback_data = {
        'status_id': '1',
        'amount': '100',
        'utr': 'TEST_UTR_123456',
        'client_id': 'TEST_CLIENT_ID',
        'message': 'Test callback'
    }
    
    try:
        url = "http://localhost:5000/test-rang-callback"
        
        print(f"Sending test callback to: {url}")
        
        response = requests.post(
            url,
            data=callback_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test callback endpoint working!")
        else:
            print("❌ Test callback endpoint failed!")
            
    except Exception as e:
        print(f"❌ Test callback failed with error: {str(e)}")

if __name__ == "__main__":
    test_rang_test_callback()
    test_rang_callback()