#!/usr/bin/env python3
"""
ViyonaPay Encrypted Token API Test
Tests ONLY the token generation endpoint
Based on official API documentation
"""

import os
import sys
import json
import time
import uuid
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA as CryptoRSA

# Load environment
load_dotenv()

# Configuration from config
BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_json(data, title=""):
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2))

def load_keys():
    """Load RSA private and public keys"""
    print("\n📂 Loading RSA keys...")
    
    # Load private key for signing (using PyCryptodome)
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key_crypto = CryptoRSA.import_key(f.read())
    print(f"  ✓ Private key loaded from: {PRIVATE_KEY_PATH}")
    
    # Load public key for encryption (using cryptography)
    with open(PUBLIC_KEY_PATH, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(), backend=default_backend()
        )
    print(f"  ✓ Public key loaded from: {PUBLIC_KEY_PATH}")
    
    return private_key_crypto, public_key

def generate_session_key():
    """Generate random AES-256 session key"""
    return os.urandom(32)  # 256 bits

def encrypt_session_key(session_key, public_key):
    """Encrypt session key with RSA-OAEP"""
    encrypted = public_key.encrypt(
        session_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode('utf-8')

def encrypt_data(data_dict, session_key, aad_dict):
    """Encrypt data with AES-GCM"""
    # Convert data to JSON
    plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
    
    # Convert AAD to canonical JSON (sorted keys)
    aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
    aad_bytes = aad_json.encode('utf-8')
    
    # Generate random nonce (12 bytes for GCM)
    nonce = os.urandom(12)
    
    # Encrypt with AES-GCM
    aesgcm = AESGCM(session_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    
    # Combine: nonce + ciphertext (tag is included in ciphertext)
    encrypted = nonce + ciphertext
    
    return base64.b64encode(encrypted).decode('utf-8')

def sign_request(request_body, private_key_crypto):
    """Sign request with RSA private key using PKCS#1 v1.5"""
    # Convert to canonical JSON (sorted keys)
    message = json.dumps(request_body, separators=(',', ':'), sort_keys=True).encode('utf-8')
    
    # Create SHA-256 hash
    hash_obj = SHA256.new(message)
    
    # Sign with PKCS#1 v1.5
    signature = pkcs1_15.new(private_key_crypto).sign(hash_obj)
    
    return base64.b64encode(signature).decode('utf-8')

def decrypt_response(encrypted_b64, session_key, aad_dict):
    """Decrypt response data"""
    try:
        # Decode base64
        encrypted = base64.b64decode(encrypted_b64)
        
        # Extract nonce and ciphertext
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        
        # Convert AAD to canonical JSON
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Decrypt
        aesgcm = AESGCM(session_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        
        return json.loads(plaintext.decode('utf-8'))
    except Exception as e:
        print(f"  ✗ Decryption error: {e}")
        return None

def test_token_generation():
    """Test ViyonaPay Token Generation API"""
    print_header("ViyonaPay Encrypted Token API Test")
    
    print(f"\n📋 Configuration:")
    print(f"  • Base URL: {BASE_URL}")
    print(f"  • Endpoint: /v1/auth/token")
    print(f"  • Client ID: {CLIENT_ID}")
    print(f"  • Client Secret: {'***' + CLIENT_SECRET[-4:] if CLIENT_SECRET else '❌ NOT SET'}")
    
    if not all([CLIENT_ID, CLIENT_SECRET]):
        print("\n❌ ERROR: Missing required configuration!")
        print("Set in .env file:")
        print("  - VIYONAPAY_CLIENT_ID")
        print("  - VIYONAPAY_CLIENT_SECRET")
        return None
    
    try:
        # Load keys
        private_key_crypto, public_key = load_keys()
        
        # Generate session key
        print("\n🔑 Generating session key...")
        session_key = generate_session_key()
        print(f"  ✓ Generated 256-bit AES session key")
        
        # Encrypt session key
        print("\n🔐 Encrypting session key with RSA-OAEP...")
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        print(f"  ✓ Encrypted session key (Base64): {encrypted_session_key[:60]}...")
        
        # Prepare request data
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        print(f"\n📝 Preparing request...")
        print(f"  • Request ID: {request_id}")
        print(f"  • Timestamp: {timestamp} ({datetime.fromtimestamp(timestamp)})")
        
        # Prepare AAD (Additional Authenticated Data)
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        print_json(aad, "  • AAD")
        
        # Prepare inner payload
        inner_payload = {
            "client_secret": CLIENT_SECRET,
            "scopes": ["PAYMENT_GATEWAY"]
        }
        print(f"\n  • Inner Payload:")
        print(f"    - client_secret: ***{CLIENT_SECRET[-4:]}")
        print(f"    - scopes: {inner_payload['scopes']}")
        
        # Encrypt inner payload
        print("\n🔐 Encrypting inner payload with AES-GCM...")
        encrypted_data = encrypt_data(inner_payload, session_key, aad)
        print(f"  ✓ Encrypted data (Base64): {encrypted_data[:60]}...")
        
        # Build request body
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        # Sign request
        print("\n✍️  Signing request with RSA private key (PKCS#1 v1.5)...")
        signature = sign_request(request_body, private_key_crypto)
        print(f"  ✓ Signature (Base64): {signature[:60]}...")
        
        # Prepare headers
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        print("\n📤 Request Headers:")
        for key, value in headers.items():
            if key == "X-SIGNATURE":
                print(f"  • {key}: {value[:40]}...")
            else:
                print(f"  • {key}: {value}")
        
        # Make API call
        url = f"{BASE_URL}/v1/auth/token"
        print(f"\n🌐 Sending POST request to: {url}")
        print("⏳ Waiting for response...")
        
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status Code: {response.status_code}")
        
        # Check for Cloudflare block
        if response.status_code == 403 and 'cloudflare' in response.text.lower():
            print("\n❌ BLOCKED BY CLOUDFLARE")
            print(f"  • Your IP is blocked by Cloudflare protection")
            print(f"  • Cloudflare Ray ID: {response.headers.get('CF-RAY', 'Not found')}")
            print(f"\n⚠️  ACTION REQUIRED:")
            print(f"  Contact ViyonaPay support to whitelist your server IP")
            return None
        
        # Handle success response
        if response.status_code == 200:
            print("✅ Request successful!")
            
            try:
                response_json = response.json()
                print_json(response_json, "\n📥 Raw Response")
                
                # Check response status
                if response_json.get('response_status') == 0:
                    # Encrypted error response
                    if 'encrypted_data' in response_json:
                        decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                        if decrypted:
                            print_json(decrypted, "\n🔓 Decrypted Error Response")
                            print(f"\n❌ Error: {decrypted.get('result')}")
                    else:
                        print(f"\n❌ Error: {response_json.get('result')}")
                    return None
                
                # Decrypt success response
                if 'encrypted_data' in response_json:
                    print("\n🔓 Decrypting response...")
                    decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                    
                    if decrypted:
                        print_json(decrypted, "✅ Decrypted Response")
                        
                        # Extract token
                        if 'data' in decrypted and 'access_token' in decrypted['data']:
                            access_token = decrypted['data']['access_token']
                            token_type = decrypted['data']['token_type']
                            expires_in = decrypted['data']['expires_in']
                            
                            print(f"\n🎉 SUCCESS! Token Generated")
                            print(f"  • Token Type: {token_type}")
                            print(f"  • Expires In: {expires_in} seconds ({expires_in//60} minutes)")
                            print(f"  • Access Token: {access_token[:50]}...")
                            
                            return access_token
                        else:
                            print("\n❌ No access token in response")
                    else:
                        print("\n❌ Failed to decrypt response")
                else:
                    print("\n❌ No encrypted_data in response")
            
            except json.JSONDecodeError:
                print(f"\n❌ Invalid JSON response: {response.text[:200]}")
        
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"\n📥 Response: {response.text[:500]}")
        
        return None
        
    except FileNotFoundError as e:
        print(f"\n❌ Key file not found: {e}")
        print("Make sure the key files exist:")
        print(f"  - {PRIVATE_KEY_PATH}")
        print(f"  - {PUBLIC_KEY_PATH}")
        return None
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ViyonaPay Encrypted Token API - Test Script".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run test
    access_token = test_token_generation()
    
    # Summary
    print_header("Test Summary")
    print(f"⏰ Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if access_token:
        print("\n✅ Token generation successful!")
        print(f"\n💡 Next Steps:")
        print(f"  1. Use this token for payment intent creation")
        print(f"  2. Token is valid for 30 minutes")
        print(f"  3. Include in Authorization header: Bearer {access_token[:30]}...")
    else:
        print("\n❌ Token generation failed")
        print(f"\n💡 Troubleshooting:")
        print(f"  1. Check if credentials are correct in .env")
        print(f"  2. Verify RSA key files exist and are valid")
        print(f"  3. If Cloudflare blocked: Contact ViyonaPay support")
        print(f"  4. Check timestamp is within ±5 minutes of server time")

if __name__ == "__main__":
    main()
