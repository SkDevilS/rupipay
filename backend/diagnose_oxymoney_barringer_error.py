"""
Diagnose Oxymoney Barringer Token Generation Error
"""

import requests
import json
from config import Config

def check_credentials():
    """Check if all required credentials are set"""
    print("=" * 60)
    print("CHECKING OXYMONEY BARRINGER CREDENTIALS")
    print("=" * 60)
    
    print(f"\n📋 Configuration:")
    print(f"  Base URL: {Config.OXY_BAR_BASE_URL}")
    print(f"  Username: {Config.OXY_BAR_USERNAME}")
    print(f"  Password: {Config.OXY_BAR_PASSWORD[:10]}..." if len(Config.OXY_BAR_PASSWORD) > 10 else Config.OXY_BAR_PASSWORD)
    print(f"  Initial Token: {Config.OXY_BAR_INITIAL_AUTH_TOKEN[:30]}..." if len(Config.OXY_BAR_INITIAL_AUTH_TOKEN) > 30 else Config.OXY_BAR_INITIAL_AUTH_TOKEN)
    print(f"  Secret Key: {Config.OXY_BAR_SECRET_KEY[:10]}..." if len(Config.OXY_BAR_SECRET_KEY) > 10 else Config.OXY_BAR_SECRET_KEY)
    print()
    
    # Check if credentials are set
    if not Config.OXY_BAR_USERNAME:
        print("  ✗ OXY_BAR_USERNAME is not set!")
        return False
    if not Config.OXY_BAR_PASSWORD:
        print("  ✗ OXY_BAR_PASSWORD is not set!")
        return False
    if not Config.OXY_BAR_INITIAL_AUTH_TOKEN:
        print("  ✗ OXY_BAR_INITIAL_AUTH_TOKEN is not set!")
        print("  ⚠️  This is the root cause of the 400 Bad Request error!")
        return False
    print("  ✓ All credentials are set")
    return True

def test_token_generation():
    """Test token generation"""
    print("\n" + "=" * 60)
    print("TESTING TOKEN GENERATION")
    print("=" * 60)
    
    url = f"{Config.OXY_BAR_BASE_URL}/api/1.0/auth"
    
    payload = {
        "payload": {
            "userName": Config.OXY_BAR_USERNAME,
            "password": Config.OXY_BAR_PASSWORD
        },
        "checksum": "92992"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {Config.OXY_BAR_INITIAL_AUTH_TOKEN}'
    }
    
    print(f"\n📤 Request:")
    print(f"  URL: {url}")
    print(f"  Headers: {json.dumps({k: v[:30] + '...' if len(v) > 30 else v for k, v in headers.items()}, indent=4)}")
    print(f"  Payload: {json.dumps(payload, indent=4)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Body: {json.dumps(response.json(), indent=4)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errorCode') in ['0', '00', '000']:
                print("\n✅ Token generation successful!")
                return True
            else:
                print(f"\n❌ Token generation failed: {result.get('errorMsg')}")
                return False
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_with_truaxis():
    """Compare Barringer config with Truaxis (working)"""
    print("\n" + "=" * 60)
    print("COMPARING WITH TRUAXIS (WORKING)")
    print("=" * 60)
    
    print(f"\n📊 Comparison:")
    print(f"\n  Truaxis:")
    print(f"    Base URL: {Config.OXYMONEY_TRUAXIS_BASE_URL}")
    print(f"    Username: {Config.OXYMONEY_TRUAXIS_USERNAME}")
    print(f"    Password: {Config.OXYMONEY_TRUAXIS_PASSWORD[:10]}...")
    print(f"    Initial Token: {Config.OXYMONEY_TRUAXIS_INITIAL_AUTH_TOKEN[:30]}...")
    print(f"    MID: {Config.OXYMONEY_TRUAXIS_MID}")
    print(f"    BPM ID: {Config.OXYMONEY_TRUAXIS_BPM_IDENTIFIER}")
    
    print(f"\n  Barringer:")
    print(f"    Base URL: {Config.OXY_BAR_BASE_URL}")
    print(f"    Username: {Config.OXY_BAR_USERNAME}")
    print(f"    Password: {Config.OXY_BAR_PASSWORD[:10] if Config.OXY_BAR_PASSWORD else 'NOT SET'}...")
    print(f"    Initial Token: {Config.OXY_BAR_INITIAL_AUTH_TOKEN[:30] if Config.OXY_BAR_INITIAL_AUTH_TOKEN else 'NOT SET'}...")
    print(f"    MID: {Config.OXY_BAR_MID if Config.OXY_BAR_MID else 'NOT SET'}")
    print(f"    BPM ID: {Config.OXY_BAR_BPM_IDENTIFIER if Config.OXY_BAR_BPM_IDENTIFIER else 'NOT SET'}")
    
    print(f"\n🔍 Differences:")
    if Config.OXY_BAR_BASE_URL != Config.OXYMONEY_TRUAXIS_BASE_URL:
        print(f"  ⚠️  Base URLs are different")
    else:
        print(f"  ✓ Base URLs match")
    
    if not Config.OXY_BAR_INITIAL_AUTH_TOKEN:
        print(f"  ❌ Barringer Initial Token is NOT SET (This is the problem!)")
    elif Config.OXY_BAR_INITIAL_AUTH_TOKEN != Config.OXYMONEY_TRUAXIS_INITIAL_AUTH_TOKEN:
        print(f"  ⚠️  Initial tokens are different (expected if different accounts)")
    else:
        print(f"  ✓ Initial tokens match")

def main():
    """Main diagnostic function"""
    print("\n🔍 OXYMONEY BARRINGER DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Step 1: Check credentials
    if not check_credentials():
        print("\n" + "=" * 60)
        print("❌ DIAGNOSIS: MISSING CREDENTIALS")
        print("=" * 60)
        print("\nThe OXY_BAR_INITIAL_AUTH_TOKEN is not set in your environment.")
        print("\n📝 TO FIX:")
        print("  1. Get the initial auth token from Barringer/TransXT")
        print("  2. Add it to your .env file:")
        print("     OXY_BAR_INITIAL_AUTH_TOKEN=eyJhbGciOiJIUzUxMiJ9...")
        print("  3. Restart the backend server")
        print("\n💡 NOTE:")
        print("  - Truaxis and Grosmart have their initial tokens set")
        print("  - Barringer needs the same type of token")
        print("  - The initial token is used to authenticate the /api/1.0/auth endpoint")
        print("  - After authentication, you get a session token that expires in 15 minutes")
        return
    
    # Step 2: Test token generation
    test_token_generation()
    
    # Step 3: Compare with working integration
    compare_with_truaxis()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
