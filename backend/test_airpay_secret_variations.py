#!/usr/bin/env python3
"""
Test different possible secret values for Airpay privatekey
"""

import hashlib
import requests
import json
from airpay_service import airpay_service

def test_secret_variation(secret_value, secret_name):
    """Test verify API with a specific secret value"""
    
    print(f"\n{'='*100}")
    print(f"TESTING: {secret_name}")
    print(f"{'='*100}")
    print(f"Secret Value: {secret_value}")
    
    # Generate privatekey with this secret
    username = airpay_service.username
    password = airpay_service.password
    
    privatekey_string = f"{secret_value}@{username}:|:{password}"
    privatekey = hashlib.sha256(privatekey_string.encode('utf-8')).hexdigest()
    
    print(f"Private Key: {privatekey}")
    
    # Get access token
    token = airpay_service.generate_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    # Prepare verify data
    verify_data = {'ap_transactionid': '1820937737'}
    
    # Encrypt data
    encrypted_data = airpay_service.encrypt_data(json.dumps(verify_data))
    checksum = airpay_service.generate_checksum(verify_data)
    
    # Prepare payload with this privatekey
    payload = {
        'merchant_id': airpay_service.merchant_id,
        'encdata': encrypted_data,
        'checksum': checksum,
        'privatekey': privatekey
    }
    
    # Send request
    url = f"{airpay_service.base_url}/airpay/pay/v4/api/verify/?token={token}"
    
    try:
        response = requests.post(
            url,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        result = response.json()
        
        # Decrypt response
        if 'response' in result:
            decrypted = airpay_service.decrypt_data(result['response'])
            if decrypted:
                result = decrypted
        
        # Check result
        status_code = result.get('status_code')
        message = result.get('message', '')
        
        print(f"\nResponse:")
        print(f"  Status Code: {status_code}")
        print(f"  Message: {message}")
        
        if status_code == '200':
            print(f"\n✅ SUCCESS! This is the correct secret!")
            print(f"   Secret: {secret_value}")
            print(f"   Private Key: {privatekey}")
            return True
        elif status_code == '108':
            print(f"\n❌ Authentication Failed (wrong secret)")
            return False
        else:
            print(f"\n⚠️  Different error: {message}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    """Test various possible secret values"""
    
    print("=" * 100)
    print("AIRPAY SECRET VALUE TESTING")
    print("=" * 100)
    print("\nTrying different possible secret values...")
    print("This will help identify the correct secret for privatekey generation.")
    
    # Get current credentials
    client_id = airpay_service.client_id
    client_secret = airpay_service.client_secret
    merchant_id = airpay_service.merchant_id
    username = airpay_service.username
    password = airpay_service.password
    encryption_key = airpay_service.encryption_key
    
    # List of possible secret values to try
    secret_variations = [
        (client_secret, "Client Secret (current)"),
        (client_id, "Client ID"),
        (merchant_id, "Merchant ID"),
        (username, "Username"),
        (password, "Password"),
        (encryption_key, "Encryption Key"),
        (f"{client_id}{client_secret}", "Client ID + Client Secret"),
        (f"{merchant_id}{username}", "Merchant ID + Username"),
        (f"{username}{password}", "Username + Password"),
        (hashlib.md5(client_secret.encode()).hexdigest(), "MD5(Client Secret)"),
        (hashlib.sha256(client_secret.encode()).hexdigest(), "SHA256(Client Secret)"),
    ]
    
    print(f"\n📋 Will test {len(secret_variations)} variations...")
    
    for secret_value, secret_name in secret_variations:
        result = test_secret_variation(secret_value, secret_name)
        
        if result:
            print(f"\n{'='*100}")
            print(f"🎉 FOUND THE CORRECT SECRET!")
            print(f"{'='*100}")
            print(f"\nAdd this to your .env file:")
            print(f"AIRPAY_SECRET={secret_value}")
            print(f"\nThen restart the backend:")
            print(f"sudo systemctl restart moneyone-backend")
            print(f"{'='*100}")
            return
        
        # Small delay between requests
        import time
        time.sleep(1)
    
    print(f"\n{'='*100}")
    print(f"❌ NONE OF THE VARIATIONS WORKED")
    print(f"{'='*100}")
    print(f"\nThe secret value is not one of the common variations.")
    print(f"\nYou need to contact Airpay support to get the correct secret value.")
    print(f"\nEmail: support@airpay.co.in")
    print(f"Subject: Request for Secret Key for Verify API - Merchant ID {merchant_id}")
    print(f"{'='*100}")

if __name__ == '__main__':
    main()
