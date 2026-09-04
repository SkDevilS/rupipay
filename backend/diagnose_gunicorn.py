#!/usr/bin/env python3
"""
Diagnostic script to test if the Flask app can start properly with Gunicorn
Run this to identify issues before starting the actual service
"""

import sys
import os

print("=" * 60)
print("MoneyOne Backend Diagnostic Tool")
print("=" * 60)

# Test 1: Python version
print("\n1. Python Version:")
print(f"   {sys.version}")

# Test 2: Check if we're in the right directory
print("\n2. Current Directory:")
print(f"   {os.getcwd()}")
print(f"   app.py exists: {os.path.exists('app.py')}")
print(f"   .env exists: {os.path.exists('.env')}")

# Test 3: Try importing required modules
print("\n3. Testing Module Imports:")
required_modules = [
    'flask', 'flask_cors', 'flask_jwt_extended', 'bcrypt', 
    'pymysql', 'pytz', 'dotenv', 'PIL'
]

for module in required_modules:
    try:
        __import__(module)
        print(f"   ✓ {module}")
    except ImportError as e:
        print(f"   ✗ {module} - ERROR: {e}")

# Test 4: Load environment variables
print("\n4. Environment Variables:")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
        'JWT_SECRET_KEY', 'SMTP_HOST', 'CORS_ORIGINS'
    ]
    
    for var in env_vars:
        value = os.getenv(var, 'NOT SET')
        # Mask sensitive values
        if 'PASSWORD' in var or 'SECRET' in var:
            display_value = '***' if value != 'NOT SET' else 'NOT SET'
        else:
            display_value = value
        print(f"   {var}: {display_value}")
except Exception as e:
    print(f"   ERROR loading .env: {e}")

# Test 5: Test database connection
print("\n5. Database Connection:")
try:
    from database import get_db_connection
    conn = get_db_connection()
    if conn:
        print("   ✓ Database connection successful")
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM admin_users")
            result = cursor.fetchone()
            print(f"   ✓ Admin users in database: {result['count']}")
        conn.close()
    else:
        print("   ✗ Database connection failed")
except Exception as e:
    print(f"   ✗ Database error: {e}")

# Test 6: Try importing the Flask app
print("\n6. Flask App Import:")
try:
    from app import app
    print("   ✓ Flask app imported successfully")
    print(f"   ✓ Registered blueprints: {[bp.name for bp in app.blueprints.values()]}")
except Exception as e:
    print(f"   ✗ Flask app import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Check if port 5000 is available
print("\n7. Port Availability:")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5000))
    if result == 0:
        print("   ⚠ Port 5000 is already in use!")
        print("   Run: sudo lsof -i :5000 to see what's using it")
    else:
        print("   ✓ Port 5000 is available")
    sock.close()
except Exception as e:
    print(f"   ? Could not check port: {e}")

# Test 8: Check uploads directory
print("\n8. Uploads Directory:")
uploads_dir = os.getenv('UPLOADS_FOLDER', 'uploads')
if os.path.exists(uploads_dir):
    print(f"   ✓ {uploads_dir} exists")
    print(f"   ✓ Writable: {os.access(uploads_dir, os.W_OK)}")
else:
    print(f"   ✗ {uploads_dir} does not exist")

print("\n" + "=" * 60)
print("Diagnostic Complete!")
print("=" * 60)
print("\nIf all tests pass, try running:")
print("  gunicorn --bind 127.0.0.1:5000 app:app --log-level debug")
print("\nTo see detailed logs, check:")
print("  sudo tail -f /var/log/moneyone/api-stderr.log")
print("=" * 60)
