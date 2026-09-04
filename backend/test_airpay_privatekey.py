#!/usr/bin/env python3
"""
Test Airpay Private Key Generation and Verify API
"""

import hashlib
from airpay_service import airpay_service

def test_privatekey():
    """Test privatekey generation"""
    
    print("=" * 100)
    print("AIRPAY PRIVATE KEY TEST")
    print("=" * 100)
    
    # Get credentials
    username = airpay_service.username
    password = airpay_service.password
    secret = airpay_service.secret
    
    print(f"\n📋 Credentials:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Secret: {secret}")
    
    # Generate privatekey
    privatekey_string = f"{secret}@{username}:|:{password}"
    privatekey = hashlib.sha256(privatekey_string.encode('utf-8')).hexdigest()
    
    print(f"\n🔑 Private Key Generation:")
    print(f"  Formula: SHA256(secret@username:|:password)")
    print(f"  String: {privatekey_string}")
    print(f"  Private Key: {privatekey}")
    
    # Compare with service privatekey
    print(f"\n✓ Service Private Key: {airpay_service.privatekey}")
    
    if privatekey == airpay_service.privatekey:
        print(f"\n✅ Private key matches!")
    else:
        print(f"\n❌ Private key mismatch!")
    
    print(f"\n{'='*100}")
    print("Now testing verify API with privatekey...")
    print(f"{'='*100}\n")
    
    # Test verify API with a transaction
    result = airpay_service.verify_payment(
        ap_transactionid='1820937737'
    )
    
    print(f"\n📊 Verify Result:")
    import json
    print(json.dumps(result, indent=2, default=str))
    
    if result.get('success'):
        print(f"\n✅ Verify API working with privatekey!")
    else:
        print(f"\n⚠️  Verify API response: {result.get('message')}")

if __name__ == '__main__':
    test_privatekey()
