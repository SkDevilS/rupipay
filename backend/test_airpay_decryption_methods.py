#!/usr/bin/env python3
"""
Test different decryption methods for Airpay response
"""

import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def method1_original(encrypted_response, encryption_key):
    """Original method - IV hex + base64 data"""
    try:
        print("🔓 Method 1: IV hex (16 chars) + base64 data")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        iv_bytes = bytes.fromhex(iv_hex)
        aes_iv = iv_bytes + b'\x00' * 8  # Pad to 16 bytes
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
        
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ Method 1 SUCCESS: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
        return None

def method2_full_base64(encrypted_response, encryption_key):
    """Method 2: Entire response is base64 encoded"""
    try:
        print("🔓 Method 2: Full base64 decode first")
        
        # Decode entire response as base64
        full_data = base64.b64decode(encrypted_response)
        
        # Extract IV (first 16 bytes) and data
        aes_iv = full_data[:16]
        encrypted_data = full_data[16:]
        
        key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
        
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ Method 2 SUCCESS: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Method 2 failed: {e}")
        return None

def method3_no_padding(encrypted_response, encryption_key):
    """Method 3: Try without unpadding"""
    try:
        print("🔓 Method 3: No padding removal")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        iv_bytes = bytes.fromhex(iv_hex)
        aes_iv = iv_bytes + b'\x00' * 8
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
        
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Try to find JSON in the decrypted data
        decrypted_str = decrypted_data.decode('utf-8', errors='ignore')
        print(f"Raw decrypted: {decrypted_str}")
        
        # Look for JSON patterns
        start = decrypted_str.find('{')
        end = decrypted_str.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = decrypted_str[start:end]
            result = json.loads(json_str)
            print(f"✅ Method 3 SUCCESS: {result}")
            return result
        
    except Exception as e:
        print(f"❌ Method 3 failed: {e}")
        return None

def main():
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    print(f"Testing decryption methods...")
    print(f"Encrypted response: {encrypted_response}")
    print(f"Length: {len(encrypted_response)}")
    
    # Try all methods
    methods = [method1_original, method2_full_base64, method3_no_padding]
    
    for method in methods:
        result = method(encrypted_response, encryption_key)
        if result:
            return result
    
    print("❌ All methods failed")

if __name__ == "__main__":
    main()