#!/usr/bin/env python3
"""
Debug script to decrypt the Viyonapay callback they sent
Uses AES-128-GCM with 16-byte hex key (as per Viyonapay webhook documentation)
"""
import base64
import json
from Crypto.Cipher import AES

# The encrypted data from Viyonapay team
encrypted_data = "Afp2eED73mw5VSM0Esa5e7CXzniYU62OKDjf5G5+3//G6xsxCboPHnC2D3XEiQ5lPp6PMVh7dCsrt8lvsNgbqB/Ar2ypfhMYibsKfu1DcM5+d1UNVpHgZxV4s2a9CYVMdsuxzeYWwi7c826G0cbMVlwNlEt9i88HhLb8BPEQKqEfRdIx+pPQncat6pd69hLureA7sfkG2XdthEfL94OcDi1Gb31IePg3OgstY8aGqk027JrxPU6yApZkyu8h0oz861e17f7AUIR6+21rslmRV10VoAvHIH4zZtUXzPU8FVa/PGumbk1LlM4Zfn4omzFClOGDv1zjccLIuH2bfH861+Cunmmq6DP4qU7xUgRDzi7aa5rZse/gPdzhsXeu+zMAaVjx7+P/l/kd5C11ApfABoKdBiyZWl4XbaZBmZajjQJ/YGE4KvHKbTRVfawsLx87pQO13sXIm3fPg5rTG4aEecmiE+1KtwT+JsAgzYIV5Rg7CsEL/HkBbwcthP+m3Lr8KBH10NtJQgFR06FmcqqCpO1q61aoJWh8fjT61TSs5tGfhpsj8V8="

# Headers from the callback
timestamp = "1774204672"
request_id = "5cfe4bd1-35c6-43b2-bdb8-aedd9d77a982"

# Your client secret key (from .env) - this is a HEX string, not base64!
# The webhook uses AES-128-GCM which requires 16 bytes (32 hex characters)
CLIENT_SECRET_KEY = "e8119e69a3d56ec5d117e7dff06467c3"

def canonical_json(obj):
    """Convert dict to canonical JSON string (sorted keys, no spaces)"""
    return json.dumps(obj, separators=(',', ':'), sort_keys=True).encode('utf-8')

def decrypt_webhook_response(encrypted_b64, secret_key, aad_dict):
    """
    Decrypt VIYONAPAY webhook response using AES-128-GCM
    Based on Viyonapay's official documentation
    """
    try:
        # Convert key from hex string to bytes (16 bytes for AES-128)
        if isinstance(secret_key, str):
            key16 = bytes.fromhex(secret_key)
        else:
            key16 = secret_key
        
        # Validate key length (must be 16 bytes for AES-128)
        if not isinstance(key16, (bytes, bytearray)) or len(key16) != 16:
            print(f"❌ Invalid key: must be 16 bytes, got {len(key16) if isinstance(key16, (bytes, bytearray)) else 'invalid type'}")
            return None
        
        # Decode base64 encrypted data
        raw = base64.b64decode(encrypted_b64)
        
        # Extract components (as per Viyonapay spec)
        nonce = raw[:12]  # First 12 bytes
        tag = raw[-16:]   # Last 16 bytes
        ciphertext = raw[12:-16]  # Middle part
        
        # Create AAD bytes (canonical JSON with sorted keys, no spaces)
        aad_bytes = canonical_json(aad_dict)
        
        print(f"🔐 Decryption Details:")
        print(f"  Nonce length: {len(nonce)}")
        print(f"  Tag length: {len(tag)}")
        print(f"  Ciphertext length: {len(ciphertext)}")
        print(f"  Key length: {len(key16)} bytes")
        print(f"  AAD: {aad_bytes.decode('utf-8')}")
        
        # Create AES-GCM cipher
        cipher = AES.new(key16, AES.MODE_GCM, nonce=nonce)
        cipher.update(aad_bytes)
        
        # Decrypt and verify
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        
        # Decode JSON
        decrypted_data = json.loads(plaintext.decode('utf-8'))
        
        return decrypted_data
        
    except Exception as e:
        print(f"❌ Decryption failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Create AAD
aad = {
    'timestamp': int(timestamp),
    'request_id': request_id
}

print(f"\n{'='*60}")
print(f"🔍 Decrypting Viyonapay Callback Data")
print(f"{'='*60}\n")

# Decrypt
decrypted = decrypt_webhook_response(encrypted_data, CLIENT_SECRET_KEY, aad)

if decrypted:
    print(f"\n✅ Decryption Successful!")
    print(f"\n📦 Decrypted Payload:")
    print(json.dumps(decrypted, indent=2))
    
    # Extract key fields from responseBody
    response_body = decrypted.get('responseBody', {})
    print(f"\n📋 Key Fields:")
    print(f"  Order ID: {response_body.get('orderId')}")
    print(f"  Transaction ID: {response_body.get('transactionId')}")
    print(f"  Payment Status: {response_body.get('paymentStatus')}")
    print(f"  Amount: {response_body.get('amount')}")
    print(f"  Paid Amount: {response_body.get('paidAmount')}")
    print(f"  Bank Ref: {response_body.get('bankRefId')}")
    print(f"  Payment Mode: {response_body.get('paymentMode')}")
    print(f"  Customer: {response_body.get('customerName')} ({response_body.get('customerEmail')})")
else:
    print(f"\n❌ Failed to decrypt payload")
