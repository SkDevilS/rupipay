#!/usr/bin/env python3
"""
Airpay Correct Decryption - Following PHP Documentation Exactly
Key insight: IV is first 16 characters as RAW STRING, not hex!
"""

import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def decrypt_airpay_correct(encrypted_response, encryption_key):
    """
    Correct Airpay decryption following their PHP code exactly:
    
    PHP:
    $iv = substr($response, 0, 16);  // First 16 chars as STRING
    $encryptedData = substr($response, 16);  // Rest as base64
    $decryptedData = openssl_decrypt(base64_decode($encryptedData), 'AES-256-CBC', $encryptionkey, OPENSSL_RAW_DATA, $iv);
    
    In PHP, when you pass a string to openssl_decrypt as IV, it treats each character as a byte!
    """
    try:
        print(f"🔓 Correct Airpay Decryption (Following PHP Exactly)")
        print(f"=" * 60)
        print(f"Encrypted response: {encrypted_response}")
        print(f"Response length: {len(encrypted_response)}")
        
        # Step 1: Extract IV (first 16 characters as STRING)
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"\nStep 1: Extract IV")
        print(f"IV string: '{iv_string}'")
        print(f"IV length: {len(iv_string)} characters")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Step 2: Convert IV string to bytes
        # In PHP, each character becomes one byte
        # We need to use 'latin-1' encoding to preserve byte values
        iv_bytes = iv_string.encode('latin-1')
        
        print(f"\nStep 2: Convert IV to bytes")
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV bytes length: {len(iv_bytes)}")
        
        # Step 3: Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        print(f"\nStep 3: Decode base64")
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        print(f"Encrypted data (hex): {encrypted_data.hex()}")
        
        # Step 4: Prepare encryption key
        # Use the key directly as provided
        key_bytes = encryption_key.encode('latin-1')
        
        # For AES-256, we need 32 bytes
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\x00')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        
        print(f"\nStep 4: Prepare key")
        print(f"Key: '{encryption_key}'")
        print(f"Key bytes: {key_bytes.hex()}")
        print(f"Key length: {len(key_bytes)} bytes")
        
        # Step 5: Decrypt using AES-256-CBC
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        print(f"\nStep 5: Decrypt")
        print(f"Decrypted data (hex): {decrypted_data.hex()}")
        print(f"Decrypted data (raw): {decrypted_data}")
        
        # Step 6: Remove PKCS5 padding and parse JSON
        try:
            # Try standard unpad
            unpadded_data = unpad(decrypted_data, AES.block_size)
            print(f"\nStep 6: Remove padding (standard)")
            print(f"Unpadded data: {unpadded_data}")
            
            json_str = unpadded_data.decode('utf-8')
            result = json.loads(json_str)
            
            print(f"\n🎉 SUCCESS!")
            print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
            return result
            
        except ValueError as e:
            print(f"\nStandard unpad failed: {e}")
            print(f"Trying manual padding removal...")
            
            # Manual PKCS5 padding removal
            padding_length = decrypted_data[-1]
            if isinstance(padding_length, str):
                padding_length = ord(padding_length)
            
            print(f"Padding length: {padding_length}")
            
            if 1 <= padding_length <= 16:
                unpadded_data = decrypted_data[:-padding_length]
                print(f"Manually unpadded data: {unpadded_data}")
                
                json_str = unpadded_data.decode('utf-8')
                result = json.loads(json_str)
                
                print(f"\n🎉 SUCCESS!")
                print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
                return result
            else:
                raise ValueError(f"Invalid padding length: {padding_length}")
        
    except Exception as e:
        print(f"\n❌ Decryption failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_actual_response():
    """Test with the actual Airpay response"""
    print("🧪 Testing Actual Airpay Response")
    print("=" * 60)
    
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', 'V8GqK8T6RC4ajHM8')
    
    print(f"Using encryption key: {encryption_key}\n")
    
    result = decrypt_airpay_correct(encrypted_response, encryption_key)
    
    if result:
        print(f"\n" + "=" * 60)
        print(f"🎯 AIRPAY DECRYPTION WORKING!")
        print(f"=" * 60)
        
        # Check for important fields
        if isinstance(result, dict):
            print(f"\nResponse fields:")
            for key, value in result.items():
                print(f"  {key}: {value}")
                
            # Look for QR code
            qr_fields = ['QRCODE_STRING', 'qrcode_string', 'qr_string', 'qr_code', 'upi_string']
            for field in qr_fields:
                if field in result:
                    print(f"\n✅ QR Code found: {result[field]}")
                    break
        
        return result
    else:
        print(f"\n❌ Decryption failed")
        return None

if __name__ == "__main__":
    test_with_actual_response()
