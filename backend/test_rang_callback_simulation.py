#!/usr/bin/env python3
"""
Test script to simulate Rang callback
This simulates the exact format that Rang will send to our callback URL
"""

import requests
import sys
import os

def test_rang_callback():
    """Test Rang callback with sample data"""
    
    # Callback URL (use localhost for testing, production will be https://api.moneyone.co.in/rang-payin-callback)
    callback_url = "http://localhost:5000/rang-payin-callback"
    
    # Sample callback data (matching the format you provided)
    callback_data = {
        'status_id': '1',  # 1 = Success, 2 = Pending, 3 = Failed
        'amount': '500',
        'utr': '60xxx763',
        'report_id': '1215',
        'client_id': '202xxxx760',  # This should be our txn_id (20-digit RefID)
        'message': 'Payment success'
    }
    
    print("=" * 80)
    print("TESTING RANG CALLBACK SIMULATION")
    print("=" * 80)
    print(f"Callback URL: {callback_url}")
    print(f"Callback Data: {callback_data}")
    print()
    
    try:
        # Send form-data POST request (exactly like Rang will send)
        response = requests.post(
            callback_url,
            data=callback_data,  # Use data= for form-data, not json=
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Callback test SUCCESSFUL!")
        else:
            print(f"\n❌ Callback test FAILED with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure Flask server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_rang_callback()