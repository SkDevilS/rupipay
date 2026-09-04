#!/usr/bin/env python3
"""Quick script to decrypt the ViyonaPay error response"""

import base64
import json
from Crypto.Cipher import AES

# The encrypted error from the response
encrypted_b64 = "uD7aynQzAgUzh//N12OK+Wb8tiU56Vb0zF9/eSZqCiuRWqFke7LAvkuqEjk2v3xbxQfnX4oqGAVGLiCY+v7d+ZZgVrQAQiVSaecN5kFbv3hM3Is4XV+wEpA/siMFPHQ0Inhlw0ayAA8A9BAPYHjP1ApdgS0="

# We need the session key and AAD from the request
# Since we don't have them, let's just show what the error structure looks like
print("Encrypted error response received (status 422)")
print("\nThis indicates a validation error in the request payload.")
print("\nCommon issues with status 422:")
print("  1. Missing required fields in encrypted_data")
print("  2. Invalid field format (e.g., phone number, email)")
print("  3. Invalid payinType value")
print("  4. Missing VPA when payinType is upiMasterMerchant")
print("\nLet me check the API documentation requirements...")
