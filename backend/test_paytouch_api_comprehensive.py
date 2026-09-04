#!/usr/bin/env python3
"""
Comprehensive PayTouch API Test
Tests the PayTouch API with different scenarios and endpoints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from config import Config
from datetime import datetime

def test_paytouch_api_comprehensive():
    """
    Comprehensive test of PayTouch API
    """
    
    print("=" * 80)
    print(f"PayTouch API Comprehensive Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    base_url = Config.PAYTOUCH_BASE_URL
    token = Config.PAYTOUCH_TOKEN
    
    print(f"Base URL: {base_url}")
    print(f"Token: {token}")
    
    # Test 1: Check if API server is accessible
    print(f"\n{'='*60}")
    print("Test 1: API Server Accessibility")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{base_url}", timeout=10)
        print(f"Base URL Response: {response.status_code}")
        if response.status_code in [200, 404]:
            print("✅ API server is accessible")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach API server: {e}")
        return
    
    # Test 2: Test different endpoint variations
    print(f"\n{'='*60}")
    print("Test 2: Endpoint Variations")
    print(f"{'='*60}")
    
    endpoints = [
        "/api/payout/v2/get-report-status",  # From documentation
        "/api/payout/v2/get-reportstatus",   # Alternative without hyphen
        "/api/payout/v2/status",             # Simplified
        "/api/payout/status",                # Without version
    ]
    
    test_payload = {
        'token': token,
        'transaction_id': 'TEST_TXN_001',
        'external_ref': 'TEST_REF_001'
    }
    
    for endpoint in endpoints:
        print(f"\nTesting endpoint: {endpoint}")
        url = f"{base_url}{endpoint}"
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=test_payload,
                timeout=30
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 404:
                print("  ❌ Endpoint not found")
            elif response.status_code == 200:
                try:
                    response_json = response.json()
                    print(f"  ✅ Endpoint exists - Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"  ✅ Endpoint exists - Response: {response.text[:200]}")
            elif response.status_code == 400:
                print("  ⚠️  Bad request (endpoint exists but invalid data)")
            elif response.status_code == 401:
                print("  ⚠️  Unauthorized (endpoint exists but token issue)")
            else:
                print(f"  ⚠️  Unexpected response: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
    
    # Test 3: Test with actual transaction IDs
    print(f"\n{'='*60}")
    print("Test 3: Actual Transaction IDs")
    print(f"{'='*60}")
    
    # Use the correct endpoint from documentation
    correct_endpoint = "/api/payout/v2/get-report-status"
    url = f"{base_url}{correct_endpoint}"
    
    actual_transactions = [
        {
            'transaction_id': 'ADMIN20260310182521A6904E',
            'external_ref': 'ADMIN20260310182521A6904E'
        },
        {
            'transaction_id': 'ADMIN20260310182131FF1C8D',
            'external_ref': 'ADMIN20260310182131FF1C8D'
        }
    ]
    
    for i, txn in enumerate(actual_transactions, 1):
        print(f"\nTest 3.{i}: {txn['transaction_id']}")
        
        payload = {
            'token': token,
            'transaction_id': txn['transaction_id'],
            'external_ref': txn['external_ref']
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=30
            )
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    print(f"Response JSON: {json.dumps(response_json, indent=2)}")
                    
                    status = response_json.get('status', 'UNKNOWN')
                    message = response_json.get('message', '')
                    
                    if status.lower() == 'failed' and 'not found' in message.lower():
                        print(f"❌ Transaction not found in PayTouch system")
                    elif status.lower() == 'success':
                        print(f"✅ Transaction is SUCCESS in PayTouch!")
                    elif status.lower() == 'pending':
                        print(f"⏳ Transaction is PENDING in PayTouch")
                    else:
                        print(f"📊 Transaction status: {status}")
                        
                except json.JSONDecodeError:
                    print(f"Response Text: {response.text[:500]}")
                    if "404" in response.text:
                        print(f"❌ Endpoint returns 404 page")
                    
            elif response.status_code == 404:
                print(f"❌ Endpoint not found")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
    
    # Test 4: Test with different payload formats
    print(f"\n{'='*60}")
    print("Test 4: Different Payload Formats")
    print(f"{'='*60}")
    
    payload_variations = [
        {
            'name': 'Standard Format',
            'payload': {
                'token': token,
                'transaction_id': 'ADMIN20260310182521A6904E',
                'external_ref': 'ADMIN20260310182521A6904E'
            }
        },
        {
            'name': 'Only Transaction ID',
            'payload': {
                'token': token,
                'transaction_id': 'ADMIN20260310182521A6904E'
            }
        },
        {
            'name': 'Only External Ref',
            'payload': {
                'token': token,
                'external_ref': 'ADMIN20260310182521A6904E'
            }
        },
        {
            'name': 'Empty External Ref',
            'payload': {
                'token': token,
                'transaction_id': 'ADMIN20260310182521A6904E',
                'external_ref': ''
            }
        }
    ]
    
    for variation in payload_variations:
        print(f"\nTesting: {variation['name']}")
        print(f"Payload: {json.dumps(variation['payload'], indent=2)}")
        
        try:
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=variation['payload'],
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    print(f"Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"Response: {response.text[:200]}")
            else:
                print(f"Error Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
    
    # Test 5: Check if transactions were ever created in PayTouch
    print(f"\n{'='*60}")
    print("Test 5: Analysis & Recommendations")
    print(f"{'='*60}")
    
    print("Based on the test results:")
    print("1. ✅ API endpoint is accessible")
    print("2. 🔍 Check if transactions were actually sent to PayTouch")
    print("3. 📋 Verify PayTouch dashboard for these transaction IDs")
    print("4. 📞 Contact PayTouch support if transactions should exist")
    print("5. 🔧 Check payout initiation logs to confirm transactions were sent")
    
    print(f"\nNext Steps:")
    print("1. Check your payout initiation logs for these transactions")
    print("2. Verify in PayTouch dashboard if these transactions exist")
    print("3. If transactions don't exist in PayTouch, they were never sent")
    print("4. If transactions exist but API returns 'not found', contact PayTouch support")
    
    print(f"\nPayTouch Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Endpoint: {correct_endpoint}")
    print(f"  Token: {token}")

if __name__ == "__main__":
    test_paytouch_api_comprehensive()