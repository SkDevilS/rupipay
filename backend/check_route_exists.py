"""
Check if the check-status route exists and is working
"""

import sys
sys.path.insert(0, '/home/ubuntu/moneyone_backend')

from app import app

print("=" * 80)
print("Checking Routes")
print("=" * 80)
print()

# Get all routes
routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ','.join(rule.methods),
        'path': str(rule)
    })

# Sort by path
routes.sort(key=lambda x: x['path'])

# Find payout routes
print("Payout Routes:")
print("-" * 80)
for route in routes:
    if 'payout' in route['path'].lower() or 'payout' in route['endpoint'].lower():
        print(f"{route['methods']:20} {route['path']:50} {route['endpoint']}")

print()
print("=" * 80)
print("Looking for check-status route...")
print("=" * 80)
print()

found = False
for route in routes:
    if 'check-status' in route['path']:
        print(f"✓ FOUND: {route['methods']} {route['path']} -> {route['endpoint']}")
        found = True

if not found:
    print("✗ NOT FOUND: /api/payout/client/check-status/<txn_id>")
    print()
    print("This means the route is not registered in the Flask app.")
    print()
    print("Possible causes:")
    print("1. payout_routes.py not imported correctly")
    print("2. Blueprint not registered in app.py")
    print("3. Syntax error in payout_routes.py preventing import")
    print()
    print("Check backend logs:")
    print("  sudo journalctl -u moneyone_backend -n 100")

print()
