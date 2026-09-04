"""
Test Airpay decryption with the IV padding fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force reload of the module to get latest changes
import importlib
if 'airpay_service' in sys.modules:
    importlib.reload(sys.modules['airpay_service'])

from airpay_service import airpay_service
import json

def main():
    print("\n" + "="*60)
    print("AIRPAY DECRYPTION FIX TEST")
    print("="*60 + "\n")
    
    print("Testing with fresh module import...")
    print(f"Module location: {airpay_service.__class__.__module__}")
    
    print("\nStep 1: Generating access token with decryption...")
    token = airpay_service.generate_access_token()
    
    if token:
        print(f"\n✅ SUCCESS!")
        print(f"Access Token: {token[:30]}...")
        print(f"Token Length: {len(token)}")
        print(f"Expires: {airpay_service.token_expiry}")
        
        print(f"\n🎉 Decryption is working correctly!")
        print(f"\nThe fix applied:")
        print(f"1. Convert hex IV to bytes (8 bytes)")
        print(f"2. Pad IV to 16 bytes with null bytes")
        print(f"3. Use padded IV for AES-256-CBC decryption")
        
        return True
    else:
        print(f"\n❌ FAILED")
        print(f"\nPossible issues:")
        print(f"1. Module not reloaded - try restarting Python")
        print(f"2. Credentials incorrect")
        print(f"3. Network/API issue")
        
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
