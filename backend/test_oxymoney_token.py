"""
Test Oxymoney_Grosmart Token Generation
"""

import requests
import json
from config import Config

def test_token_generation():
    """Test token generation with current credentials"""
    
    print("=" * 80)
    print("OXYMONEY_GROSMART TOKEN GENERATION TEST")
    print("=" * 80)
    
    # Display configuration
    print("\n📋 Configuration:")
    print(f"  Base URL: {Config.OXYMONEY_GROSMART_BASE_URL}")
    print(f"  Username: {Config.OXYMONEY_GROSMART_USERNAME}")
    print(f"  Password: {Config.OXYMONEY_GROSMART_PASSWORD}")
    print(f"  Initial Auth Token: {Config.OXYMONEY_GROSMART_INITIAL_AUTH_TOKEN[:50]}...")
    
    # Test 1: Token generation
    print("\n" + "=" * 80)
    print("TEST 1: Generate Access Token")
    print("=" * 80)
    
    url = f"{Config.OXYMONEY_GROSMART_BASE_URL}/api/1.0/auth"
    
    payload = {
        "payload": {
            "userName": Config.OXYMONEY_GROSMART_USERNAME,
            "password": Config.OXYMONEY_GROSMART_PASSWORD
        },
        "checksum": "92992"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {Config.OXYMONEY_GROSMART_INITIAL_AUTH_TOKEN}'
    }
    
    print(f"\n📤 Request:")
    print(f"  URL: {url}")
    print(f"  Method: POST")
    print(f"  Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=4)}")
    print(f"  Payload: {json.dumps(payload, indent=4)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"  Body: {json.dumps(result, indent=4)}")
            
            if response.status_code == 200:
                if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                    token = result.get('token')
                    if token:
                        print(f"\n✅ SUCCESS: Token generated")
                        print(f"  Token: {token[:50]}...")
                        print(f"  Token Length: {len(token)}")
                        return True
                    else:
                        print(f"\n❌ FAILED: No token in response")
                        return False
                else:
                    print(f"\n❌ FAILED: {result.get('errorMsg', 'Unknown error')}")
                    print(f"  Error Code: {result.get('errorCode')}")
                    return False
            else:
                print(f"\n❌ FAILED: HTTP {response.status_code}")
                return False
                
        except json.JSONDecodeError:
            print(f"  Body (raw): {response.text}")
            print(f"\n❌ FAILED: Invalid JSON response")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ FAILED: Request timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILED: Request error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_token_generation()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TOKEN GENERATION TEST PASSED")
    else:
        print("❌ TOKEN GENERATION TEST FAILED")
        print("\n💡 Troubleshooting:")
        print("  1. Verify the initial auth token is correct and not expired")
        print("  2. Check if username and password are correct")
        print("  3. Ensure the base URL is accessible")
        print("  4. Contact Oxymoney support if the issue persists")
    print("=" * 80)
