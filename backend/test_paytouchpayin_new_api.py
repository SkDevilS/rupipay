"""
Test PayTouch Payin New API (Updated 2026)
Tests the updated dynamic-qr-simple endpoint
"""

import requests
import json
import time
from config import Config

def test_new_api():
    """Test the new PayTouch Payin API endpoint"""
    
    print("="*80)
    print("🧪 Testing PayTouch Payin New API (2026)")
    print("="*80)
    
    # API Configuration
    base_url = Config.PAYTOUCHPAYIN_BASE_URL
    token = Config.PAYTOUCHPAYIN_TOKEN
    
    print(f"\n📋 Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Token: {token[:20]}...")
    
    # Test data
    test_txnid = f"TEST{int(time.time())}"
    
    payload = {
        "token": token,
        "mobile": "9876543210",
        "amount": "20",
        "txnid": test_txnid,
        "name": "Test Customer"
    }
    
    print(f"\n📤 Request:")
    print(f"  Endpoint: {base_url}/api/payin/dynamic-qr-simple")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Make API call
        url = f"{base_url}/api/payin/dynamic-qr-simple"
        headers = {
            'Content-Type': 'application/json'
        }
        
        print(f"\n🚀 Sending request...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        print(f"  Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'SUCCESS':
                print(f"\n✅ SUCCESS!")
                print(f"\n📦 Response Data:")
                response_data = data.get('data', {})
                print(f"  - txnid: {response_data.get('txnid')}")
                print(f"  - apitxnid: {response_data.get('apitxnid')}")
                print(f"  - amount: {response_data.get('amount')}")
                print(f"  - name: {response_data.get('name')}")
                print(f"  - expire_at: {response_data.get('expire_at')}")
                print(f"  - upi_string: {response_data.get('upi_string', '')[:100]}...")
                
                print(f"\n💡 New API Features:")
                print(f"  ✓ Endpoint changed to: /api/payin/dynamic-qr-simple")
                print(f"  ✓ Returns UPI string instead of redirect URL")
                print(f"  ✓ Includes expire_at timestamp")
                print(f"  ✓ QR expires after 5 minutes if not paid")
                
                return True
            else:
                print(f"\n❌ API returned error:")
                print(f"  Message: {data.get('message')}")
                return False
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def compare_old_vs_new():
    """Compare old and new API response structures"""
    
    print("\n" + "="*80)
    print("📊 API Comparison: Old vs New")
    print("="*80)
    
    print("\n🔴 OLD API (deprecated):")
    print("  Endpoint: /api/payin/dynamic-qr")
    print("  Response:")
    print("    - redirect_url: Web page URL for payment")
    print("    - User redirected to payment page")
    
    print("\n🟢 NEW API (2026):")
    print("  Endpoint: /api/payin/dynamic-qr-simple")
    print("  Response:")
    print("    - upi_string: Direct UPI payment string")
    print("    - Can generate QR code from UPI string")
    print("    - No redirect needed")
    print("    - expire_at: Unix timestamp for expiry")
    
    print("\n📝 Migration Notes:")
    print("  1. Update endpoint to /api/payin/dynamic-qr-simple")
    print("  2. Use upi_string instead of redirect_url")
    print("  3. Generate QR code from UPI string on frontend")
    print("  4. Handle expire_at for QR expiry (5 minutes)")
    print("  5. Callback format remains the same")


if __name__ == "__main__":
    # Test new API
    success = test_new_api()
    
    # Show comparison
    compare_old_vs_new()
    
    if success:
        print("\n" + "="*80)
        print("✅ PayTouch Payin New API Test Completed Successfully!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ PayTouch Payin New API Test Failed")
        print("="*80)
