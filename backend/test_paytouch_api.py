"""
Test PayTouch API Connectivity
Tests the PayTouch API endpoints to verify configuration
"""

import requests
import json
from datetime import datetime
from config import Config

def test_paytouch_initiate():
    """Test PayTouch payout initiation endpoint"""
    print("=" * 80)
    print("Testing PayTouch Payout Initiation API")
    print("=" * 80)
    
    url = f"{Config.PAYTOUCH_BASE_URL}/api/payout/v2/transaction"
    
    # Test payload
    payload = {
        'token': Config.PAYTOUCH_TOKEN,
        'request_id': f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'bene_account': '1234567890',
        'bene_ifsc': 'SBIN0001234',
        'bene_name': 'Test User',
        'amount': 10.00,
        'currency': 'INR',
        'narration': 'Test Payment',
        'payment_mode': 'IMPS',
        'bank_name': 'State Bank of India',
        'bank_branch': 'Test Branch'
    }
    
    print(f"\nConfiguration:")
    print(f"  Base URL: {Config.PAYTOUCH_BASE_URL}")
    print(f"  Token: {Config.PAYTOUCH_TOKEN[:10]}...{Config.PAYTOUCH_TOKEN[-5:]}")
    print(f"\nEndpoint: {url}")
    print(f"\nRequest Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        print("Sending request...")
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        print(f"\nResponse:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        print(f"  Content-Length: {len(response.text)} bytes")
        print(f"\nRaw Response:")
        print(response.text)
        print()
        
        if response.status_code in [200, 201]:
            try:
                response_json = response.json()
                print("Parsed JSON Response:")
                print(json.dumps(response_json, indent=2))
                print()
                print("✅ PayTouch API is responding correctly")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print("This indicates PayTouch API is returning invalid JSON")
        else:
            print(f"❌ PayTouch API returned error status: {response.status_code}")
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out - PayTouch API is not responding")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("Check network connectivity and firewall rules")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)

def test_paytouch_status():
    """Test PayTouch status check endpoint"""
    print("\n")
    print("=" * 80)
    print("Testing PayTouch Status Check API")
    print("=" * 80)
    
    url = f"{Config.PAYTOUCH_BASE_URL}/api/payout/v2/get-report-status"
    
    # Test payload
    payload = {
        'token': Config.PAYTOUCH_TOKEN,
        'transaction_id': 'TEST123',
        'external_ref': 'TEST_REF'
    }
    
    print(f"\nEndpoint: {url}")
    print(f"\nRequest Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        print("Sending request...")
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        print(f"\nResponse:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        print(f"  Content-Length: {len(response.text)} bytes")
        print(f"\nRaw Response:")
        print(response.text)
        print()
        
        if response.status_code in [200, 201]:
            try:
                response_json = response.json()
                print("Parsed JSON Response:")
                print(json.dumps(response_json, indent=2))
                print()
                print("✅ PayTouch Status API is responding correctly")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
        else:
            print(f"⚠️  PayTouch Status API returned: {response.status_code}")
            print("(This is expected for non-existent transaction)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)

def check_configuration():
    """Check PayTouch configuration"""
    print("\n")
    print("=" * 80)
    print("PayTouch Configuration Check")
    print("=" * 80)
    
    print(f"\nBase URL: {Config.PAYTOUCH_BASE_URL}")
    print(f"Token: {Config.PAYTOUCH_TOKEN[:10]}...{Config.PAYTOUCH_TOKEN[-5:]}")
    print(f"Token Length: {len(Config.PAYTOUCH_TOKEN)} characters")
    print()
    
    # Validate configuration
    issues = []
    
    if not Config.PAYTOUCH_BASE_URL:
        issues.append("❌ PAYTOUCH_BASE_URL is not set")
    elif not Config.PAYTOUCH_BASE_URL.startswith('http'):
        issues.append("❌ PAYTOUCH_BASE_URL must start with http:// or https://")
    
    if not Config.PAYTOUCH_TOKEN:
        issues.append("❌ PAYTOUCH_TOKEN is not set")
    elif len(Config.PAYTOUCH_TOKEN) < 20:
        issues.append("⚠️  PAYTOUCH_TOKEN seems too short")
    
    if issues:
        print("Configuration Issues:")
        for issue in issues:
            print(f"  {issue}")
        print()
        return False
    else:
        print("✅ Configuration looks good")
        print()
        return True
    
    print("=" * 80)

if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PayTouch API Test Suite" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Check configuration first
    if check_configuration():
        # Test initiation endpoint
        test_paytouch_initiate()
        
        # Test status endpoint
        test_paytouch_status()
    else:
        print("\n❌ Please fix configuration issues before testing API")
    
    print("\n")
    print("Test complete!")
    print()
