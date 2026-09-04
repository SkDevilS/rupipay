#!/usr/bin/env python3
"""
Simple standalone test script for ViyonaPay Payin API
Tests with UpiMasterMerchant and VPA: vfipl.188690284791@kvb
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

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET', '')
API_KEY = os.getenv('VIYONAPAY_API_KEY', '')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

# Test parameters
VPA = "vfipl.188690284791@kvb"
PAYIN_TYPE = "upiMasterMerchant"

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_json(data, title=""):
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2))

def load_private_key():
    """Load client private key"""
    try:
        with open(PRIVATE_KEY_PATH, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    except Exception as e:
        print(f"❌ Error loading private key: {e}")
        return None

def load_public_key():
    """Load server public key"""
    try:
        with open(PUBLIC_KEY_PATH, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    except Exception as e:
        print(f"❌ Error loading public key: {e}")
        return None

def generate_session_key():
    """Generate random AES session key"""
    return os.urandom(32)  # 256-bit key

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
    try:
        # Convert data to JSON
        plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
        
        # Convert AAD to canonical JSON
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Encrypt with AES-GCM
        aesgcm = AESGCM(session_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
        
        # Combine: nonce + ciphertext (tag is included in ciphertext)
        encrypted = nonce + ciphertext
        
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        print(f"❌ Encryption error: {e}")
        raise

def sign_request(request_body, private_key):
    """Sign request with private key"""
    try:
        # Convert to canonical JSON
        message = json.dumps(request_body, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        # Sign with RSA-PSS
        signature = private_key.sign(
            message,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"❌ Signing error: {e}")
        raise

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
        print(f"❌ Decryption error: {e}")
        return None

def get_access_token():
    """Step 1: Get access token"""
    print_header("STEP 1: Get Access Token")
    
    try:
        # Load keys
        private_key = load_private_key()
        public_key = load_public_key()
        
        if not private_key or not public_key:
            return None
        
        # Generate session key
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        # Prepare request
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
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        print("\n📤 Request URL:", f"{BASE_URL}/v1/auth/token")
        print_json(headers, "📤 Request Headers")
        
        # Make API call
        url = f"{BASE_URL}/v1/auth/token"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_json = response.json()
            print_json(response_json, "📥 Raw Response")
            
            # Decrypt response
            if 'encrypted_data' in response_json:
                decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                if decrypted:
                    print_json(decrypted, "🔓 Decrypted Response")
                    access_token = decrypted.get('data', {}).get('access_token')
                    if access_token:
                        print(f"\n✅ Access Token: {access_token[:50]}...")
                        return access_token
        else:
            print(f"❌ Error: {response.text}")
        
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_payment_intent(access_token):
    """Step 2: Create payment intent"""
    print_header("STEP 2: Create Payment Intent")
    
    if not access_token:
        print("❌ No access token available")
        return None
    
    try:
        # Load keys
        private_key = load_private_key()
        public_key = load_public_key()
        
        if not private_key or not public_key:
            return None
        
        # Generate session key
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        # Prepare request
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        order_id = f"TEST_VYN_{int(time.time())}"
        
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        payment_data = {
            "orderId": order_id,
            "amount": "100.00",
            "currency": "INR",
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "9999999999",
            "payinType": [PAYIN_TYPE],
            "vpa": VPA,
            "note": "Test payment for ViyonaPay"
        }
        
        print("\n💳 Payment Details:")
        print_json(payment_data)
        
        encrypted_data = encrypt_data(payment_data, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": API_KEY,
            "Authorization": f"Bearer {access_token}",
            "X-SIGNATURE": signature,
            "X-Request-ID": request_id
        }
        
        print("\n📤 Request URL:", f"{BASE_URL}/v1/payin/create_intent")
        
        # Make API call
        url = f"{BASE_URL}/v1/payin/create_intent"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            print_json(response_json, "📥 Raw Response")
            
            # Decrypt response
            if 'encrypted_data' in response_json:
                decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                if decrypted:
                    print_json(decrypted, "🔓 Decrypted Response")
                    
                    response_body = decrypted.get('response_body', {})
                    print("\n✅ Payment Intent Created!")
                    print(f"  - Payment Intent ID: {response_body.get('payment_intent_id')}")
                    print(f"  - Order ID: {response_body.get('order_id')}")
                    print(f"  - Amount: {response_body.get('amount')} {response_body.get('currency')}")
                    print(f"  - Status: {response_body.get('status')}")
                    print(f"  - Payment URL: {response_body.get('payment_url')}")
                    
                    return response_body.get('order_id')
        else:
            print(f"❌ Error: {response.text}")
        
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_payment_status(order_id):
    """Step 3: Check payment status"""
    print_header("STEP 3: Check Payment Status")
    
    if not order_id:
        print("❌ No order ID available")
        return
    
    try:
        # Get fresh token
        access_token = get_access_token()
        if not access_token:
            return
        
        # Load keys
        private_key = load_private_key()
        public_key = load_public_key()
        
        if not private_key or not public_key:
            return
        
        # Generate session key
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        # Prepare request
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        status_data = {
            "order_id": order_id
        }
        
        encrypted_data = encrypt_data(status_data, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": API_KEY,
            "Authorization": f"Bearer {access_token}",
            "X-SIGNATURE": signature,
            "X-Request-ID": request_id
        }
        
        print(f"\n🔍 Checking status for Order ID: {order_id}")
        
        # Make API call
        url = f"{BASE_URL}/v1/payin/status_check"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            print_json(response_json, "📥 Raw Response")
            
            # Decrypt response
            if 'encrypted_data' in response_json:
                decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                if decrypted:
                    print_json(decrypted, "🔓 Decrypted Response")
                    
                    result = decrypted.get('result', {})
                    print("\n✅ Payment Status:")
                    print(f"  - Status: {result.get('status')}")
                    print(f"  - Transaction ID: {result.get('transaction_id')}")
                    print(f"  - Payment Mode: {result.get('payment_mode')}")
                    print(f"  - Amount: {result.get('amount')}")
                    print(f"  - Bank Reference: {result.get('bank_reference_number')}")
        else:
            print(f"❌ Error: {response.text}")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("\n" + "█"*80)
    print("█  VIYONAPAY PAYIN API TEST - Simple Version".center(80) + "█")
    print("█"*80)
    
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check config
    print_header("Configuration")
    print(f"✓ Base URL: {BASE_URL}")
    print(f"✓ Client ID: {CLIENT_ID if CLIENT_ID else '❌ NOT SET'}")
    print(f"✓ Client Secret: {'***' if CLIENT_SECRET else '❌ NOT SET'}")
    print(f"✓ API Key: {'***' if API_KEY else '❌ NOT SET'}")
    print(f"✓ VPA: {VPA}")
    print(f"✓ Payin Type: {PAYIN_TYPE}")
    
    if not all([CLIENT_ID, CLIENT_SECRET, API_KEY]):
        print("\n❌ Missing configuration! Please set in .env file:")
        print("  - VIYONAPAY_CLIENT_ID")
        print("  - VIYONAPAY_CLIENT_SECRET")
        print("  - VIYONAPAY_API_KEY")
        return
    
    # Run tests
    access_token = get_access_token()
    
    if access_token:
        order_id = create_payment_intent(access_token)
        
        if order_id:
            print("\n⏳ Waiting 3 seconds before status check...")
            time.sleep(3)
            check_payment_status(order_id)
    
    print_header("Test Complete")
    print(f"⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
