#!/usr/bin/env python3
"""
Test PayTouch API with Correct Endpoint
Tests the PayTouch status API with the correct endpoint URL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from config import Config

def test_paytouch_api():
    """
    Test PayTouch API with the correct endpoint
    """
    
    print("=" * 80)
    print("PayTouch API Test with Correct Endpoint")
    print("=" * 80)
    
    # Test the specific transactions from your issue
    test_transactions = [
        {
            'transaction_id': 'ADMIN20260310182521A6904E',
            'external_ref': 'ADMIN20260310182521A6904E'
        },
        {
            'transaction_id': 'ADMIN20260310182131FF1C8D',
            'external_ref': 'ADMIN20260310182131FF1C8D'
        }
    ]
    
    base_url = Config.PAYTOUCH_BASE_URL
    token = Config.PAYTOUCH_TOKEN
    
    print(f"Base URL: {base_url}")
    print(f"Token: {token}")
    
    # Test both endpoint variations
    endpoints = [
        "/api/payout/v2/get-reportstatus",  # From documentation (no hyphen)
        "/api/payout/v2/get-report-status"  # Previous version (with hyphen)
    ]
    
    for endpoint in endpoints:
        print(f"\n{'='*60}")
        print(f"Testing Endpoint: {endpoint}")
        print(f"{'='*60}")
        
        url = f"{base_url}{endpoint}"
        print(f"Full URL: {url}")
        
        for i, txn in enumerate(test_transactions, 1):
            print(f"\n--- Test {i}: {txn['transaction_id']} ---")
            
            payload = {
                'token': token,
                'transaction_id': txn['transaction_id'],
                'external_ref': txn['external_ref']
            }
            
            print(f"Request Payload: {json.dumps(payload, indent=2)}")
            
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                print(f"Response Status: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                
                try:
                    response_json = response.json()
                    print(f"Response JSON: {json.dumps(response_json, indent=2)}")
                    
                    # Check if this is a successful response
                    if response.status_code == 200:
                        status = response_json.get('status', 'UNKNOWN')
                        message = response_json.get('message', '')
                        
                        print(f"✅ API Call Successful")
                        print(f"   Status: {status}")
                        print(f"   Message: {message}")
                        
                        if status.lower() != 'failed':
                            print(f"🎉 TRANSACTION FOUND! Status: {status}")
                        else:
                            print(f"⚠️  Transaction status is FAILED: {message}")
                    else:
                        print(f"❌ API Call Failed: {response.status_code}")
                        
                except json.JSONDecodeError:
                    print(f"Response Text: {response.text}")
                    print(f"❌ Invalid JSON response")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Request Error: {e}")
            
            print("-" * 40)
    
    # Test with a simple ping/health check if available
    print(f"\n{'='*60}")
    print("Testing API Connectivity")
    print(f"{'='*60}")
    
    try:
        # Try a simple GET request to see if the API is accessible
        response = requests.get(f"{base_url}/api", timeout=10)
        print(f"API Base Response: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ API server is accessible (404 expected for base path)")
        elif response.status_code == 200:
            print("✅ API server is accessible")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach API server: {e}")
    
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    
    print("1. ✅ Updated endpoint to use 'get-reportstatus' (without hyphen)")
    print("2. 🔍 Check the test results above to see which endpoint works")
    print("3. 📞 If both endpoints fail, contact PayTouch support")
    print("4. 🔧 Verify your token and credentials with PayTouch")
    print("5. 📋 Check if the transactions exist in PayTouch dashboard")
    
    print(f"\nCorrect API Configuration:")
    print(f"  URL: {base_url}/api/payout/v2/get-reportstatus")
    print(f"  Method: POST")
    print(f"  Content-Type: application/json")
    print(f"  Token: {token}")

if __name__ == "__main__":
    test_paytouch_api()