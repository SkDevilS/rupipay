#!/usr/bin/env python3
"""
Debug Airpay Decryption - Step by step analysis
"""

import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def analyze_response():
    """Analyze the encrypted response step by step"""
    
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    encryption_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', 'V8GqK8T6RC4ajHM8')
    
    print(f"🔍 Analyzing Airpay Response")
    print(f"=" * 50)
    print(f"Full response: {encrypted_response}")
    print(f"Response length: {len(encrypted_response)}")
    print(f"Encryption key: {encryption_key}")
    print(f"Key length: {len(encryption_key)}")
    
    # Split the response
    iv_part = encrypted_response[:16]
    data_part = encrypted_response[16:]
    
    print(f"\nSplit Analysis:")
    print(f"IV part (first 16 chars): '{iv_part}'")
    print(f"Data part (remaining): '{data_part}'")
    print(f"Data part length: {len(data_part)}")
    
    # Try to decode data part as base64
    try:
        decoded_data = base64.b64decode(data_part)
        print(f"\n✅ Base64 decode successful")
        print(f"Decoded data length: {len(decoded_data)} bytes")
        print(f"Decoded data (hex): {decoded_data.hex()}")
    except Exception as e:
        print(f"\n❌ Base64 decode failed: {e}")
        return
    
    # Analyze IV part
    print(f"\nIV Analysis:")
    print(f"IV as string: '{iv_part}'")
    print(f"IV as bytes (utf-8): {iv_part.encode('utf-8').hex()}")
    print(f"IV as bytes (latin-1): {iv_part.encode('latin-1').hex()}")
    
    # Try to interpret as hex
    try:
        iv_as_hex = bytes.fromhex(iv_part)
        print(f"IV as hex bytes: {iv_as_hex.hex()} (length: {len(iv_as_hex)})")
    except:
        print(f"IV is not valid hex")
    
    # Key analysis
    print(f"\nKey Analysis:")
    key_utf8 = encryption_key.encode('utf-8')
    print(f"Key as UTF-8: {key_utf8.hex()} (length: {len(key_utf8)})")
    
    # Pad key to 32 bytes
    key_32 = key_utf8.ljust(32, b'\x00')
    print(f"Key padded to 32: {key_32.hex()}")
    
    # Try SHA256 of key
    key_sha256 = hashlib.sha256(key_utf8).digest()
    print(f"Key SHA256: {key_sha256.hex()}")
    
    # Try username~password method
    username = getattr(Config, 'AIRPAY_USERNAME', 'CKFzeZGut2')
    password = getattr(Config, 'AIRPAY_PASSWORD', 'WRx4M373')
    hash_string = f"{username}~:~{password}"
    key_user_pass = hashlib.sha256(hash_string.encode('utf-8')).digest()
    print(f"Username~password key: {key_user_pass.hex()}")
    
    print(f"\n" + "=" * 50)
    print(f"Now trying different decryption combinations...")
    
    # Test different IV interpretations
    iv_options = []
    
    # Option 1: IV as UTF-8 bytes, padded
    iv1 = iv_part.encode('utf-8')[:16].ljust(16, b'\x00')
    iv_options.append(("UTF-8 padded", iv1))
    
    # Option 2: IV as latin-1 bytes, padded  
    iv2 = iv_part.encode('latin-1')[:16].ljust(16, b'\x00')
    iv_options.append(("Latin-1 padded", iv2))
    
    # Option 3: IV as hex bytes, padded
    try:
        iv3 = bytes.fromhex(iv_part).ljust(16, b'\x00')
        iv_options.append(("Hex padded", iv3))
    except:
        pass
    
    # Key options
    key_options = [
        ("Raw key padded", key_32),
        ("SHA256 key", key_sha256[:32]),
        ("Username~password key", key_user_pass[:32])
    ]
    
    # Try all combinations
    for iv_name, iv_bytes in iv_options:
        for key_name, key_bytes in key_options:
            try:
                print(f"\nTrying: {iv_name} + {key_name}")
                print(f"IV: {iv_bytes.hex()}")
                print(f"Key: {key_bytes.hex()}")
                
                cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                decrypted = cipher.decrypt(decoded_data)
                
                print(f"Raw decrypted: {decrypted.hex()}")
                
                # Try with unpad
                try:
                    unpadded = unpad(decrypted, AES.block_size)
                    json_str = unpadded.decode('utf-8')
                    result = json.loads(json_str)
                    print(f"🎉 SUCCESS! JSON: {json.dumps(result, indent=2)}")
                    return result
                except Exception as e:
                    print(f"Unpad failed: {e}")
                
                # Try without unpad
                try:
                    # Remove common padding bytes
                    cleaned = decrypted.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10')
                    json_str = cleaned.decode('utf-8')
                    result = json.loads(json_str)
                    print(f"🎉 SUCCESS! JSON: {json.dumps(result, indent=2)}")
                    return result
                except Exception as e:
                    print(f"Manual clean failed: {e}")
                
                # Try to find JSON in the data
                try:
                    decrypted_str = decrypted.decode('utf-8', errors='ignore')
                    start = decrypted_str.find('{')
                    end = decrypted_str.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_str = decrypted_str[start:end+1]
                        result = json.loads(json_str)
                        print(f"🎉 SUCCESS! JSON: {json.dumps(result, indent=2)}")
                        return result
                except Exception as e:
                    print(f"JSON search failed: {e}")
                    
            except Exception as e:
                print(f"Decryption failed: {e}")
    
    print(f"\n❌ All combinations failed")
    return None

if __name__ == "__main__":
    analyze_response()