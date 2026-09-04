#!/usr/bin/env python3
"""
ViyonaPay Payin API Test - Following Exact Documentation Steps
Step 1: Get JWT Access Token
Step 2: Create Payment Intent with upiMasterMerchant
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

# Load environment
load_dotenv()

# Configuration from config
BASE_URL = os.getenv('VIYONAPAY_BASE_URL', 'https://core.viyonapay.com')
CLIENT_ID = os.getenv('VIYONAPAY_CLIENT_ID')
CLIENT_SECRET = os.getenv('VIYONAPAY_CLIENT_SECRET')
API_KEY = os.getenv('VIYONAPAY_API_KEY')
PRIVATE_KEY_PATH = os.getenv('VIYONAPAY_CLIENT_PRIVATE_KEY_PATH', 'keys/viyonapay_client_private.pem')
PUBLIC_KEY_PATH = os.getenv('VIYONAPAY_SERVER_PUBLIC_KEY_PATH', 'keys/viyonapay_server_public.pem')

# Test parameters
VPA = "vfipl.188690284791@kvb"
PAYIN_TYPE = "upiMasterMerchant"

def print_step(step_num, title):
    """Print step header"""
    print("\n" + "="*80)
    print(f"STEP {step_num}: {title}")
    print("="*80)

def print_substep(substep, description):
    """Print substep"""
    print(f"\n  {substep}. {description}")

# ============================================================================
# STEP 1: GET JWT ACCESS TOKEN
# ============================================================================

def step1_load_keys():
    """Step 1.1: Load RSA keys"""
    print_substep("1.1", "Loading RSA keys")
    
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )
    print(f"     ✓ Loaded private key from: {PRIVATE_KEY_PATH}")
    
    with open(PUBLIC_KEY_PATH, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(), backend=default_backend()
        )
    print(f"     ✓ Loaded public key from: {PUBLIC_KEY_PATH}")
    
    return private_key, public_key

def step2_generate_session_key():
    """Step 1.2: Generate random AES-256 session key"""
    print_substep("1.2", "Generate random AES-256 session key")
    session_key = os.urandom(32)  # 256 bits
    print(f"     ✓ Generated 256-bit session key: {session_key.hex()[:32]}...")
    return session_key

def step3_prepare_inner_payload():
    """Step 1.3: Prepare the inner payload"""
    print_substep("1.3", "Prepare the inner payload")
    payload = {
        "client_secret": CLIENT_SECRET,
        "scopes": ["PAYMENT_GATEWAY"]
    }
    print(f"     ✓ Inner payload:")
    print(f"       {json.dumps(payload, indent=8)}")
    return payload

def step4_prepare_aad(client_id, request_id, timestamp):
    """Step 1.4: Prepare the AAD (Additional Authenticated Data)"""
    print_substep("1.4", "Prepare the AAD (Additional Authenticated Data)")
    aad = {
        "client_id": client_id,
        "request_id": request_id,
        "timestamp": timestamp
    }
    print(f"     ✓ AAD:")
    print(f"       {json.dumps(aad, indent=8)}")
    return aad

def step5_encrypt_payload(payload, session_key, aad):
    """Step 1.5: Encrypt the inner payload using AES-GCM"""
    print_substep("1.5", "Encrypt the inner payload using AES-GCM with session key + AAD")
    
    # Convert to JSON
    plaintext = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    # Convert AAD to canonical JSON
    aad_json = json.dumps(aad, separators=(',', ':'), sort_keys=True)
    aad_bytes = aad_json.encode('utf-8')
    
    # Generate nonce
    nonce = os.urandom(12)
    
    # Encrypt with AES-GCM
    aesgcm = AESGCM(session_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    
    # Combine: nonce + ciphertext
    encrypted = nonce + ciphertext
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    
    print(f"     ✓ Encrypted data (Base64): {encrypted_b64[:60]}...")
    return encrypted_b64

def step6_encrypt_session_key(session_key, public_key):
    """Step 1.6: Encrypt the AES session key using RSA-OAEP"""
    print_substep("1.6", "Encrypt the AES session key using server's RSA public key (RSA-OAEP)")
    
    encrypted = public_key.encrypt(
        session_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    
    print(f"     ✓ Encrypted session key (Base64): {encrypted_b64[:60]}...")
    return encrypted_b64

def step7_build_request_body(client_id, request_id, timestamp, encrypted_data, encrypted_session_key):
    """Step 1.7: Build the request body"""
    print_substep("1.7", "Build the request body")
    
    request_body = {
        "client_id": client_id,
        "request_id": request_id,
        "timestamp": timestamp,
        "encrypted_data": encrypted_data,
        "encrypted_session_key": encrypted_session_key
    }
    
    print(f"     ✓ Request body structure:")
    print(f"       - client_id: {client_id}")
    print(f"       - request_id: {request_id}")
    print(f"       - timestamp: {timestamp}")
    print(f"       - encrypted_data: {encrypted_data[:40]}...")
    print(f"       - encrypted_session_key: {encrypted_session_key[:40]}...")
    
    return request_body

def step8_sign_request(request_body, private_key):
    """Step 1.8: Sign the entire request body with RSA private key"""
    print_substep("1.8", "Sign the entire request body with RSA private key")
    
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
    
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    print(f"     ✓ Signature (Base64): {signature_b64[:60]}...")
    
    return signature_b64

def step9_send_token_request(request_body, signature, request_id):
    """Step 1.9: Send the request with headers"""
    print_substep("1.9", "Send the request with headers")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-TYPE": "PAYMENT_GATEWAY",
        "X-Request-ID": request_id,
        "X-SIGNATURE": signature
    }
    
    print(f"     ✓ Headers:")
    for key, value in headers.items():
        if key == "X-SIGNATURE":
            print(f"       {key}: {value[:40]}...")
        else:
            print(f"       {key}: {value}")
    
    url = f"{BASE_URL}/v1/auth/token"
    print(f"\n     ✓ Sending POST request to: {url}")
    
    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        print(f"     ✓ Response Status Code: {response.status_code}")
        
        return response
    except Exception as e:
        print(f"     ✗ Request failed: {e}")
        return None

def step10_decrypt_response(response, session_key, aad):
    """Step 1.10: Decrypt the response"""
    print_substep("1.10", "Decrypt the response encrypted_data using AES session key")
    
    try:
        response_json = response.json()
        
        if response.status_code != 200:
            print(f"     ✗ Error response: {response.text}")
            return None
        
        if 'encrypted_data' not in response_json:
            print(f"     ✗ No encrypted_data in response")
            return None
        
        encrypted_b64 = response_json['encrypted_data']
        encrypted = base64.b64decode(encrypted_b64)
        
        # Extract nonce and ciphertext
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        
        # Convert AAD to canonical JSON
        aad_json = json.dumps(aad, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Decrypt
        aesgcm = AESGCM(session_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        
        decrypted = json.loads(plaintext.decode('utf-8'))
        print(f"     ✓ Decrypted response:")
        print(f"       {json.dumps(decrypted, indent=8)}")
        
        return decrypted
        
    except Exception as e:
        print(f"     ✗ Decryption failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_jwt_token():
    """Execute Step 1: Get JWT Access Token"""
    print_step(1, "Get JWT Access Token")
    print(f"     Endpoint: POST {BASE_URL}/v1/auth/token")
    
    # Execute all substeps
    private_key, public_key = step1_load_keys()
    session_key = step2_generate_session_key()
    
    request_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    inner_payload = step3_prepare_inner_payload()
    aad = step4_prepare_aad(CLIENT_ID, request_id, timestamp)
    encrypted_data = step5_encrypt_payload(inner_payload, session_key, aad)
    encrypted_session_key = step6_encrypt_session_key(session_key, public_key)
    request_body = step7_build_request_body(CLIENT_ID, request_id, timestamp, encrypted_data, encrypted_session_key)
    signature = step8_sign_request(request_body, private_key)
    response = step9_send_token_request(request_body, signature, request_id)
    
    if response and response.status_code == 200:
        decrypted = step10_decrypt_response(response, session_key, aad)
        if decrypted and 'data' in decrypted:
            access_token = decrypted['data'].get('access_token')
            expires_in = decrypted['data'].get('expires_in')
            
            print(f"\n     ✅ SUCCESS! Access token obtained")
            print(f"     ✓ Token: {access_token[:50]}...")
            print(f"     ✓ Expires in: {expires_in} seconds ({expires_in//60} minutes)")
            
            return access_token
    
    print(f"\n     ✗ Failed to get access token")
    return None

# ============================================================================
# STEP 2: CREATE PAYMENT INTENT
# ============================================================================

def step2_1_generate_fresh_session_key():
    """Step 2.1: Generate a fresh AES-256 session key"""
    print_substep("2.1", "Generate a fresh AES-256 session key (do not reuse from Step 1)")
    session_key = os.urandom(32)
    print(f"     ✓ Generated new 256-bit session key: {session_key.hex()[:32]}...")
    return session_key

def step2_2_prepare_payment_payload(order_id):
    """Step 2.2: Prepare the inner payload"""
    print_substep("2.2", "Prepare the inner payload")
    
    payload = {
        "orderId": order_id,
        "amount": "500.00",
        "currency": "INR",
        "name": "Test Customer",
        "email": "customer@example.com",
        "phone": "9999999999",
        "payinType": [PAYIN_TYPE],
        "note": "Test payment for ViyonaPay integration",
        "vpa": VPA
    }
    
    print(f"     ✓ Payment payload:")
    print(f"       {json.dumps(payload, indent=8)}")
    return payload

def step2_9_send_payment_request(request_body, signature, request_id, access_token):
    """Step 2.9: Send the request with headers"""
    print_substep("2.9", "Send the request with headers")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-KEY": API_KEY,
        "Authorization": f"Bearer {access_token}",
        "X-Request-Id": request_id,
        "X-SIGNATURE": signature
    }
    
    print(f"     ✓ Headers:")
    for key, value in headers.items():
        if key in ["X-SIGNATURE", "Authorization"]:
            print(f"       {key}: {value[:40]}...")
        elif key == "X-API-KEY":
            print(f"       {key}: {value[:20]}...")
        else:
            print(f"       {key}: {value}")
    
    url = f"{BASE_URL}/v1/payin/create_intent"
    print(f"\n     ✓ Sending POST request to: {url}")
    
    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        print(f"     ✓ Response Status Code: {response.status_code}")
        
        return response
    except Exception as e:
        print(f"     ✗ Request failed: {e}")
        return None

def create_payment_intent(access_token):
    """Execute Step 2: Create Payment Intent"""
    print_step(2, "Create Payment Intent")
    print(f"     Endpoint: POST {BASE_URL}/v1/payin/create_intent")
    
    # Load keys
    private_key, public_key = step1_load_keys()
    
    # Generate fresh session key
    session_key = step2_1_generate_fresh_session_key()
    
    # Generate unique order ID
    order_id = f"TEST_VYN_{int(time.time())}"
    
    # Prepare request
    request_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    payment_payload = step2_2_prepare_payment_payload(order_id)
    aad = step4_prepare_aad(CLIENT_ID, request_id, timestamp)
    encrypted_data = step5_encrypt_payload(payment_payload, session_key, aad)
    encrypted_session_key = step6_encrypt_session_key(session_key, public_key)
    request_body = step7_build_request_body(CLIENT_ID, request_id, timestamp, encrypted_data, encrypted_session_key)
    signature = step8_sign_request(request_body, private_key)
    response = step2_9_send_payment_request(request_body, signature, request_id, access_token)
    
    if response and response.status_code == 200:
        decrypted = step10_decrypt_response(response, session_key, aad)
        if decrypted and 'response_body' in decrypted:
            response_body = decrypted['response_body']
            
            print(f"\n     ✅ SUCCESS! Payment intent created")
            print(f"     ✓ Payment Intent ID: {response_body.get('payment_intent_id')}")
            print(f"     ✓ Order ID: {response_body.get('order_id')}")
            print(f"     ✓ Amount: {response_body.get('amount')} {response_body.get('currency')}")
            print(f"     ✓ Status: {response_body.get('status')}")
            print(f"     ✓ Payment URL: {response_body.get('payment_url')}")
            print(f"     ✓ Expires At: {response_body.get('expires_at')}")
            
            return response_body
    
    print(f"\n     ✗ Failed to create payment intent")
    return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ViyonaPay Payin API - Step-by-Step Test".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration check
    print("\n" + "="*80)
    print("CONFIGURATION")
    print("="*80)
    print(f"✓ Base URL: {BASE_URL}")
    print(f"✓ Client ID: {CLIENT_ID}")
    print(f"✓ Client Secret: {'***' + CLIENT_SECRET[-4:] if CLIENT_SECRET else '❌ NOT SET'}")
    print(f"✓ API Key: {'***' + API_KEY[-4:] if API_KEY else '❌ NOT SET'}")
    print(f"✓ VPA: {VPA}")
    print(f"✓ Payin Type: {PAYIN_TYPE}")
    
    if not all([CLIENT_ID, CLIENT_SECRET, API_KEY]):
        print("\n❌ ERROR: Missing required configuration!")
        print("Please set in .env file:")
        print("  - VIYONAPAY_CLIENT_ID")
        print("  - VIYONAPAY_CLIENT_SECRET")
        print("  - VIYONAPAY_API_KEY")
        return
    
    # Execute Step 1
    access_token = get_jwt_token()
    
    if not access_token:
        print("\n❌ Cannot proceed without access token")
        print("\n⚠️  If you see Cloudflare 403 error:")
        print("   Contact ViyonaPay support to whitelist your server IP")
        return
    
    # Wait a moment
    print("\n⏳ Waiting 2 seconds before creating payment intent...")
    time.sleep(2)
    
    # Execute Step 2
    payment_intent = create_payment_intent(access_token)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"⏰ Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if access_token and payment_intent:
        print("\n✅ All steps completed successfully!")
        print(f"\n📋 Results:")
        print(f"  - Access Token: Obtained (valid for 30 minutes)")
        print(f"  - Payment Intent: Created")
        print(f"  - Order ID: {payment_intent.get('order_id')}")
        print(f"  - Payment URL: {payment_intent.get('payment_url')}")
        print(f"\n💡 Next Steps:")
        print(f"  1. Use the payment URL to complete the payment")
        print(f"  2. Monitor webhook callbacks for status updates")
        print(f"  3. Use status check API to verify payment status")
    else:
        print("\n⚠️  Test incomplete - check errors above")

if __name__ == "__main__":
    main()
