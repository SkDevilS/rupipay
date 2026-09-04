"""
Debug Viyonapay Signature Verification
This script helps diagnose signature verification issues
"""

import json
import base64
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from config import Config

def load_viyonapay_public_key():
    """Load VIYONAPAY's public key"""
    try:
        key_path = Config.VIYONAPAY_SERVER_PUBLIC_KEY_PATH
        print(f"Loading public key from: {key_path}")
        with open(key_path, 'r') as f:
            key_data = f.read()
        print(f"✓ Public key loaded successfully")
        print(f"Key preview: {key_data[:100]}...")
        return RSA.import_key(key_data)
    except Exception as e:
        print(f"❌ Failed to load public key: {e}")
        return None

def test_signature_verification():
    """Test different signature verification approaches"""
    
    print("\n" + "="*60)
    print("VIYONAPAY SIGNATURE VERIFICATION DEBUG")
    print("="*60)
    
    # Load public key
    public_key = load_viyonapay_public_key()
    if not public_key:
        print("❌ Cannot proceed without public key")
        return
    
    print(f"\n✓ Public key loaded")
    print(f"  Key size: {public_key.size_in_bits()} bits")
    print(f"  Key type: RSA")
    
    # Test payload (example - replace with actual callback data)
    test_payload = {
        "orderId": "ORD123456789",
        "transactionId": "TXN123456789",
        "paymentStatus": "SUCCESS",
        "amount": 100.00
    }
    
    print(f"\n📦 Test Payload:")
    print(json.dumps(test_payload, indent=2))
    
    # Method 1: Sorted keys, no spaces (canonical JSON)
    print(f"\n🔍 Method 1: Canonical JSON (sorted keys, no spaces)")
    json_canonical = json.dumps(test_payload, separators=(',', ':'), sort_keys=True)
    print(f"  JSON: {json_canonical}")
    hash_canonical = SHA256.new(json_canonical.encode('utf-8'))
    print(f"  SHA256: {hash_canonical.hexdigest()}")
    
    # Method 2: Sorted keys with spaces
    print(f"\n🔍 Method 2: Sorted keys with spaces")
    json_spaces = json.dumps(test_payload, sort_keys=True)
    print(f"  JSON: {json_spaces}")
    hash_spaces = SHA256.new(json_spaces.encode('utf-8'))
    print(f"  SHA256: {hash_spaces.hexdigest()}")
    
    # Method 3: Original order, no spaces
    print(f"\n🔍 Method 3: Original order, no spaces")
    json_original = json.dumps(test_payload, separators=(',', ':'))
    print(f"  JSON: {json_original}")
    hash_original = SHA256.new(json_original.encode('utf-8'))
    print(f"  SHA256: {hash_original.hexdigest()}")
    
    print(f"\n" + "="*60)
    print("SIGNATURE VERIFICATION APPROACHES")
    print("="*60)
    
    print(f"""
The signature verification is currently using:
- Canonical JSON (sorted keys, no spaces)
- SHA-256 hash
- PKCS#1 v1.5 signature verification

If Viyonapay is sending callbacks but signature verification fails:

1. Check if the public key is correct
   - Verify with Viyonapay team
   - Ensure it's their server public key (not client key)

2. Check the JSON serialization format
   - They might use different formatting
   - Try different approaches above

3. Check what data is being signed
   - Might be signing the encrypted_data field
   - Might be signing the entire payload
   - Might be signing specific fields only

4. Check signature encoding
   - Currently expecting base64-encoded signature
   - Verify this matches Viyonapay's format

RECOMMENDED NEXT STEPS:
1. Capture actual callback from Viyonapay
2. Get the exact signature they're sending
3. Ask Viyonapay team for:
   - Exact JSON format they use for signing
   - Which fields are included in signature
   - Signature algorithm details
   - Sample signature for testing
""")

if __name__ == '__main__':
    test_signature_verification()
