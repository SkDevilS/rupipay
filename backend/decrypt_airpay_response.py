#!/usr/bin/env python3
"""
Decrypt the Airpay response we got from the encrypted test
"""

import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def decrypt_airpay_response(encrypted_response, encryption_key):
    """
    Decrypt Airpay response according to documentation:
    IV = substr(encryptedData, 0, 16);
    data = substr(encryptedData, 16);
    DecryptedData = openssl_decrypt(base64_decode(data), AES-256-CBC, EncryptionKey, options=OPENSSL_RAW_DATA, IV);
    """
    try:
        print(f"🔓 Decrypting Airpay response...")
        print(f"Encrypted data: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Extract IV (first 16 hex characters = 8 bytes)
        iv_hex = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV hex: {iv_hex}")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Convert hex IV to bytes and pad to 16 bytes for AES
        iv_bytes = bytes.fromhex(iv_hex)
        aes_iv = iv_bytes + b'\x00' * 8  # Pad to 16 bytes
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"AES IV (padded): {aes_iv.hex()}")
        
        # Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Use the encryption key provided by Airpay
        if not encryption_key:
            print("❌ AIRPAY_ENCRYPTION_KEY not configured")
            return None
        
        # Use first 32 bytes of the encryption key for AES-256
        key = encryption_key[:32].encode('utf-8').ljust(32, b'\0')
        print(f"Key length: {len(key)} bytes")
        print(f"Key (first 16 bytes): {key[:16].hex()}")
        
        # Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, aes_iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        # Parse JSON
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ Decrypted successfully!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # The encrypted response from our test
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    
    # Get encryption key from config
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', '')
    
    print(f"Encryption key: {encryption_key[:10]}..." if encryption_key else "❌ Not configured")
    
    if not encryption_key:
        print("❌ Please configure AIRPAY_ENCRYPTION_KEY in .env file")
        return
    
    # Decrypt the response
    result = decrypt_airpay_response(encrypted_response, encryption_key)
    
    if result:
        print(f"\n🎉 SUCCESS! Airpay returned:")
        print(f"Response type: {type(result)}")
        
        # Check for QR code or success indicators
        if isinstance(result, dict):
            qr_code = result.get('QRCODE_STRING') or result.get('qrcode_string') or result.get('qr_string')
            status = result.get('status') or result.get('STATUS')
            
            if qr_code:
                print(f"✅ QR Code received: {qr_code[:50]}...")
            if status:
                print(f"✅ Status: {status}")
                
            # Print all fields
            print(f"\nAll response fields:")
            for key, value in result.items():
                print(f"  {key}: {value}")
    else:
        print(f"❌ Failed to decrypt response")

if __name__ == "__main__":
    main()