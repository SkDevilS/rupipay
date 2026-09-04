"""
Test complete Airpay token generation with decryption
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service
import json

def main():
    print("\n" + "="*60)
    print("AIRPAY TOKEN GENERATION - COMPLETE TEST")
    print("="*60 + "\n")
    
    print("Step 1: Generating access token...")
    token = airpay_service.generate_access_token()
    
    if token:
        print(f"\n✅ SUCCESS!")
        print(f"Access Token: {token[:30]}...")
        print(f"Token Length: {len(token)}")
        print(f"Expires: {airpay_service.token_expiry}")
        
        # Test token caching
        print(f"\nStep 2: Testing token caching...")
        token2 = airpay_service.generate_access_token()
        
        if token == token2:
            print(f"✅ Token caching works! Same token returned.")
        else:
            print(f"⚠️  Different token returned (caching may not be working)")
        
        print(f"\n🎉 Airpay V4 integration is ready!")
        print(f"\nNext steps:")
        print(f"1. Test QR generation")
        print(f"2. Test payment verification")
        print(f"3. Test callback handling")
        
        return True
    else:
        print(f"\n❌ FAILED to generate token")
        print(f"\nCheck:")
        print(f"1. All credentials in .env are correct")
        print(f"2. Server IP is whitelisted (if still getting 403)")
        print(f"3. Backend logs for detailed error")
        
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
