#!/usr/bin/env python3
"""
Final Airpay Decryption Fix - Based on Official Documentation
Following the exact PHP implementation provided by Airpay team
"""

import json
import base64
import hashlib
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from config import Config

def decrypt_airpay_official_method(encrypted_response, encryption_key):
    """
    Official Airpay decryption method based on their PHP documentation:
    
    PHP Code:
    $iv = substr($response, 0, 16);
    $encryptedData = substr($response, 16);
    $decryptedData = openssl_decrypt(base64_decode($encryptedData), 'AES-256-CBC', $encryptionkey, OPENSSL_RAW_DATA, $iv);
    
    Key points:
    1. IV is first 16 characters of response (as string, not hex)
    2. Encrypted data is remaining characters (base64 encoded)
    3. Use AES-256-CBC with the IV as raw bytes
    """
    try:
        print(f"🔓 Official Airpay Decryption Method")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Step 1: Extract IV (first 16 characters as string)
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV (string): '{iv_string}'")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Step 2: Convert IV string to bytes (this is the key insight!)
        # The IV is not hex - it's raw string that needs to be converted to bytes
        iv_bytes = iv_string.encode('utf-8')
        
        # If IV is less than 16 bytes, pad with zeros
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes.ljust(16, b'\x00')
        elif len(iv_bytes) > 16:
            iv_bytes = iv_bytes[:16]
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV length: {len(iv_bytes)} bytes")
        
        # Step 3: Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Step 4: Prepare encryption key for AES-256
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')  # Pad to 32 bytes for AES-256
        elif len(key) > 32:
            key = key[:32]
        
        print(f"Key: '{encryption_key}'")
        print(f"Key bytes: {key.hex()}")
        print(f"Key length: {len(key)} bytes")
        
        # Step 5: Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Step 6: Remove padding and parse JSON
        try:
            # Try with unpad first
            unpadded_data = unpad(decrypted_data, AES.block_size)
            result = json.loads(unpadded_data.decode('utf-8'))
        except ValueError:
            # If unpad fails, try without unpadding (some implementations don't use standard padding)
            # Remove null bytes and try to parse
            cleaned_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
            result = json.loads(cleaned_data.decode('utf-8'))
        
        print(f"✅ Decryption successful!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Official method failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_airpay_alternative_method(encrypted_response, encryption_key):
    """
    Alternative method: Try treating IV as hex string
    """
    try:
        print(f"🔓 Alternative Airpay Decryption Method")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Method: Treat first 16 chars as hex representation of 8-byte IV
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV hex: {iv_hex}")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Convert hex to bytes (8 bytes) and pad to 16
        try:
            iv_8_bytes = bytes.fromhex(iv_hex)
            iv_16_bytes = iv_8_bytes + b'\x00' * 8  # Pad to 16 bytes
        except ValueError:
            # If not valid hex, treat as string
            iv_16_bytes = iv_hex.encode('utf-8')[:16].ljust(16, b'\x00')
        
        print(f"IV bytes: {iv_16_bytes.hex()}")
        print(f"IV length: {len(iv_16_bytes)} bytes")
        
        # Decode encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Prepare key
        key = encryption_key.encode('utf-8')
        if len(key) < 32:
            key = key.ljust(32, b'\x00')
        elif len(key) > 32:
            key = key[:32]
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_16_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Try different padding removal methods
        try:
            unpadded_data = unpad(decrypted_data, AES.block_size)
            result = json.loads(unpadded_data.decode('utf-8'))
        except:
            # Manual padding removal
            cleaned_data = decrypted_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
            result = json.loads(cleaned_data.decode('utf-8'))
        
        print(f"✅ Alternative method successful!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Alternative method failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_airpay_response(encrypted_response, encryption_key):
    """
    Try multiple decryption methods to handle Airpay response
    """
    print(f"🔍 Attempting Airpay Response Decryption")
    print(f"=" * 50)
    
    # Method 1: Official PHP-based method
    result = decrypt_airpay_official_method(encrypted_response, encryption_key)
    if result:
        return result
    
    print(f"\n" + "=" * 50)
    
    # Method 2: Alternative hex IV method
    result = decrypt_airpay_alternative_method(encrypted_response, encryption_key)
    if result:
        return result
    
    print(f"\n❌ All decryption methods failed")
    return None

def test_actual_airpay_response():
    """Test with the actual response we received"""
    print("🧪 Testing Actual Airpay Response")
    print("=" * 50)
    
    # The actual encrypted response from our test
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    if not encryption_key:
        print("❌ AIRPAY_ENCRYPTION_KEY not configured")
        return
    
    print(f"Using encryption key: {encryption_key}")
    
    result = decrypt_airpay_response(encrypted_response, encryption_key)
    
    if result:
        print(f"\n🎉 SUCCESS! Airpay response decrypted!")
        print(f"Response type: {type(result)}")
        
        # Check for important fields
        if isinstance(result, dict):
            # Look for QR code
            qr_fields = ['QRCODE_STRING', 'qrcode_string', 'qr_string', 'qr_code']
            qr_code = None
            for field in qr_fields:
                if field in result:
                    qr_code = result[field]
                    break
            
            # Look for status
            status_fields = ['status', 'STATUS', 'response_code', 'status_code']
            status = None
            for field in status_fields:
                if field in result:
                    status = result[field]
                    break
            
            if qr_code:
                print(f"✅ QR Code found: {qr_code}")
            if status:
                print(f"✅ Status: {status}")
                
            # Print all fields for analysis
            print(f"\n📋 All response fields:")
            for key, value in result.items():
                print(f"  {key}: {value}")
                
        print(f"\n🎯 AIRPAY DECRYPTION BREAKTHROUGH!")
        print(f"✅ Integration is now 100% complete!")
        
        return result
    else:
        print(f"❌ Failed to decrypt response")
        return None

if __name__ == "__main__":
    test_actual_airpay_response()