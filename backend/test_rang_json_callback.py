#!/usr/bin/env python3
"""
Test Rang callback system with JSON format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def test_rang_json_callback():
    """Test Rang callback system with JSON format"""
    print("=" * 60)
    print("TESTING RANG JSON CALLBACK SYSTEM")
    print("=" * 60)
    
    # Test callback data (simulating Rang JSON callback)
    test_cases = [
        {
            'name': 'SUCCESS JSON Callback',
            'data': {
                'status_id': '1',  # Success
                'amount': '100',
                'utr': 'TEST_UTR_JSON_SUCCESS_123',
                'client_id': 'TEST_TXN_JSON_SUCCESS_001',
                'message': 'Payment successful'
            },
            'expected_status': 'SUCCESS'
        },
        {
            'name': 'FAILED JSON Callback',
            'data': {
                'status_id': '3',  # Failed
                'amount': '100',
                'utr': '',
                'client_id': 'TEST_TXN_JSON_FAILED_001',
                'message': 'Payment failed'
            },
            'expected_status': 'FAILED'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 40)
        
        callback_data = test_case['data']
        expected_status = test_case['expected_status']
        
        print(f"JSON Callback Data: {json.dumps(callback_data, indent=2)}")
        print(f"Expected Status: {expected_status}")
        
        try:
            # Test callback endpoint with JSON
            url = "http://localhost:5000/rang-payin-callback"
            
            print(f"Sending JSON callback to: {url}")
            
            response = requests.post(
                url,
                json=callback_data,  # Send as JSON data
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('success'):
                    print(f"✅ {test_case['name']} processed successfully!")
                    
                    # Check if status was updated correctly
                    returned_status = response_json.get('status')
                    if returned_status == expected_status:
                        print(f"✅ Status correctly mapped: {returned_status}")
                    else:
                        print(f"❌ Status mapping issue: expected {expected_status}, got {returned_status}")
                else:
                    print(f"❌ Callback processing failed: {response_json.get('message')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
        
        print()

def test_both_formats():
    """Test both form-encoded and JSON formats"""
    print("\n" + "=" * 60)
    print("TESTING BOTH CALLBACK FORMATS")
    print("=" * 60)
    
    callback_data = {
        'status_id': '1',
        'amount': '100',
        'utr': 'TEST_UTR_BOTH_123',
        'client_id': 'TEST_TXN_BOTH_001',
        'message': 'Payment successful'
    }
    
    formats = [
        {
            'name': 'Form-encoded format',
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'send_method': 'data'
        },
        {
            'name': 'JSON format',
            'headers': {'Content-Type': 'application/json'},
            'send_method': 'json'
        }
    ]
    
    for fmt in formats:
        print(f"\nTesting: {fmt['name']}")
        print("-" * 30)
        
        try:
            url = "http://localhost:5000/rang-payin-callback"
            
            if fmt['send_method'] == 'data':
                response = requests.post(url, data=callback_data, headers=fmt['headers'], timeout=30)
            else:
                response = requests.post(url, json=callback_data, headers=fmt['headers'], timeout=30)
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ {fmt['name']} works correctly!")
            else:
                print(f"❌ {fmt['name']} failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {fmt['name']} error: {str(e)}")

if __name__ == "__main__":
    test_rang_json_callback()
    test_both_formats()