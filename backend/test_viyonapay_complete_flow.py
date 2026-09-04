#!/usr/bin/env python3
"""
ViyonaPay Complete Flow Test
1. Generate Access Token
2. Create Payment Intent with upiMasterMerchant
VPA: vfipl.188690284791@kvb
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

# Configuration
BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET')
API_KEY = os.getenv('VIYONAPAY_API_KEY')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

# Test parameters
VPA = "vfipl.188690284791@kvb"
PAYIN_TYPE = "upiMasterMerchant"

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_json(data, title=""):
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2))

def load_keys():
    """Load RSA keys"""
    print("\n📂 Loading RSA keys...")
    
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key_crypto = CryptoRSA.import_key(f.read())
    print(f"  ✓ Private key loaded")
    
    with open(PUBLIC_KEY_PATH, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(), backend=default_backend()
        )
    print(f"  ✓ Public key loaded")
    
    return private_key_crypto, public_key

def generate_session_key():
    """Generate random AES-256 session key"""
    return os.urandom(32)

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
    plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
    aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
    aad_bytes = aad_json.encode('utf-8')
    nonce = os.urandom(12)
    aesgcm = AESGCM(session_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')

def sign_request(request_body, private_key_crypto):
    """Sign request with RSA private key using PKCS#1 v1.5"""
    message = json.dumps(request_body, separators=(',', ':'), sort_keys=True).encode('utf-8')
    hash_obj = SHA256.new(message)
    signature = pkcs1_15.new(private_key_crypto).sign(hash_obj)
    return base64.b64encode(signature).decode('utf-8')

def decrypt_response(encrypted_b64, session_key, aad_dict):
    """Decrypt response data"""
    try:
        encrypted = base64.b64decode(encrypted_b64)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        aesgcm = AESGCM(session_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        return json.loads(plaintext.decode('utf-8'))
    except Exception as e:
        print(f"  ✗ Decryption error: {e}")
        return None

def get_access_token(private_key_crypto, public_key):
    """Step 1: Get access token"""
    print_header("STEP 1: Get Access Token")
    
    try:
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        aad = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp
        }
        
        inner_payload = {
            "client_secret": CLIENT_SECRET,
            "scopes": ["PAYMENT_GATEWAY"]
        }
        
        encrypted_data = encrypt_data(inner_payload, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key_crypto)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-SIGNATURE": signature,
            "X-API-TYPE": "PAYMENT_GATEWAY",
            "X-Request-ID": request_id
        }
        
        print(f"\n🌐 POST {BASE_URL}/v1/auth/token")
        
        url = f"{BASE_URL}/v1/auth/token"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"📥 Response: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            
            if 'encrypted_data' in response_json:
                decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                
                if decrypted and 'data' in decrypted:
                    access_token = decrypted['data']['access_token']
                    expires_in = decrypted['data']['expires_in']
                    
                    print(f"✅ Token obtained (expires in {expires_in}s)")
                    print(f"   Token: {access_token[:50]}...")
                    
                    return access_token
        
        print(f"❌ Failed: {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def create_payment_intent(access_token, private_key_crypto, public_key):
    """Step 2: Create payment intent"""
    print_header("STEP 2: Create Payment Intent")
    
    if not access_token:
        print("❌ No access token")
        return None
    
    try:
        session_key = generate_session_key()
        encrypted_session_key = encrypt_session_key(session_key, public_key)
        
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
            "payinType": PAYIN_TYPE,
            "note": "Test payment for ViyonaPay",
            "vpa": VPA
        }
        
        print("\n💳 Payment Details:")
        print(f"   Order ID: {order_id}")
        print(f"   Amount: ₹{payment_data['amount']}")
        print(f"   Payin Type: {PAYIN_TYPE}")
        print(f"   VPA: {VPA}")
        
        encrypted_data = encrypt_data(payment_data, session_key, aad)
        
        request_body = {
            "client_id": CLIENT_ID,
            "request_id": request_id,
            "timestamp": timestamp,
            "encrypted_data": encrypted_data,
            "encrypted_session_key": encrypted_session_key
        }
        
        signature = sign_request(request_body, private_key_crypto)
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": API_KEY,
            "Authorization": f"Bearer {access_token}",
            "X-SIGNATURE": signature,
            "X-Request-ID": request_id
        }
        
        print(f"\n🌐 POST {BASE_URL}/v1/payin/create_intent")
        
        url = f"{BASE_URL}/v1/payin/create_intent"
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        
        print(f"📥 Response: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 422:
            response_json = response.json()
            
            if response_json.get('response_status') == 0 or response.status_code == 422:
                # Error response
                if 'encrypted_data' in response_json:
                    decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                    if decrypted:
                        print(f"\n🔓 Decrypted error:")
                        print(json.dumps(decrypted, indent=2))
                        print(f"\n❌ Error: {decrypted.get('result', decrypted)}")
                    else:
                        print(f"❌ Could not decrypt error response")
                else:
                    print(f"❌ Error: {response_json.get('result')}")
                return None
            
            if 'encrypted_data' in response_json:
                decrypted = decrypt_response(response_json['encrypted_data'], session_key, aad)
                
                if decrypted:
                    print(f"\n🔓 Decrypted response:")
                    print(json.dumps(decrypted, indent=2))
                    
                    response_body = decrypted.get('response_body', decrypted.get('data', {}))
                    
                    if response_body:
                        print(f"\n✅ Payment Intent Created!")
                        print(f"   Payment Intent ID: {response_body.get('payment_intent_id')}")
                        print(f"   Order ID: {response_body.get('order_id')}")
                        print(f"   Amount: ₹{response_body.get('amount')}")
                        print(f"   Status: {response_body.get('status')}")
                        print(f"   Payment URL: {response_body.get('payment_url')}")
                        print(f"   Expires At: {response_body.get('expires_at')}")
                        
                        return response_body
        else:
            print(f"❌ Failed: {response.text[:200]}")
        
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ViyonaPay Complete Flow Test".center(78) + "█")
    print("█" + "  Token Generation + Payment Intent Creation".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration check
    print_header("Configuration")
    print(f"✓ Base URL: {BASE_URL}")
    print(f"✓ Client ID: {CLIENT_ID}")
    print(f"✓ API Key: {'***' + API_KEY[-4:] if API_KEY else '❌ NOT SET'}")
    print(f"✓ VPA: {VPA}")
    print(f"✓ Payin Type: {PAYIN_TYPE}")
    
    if not all([CLIENT_ID, CLIENT_SECRET, API_KEY]):
        print("\n❌ Missing configuration!")
        return
    
    try:
        # Load keys
        private_key_crypto, public_key = load_keys()
        
        # Step 1: Get token
        access_token = get_access_token(private_key_crypto, public_key)
        
        if not access_token:
            print("\n❌ Cannot proceed without token")
            return
        
        # Wait a moment
        print("\n⏳ Waiting 2 seconds...")
        time.sleep(2)
        
        # Step 2: Create payment intent
        payment_intent = create_payment_intent(access_token, private_key_crypto, public_key)
        
        # Summary
        print_header("Test Summary")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if payment_intent:
            print("\n✅ Complete flow successful!")
            print(f"\n📋 Results:")
            print(f"   ✓ Access token obtained")
            print(f"   ✓ Payment intent created")
            print(f"   ✓ Order ID: {payment_intent.get('order_id')}")
            print(f"\n🔗 Payment URL:")
            print(f"   {payment_intent.get('payment_url')}")
            print(f"\n💡 Next Steps:")
            print(f"   1. Open the payment URL in browser")
            print(f"   2. Complete the UPI payment")
            print(f"   3. Check webhook for status updates")
        else:
            print("\n❌ Payment intent creation failed")
        
    except FileNotFoundError as e:
        print(f"\n❌ Key file not found: {e}")
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
