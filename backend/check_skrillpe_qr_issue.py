"""
Diagnostic script to check SkrillPe QR decoding issue
"""

import sys
import os

print("=" * 60)
print("SkrillPe QR Decoding Diagnostic")
print("=" * 60)

# Check 1: Python packages
print("\n1. Checking Python packages...")
try:
    from PIL import Image
    print("   ✓ PIL (Pillow) is installed")
except ImportError as e:
    print(f"   ✗ PIL (Pillow) NOT installed: {e}")

try:
    from pyzbar.pyzbar import decode
    print("   ✓ pyzbar is installed")
except ImportError as e:
    print(f"   ✗ pyzbar NOT installed: {e}")

# Check 2: System library
print("\n2. Checking system library (zbar)...")
try:
    from pyzbar.pyzbar import decode
    print("   ✓ zbar shared library is available")
except Exception as e:
    print(f"   ✗ zbar shared library issue: {e}")

# Check 3: Test with sample QR
print("\n3. Testing QR decoding capability...")
try:
    from PIL import Image
    from pyzbar.pyzbar import decode
    from io import BytesIO
    import requests
    
    # Try to decode a test QR image
    test_url = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=test@upi&pn=Test&am=100"
    
    print(f"   Downloading test QR from: {test_url[:50]}...")
    response = requests.get(test_url, timeout=10)
    
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        decoded = decode(image)
        
        if decoded:
            print(f"   ✓ QR decoding works! Decoded: {decoded[0].data.decode('utf-8')[:50]}...")
        else:
            print("   ✗ QR decoding failed - no data found")
    else:
        print(f"   ✗ Failed to download test QR: {response.status_code}")
        
except Exception as e:
    print(f"   ✗ QR decoding test failed: {e}")
    import traceback
    traceback.print_exc()

# Check 4: Check actual SkrillPe service
print("\n4. Checking SkrillPe service configuration...")
try:
    from skrillpe_service import skrillpe_service, QR_DECODE_AVAILABLE
    
    print(f"   QR_DECODE_AVAILABLE flag: {QR_DECODE_AVAILABLE}")
    
    if not QR_DECODE_AVAILABLE:
        print("   ⚠ QR decoding is DISABLED in skrillpe_service.py")
        print("   This is why qr_string and upi_link are empty")
    else:
        print("   ✓ QR decoding is ENABLED in skrillpe_service.py")
        
except Exception as e:
    print(f"   ✗ Error checking service: {e}")

# Check 5: Installation commands
print("\n5. Installation commands (if needed):")
print("   System library:")
print("   - Amazon Linux: sudo yum install -y zbar")
print("   - Ubuntu/Debian: sudo apt-get install -y libzbar0")
print("\n   Python package:")
print("   - pip install pyzbar==0.1.9")
print("\n   After installation:")
print("   - sudo systemctl restart moneyone-api")

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)
