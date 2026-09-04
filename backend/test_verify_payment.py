"""
Test script for payment verification API
"""
import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Your merchant credentials (get from dashboard)
AUTH_KEY = 'your_authorization_key'
MODULE_SECRET = 'your_module_secret'
AES_KEY = bytes.fromhex('your_aes_key_hex')  # 32 bytes
AES_IV = bytes.fromhex('your_aes_iv_hex')    # 16 bytes
MERCHANT_TOKEN = 'your_jwt_token'  # Get from login

# API endpoint
API_URL = 'http://localhost:5000/api/payin/verify-payment'

def encrypt_aes(data, key, iv):
    """Encrypt data using AES-256-CBC"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    json_data = json.dumps(data)
    padded_data = pad(json_data.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_aes(encrypted_data, key, iv):
    """Decrypt data using AES-256-CBC"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_bytes = base64.b64decode(encrypted_data)
    decrypted = cipher.decrypt(encrypted_bytes)
    unpadded = unpad(decrypted, AES.block_size)
    return json.loads(unpadded.decode('utf-8'))

def verify_payment(order_id=None, txn_id=None):
    """Verify payment status"""
    try:
        # Prepare request data
        request_data = {}
        if order_id:
            request_data['order_id'] = order_id
        if txn_id:
            request_data['txn_id'] = txn_id
        
        print('Request Data:', json.dumps(request_data, indent=2))
        
        # Encrypt the payload
        encrypted_data = encrypt_aes(request_data, AES_KEY, AES_IV)
        print(f'\nEncrypted Data: {encrypted_data[:50]}...')
        
        # Make API request
        response = requests.post(
            API_URL,
            json={'data': encrypted_data},
            headers={
                'Authorization': f'Bearer {MERCHANT_TOKEN}',
                'Content-Type': 'application/json'
            }
        )
        
        print(f'\n✓ API Response Status: {response.status_code}')
        print(f'✓ API Response: {json.dumps(response.json(), indent=2)}')
        
        # Decrypt response
        if response.json().get('success') and response.json().get('data'):
            decrypted_response = decrypt_aes(response.json()['data'], AES_KEY, AES_IV)
            print('\n✓ Decrypted Response:', json.dumps(decrypted_response, indent=2))
            print(f'\n✓ Transaction ID: {decrypted_response.get("txn_id")}')
            print(f'✓ Order ID: {decrypted_response.get("order_id")}')
            print(f'✓ Amount: ₹{decrypted_response.get("amount")}')
            print(f'✓ Status: {decrypted_response.get("status")}')
            print(f'✓ Payment Gateway: {decrypted_response.get("pg_partner")}')
            print(f'✓ UTR: {decrypted_response.get("utr")}')
            print(f'✓ Payment Mode: {decrypted_response.get("payment_mode")}')
            print(f'✓ Created At: {decrypted_response.get("created_at")}')
            print(f'✓ Completed At: {decrypted_response.get("completed_at")}')
        
    except Exception as e:
        print(f'✗ Error: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: python test_verify_payment.py <order_id>')
        print('   or: python test_verify_payment.py --txn <txn_id>')
        sys.exit(1)
    
    if sys.argv[1] == '--txn':
        verify_payment(txn_id=sys.argv[2])
    else:
        verify_payment(order_id=sys.argv[1])
