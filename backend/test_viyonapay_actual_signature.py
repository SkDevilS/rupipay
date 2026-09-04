"""
Test Viyonapay Signature Verification with Actual Callback Data
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
        return RSA.import_key(key_data)
    except Exception as e:
        print(f"❌ Failed to load public key: {e}")
        return None

def verify_signature(payload_dict, signature_b64):
    """Verify webhook signature"""
    try:
        # Load public key
        public_key = load_viyonapay_public_key()
        if not public_key:
            return False
        
        # Convert payload to canonical JSON
        json_data = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True)
        
        print(f"\n📋 Canonical JSON for signing:")
        print(json_data)
        
        # Create SHA-256 hash
        hash_obj = SHA256.new(json_data.encode('utf-8'))
        print(f"\n🔐 SHA256 Hash: {hash_obj.hexdigest()}")
        
        # Decode signature
        signature = base64.b64decode(signature_b64)
        print(f"\n📝 Signature length: {len(signature)} bytes")
        
        # Verify signature
        pkcs1_15.new(public_key).verify(hash_obj, signature)
        
        return True
    except Exception as e:
        print(f"❌ Signature verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_actual_callback():
    """Test with actual callback data from Viyonapay"""
    
    print("\n" + "="*60)
    print("VIYONAPAY ACTUAL CALLBACK SIGNATURE TEST")
    print("="*60)
    
    # Actual callback data from Viyonapay
    payload = {
        "response_status": 1,
        "encrypted_data": "Afp2eED73mw5VSM0Esa5e7CXzniYU62OKDjf5G5+3//G6xsxCboPHnC2D3XEiQ5lPp6PMVh7dCsrt8lvsNgbqB/Ar2ypfhMYibsKfu1DcM5+d1UNVpHgZxV4s2a9CYVMdsuxzeYWwi7c826G0cbMVlwNlEt9i88HhLb8BPEQKqEfRdIx+pPQncat6pd69hLureA7sfkG2XdthEfL94OcDi1Gb31IePg3OgstY8aGqk027JrxPU6yApZkyu8h0oz861e17f7AUIR6+21rslmRV10VoAvHIH4zZtUXzPU8FVa/PGumbk1LlM4Zfn4omzFClOGDv1zjccLIuH2bfH861+Cunmmq6DP4qU7xUgRDzi7aa5rZse/gPdzhsXeu+zMAaVjx7+P/l/kd5C11ApfABoKdBiyZWl4XbaZBmZajjQJ/YGE4KvHKbTRVfawsLx87pQO13sXIm3fPg5rTG4aEecmiE+1KtwT+JsAgzYIV5Rg7CsEL/HkBbwcthP+m3Lr8KBH10NtJQgFR06FmcqqCpO1q61aoJWh8fjT61TSs5tGfhpsj8V8="
    }
    
    signature = "YrAE9oqPFp/qUGkdt7Z61aZcldGwPbwon6uGVPSrqHL0LdvHCOYyGXJ3vNkbWgt1Dg9LtFzzTmpAOUPtjIh5Zw7omb/AOJ608qgbMmjjv64iiIrZ+8j3rrv+kqBSS6MzLvSmjI4go0nmSwCFYKPkX09bVpKm0OI8XjEg+7d9m5trDj+w0KJ5/JhP8S7OIvSZjYbIZ26grcx/9NdZgG6MNN0wSU86XQrIDl9mOHPVslSw8o/ekrYNi8Ec7iZFElxEYMWfqFP1gxdtImlafQf0pP9hd91HC+8P151Fgmp3osBXWYXVOpMUJ4zlh+M9DaeQXjlfbneBFsxVT4usr1iHiA=="
    
    print(f"\n📦 Payload:")
    print(json.dumps(payload, indent=2))
    
    print(f"\n📝 Signature:")
    print(signature[:80] + "...")
    
    # Test signature verification
    print(f"\n🔐 Testing signature verification...")
    result = verify_signature(payload, signature)
    
    if result:
        print(f"\n✅ SUCCESS! Signature is valid!")
        print(f"\nThe signature verification is working correctly.")
        print(f"Viyonapay signs the encrypted payload (before decryption).")
    else:
        print(f"\n❌ FAILED! Signature is invalid!")
        print(f"\nPossible issues:")
        print(f"1. Wrong public key")
        print(f"2. Different JSON serialization")
        print(f"3. Signature is on different data")
    
    # Try different JSON formats
    print(f"\n" + "="*60)
    print("TESTING DIFFERENT JSON FORMATS")
    print("="*60)
    
    formats = [
        ("Canonical (sorted, no spaces)", lambda d: json.dumps(d, separators=(',', ':'), sort_keys=True)),
        ("Sorted with spaces", lambda d: json.dumps(d, sort_keys=True)),
        ("Original order, no spaces", lambda d: json.dumps(d, separators=(',', ':'))),
        ("Original order with spaces", lambda d: json.dumps(d)),
    ]
    
    for name, formatter in formats:
        print(f"\n🔍 Format: {name}")
        json_str = formatter(payload)
        print(f"  JSON: {json_str[:100]}...")
        hash_obj = SHA256.new(json_str.encode('utf-8'))
        print(f"  SHA256: {hash_obj.hexdigest()}")

if __name__ == '__main__':
    test_actual_callback()
