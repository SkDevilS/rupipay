#!/usr/bin/env python3
"""
Official Airpay Implementation
Based on the exact PHP code provided by Airpay team
"""

import json
import base64
import hashlib
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config

def encrypt_airpay_official(data, encryption_key):
    """
    Official Airpay encryption method:
    $iv = bin2hex(openssl_random_pseudo_bytes(8));
    $raw = openssl_encrypt($data, 'AES-256-CBC', $encryptionkey, OPENSSL_RAW_DATA, $iv);
    $encryptedata = $iv . base64_encode($raw);
    """
    try:
        print(f"🔐 Official Airpay Encryption")
        
        # Step 1: Convert data to JSON string if it's a dict
        if isinstance(data, dict):
            data = json.dumps(data)
        
        # Step 2: Generate 8 random bytes and convert to hex (16 characters)
        iv_bytes = get_random_bytes(8)
        iv_hex = iv_bytes.hex()  # This creates 16 hex characters
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV hex string: {iv_hex}")
        print(f"IV hex length: {len(iv_hex)}")
        
        # Step 3: Use encryption key directly
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\0')
        elif len(key) > 32:
            key = key[:32]
        
        # Step 4: For AES, we need the IV as bytes (convert hex back to bytes)
        aes_iv = bytes.fromhex(iv_hex)
        
        # Step 5: Encrypt using AES-256-CBC
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
        
        # Step 6: Create final result: iv_hex + base64(encrypted_data)
        encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        result = iv_hex + encrypted_b64
        
        print(f"✅ Encrypted successfully!")
        print(f"Final result length: {len(result)}")
        print(f"Result: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_airpay_official(encrypted_response, encryption_key):
    """
    Official Airpay decryption method:
    $iv = substr($response, 0, 16);
    $encryptedData = substr($response, 16);
    $decryptedData = openssl_decrypt(base64_decode($encryptedData), 'AES-256-CBC', $encryptionkey, OPENSSL_RAW_DATA, $iv);
    """
    try:
        print(f"🔓 Official Airpay Decryption")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Step 1: Extract IV (first 16 characters as hex string)
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV hex: {iv_hex}")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Step 2: Convert hex IV to bytes
        iv_bytes = bytes.fromhex(iv_hex)
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV length: {len(iv_bytes)} bytes")
        
        # Step 3: Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Step 4: Use encryption key directly
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\0')
        elif len(key) > 32:
            key = key[:32]
        
        print(f"Key length: {len(key)} bytes")
        
        # Step 5: Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        # Step 6: Parse JSON
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ Decryption successful!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_round_trip():
    """Test encryption and decryption round trip"""
    print("🧪 Testing Airpay Encryption/Decryption Round Trip")
    print("=" * 60)
    
    # Get encryption key
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    if not encryption_key:
        print("❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    # Test data
    test_data = {
        'mercid': 335854,
        'orderid': 'TEST_12345',
        'amount': '1.00',
        'buyerPhone': '9876543210',
        'buyerEmail': 'test@example.com'
    }
    
    print(f"Original data: {json.dumps(test_data, indent=2)}")
    
    # Encrypt
    encrypted = encrypt_airpay_official(test_data, encryption_key)
    if not encrypted:
        print("❌ Encryption failed")
        return
    
    # Decrypt
    decrypted = decrypt_airpay_official(encrypted, encryption_key)
    if not decrypted:
        print("❌ Decryption failed")
        return
    
    # Compare
    if decrypted == test_data:
        print("🎉 ROUND TRIP SUCCESS!")
        print("✅ Encryption and decryption working perfectly")
    else:
        print("❌ Round trip failed - data mismatch")
        print(f"Expected: {test_data}")
        print(f"Got: {decrypted}")

def test_actual_response():
    """Test with the actual response we received"""
    print("\n🧪 Testing Actual Airpay Response")
    print("=" * 40)
    
    # The actual encrypted response from our test
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    if not encryption_key:
        print("❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    result = decrypt_airpay_official(encrypted_response, encryption_key)
    
    if result:
        print(f"\n🎉 ACTUAL RESPONSE DECRYPTED!")
        print(f"Response type: {type(result)}")
        
        # Check for QR code or success indicators
        if isinstance(result, dict):
            qr_code = result.get('QRCODE_STRING') or result.get('qrcode_string') or result.get('qr_string')
            status = result.get('status') or result.get('STATUS')
            
            if qr_code:
                print(f"✅ QR Code: {qr_code}")
            if status:
                print(f"✅ Status: {status}")
                
            # Print all fields
            print(f"\nAll response fields:")
            for key, value in result.items():
                print(f"  {key}: {value}")
    else:
        print(f"❌ Failed to decrypt actual response")

if __name__ == "__main__":
    test_round_trip()
    test_actual_response()