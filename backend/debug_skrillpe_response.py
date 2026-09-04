#!/usr/bin/env python3
"""
Debug SkrillPe API response to understand the actual response structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from config import Config

def test_skrillpe_api_directly():
    """Test SkrillPe API directly to see actual response"""
    print("🔍 Testing SkrillPe API Directly")
    print("=" * 50)
    
    # API configuration
    base_url = Config.SKRILLPE_BASE_URL
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    # Headers
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    
    # Test payload
    payload = {
        'transactionId': 'TEST_TXN_123456789',
        'amount': '100.00',
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    print(f"🌐 Base URL: {base_url}")
    print(f"🔑 Company Alias: {company_alias}")
    print(f"📦 Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    # Make API call
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    
    try:
        print(f"🚀 Calling: {url}")
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print(f"📄 Raw Response: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n✅ Parsed JSON Response:")
                print(json.dumps(data, indent=2))
                
                # Analyze response structure
                print(f"\n🔍 Response Analysis:")
                for key, value in data.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")
                
                # Check different success conditions
                print(f"\n🎯 Success Condition Analysis:")
                print(f"  data.get('success'): {data.get('success')}")
                print(f"  data.get('code'): {data.get('code')}")
                print(f"  data.get('intentUrl'): {data.get('intentUrl')}")
                print(f"  data.get('tinyUrl'): {data.get('tinyUrl')}")
                print(f"  data.get('reason'): {data.get('reason')}")
                print(f"  'Successful' in message: {'Successful' in str(data.get('message', ''))}")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Request Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_skrillpe_api_directly()