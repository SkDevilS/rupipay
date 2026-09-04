#!/usr/bin/env python3
"""
Ultimate Airpay Decryption Fix
Trying all possible IV and key interpretations based on the documentation
"""

import json
import base64
import hashlib
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config

def try_decrypt_method_1(encrypted_response, encryption_key):
    """
    Method 1: IV as first 16 chars (string), treat as raw bytes
    """
    try:
        print(f"🔓 Method 1: IV as raw string bytes")
        
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert IV string directly to bytes
        iv_bytes = iv_string.encode('latin-1')[:16]  # Use latin-1 to preserve byte values
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes.ljust(16, b'\x00')
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Prepare key
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Try different padding removal methods
        try:
            result_data = unpad(decrypted_data, AES.block_size)
        except:
            # Manual padding removal
            result_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
        
        result = json.loads(result_data.decode('utf-8'))
        print(f"✅ Method 1 SUCCESS!")
        return result
        
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
        return None

def try_decrypt_method_2(encrypted_response, encryption_key):
    """
    Method 2: IV as hex string (first 16 chars represent 8 hex bytes)
    """
    try:
        print(f"🔓 Method 2: IV as hex string")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert hex to bytes and pad to 16
        iv_bytes = bytes.fromhex(iv_hex)
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes + b'\x00' * (16 - len(iv_bytes))
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Prepare key
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        try:
            result_data = unpad(decrypted_data, AES.block_size)
        except:
            result_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
        
        result = json.loads(result_data.decode('utf-8'))
        print(f"✅ Method 2 SUCCESS!")
        return result
        
    except Exception as e:
        print(f"❌ Method 2 failed: {e}")
        return None

def try_decrypt_method_3(encrypted_response, encryption_key):
    """
    Method 3: Entire response is base64, IV is first 16 bytes of decoded data
    """
    try:
        print(f"🔓 Method 3: Full base64 decode, IV from decoded data")
        
        # Decode entire response as base64
        full_decoded = base64.b64decode(encrypted_response)
        
        iv_bytes = full_decoded[:16]
        encrypted_data = full_decoded[16:]
        
        # Prepare key
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        try:
            result_data = unpad(decrypted_data, AES.block_size)
        except:
            result_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
        
        result = json.loads(result_data.decode('utf-8'))
        print(f"✅ Method 3 SUCCESS!")
        return result
        
    except Exception as e:
        print(f"❌ Method 3 failed: {e}")
        return None

def try_decrypt_method_4(encrypted_response, encryption_key):
    """
    Method 4: Use SHA256 hash of the encryption key instead of raw key
    """
    try:
        print(f"🔓 Method 4: Using SHA256 hashed key")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert hex IV to bytes and pad
        iv_bytes = bytes.fromhex(iv_hex)
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes + b'\x00' * (16 - len(iv_bytes))
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Use SHA256 hash of encryption key
        key = hashlib.sha256(encryption_key.encode('utf-8')).digest()[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        try:
            result_data = unpad(decrypted_data, AES.block_size)
        except:
            result_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
        
        result = json.loads(result_data.decode('utf-8'))
        print(f"✅ Method 4 SUCCESS!")
        return result
        
    except Exception as e:
        print(f"❌ Method 4 failed: {e}")
        return None

def try_decrypt_method_5(encrypted_response, encryption_key):
    """
    Method 5: Use the username~:~password key generation method
    """
    try:
        print(f"🔓 Method 5: Using username~:~password key")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert hex IV to bytes and pad
        iv_bytes = bytes.fromhex(iv_hex)
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes + b'\x00' * (16 - len(iv_bytes))
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Generate key using username~:~password method
        username = getattr(Config, 'AIRPAY_USERNAME', '')
        password = getattr(Config, 'AIRPAY_PASSWORD', '')
        hash_string = f"{username}~:~{password}"
        key = hashlib.sha256(hash_string.encode('utf-8')).digest()[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        try:
            result_data = unpad(decrypted_data, AES.block_size)
        except:
            result_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
        
        result = json.loads(result_data.decode('utf-8'))
        print(f"✅ Method 5 SUCCESS!")
        return result
        
    except Exception as e:
        print(f"❌ Method 5 failed: {e}")
        return None

def try_decrypt_method_6(encrypted_response, encryption_key):
    """
    Method 6: No padding removal, just raw decryption
    """
    try:
        print(f"🔓 Method 6: Raw decryption, no padding removal")
        
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert hex IV to bytes and pad
        iv_bytes = bytes.fromhex(iv_hex)
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes + b'\x00' * (16 - len(iv_bytes))
        
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Prepare key
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Try to find JSON in the decrypted data
        decrypted_str = decrypted_data.decode('utf-8', errors='ignore')
        
        # Look for JSON patterns
        start_idx = decrypted_str.find('{')
        end_idx = decrypted_str.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = decrypted_str[start_idx:end_idx+1]
            result = json.loads(json_str)
            print(f"✅ Method 6 SUCCESS!")
            return result
        else:
            raise ValueError("No JSON found in decrypted data")
        
    except Exception as e:
        print(f"❌ Method 6 failed: {e}")
        return None

def decrypt_airpay_ultimate(encrypted_response, encryption_key):
    """
    Try all possible decryption methods
    """
    print(f"🔍 Ultimate Airpay Decryption - Trying All Methods")
    print(f"=" * 60)
    print(f"Encrypted response: {encrypted_response}")
    print(f"Encryption key: {encryption_key}")
    print(f"Response length: {len(encrypted_response)}")
    print(f"=" * 60)
    
    methods = [
        try_decrypt_method_1,
        try_decrypt_method_2,
        try_decrypt_method_3,
        try_decrypt_method_4,
        try_decrypt_method_5,
        try_decrypt_method_6
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\n--- Trying Method {i} ---")
        result = method(encrypted_response, encryption_key)
        if result:
            print(f"\n🎉 SUCCESS WITH METHOD {i}!")
            print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
            return result
    
    print(f"\n❌ All methods failed")
    return None

def test_actual_response():
    """Test with the actual response"""
    print("🧪 Testing Actual Airpay Response - Ultimate Method")
    print("=" * 60)
    
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    if not encryption_key:
        print("❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    result = decrypt_airpay_ultimate(encrypted_response, encryption_key)
    
    if result:
        print(f"\n🎯 BREAKTHROUGH! Airpay decryption working!")
        
        # Check for important fields
        if isinstance(result, dict):
            qr_fields = ['QRCODE_STRING', 'qrcode_string', 'qr_string', 'qr_code', 'upi_string']
            status_fields = ['status', 'STATUS', 'response_code', 'status_code']
            
            for field in qr_fields:
                if field in result:
                    print(f"✅ QR Code: {result[field]}")
                    break
            
            for field in status_fields:
                if field in result:
                    print(f"✅ Status: {result[field]}")
                    break
        
        return result
    else:
        print(f"❌ All decryption methods failed")
        return None

if __name__ == "__main__":
    test_actual_response()