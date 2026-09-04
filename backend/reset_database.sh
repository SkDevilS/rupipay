#!/bin/bash

# Reset Database and Create Admin User
# Admin ID: 6239572985
# Password: Admin@123

echo "=============================================================="
echo "⚠️  WARNING: DATABASE RESET"
echo "=============================================================="
echo ""
echo "This script will:"
echo "  1. DROP the entire moneyone_db database"
echo "  2. CREATE a fresh moneyone_db database"
echo "  3. Import all tables from moneyone_db.sql"
echo "  4. Create admin user with ID: 6239572985"
echo ""
echo "⚠️  ALL EXISTING DATA WILL BE LOST!"
echo "=============================================================="
echo ""

read -p "Type 'YES' to continue or anything else to cancel: " confirm

if [ "$confirm" != "YES" ]; then
    echo ""
    echo "❌ Database reset cancelled"
    exit 1
fi

echo ""
echo "=============================================================="
echo "Starting Database Reset..."
echo "=============================================================="

# Backup current database (optional)
echo ""
echo "📝 Creating backup (optional)..."
mysqldump -u root -p moneyone_db > backup_before_reset_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Backup created"
else
    echo "⚠️  Backup skipped (database might not exist)"
fi

# Drop and recreate database
echo ""
echo "📝 Dropping and recreating database..."
mysql -u root -p <<EOF
DROP DATABASE IF EXISTS moneyone_db;
CREATE DATABASE moneyone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

if [ $? -ne 0 ]; then
    echo "❌ Failed to drop/create database"
    exit 1
fi
echo "✅ Database recreated"

# Import SQL file
echo ""
echo "📝 Importing schema from moneyone_db.sql..."
mysql -u root -p moneyone_db < moneyone_db.sql

if [ $? -ne 0 ]; then
    echo "❌ Failed to import SQL file"
    exit 1
fi
echo "✅ Schema imported"

# Create admin user using Python
echo ""
echo "📝 Creating admin user..."
source venv/bin/activate
python3 create_admin_user.py

# Restart backend
echo ""
echo "📝 Restarting backend service..."
sudo supervisorctl restart moneyone-api

echo ""
echo "=============================================================="
echo "✅ DATABASE RESET COMPLETED!"
echo "=============================================================="
echo ""
echo "Admin Login Credentials:"
echo "  Admin ID: 6239572985"
echo "  Password: Admin@123"
echo ""
echo "Login at: https://admin.moneyone.co.in"
echo "=============================================================="
