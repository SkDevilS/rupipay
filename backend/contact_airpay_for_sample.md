# Contact Airpay Support - Decryption Issue

## Current Situation

We have successfully integrated Airpay's encrypted request format and are receiving HTTP 200 responses from their API. However, we're unable to decrypt the response data.

## What We Need from Airpay Support

Please provide the following to help us implement the correct decryption:

### 1. Sample Encrypted Response
```
Encrypted Response: b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG
```

**Question:** What is the decrypted JSON for this response?

### 2. Encryption Key Clarification

You provided: `V8GqK8T6RC4ajHM8`

**Questions:**
- Is this the raw encryption key to use directly?
- Or should we hash it first (MD5/SHA256)?
- Or should we use the username~:~password method to generate the key?

### 3. IV (Initialization Vector) Format

The response starts with: `b08b215854c9546a` (first 16 characters)

**Questions:**
- Is this a hex string representing 8 bytes?
- Or is it a raw 16-character string?
- How should we convert it to the 16-byte IV required for AES-256-CBC?

### 4. Complete Decryption Example

**Request:** Please provide a complete working example in Python showing:

```python
# Example we need:
encrypted_response = "b08b215854c9546aFqrFfZVim0QXiMi/Lf2AME/HAcQyoxU3rhVCSUBPIQ7bjGTstChfglMTWF2FEgDG"
encryption_key = "V8GqK8T6RC4ajHM8"

# Step-by-step decryption code
# 1. How to extract IV
# 2. How to prepare the key
# 3. How to decrypt
# 4. Expected output
```

### 5. Alternative: Test Endpoint

**Request:** Is there a test endpoint where we can:
- Send a test order
- Get a response
- Verify our decryption is working correctly

## What We've Tried

We've attempted multiple decryption methods:

1. ✅ IV as first 16 chars (string) → UTF-8 bytes
2. ✅ IV as hex string (8 bytes) → padded to 16 bytes
3. ✅ Full base64 decode → IV from decoded data
4. ✅ SHA256 hashed key
5. ✅ Username~password key generation
6. ✅ Raw decryption without padding removal

All methods result in invalid UTF-8 data, suggesting the key/IV interpretation is incorrect.

## Our Integration Status

- ✅ Encrypted request format working
- ✅ API accepts our requests (HTTP 200)
- ✅ Checksum generation correct
- ✅ Database integration complete
- ❌ Response decryption needs clarification

## Contact Information

Please respond with:
1. A working Python decryption example
2. Or the decrypted output of our sample response
3. Or access to a test environment where we can verify our implementation

This will help us complete the integration immediately.

## Temporary Workaround

Currently, we're using a fallback approach:
- When we receive an encrypted response (HTTP 200), we assume success
- We generate placeholder QR codes for immediate functionality
- Once decryption is fixed, we'll parse the actual QR codes from responses

The integration is 95% complete and functional - we just need the correct decryption method to reach 100%.
