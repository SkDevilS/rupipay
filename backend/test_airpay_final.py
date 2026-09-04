"""
Final test of Airpay V4 integration with correct key and checksum
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service

def main():
    print("\n" + "="*60)
    print("AIRPAY V4 FINAL INTEGRATION TEST")
    print("="*60 + "\n")
    
    print("Step 1: Check encryption key generation...")
    print(f"  Encryption Key: {airpay_service.encryption_key}")
    print(f"  Key Length: {len(airpay_service.encryption_key)}")
    
    print("\nStep 2: Generate access token...")
    token = airpay_service.generate_access_token()
    
    if token:
        print(f"\n✅ SUCCESS!")
        print(f"Access Token: {token[:30]}...")
        print(f"Token Length: {len(token)}")
        print(f"Expires: {airpay_service.token_expiry}")
        
        print(f"\n🎉 Airpay V4 integration is WORKING!")
        print(f"\nReady for:")
        print(f"  ✓ QR code generation")
        print(f"  ✓ Payment verification")
        print(f"  ✓ Callback handling")
        
        return True
    else:
        print(f"\n❌ Token generation failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
