#!/usr/bin/env python3
"""
List all registered Flask routes
"""

from app import app

print("=" * 80)
print("ALL REGISTERED FLASK ROUTES")
print("=" * 80)

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
        'path': str(rule)
    })

# Sort by path
routes.sort(key=lambda x: x['path'])

# Filter for callback routes
print("\n🔍 CALLBACK ROUTES:")
print("-" * 80)
for route in routes:
    if 'callback' in route['path'].lower():
        print(f"{route['methods']:10} {route['path']:50} -> {route['endpoint']}")

print("\n📋 ALL ROUTES:")
print("-" * 80)
for route in routes:
    print(f"{route['methods']:10} {route['path']:50} -> {route['endpoint']}")

print("\n" + "=" * 80)
print(f"Total routes: {len(routes)}")
print("=" * 80)
