#!/usr/bin/env python3
"""
Simple test to check if Rang callback endpoint is accessible
"""

import requests
import json

def test_callback_endpoint():
    """Test if the callback endpoint is accessible"""
    
    print("=" * 60)
    print("TESTING RANG CALLBACK ENDPOINT ACCESS")
    print("=" * 60)
    
    # Test with minimal data first
    callback_url = "https://api.moneyone.co.in/rang-payin-callback"
    
    # Minimal test data
    test_data = {
        'status_id': '1',
        'client_id': 'TEST123',
        'amount': '100',
        'message': 'test'
    }
    
    print(f"Testing URL: {callback_url}")
    print(f"Test data: {test_data}")
    print()
    
    try:
        response = requests.post(
            callback_url,
            data=test_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        # Try to parse response as JSON
        try:
            response_json = response.json()
            print(f"Response JSON: {json.dumps(response_json, indent=2)}")
        except:
            print("Response is not valid JSON")
        
        if response.status_code == 200:
            print("\n✅ Endpoint is accessible!")
        elif response.status_code == 404:
            print("\n❌ Endpoint not found - check if route is registered")
        elif response.status_code == 500:
            print("\n❌ Internal server error - check server logs")
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_test_endpoint():
    """Test the test callback endpoint"""
    
    print("\n" + "=" * 60)
    print("TESTING RANG TEST CALLBACK ENDPOINT")
    print("=" * 60)
    
    callback_url = "https://api.moneyone.co.in/test-rang-callback"
    
    test_data = {
        'test': 'data',
        'status': 'success'
    }
    
    print(f"Testing URL: {callback_url}")
    print(f"Test data: {test_data}")
    print()
    
    try:
        response = requests.post(
            callback_url,
            data=test_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Test endpoint works!")
        else:
            print(f"\n❌ Test endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_test_endpoint()
    test_callback_endpoint()