#!/usr/bin/env python3
"""
Diagnose Viyonapay callback decryption issue
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# The callback data
encrypted_data = "Afp2eED73mw5VSM0Esa5e7CXzniYU62OKDjf5G5+3//G6xsxCboPHnC2D3XEiQ5lPp6PMVh7dCsrt8lvsNgbqB/Ar2ypfhMYibsKfu1DcM5+d1UNVpHgZxV4s2a9CYVMdsuxzeYWwi7c826G0cbMVlwNlEt9i88HhLb8BPEQKqEfRdIx+pPQncat6pd69hLureA7sfkG2XdthEfL94OcDi1Gb31IePg3OgstY8aGqk027JrxPU6yApZkyu8h0oz861e17f7AUIR6+21rslmRV10VoAvHIH4zZtUXzPU8FVa/PGumbk1LlM4Zfn4omzFClOGDv1zjccLIuH2bfH861+Cunmmq6DP4qU7xUgRDzi7aa5rZse/gPdzhsXeu+zMAaVjx7+P/l/kd5C11ApfABoKdBiyZWl4XbaZBmZajjQJ/YGE4KvHKbTRVfawsLx87pQO13sXIm3fPg5rTG4aEecmiE+1KtwT+JsAgzYIV5Rg7CsEL/HkBbwcthP+m3Lr8KBH10NtJQgFR06FmcqqCpO1q61aoJWh8fjT61TSs5tGfhpsj8V8="

timestamp = "1774204672"
request_id = "5cfe4bd1-35c6-43b2-bdb8-aedd9d77a982"

print(f"\n{'='*60}")
print(f"🔍 Viyonapay Callback Decryption Diagnosis")
print(f"{'='*60}\n")

# Check encrypted data
print(f"📋 Encrypted Data Info:")
encrypted_bytes = base64.b64decode(encrypted_data)
print(f"  Base64 length: {len(encrypted_data)}")
print(f"  Decoded length: {len(encrypted_bytes)} bytes")
print(f"  First 20 bytes (hex): {encrypted_bytes[:20].hex()}")
print()

# Extract nonce and ciphertext
nonce = encrypted_bytes[:12]
ciphertext = encrypted_bytes[12:]
print(f"📋 Encryption Structure:")
print(f"  Nonce (12 bytes): {nonce.hex()}")
print(f"  Ciphertext length: {len(ciphertext)} bytes")
print()

# Check secret key
print(f"📋 Checking Secret Key Sources:")

# 1. Environment variable
secret_key_env = os.getenv('VIYONAPAY_WEBHOOK_SECRET_KEY')
if secret_key_env:
    try:
        key_from_env = base64.b64decode(secret_key_env)
        print(f"  ✅ Environment variable found: {len(key_from_env)} bytes")
        print(f"     First 8 bytes (hex): {key_from_env[:8].hex()}")
    except Exception as e:
        print(f"  ❌ Environment variable exists but decode failed: {e}")
else:
    print(f"  ❌ VIYONAPAY_WEBHOOK_SECRET_KEY not in environment")

# 2. File
key_path = os.path.join(os.path.dirname(__file__), 'viyonapay_webhook_secret.key')
if os.path.exists(key_path):
    with open(key_path, 'rb') as f:
        key_from_file = f.read()
    print(f"  ✅ File found: {len(key_from_file)} bytes")
    print(f"     First 8 bytes (hex): {key_from_file[:8].hex()}")
else:
    print(f"  ❌ File not found: {key_path}")

print()

# Try different AAD formats
print(f"📋 Testing Different AAD Formats:\n")

# Load the secret key (try env first, then file)
secret_key = None
if secret_key_env:
    try:
        secret_key = base64.b64decode(secret_key_env)
    except:
        pass

if not secret_key and os.path.exists(key_path):
    with open(key_path, 'rb') as f:
        secret_key = f.read()

if not secret_key:
    print("❌ No secret key available for testing")
    sys.exit(1)

print(f"Using secret key: {len(secret_key)} bytes\n")

# Test different AAD formats
test_cases = [
    {
        "name": "Format 1: timestamp as int, sorted keys",
        "aad": {"request_id": request_id, "timestamp": int(timestamp)}
    },
    {
        "name": "Format 2: timestamp as string, sorted keys",
        "aad": {"request_id": request_id, "timestamp": timestamp}
    },
    {
        "name": "Format 3: timestamp first (unsorted)",
        "aad": {"timestamp": int(timestamp), "request_id": request_id}
    },
    {
        "name": "Format 4: timestamp as string, unsorted",
        "aad": {"timestamp": timestamp, "request_id": request_id}
    },
    {
        "name": "Format 5: No spaces in JSON",
        "aad": {"timestamp": int(timestamp), "request_id": request_id},
        "separators": (',', ':')
    },
    {
        "name": "Format 6: With spaces",
        "aad": {"timestamp": int(timestamp), "request_id": request_id},
        "separators": (', ', ': ')
    },
]

for i, test in enumerate(test_cases, 1):
    print(f"Test {i}: {test['name']}")
    
    aad_dict = test['aad']
    separators = test.get('separators', (',', ':'))
    
    # Create AAD JSON
    aad_json = json.dumps(aad_dict, separators=separators, sort_keys=True)
    aad_bytes = aad_json.encode('utf-8')
    
    print(f"  AAD JSON: {aad_json}")
    print(f"  AAD bytes: {len(aad_bytes)} bytes")
    
    try:
        aesgcm = AESGCM(secret_key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        decrypted_json = json.loads(decrypted_bytes.decode('utf-8'))
        
        print(f"  ✅ SUCCESS! Decryption worked!")
        print(f"  📦 Decrypted data:")
        print(json.dumps(decrypted_json, indent=4))
        print()
        break
    except Exception as e:
        print(f"  ❌ Failed: {str(e)[:100]}")
        print()

print(f"\n{'='*60}")
print(f"💡 Next Steps:")
print(f"{'='*60}")
print(f"1. Contact Viyonapay team to confirm:")
print(f"   - The webhook secret key they provided")
print(f"   - The exact AAD format they use")
print(f"   - Whether timestamp should be int or string")
print(f"2. Check if the secret key in your environment matches")
print(f"3. Verify the encryption algorithm (AES-256-GCM)")
