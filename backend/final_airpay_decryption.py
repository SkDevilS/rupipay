#!/usr/bin/env python3
"""
Final correct Airpay decryption based on their documentation
The response format is: IV (16 bytes) + encrypted_data (base64 encoded together)
"""

import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def decrypt_airpay_final(encrypted_response, encryption_key):
    """
    Final correct Airpay decryption:
    1. The entire response is base64 encoded
    2. After decoding: first 16 bytes = IV, rest = encrypted data
    3. Decrypt using AES-256-CBC with the encryption key
    """
    try:
        print(f"🔓 Final Correct Airpay Decryption")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Step 1: Decode the entire response as base64
        try:
            full_decoded = base64.b64decode(encrypted_response)
            print(f"✅ Successfully decoded base64")
            print(f"Decoded length: {len(full_decoded)} bytes")
        except Exception as e:
            print(f"❌ Base64 decode failed: {e}")
            return None
        
        # Step 2: Extract IV (first 16 bytes) and encrypted data (rest)
        iv_bytes = full_decoded[:16]
        encrypted_data = full_decoded[16:]
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV length: {len(iv_bytes)} bytes")
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Step 3: Use encryption key directly
        key = encryption_key.encode('utf-8')
        print(f"Key: '{encryption_key}'")
        print(f"Key bytes: {key.hex()}")
        print(f"Key length: {len(key)} bytes")
        
        # Step 4: Ensure key is exactly 32 bytes for AES-256
        if len(key) < 32:
            key = key.ljust(32, b'\0')  # Pad with null bytes
        elif len(key) > 32:
            key = key[:32]  # Truncate to 32 bytes
        
        print(f"Final key length: {len(key)} bytes")
        
        # Step 5: Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        # Step 6: Parse JSON
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ SUCCESS! Final decryption worked!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Final method failed: {e}")
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
    
    # Test final decryption method
    result = decrypt_airpay_final(encrypted_response, encryption_key)
    
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
                
        print(f"\n🎯 AIRPAY INTEGRATION BREAKTHROUGH!")
        print(f"✅ Encrypted requests work")
        print(f"✅ Response decryption works")
        print(f"✅ Ready for full integration")
    else:
        print(f"❌ Decryption failed")

if __name__ == "__main__":
    main()