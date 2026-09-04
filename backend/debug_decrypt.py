import base64
import hashlib
from Crypto.Cipher import AES

# Test response from your output
encrypted_response = "2baa5c38e7f1ebddcVKDpgCStciQuAlpuGp8slhHQi/CRAjDW5BeqNlIQ+oAN0ny6W8oTIsBXv812PHvXgLok30ZaxDyb3fvOjJosz4wWT3Oeo0Cxc6K+7kNb0YMm53kpzViWDxfeEdV+kGXH1eUBI7Hu0mArZ4eyA+"

# Extract IV and encrypted data
iv_string = encrypted_response[:16]
encrypted_data_b64 = encrypted_response[16:]

print(f"IV: {iv_string}")
print(f"IV bytes (hex): {iv_string.encode('latin-1').hex()}")
print(f"Encrypted data (b64): {encrypted_data_b64[:50]}...")

# Decode base64
encrypted_data = base64.b64decode(encrypted_data_b64)
print(f"Encrypted data length: {len(encrypted_data)} bytes")

# Try with current key
username = "CKFzeZGut2"
password = "WRx4M373"
key_string = f"{username}~:~{password}"
encryption_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()

print(f"\nEncryption key: {encryption_key}")
print(f"Key length: {len(encryption_key)}")

# Try decryption
iv_bytes = iv_string.encode('latin-1')
key_bytes = encryption_key.encode('latin-1')

print(f"\nAttempting decryption...")
cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
decrypted = cipher.decrypt(encrypted_data)

print(f"Decrypted length: {len(decrypted)}")
print(f"Last 16 bytes (hex): {decrypted[-16:].hex()}")
print(f"Last byte value: {decrypted[-1]}")

# Try to decode
try:
    decoded = decrypted.decode('utf-8', errors='ignore')
    print(f"\nDecoded (with errors ignored): {decoded}")
except Exception as e:
    print(f"Decode error: {e}")
