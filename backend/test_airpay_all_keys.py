#!/usr/bin/env python3
"""
Final Comprehensive Airpay Decryption Test
Testing with both provided key and MD5-generated key
"""

import json
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config

def test_decryption_with_key(encrypted_response, key, key_description):
    """Test decryption with a specific key"""
    try:
        print(f"\n{'='*60}")
        print(f"Testing with: {key_description}")
        print(f"Key: {key}")
        print(f"Key length: {len(key)}")
        print(f"{'='*60}")
        
        # Extract IV (first 16 characters)
        iv_string = encrypted_response[:16]
        encrypted_data_b64 = encrypted_response[16:]
        
        # Convert IV to bytes (latin-1 encoding)
        iv_bytes = iv_string.encode('latin-1')
        
        # Decode base64
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Prepare key bytes
        key_bytes = key.encode('latin-1')
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\x00')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        
        print(f"IV: {iv_bytes.hex()}")
        print(f"Key bytes: {key_bytes.hex()}")
        print(f"Encrypted data length: {len(encrypted_data)} bytes")
        
        # Decrypt
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        print(f"Decrypted (hex): {decrypted_data.hex()}")
        
        # Try to unpad and parse
        try:
            unpadded = unpad(decrypted_data, AES.block_size)
            json_str = unpadded.decode('utf-8')
            result = json.loads(json_str)
            print(f"\n🎉 SUCCESS with {key_description}!")
            print(f"Result: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            print(f"Failed to parse: {e}")
            
            # Try manual padding removal
            for padding_len in range(1, 17):
                try:
                    unpadded = decrypted_data[:-padding_len] if padding_len > 0 else decrypted_data
                    json_str = unpadded.decode('utf-8')
                    result = json.loads(json_str)
                    print(f"\n🎉 SUCCESS with {key_description} (manual padding {padding_len})!")
                    print(f"Result: {json.dumps(result, indent=2)}")
                    return result
                except:
                    continue
            
            print(f"❌ Could not parse JSON")
            return None
            
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        return None

def main():
    """Test all possible key combinations"""
    
    encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
    
    # Get credentials
    provided_key = getattr(Config, 'AIRPAY_ENCRYPTION_KEY', 'V8GqK8T6RC4ajHM8')
    username = getattr(Config, 'AIRPAY_USERNAME', 'CKFzeZGut2')
    password = getattr(Config, 'AIRPAY_PASSWORD', 'WRx4M373')
    
    print(f"🧪 Comprehensive Airpay Decryption Test")
    print(f"=" * 60)
    print(f"Encrypted response: {encrypted_response}")
    print(f"Response length: {len(encrypted_response)}")
    print(f"\nCredentials:")
    print(f"  Provided key: {provided_key}")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    # Generate MD5 key as per documentation
    hash_string = f"{username}~:~{password}"
    md5_key = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    # Generate SHA256 key (alternative)
    sha256_key = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    print(f"\nGenerated keys:")
    print(f"  MD5 key: {md5_key}")
    print(f"  SHA256 key: {sha256_key}")
    
    # Test all key options
    keys_to_test = [
        (provided_key, "Provided key (V8GqK8T6RC4ajHM8)"),
        (md5_key, "MD5(username~:~password)"),
        (md5_key[:16], "MD5 key (first 16 chars)"),
        (sha256_key[:32], "SHA256 key (first 32 chars)"),
        (sha256_key[:16], "SHA256 key (first 16 chars)"),
    ]
    
    for key, description in keys_to_test:
        result = test_decryption_with_key(encrypted_response, key, description)
        if result:
            print(f"\n🎯 FOUND WORKING KEY: {description}")
            print(f"Key value: {key}")
            return result
    
    print(f"\n❌ None of the keys worked")
    print(f"\n📝 Possible reasons:")
    print(f"1. The response might be an error message, not encrypted data")
    print(f"2. The encryption key provided by Airpay might be incorrect")
    print(f"3. There might be additional key derivation steps not documented")
    print(f"\n💡 Recommendation:")
    print(f"Contact Airpay support with this exact encrypted response")
    print(f"and ask them to provide the decrypted output for verification")
    
    return None

if __name__ == "__main__":
    main()
