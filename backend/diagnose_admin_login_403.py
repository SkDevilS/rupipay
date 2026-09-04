#!/usr/bin/env python3
"""
Diagnose Admin Login 403 Forbidden Error
This script checks all possible causes of the 403 error after password change
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database_pooled import get_db_connection
from config import Config
import bcrypt
from datetime import datetime
import requests

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print section title"""
    print(f"\n{title}")
    print("-" * 60)

def check_database_connection():
    """Check if database connection is working"""
    print_section("1️⃣  Checking Database Connection")
    try:
        conn = get_db_connection()
        if conn:
            print("✓ Database connection successful")
            conn.close()
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_cors_configuration():
    """Check CORS configuration"""
    print_section("2️⃣  Checking CORS Configuration")
    try:
        print(f"CORS_ORIGINS: {Config.CORS_ORIGINS}")
        print(f"CORS_ALLOW_CREDENTIALS: {Config.CORS_ALLOW_CREDENTIALS}")
        
        # Check if admin domain is in CORS origins
        admin_domains = [
            'https://admin.moneyone.co.in',
            'http://localhost:5173',
            'http://localhost:5174'
        ]
        
        missing_domains = []
        for domain in admin_domains:
            if domain not in Config.CORS_ORIGINS and '*' not in Config.CORS_ORIGINS:
                missing_domains.append(domain)
        
        if missing_domains:
            print(f"⚠ Missing domains in CORS_ORIGINS: {', '.join(missing_domains)}")
            return False
        else:
            print("✓ All required domains are in CORS_ORIGINS")
            return True
    except Exception as e:
        print(f"❌ Error checking CORS: {e}")
        return False

def check_admin_users():
    """Check admin users table"""
    print_section("3️⃣  Checking Admin Users Table")
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return False
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT admin_id, is_active, locked_until, login_attempts, 
                       last_login, password_changed_at
                FROM admin_users 
                ORDER BY last_login DESC
                LIMIT 5
            """)
            admins = cursor.fetchall()
            
            if not admins:
                print("⚠ No admin users found in database")
                conn.close()
                return False
            
            print(f"✓ Found {len(admins)} admin user(s):\n")
            for admin in admins:
                status = "🟢 Active" if admin['is_active'] else "🔴 Inactive"
                locked = ""
                if admin['locked_until']:
                    if datetime.now() < admin['locked_until']:
                        locked = f"🔒 Locked until {admin['locked_until']}"
                    else:
                        locked = "🔓 Lock expired"
                else:
                    locked = "🔓 Unlocked"
                
                print(f"  Admin ID: {admin['admin_id']}")
                print(f"    Status: {status}")
                print(f"    Lock Status: {locked}")
                print(f"    Login Attempts: {admin['login_attempts']}")
                print(f"    Last Login: {admin['last_login'] or 'Never'}")
                print(f"    Password Changed: {admin['password_changed_at'] or 'Never'}")
                print()
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking admin users: {e}")
        return False

def check_specific_admin(admin_id):
    """Check specific admin account details"""
    print_section(f"4️⃣  Checking Specific Admin: {admin_id}")
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return False
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM admin_users WHERE admin_id = %s
            """, (admin_id,))
            admin = cursor.fetchone()
            
            if not admin:
                print(f"❌ Admin '{admin_id}' not found")
                conn.close()
                return False
            
            print(f"✓ Admin '{admin_id}' found\n")
            print(f"  Is Active: {admin['is_active']}")
            print(f"  Login Attempts: {admin['login_attempts']}")
            print(f"  Locked Until: {admin['locked_until'] or 'Not locked'}")
            print(f"  Last Login: {admin['last_login'] or 'Never'}")
            print(f"  Password Changed At: {admin['password_changed_at'] or 'Never'}")
            print(f"  Must Change Password: {admin.get('must_change_password', False)}")
            
            # Check if account is locked
            if admin['locked_until'] and datetime.now() < admin['locked_until']:
                print(f"\n⚠ Account is LOCKED until {admin['locked_until']}")
                print("  Wait for lock to expire or reset in database")
                return False
            
            # Check if account is inactive
            if not admin['is_active']:
                print("\n⚠ Account is INACTIVE")
                return False
            
            print("\n✓ Account is active and not locked")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking admin: {e}")
        return False

def test_cors_preflight():
    """Test CORS preflight request"""
    print_section("5️⃣  Testing CORS Preflight Request")
    try:
        url = "https://api.moneyone.co.in/api/admin/login"
        headers = {
            "Origin": "https://admin.moneyone.co.in",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        print(f"Testing: OPTIONS {url}")
        print(f"Origin: {headers['Origin']}\n")
        
        response = requests.options(url, headers=headers, timeout=10)
        
        print(f"HTTP Status: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
        print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NOT SET')}")
        print(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'NOT SET')}")
        print(f"Access-Control-Allow-Credentials: {response.headers.get('Access-Control-Allow-Credentials', 'NOT SET')}")
        
        if response.status_code in [200, 204]:
            print("\n✓ CORS preflight passed")
            return True
        else:
            print(f"\n❌ CORS preflight failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")
        return False

def test_login_endpoint():
    """Test login endpoint with dummy credentials"""
    print_section("6️⃣  Testing Login Endpoint")
    try:
        url = "https://api.moneyone.co.in/api/admin/login"
        headers = {
            "Origin": "https://admin.moneyone.co.in",
            "Content-Type": "application/json"
        }
        data = {
            "adminId": "test_dummy_user",
            "password": "test_dummy_password"
        }
        
        print(f"Testing: POST {url}")
        print(f"Origin: {headers['Origin']}")
        print(f"Payload: {data}\n")
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"HTTP Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 400 or response.status_code == 401:
            print("\n✓ Endpoint is accessible (authentication failed as expected with dummy credentials)")
            return True
        elif response.status_code == 403:
            print("\n❌ 403 Forbidden - CORS or authentication issue")
            print("This is the error you're experiencing!")
            return False
        elif response.status_code == 500:
            print("\n❌ 500 Internal Server Error - Backend issue")
            return False
        else:
            print(f"\n⚠ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        return False

def check_jwt_configuration():
    """Check JWT configuration"""
    print_section("7️⃣  Checking JWT Configuration")
    try:
        print(f"JWT_SECRET_KEY: {'SET' if Config.JWT_SECRET_KEY else 'NOT SET'}")
        print(f"JWT_ACCESS_TOKEN_EXPIRES: {Config.JWT_ACCESS_TOKEN_EXPIRES} seconds")
        
        if not Config.JWT_SECRET_KEY or Config.JWT_SECRET_KEY == 'your-super-secret-jwt-key':
            print("\n⚠ JWT_SECRET_KEY is not properly configured")
            return False
        
        print("\n✓ JWT configuration looks good")
        return True
    except Exception as e:
        print(f"❌ Error checking JWT: {e}")
        return False

def unlock_admin_account(admin_id):
    """Unlock admin account"""
    print_section(f"🔓 Unlocking Admin Account: {admin_id}")
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return False
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE admin_users 
                SET locked_until = NULL, login_attempts = 0
                WHERE admin_id = %s
            """, (admin_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✓ Admin account '{admin_id}' unlocked successfully")
                print("  Login attempts reset to 0")
                conn.close()
                return True
            else:
                print(f"❌ Admin '{admin_id}' not found")
                conn.close()
                return False
    except Exception as e:
        print(f"❌ Error unlocking account: {e}")
        return False

def main():
    """Main diagnostic function"""
    print_header("Admin Login 403 Forbidden Error Diagnosis")
    
    results = {
        'database': False,
        'cors': False,
        'admin_users': False,
        'jwt': False,
        'cors_preflight': False,
        'login_endpoint': False
    }
    
    # Run all checks
    results['database'] = check_database_connection()
    results['cors'] = check_cors_configuration()
    results['admin_users'] = check_admin_users()
    results['jwt'] = check_jwt_configuration()
    results['cors_preflight'] = test_cors_preflight()
    results['login_endpoint'] = test_login_endpoint()
    
    # Check specific admin if provided
    if len(sys.argv) > 1:
        admin_id = sys.argv[1]
        check_specific_admin(admin_id)
        
        # Ask if user wants to unlock
        if len(sys.argv) > 2 and sys.argv[2] == '--unlock':
            unlock_admin_account(admin_id)
    
    # Summary
    print_header("Diagnosis Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nChecks Passed: {passed}/{total}\n")
    
    for check, result in results.items():
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {check.replace('_', ' ').title()}: {status}")
    
    # Recommendations
    print_header("Recommendations")
    
    if not results['cors']:
        print("\n🔧 Fix CORS Configuration:")
        print("  Run: ./fix_admin_login_403.sh")
        print("  Or manually add https://admin.moneyone.co.in to CORS_ORIGINS in .env")
    
    if not results['cors_preflight'] or not results['login_endpoint']:
        print("\n🔧 CORS Issue Detected:")
        print("  1. Update CORS_ORIGINS in backend/.env")
        print("  2. Restart backend: sudo systemctl restart moneyone-api")
        print("  3. Clear browser cache and cookies")
    
    if not results['database']:
        print("\n🔧 Database Connection Issue:")
        print("  Check database credentials in backend/.env")
        print("  Verify database server is running")
    
    if not results['jwt']:
        print("\n🔧 JWT Configuration Issue:")
        print("  Set a strong JWT_SECRET_KEY in backend/.env")
    
    print("\n" + "=" * 60)
    print("\nUsage:")
    print("  python3 backend/diagnose_admin_login_403.py")
    print("  python3 backend/diagnose_admin_login_403.py <admin_id>")
    print("  python3 backend/diagnose_admin_login_403.py <admin_id> --unlock")
    print("\nExample:")
    print("  python3 backend/diagnose_admin_login_403.py admin001")
    print("  python3 backend/diagnose_admin_login_403.py admin001 --unlock")
    print()

if __name__ == "__main__":
    main()
