#!/usr/bin/env python3
"""
ViyonaPay Test with Enhanced Headers to Bypass Cloudflare
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

load_dotenv()

BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET', '')
API_KEY = os.getenv('VIYONAPAY_API_KEY', '')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

def load_private_key():
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

def load_public_key():
    with open(PUBLIC_KEY_PATH, 'rb') as f:
        return serialization.load_pem_public_key(f.read(), backend=default_backend())

def generate_session_key():
    return os.urandom(32)

def encrypt_session_key(session_key, public_key):
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
    plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
    aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
    aad_bytes = aad_json.encode('utf-8')
    nonce = os.urandom(12)
    aesgcm = AESGCM(session_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')

def sign_request(request_body, private_key):
    message = json.dumps(request_body, separators=(',', ':'), sort_keys=True).encode('utf-8')
    signature = private_key.sign(
        message,
        asym_padding.PSS(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            salt_length=asym_padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def test_with_enhanced_headers():
    """Test with browser-like headers to bypass Cloudflare"""
    print("="*80)
    print("  ViyonaPay API Test with Enhanced Headers")
    print("="*80)
    
    try:
        private_key = load_private_key()
        public_key = load_public_key()
        
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        data_to_encrypt = {
            "client_secret": CLIENT_SECRET,
            "scopes": ["PAYMENT_GATEWAY"]
        }
        
        encrypted_data = encrypt_data(data_to_encrypt, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key)
        
        # Enhanced headers to look like a real browser
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "content-type": "application/json",
            "origin": BASE_URL,
            "referer": f"{BASE_URL}/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        print("\n📤 Request URL:", f"{BASE_URL}/v1/auth/token")
        print("\n📤 Enhanced Headers:")
        for key, value in headers.items():
            if key.startswith('X-'):
                print(f"  {key}: {value[:50]}...")
            else:
                print(f"  {key}: {value}")
        
        # Create session with retry logic
        session = requests.Session()
        session.headers.update(headers)
        
        url = f"{BASE_URL}/v1/auth/token"
        
        print("\n⏳ Making request with enhanced headers...")
        response = session.post(url, json=request_body, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Request passed Cloudflare")
            print(f"📥 Response: {response.text[:500]}")
        elif response.status_code == 403:
            print("❌ Still blocked by Cloudflare")
            print("\n🔍 Cloudflare Ray ID:", response.headers.get('CF-RAY', 'Not found'))
            print("\n⚠️  ACTION REQUIRED:")
            print("   Contact ViyonaPay support to whitelist your server IP: 13.234.15.221")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"📥 Response: {response.text[:500]}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

def test_with_curl_simulation():
    """Test simulating curl request"""
    print("\n" + "="*80)
    print("  Testing with CURL-like Headers")
    print("="*80)
    
    try:
        private_key = load_private_key()
        public_key = load_public_key()
        
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        data_to_encrypt = {
            "client_secret": CLIENT_SECRET,
            "scopes": ["PAYMENT_GATEWAY"]
        }
        
        encrypted_data = encrypt_data(data_to_encrypt, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key)
        
        # Minimal curl-like headers
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        url = f"{BASE_URL}/v1/auth/token"
        
        print("\n⏳ Making request with curl-like headers...")
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
        elif response.status_code == 403:
            print("❌ Still blocked")
        
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("\n" + "█"*80)
    print("█  ViyonaPay Cloudflare Bypass Test".center(80) + "█")
    print("█"*80)
    
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📍 Server IP: Check with 'curl ifconfig.me'")
    print(f"🌐 Target: {BASE_URL}")
    
    if not all([CLIENT_ID, CLIENT_SECRET, API_KEY]):
        print("\n❌ Missing configuration!")
        return
    
    # Test 1: Enhanced browser headers
    test_with_enhanced_headers()
    
    # Test 2: Curl-like headers
    time.sleep(2)
    test_with_curl_simulation()
    
    print("\n" + "="*80)
    print("  Summary")
    print("="*80)
    print("\n⚠️  If both tests fail with 403:")
    print("   1. Your server IP is blocked by Cloudflare")
    print("   2. Contact ViyonaPay support to whitelist: 13.234.15.221")
    print("   3. Or test from your local machine first")
    print("\n💡 To test locally:")
    print("   1. Copy this script to your local machine")
    print("   2. Set up .env with ViyonaPay credentials")
    print("   3. Run: python test_viyonapay_with_headers.py")

if __name__ == "__main__":
    main()
