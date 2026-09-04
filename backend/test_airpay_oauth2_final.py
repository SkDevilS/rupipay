"""
Test Airpay OAuth2 Token Generation - Final Implementation
Based on PHP documentation provided by user
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airpay_service import airpay_service
import json

print("=" * 60)
print("AIRPAY OAUTH2 TOKEN GENERATION - FINAL TEST")
print("=" * 60)

print("\nStep 1: Check configuration...")
print(f"Base URL: {airpay_service.base_url}")
print(f"Merchant ID: {airpay_service.merchant_id}")
print(f"Client ID: {airpay_service.client_id}")
print(f"Username: {airpay_service.username}")
print(f"Password: {airpay_service.password}")
print(f"Encryption Key: {airpay_service.encryption_key}")
print(f"Key Length: {len(airpay_service.encryption_key)}")

print("\nStep 2: Generate access token...")
print("-" * 60)

token = airpay_service.generate_access_token()

print("-" * 60)

if token:
    print(f"\n✅ SUCCESS!")
    print(f"Access Token: {token}")
    print(f"Token Length: {len(token)}")
    print(f"Expires: {airpay_service.token_expiry}")
else:
    print(f"\n❌ FAILED!")
    print("Token generation failed. Check logs above for details.")

print("\n" + "=" * 60)
