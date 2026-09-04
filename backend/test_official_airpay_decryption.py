#!/usr/bin/env python3
"""
Test the official Airpay decryption method
Based on the PHP code provided by Airpay team
"""

import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def decrypt_airpay_official(encrypted_response, encryption_key):
    """
    Official Airpay decryption method:
    $iv = substr($response, 0, 16);
    $encryptedData = substr($response, 16);
    $decryptedData = openssl_decrypt(base64_decode($encryptedData), 'AES-256-CBC', $encryptionkey, OPENSSL_RAW_DATA, $iv);
    """
    try:
        print(f"🔓 Official Airpay Decryption Method")
        print(f"Encrypted response: {encrypted_response}")
        print(f"Length: {len(encrypted_response)}")
        
        # Step 1: Extract IV (first 16 characters as string)
        iv = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        print(f"IV (string): '{iv}'")
        print(f"Encrypted data (base64): {encrypted_data_b64}")
        
        # Step 2: Convert IV to bytes (each character becomes a byte)
        iv_bytes = iv.encode('latin-1')  # Preserve byte values
        
        print(f"IV bytes: {iv_bytes.hex()}")
        print(f"IV length: {len(iv_bytes)} bytes")
        
        # Step 3: Decode base64 encrypted data
        encrypted_data = base64.b64decode(encrypted_data_b64)
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Step 4: Use encryption key directly (as provided by Airpay)
        key = encryption_key.encode('utf-8')
        print(f"Key: '{encryption_key}'")
        print(f"Key bytes: {key.hex()}")
        print(f"Key length: {len(key)} bytes")
        
        # Step 5: Ensure key is exactly 32 bytes for AES-256
        if len(key) < 32:
            key = key.ljust(32, b'\0')  # Pad with null bytes
        elif len(key) > 32:
            key = key[:32]  # Truncate to 32 bytes
        
        print(f"Final key length: {len(key)} bytes")
        
        # Step 6: Ensure IV is exactly 16 bytes
        if len(iv_bytes) < 16:
            iv_bytes = iv_bytes.ljust(16, b'\0')  # Pad with null bytes
        elif len(iv_bytes) > 16:
            iv_bytes = iv_bytes[:16]  # Truncate to 16 bytes
        
        print(f"Final IV length: {len(iv_bytes)} bytes")
        print(f"Final IV hex: {iv_bytes.hex()}")
        
        # Step 7: Create cipher and decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        # Step 8: Parse JSON
        result = json.loads(decrypted_data.decode('utf-8'))
        print(f"✅ SUCCESS! Decrypted using official Airpay method!")
        print(f"Decrypted JSON: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"❌ Official method failed: {e}")
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
    
    # Test official decryption method
    result = decrypt_airpay_official(encrypted_response, encryption_key)
    
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