"""Quick test to verify headers are being generated correctly"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from skrillpe_service import SkrillPeService

print("=" * 60)
print("SkrillPe Headers Test")
print("=" * 60)

# Check config values
print("\n1. Config Values:")
print(f"   AUTH_API_KEY: {Config.SKRILLPE_AUTH_API_KEY}")
print(f"   AUTH_API_PASSWORD: {Config.SKRILLPE_AUTH_API_PASSWORD}")
print(f"   MID: {Config.SKRILLPE_MID}")
print(f"   Mobile: {Config.SKRILLPE_MOBILE_NUMBER}")

# Create service instance
service = SkrillPeService()

print("\n2. Service Instance Values:")
print(f"   auth_api_key: {service.auth_api_key}")
print(f"   auth_api_password: {service.auth_api_password}")

# Get headers
headers = service.get_headers()

print("\n3. Generated Headers:")
for key, value in headers.items():
    print(f"   {key}: {value}")

print("\n" + "=" * 60)
if 'AUTH-API_KEY' in headers and 'AUTH-API_PASSWORD' in headers:
    print("✓ All headers present!")
else:
    print("✗ Missing AUTH headers!")
print("=" * 60)
