#!/usr/bin/env python3
"""
Test CORS Configuration
Run this to verify CORS settings are loaded correctly
"""

from config import Config

print("=" * 60)
print("CORS Configuration Test")
print("=" * 60)
print(f"\nCORS_ORIGINS type: {type(Config.CORS_ORIGINS)}")
print(f"CORS_ORIGINS value: {Config.CORS_ORIGINS}")
print(f"CORS_ORIGINS length: {len(Config.CORS_ORIGINS)}")
print(f"\nIndividual origins:")
for i, origin in enumerate(Config.CORS_ORIGINS, 1):
    print(f"  {i}. '{origin}' (length: {len(origin)})")
print(f"\nCORS_ALLOW_CREDENTIALS: {Config.CORS_ALLOW_CREDENTIALS}")
print("=" * 60)
