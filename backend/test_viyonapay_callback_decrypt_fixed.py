#!/usr/bin/env python3
"""
Test Viyonapay callback decryption with correct secret key handling
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

# The callback data
encrypted_data = "Afp2eED73mw5VSM0Esa5e7CXzniYU62OKDjf5G5+3//G6xsxCboPHnC2D3XEiQ5lPp6PMVh7dCsrt8lvsNgbqB/Ar2ypfhMYibsKfu1DcM5+d1UNVpHgZxV4s2a9CYVMdsuxzeYWwi7c826G0cbMVlwNlEt9i88HhLb8BPEQKqEfRdIx+pPQncat6pd69hLureA7sfkG2XdthEfL94OcDi1Gb31IePg3OgstY8aGqk027JrxPU6yApZkyu8h0oz861e17f7AUIR6+21rslmRV10VoAvHIH4zZtUXzPU8FVa/PGumbk1LlM4Zfn4omzFClOGDv1zjccLIuH2bfH861+Cunmmq6DP4qU7xUgRDzi7aa5rZse/gPdzhsXeu+zMAaVjx7+P/l/kd5C11ApfABoKdBiyZWl4XbaZBmZajjQJ/YGE4KvHKbTRVfawsLx87pQO13sXIm3fPg5rTG4aEecmiE+1KtwT+JsAgzYIV5Rg7CsEL/HkBbwcthP+m3Lr8KBH10NtJQgFR06FmcqqCpO1q61aoJWh8fjT61TSs5tGfhpsj8V8="

timestamp = "1774204672"
request_id = "5cfe4bd1-35c6-43b2-bdb8-aedd9d77a982"

# The webhook secret from environment
webhook_secret_str = "e8119e69a3d56ec5d117e7dff06467c3"

print(f"\n{'='*60}")
print(f"🔍 Testing Viyonapay Callback Decryption")
print(f"{'='*60}\n")

print(f"📋 Webhook Secret: {webhook_secret_str}")
print(f"   Length: {len(webhook_secret_str)} characters\n")

# Decode encrypted data
encrypted_bytes = base64.b64decode(encrypted_data)
nonce = encrypted_bytes[:12]
ciphertext = encrypted_bytes[12:]

print(f"📋 Encrypted Data:")
print(f"   Total bytes: {len(encrypted_bytes)}")
print(f"   Nonce: {nonce.hex()}")
print(f"   Ciphertext: {len(ciphertext)} bytes\n")

# Try different ways to convert the secret key
test_cases = [
    {
        "name": "Method 1: UTF-8 encode",
        "key": webhook_secret_str.encode('utf-8')
    },
    {
        "name": "Method 2: Hex decode",
        "key": bytes.fromhex(webhook_secret_str)
    },
    {
        "name": "Method 3: SHA-256 hash of string",
        "key": hashlib.sha256(webhook_secret_str.encode('utf-8')).digest()
    },
    {
        "name": "Method 4: MD5 hash (16 bytes) + itself (32 bytes)",
        "key": hashlib.md5(webhook_secret_str.encode('utf-8')).digest() * 2
    },
]

# Try different AAD formats for each key method
aad_formats = [
    {
        "name": "AAD Format A: sorted, int timestamp",
        "aad": {"request_id": request_id, "timestamp": int(timestamp)},
        "sort": True
    },
    {
        "name": "AAD Format B: sorted, string timestamp",
        "aad": {"request_id": request_id, "timestamp": timestamp},
        "sort": True
    },
    {
        "name": "AAD Format C: unsorted, int timestamp",
        "aad": {"timestamp": int(timestamp), "request_id": request_id},
        "sort": False
    },
]

success = False

for key_test in test_cases:
    print(f"{'='*60}")
    print(f"Testing: {key_test['name']}")
    print(f"{'='*60}")
    
    key = key_test['key']
    print(f"Key length: {len(key)} bytes")
    print(f"Key (hex): {key[:16].hex()}...")
    
    # AES-GCM requires 16, 24, or 32 byte keys
    if len(key) not in [16, 24, 32]:
        print(f"❌ Invalid key length: {len(key)} bytes (must be 16, 24, or 32)\n")
        continue
    
    for aad_test in aad_formats:
        print(f"\n  {aad_test['name']}")
        
        aad_dict = aad_test['aad']
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=aad_test['sort'])
        aad_bytes = aad_json.encode('utf-8')
        
        print(f"    AAD: {aad_json}")
        
        try:
            aesgcm = AESGCM(key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
            decrypted_json = json.loads(decrypted_bytes.decode('utf-8'))
            
            print(f"    ✅ SUCCESS!")
            print(f"\n{'='*60}")
            print(f"🎉 DECRYPTION SUCCESSFUL!")
            print(f"{'='*60}\n")
            print(f"Key Method: {key_test['name']}")
            print(f"AAD Format: {aad_test['name']}")
            print(f"\n📦 Decrypted Data:")
            print(json.dumps(decrypted_json, indent=2))
            success = True
            break
        except Exception as e:
            print(f"    ❌ Failed: {str(e)[:80]}")
    
    if success:
        break
    print()

if not success:
    print(f"\n{'='*60}")
    print(f"❌ All decryption attempts failed")
    print(f"{'='*60}")
    print(f"\n💡 Next Steps:")
    print(f"1. Contact Viyonapay team to confirm:")
    print(f"   - The exact webhook secret key format")
    print(f"   - How to derive the AES key from the secret")
    print(f"   - The AAD format they use")
    print(f"2. Ask for a sample encrypted callback with decryption code")
