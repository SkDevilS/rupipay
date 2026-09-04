"""
Test Airpay OAuth2 Token Generation - Complete Test
Tests the complete OAuth2 flow with correct credentials
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service
import json

print("=" * 70)
print("AIRPAY OAUTH2 TOKEN GENERATION - COMPLETE TEST")
print("=" * 70)

print("\n📋 Step 1: Verify Configuration")
print("-" * 70)
print(f"Base URL: {airpay_service.base_url}")
print(f"Merchant ID: {airpay_service.merchant_id}")
print(f"Client ID: {airpay_service.client_id}")
print(f"Client Secret: {airpay_service.client_secret[:10]}...")
print(f"Username: {airpay_service.username}")
print(f"Password: {airpay_service.password}")
print(f"Encryption Key: {airpay_service.encryption_key}")
print(f"Key Length: {len(airpay_service.encryption_key)} characters")

print("\n🔑 Step 2: Generate Access Token")
print("-" * 70)

token = airpay_service.generate_access_token()

print("-" * 70)

if token:
    print(f"\n✅ SUCCESS! OAuth2 Token Generated")
    print(f"📝 Access Token: {token}")
    print(f"📏 Token Length: {len(token)} characters")
    print(f"⏰ Expires: {airpay_service.token_expiry}")
    print(f"⏱️  Valid for: {(airpay_service.token_expiry - airpay_service.token_expiry.replace(second=0)).seconds} seconds")
    
    print("\n🎉 AIRPAY V4 OAUTH2 INTEGRATION COMPLETE!")
    print("\nNext Steps:")
    print("1. ✅ OAuth2 token generation working")
    print("2. ⏭️  Test QR code generation")
    print("3. ⏭️  Test payment verification")
    print("4. ⏭️  Test callback handling")
    
else:
    print(f"\n❌ FAILED! Token generation failed")
    print("\nPossible Issues:")
    print("1. Check if credentials are correct")
    print("2. Verify encryption key generation")
    print("3. Check checksum algorithm")
    print("4. Review API endpoint URL")

print("\n" + "=" * 70)
