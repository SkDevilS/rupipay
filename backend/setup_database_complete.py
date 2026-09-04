#!/usr/bin/env python3
"""
MoneyOne Complete Database Setup Script
========================================
This script creates the entire database from scratch including:
- All 25 tables with proper indexes and foreign keys
- Admin user with default credentials
- Default commercial scheme with charges
- Test merchant account
- Initial wallet balances

Usage:
    python setup_database_complete.py

Requirements:
    - MySQL server running
    - Database credentials configured in .env file
    - Python packages: pymysql, bcrypt

Author: MoneyOne Team
Version: 1.0
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main execution function"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MoneyOne Database Setup" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Check if config is available
    try:
        from config import Config
        print("✅ Configuration loaded successfully")
        print(f"   Database: {Config.DB_NAME}")
        print(f"   Host: {Config.DB_HOST}")
        print(f"   User: {Config.DB_USER}")
        print()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print()
        print("Please ensure:")
        print("  1. .env file exists in backend directory")
        print("  2. Database credentials are configured")
        print("  3. config.py is present")
        print()
        return False
    
    # Test database connection
    print("Testing database connection...")
    try:
        import pymysql
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        connection.close()
        print("✅ Database connection successful")
        print()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("Please ensure:")
        print("  1. MySQL server is running")
        print("  2. Database credentials are correct")
        print("  3. User has necessary privileges")
        print()
        return False
    
    # Confirm before proceeding
    print("⚠️  WARNING: This will create/recreate the database and all tables.")
    print("   Any existing data will be preserved if tables already exist.")
    print()
    response = input("Do you want to continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Setup cancelled by user")
        return False
    
    print()
    print("=" * 80)
    print("Starting database setup...")
    print("=" * 80)
    print()
    
    # Step 1: Create all tables
    try:
        from create_complete_database import create_complete_database
        print("Phase 1: Creating database and tables...")
        print("-" * 80)
        if not create_complete_database():
            print("\n❌ Table creation failed")
            return False
    except Exception as e:
        print(f"\n❌ Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 80)
    print("✅ DATABASE SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print()
            print("🎉 Your MoneyOne database is ready!")
            print()
            print("Quick Start Guide:")
            print("  1. Start backend: python app.py")
            print("  2. Login to admin: https://admin.moneyone.co.in")
            print("  3. Use credentials shown above")
            print()
            sys.exit(0)
        else:
            print()
            print("❌ Setup failed. Please check the errors above.")
            print()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
