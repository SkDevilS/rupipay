#!/usr/bin/env python3
"""
Diagnose ViyonaPay Token Generation Issue
Checks credentials, keys, and API connectivity
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("="*80)
print("  ViyonaPay Token Generation Diagnostic")
print("="*80)

# Check environment variables
print("\n1. Checking Environment Variables:")
print("-" * 80)

CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET')
API_KEY = os.getenv('VIYONAPAY_API_KEY')
BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
VPA = os.getenv('VIYONAPAY_VPA', 'vfipl.188690284791@kvb')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

print(f"✓ BASE_URL: {BASE_URL}")
print(f"{'✓' if CLIENT_ID else '✗'} CLIENT_ID: {CLIENT_ID if CLIENT_ID else '❌ NOT SET'}")
print(f"{'✓' if CLIENT_SECRET else '✗'} CLIENT_SECRET: {'***' + CLIENT_SECRET[-4:] if CLIENT_SECRET else '❌ NOT SET'}")
print(f"{'✓' if API_KEY else '✗'} API_KEY: {'***' + API_KEY[-4:] if API_KEY else '❌ NOT SET'}")
print(f"✓ VPA: {VPA}")
print(f"✓ PRIVATE_KEY_PATH: {PRIVATE_KEY_PATH}")
print(f"✓ PUBLIC_KEY_PATH: {PUBLIC_KEY_PATH}")

if not all([CLIENT_ID, CLIENT_SECRET, API_KEY]):
    print("\n❌ CRITICAL: Missing required credentials!")
    print("\nPlease update backend/.env with:")
    print("  VIYONAPAY_CLIENT_ID=your_client_id")
    print("  VIYONAPAY_CLIENT_SECRET=your_client_secret")
    print("  VIYONAPAY_API_KEY=your_api_key")
    sys.exit(1)

# Check key files
print("\n2. Checking RSA Key Files:")
print("-" * 80)

import os.path

if os.path.exists(PRIVATE_KEY_PATH):
    print(f"✓ Private key file exists: {PRIVATE_KEY_PATH}")
    try:
        from Crypto.PublicKey import RSA
        with open(PRIVATE_KEY_PATH, 'r') as f:
            private_key = RSA.import_key(f.read())
        print(f"  ✓ Private key loaded successfully")
        print(f"  ✓ Key size: {private_key.size_in_bits()} bits")
    except Exception as e:
        print(f"  ✗ Failed to load private key: {e}")
else:
    print(f"✗ Private key file NOT FOUND: {PRIVATE_KEY_PATH}")

if os.path.exists(PUBLIC_KEY_PATH):
    print(f"✓ Public key file exists: {PUBLIC_KEY_PATH}")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        with open(PUBLIC_KEY_PATH, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(), backend=default_backend()
            )
        print(f"  ✓ Public key loaded successfully")
        print(f"  ✓ Key size: {public_key.key_size} bits")
    except Exception as e:
        print(f"  ✗ Failed to load public key: {e}")
else:
    print(f"✗ Public key file NOT FOUND: {PUBLIC_KEY_PATH}")

# Test API connectivity
print("\n3. Testing API Connectivity:")
print("-" * 80)

try:
    import requests
    
    # Test basic connectivity
    print(f"Testing connection to {BASE_URL}...")
    response = requests.get(BASE_URL, timeout=10)
    print(f"✓ API is reachable (Status: {response.status_code})")
except requests.exceptions.Timeout:
    print(f"✗ Connection timeout - API not reachable")
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test token generation
print("\n4. Testing Token Generation:")
print("-" * 80)

try:
    from viyonapay_service import viyonapay_service
    
    print("Attempting to generate access token...")
    token = viyonapay_service.generate_access_token()
    
    if token:
        print(f"✅ SUCCESS! Token generated:")
        print(f"   Token: {token[:50]}...")
        print(f"\n✓ ViyonaPay integration is working correctly!")
    else:
        print(f"❌ FAILED: Token generation returned None")
        print(f"\nPossible issues:")
        print(f"  1. Invalid CLIENT_ID or CLIENT_SECRET")
        print(f"  2. Invalid API_KEY")
        print(f"  3. Incorrect RSA keys")
        print(f"  4. IP not whitelisted by ViyonaPay")
        print(f"\nPlease verify your credentials with ViyonaPay support.")
        
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("  Diagnostic Complete")
print("="*80)
