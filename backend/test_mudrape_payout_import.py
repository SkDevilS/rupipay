#!/usr/bin/env python3
"""
Test script to diagnose mudrape_payout_routes import issue
"""

import sys
import traceback

print("Testing mudrape_payout_routes import...")
print("=" * 60)

# Test 1: Check if file exists
print("\n1. Checking if mudrape_payout_routes.py exists...")
try:
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'mudrape_payout_routes.py')
    if os.path.exists(file_path):
        print(f"✓ File exists at: {file_path}")
    else:
        print(f"✗ File NOT found at: {file_path}")
except Exception as e:
    print(f"✗ Error checking file: {e}")

# Test 2: Try importing the module
print("\n2. Attempting to import mudrape_payout_routes module...")
try:
    import mudrape_payout_routes
    print("✓ Module imported successfully")
except Exception as e:
    print(f"✗ Failed to import module:")
    print(f"   Error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Check if blueprint exists
print("\n3. Checking if mudrape_payout_bp exists in module...")
try:
    if hasattr(mudrape_payout_routes, 'mudrape_payout_bp'):
        print("✓ mudrape_payout_bp found in module")
        print(f"   Type: {type(mudrape_payout_routes.mudrape_payout_bp)}")
    else:
        print("✗ mudrape_payout_bp NOT found in module")
        print(f"   Available attributes: {dir(mudrape_payout_routes)}")
except Exception as e:
    print(f"✗ Error checking blueprint: {e}")
    traceback.print_exc()

# Test 4: Try the actual import statement from app.py
print("\n4. Testing the exact import from app.py...")
try:
    from mudrape_payout_routes import mudrape_payout_bp
    print("✓ Import successful!")
    print(f"   Blueprint name: {mudrape_payout_bp.name}")
    print(f"   URL prefix: {mudrape_payout_bp.url_prefix}")
except Exception as e:
    print(f"✗ Import failed:")
    print(f"   Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete!")
