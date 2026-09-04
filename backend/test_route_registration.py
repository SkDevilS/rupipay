#!/usr/bin/env python3
"""
Test if PayTouch2 callback route is registered in the Flask app
"""

import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from app import app

print("=" * 80)
print("CHECKING PAYTOUCH2 CALLBACK ROUTE REGISTRATION")
print("=" * 80)

# List all registered routes
print("\nAll registered routes containing 'paytouch2':")
print("-" * 80)

found_route = False
for rule in app.url_map.iter_rules():
    if 'paytouch2' in rule.rule.lower():
        print(f"✓ Route: {rule.rule}")
        print(f"  Methods: {', '.join(rule.methods)}")
        print(f"  Endpoint: {rule.endpoint}")
        found_route = True

if not found_route:
    print("❌ NO PAYTOUCH2 ROUTES FOUND!")
    print("\nAll routes containing 'callback':")
    for rule in app.url_map.iter_rules():
        if 'callback' in rule.rule.lower():
            print(f"  {rule.rule} -> {rule.endpoint}")

print("\n" + "=" * 80)
print("CHECKING BLUEPRINT REGISTRATION")
print("=" * 80)

# Check if blueprint is registered
blueprints = app.blueprints
print(f"\nTotal blueprints registered: {len(blueprints)}")
print("\nBlueprints containing 'paytouch':")
for bp_name in blueprints:
    if 'paytouch' in bp_name.lower():
        print(f"  ✓ {bp_name}")

if 'paytouch2_callback' in blueprints:
    print("\n✅ paytouch2_callback blueprint IS registered")
else:
    print("\n❌ paytouch2_callback blueprint NOT registered")

print("\n" + "=" * 80)
