#!/usr/bin/env python3
"""
Correct Airpay decryption method
The IV should be the first 16 BYTES, not 16 characters
"""

import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def decrypt_airpay_correct(encrypted_response, encryption_key):
    """
    Correct Airpay decryption:
    The response is: IV (16 bytes) + base64_encoded_data
    But the IV is hex-encoded, so first 32 hex chars = 16 bytes
    """
    try:
        print(f"🔓 Correct Airpay Decryption Method")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # The IV is hex-encoded in the first 32 characters (16 bytes * 2)
        iv_hex = encrypted_response[:32]  # First 32 hex characters
        encrypted_data_b64 = encrypted_response[32:]  # Rest is base64 data
        
        print(f"IV (hex): '{iv_hex}'")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Convert hex IV to bytes
        iv_bytes = bytes.fromhex(iv_hex)
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV length: {len(iv_bytes)} bytes")
        
        # Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Use encryption key directly
        key = encryption_key.encode('utf-8')
        print(f"Key: '{encryption_key}'")
        print(f"Key bytes: {key.hex()}")
        print(f"Key length: {len(key)} bytes")
        
        # Ensure key is exactly 32 bytes for AES-256
        if len(key) < 32:
            key = key.ljust(32, b'\0')  # Pad with null bytes
        elif len(key) > 32:
            key = key[:32]  # Truncate to 32 bytes
        
        print(f"Final key length: {len(key)} bytes")
        print(f"Final IV length: {len(iv_bytes)} bytes")
        
        # Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        # Parse JSON
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ SUCCESS! Decrypted correctly!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Correct method failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # The encrypted response from our test
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    
    # Get encryption key from config
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    print(f"Encryption key: {encryption_key}")
    
    if not encryption_key:
        print("❌ Please configure AIRPAY_ENCRYPTION_KEY in .env file")
        return
    
    # Test correct decryption method
    result = decrypt_airpay_correct(encrypted_response, encryption_key)
    
    if result:
        print(f"\n🎉 DECRYPTION SUCCESS!")
        print(f"Response type: {type(result)}")
        
        # Check for QR code or success indicators
        if isinstance(result, dict):
            qr_code = result.get('QRCODE_STRING') or result.get('qrcode_string') or result.get('qr_string')
            status = result.get('status') or result.get('STATUS')
            
            if qr_code:
                print(f"✅ QR Code received: {qr_code}")
            if status:
                print(f"✅ Status: {status}")
                
            # Print all fields
            print(f"\nAll response fields:")
            for key, value in result.items():
                print(f"  {key}: {value}")
    else:
        print(f"❌ Decryption failed")

if __name__ == "__main__":
    main()