#!/bin/bash

# Automated fix for settlement_transactions table migration error
# This script will fix the foreign key constraint error and run migration

echo "=========================================="
echo "FIXING SETTLEMENT MIGRATION ERROR"
echo "=========================================="
echo ""

# Step 1: Check column types
echo "Step 1: Checking current column types..."
python3 check_merchant_id_type.py
echo ""
read -p "Press Enter to continue..."
echo ""

# Step 2: Drop incorrect table
echo "Step 2: Dropping incorrectly created settlement_transactions table..."
python3 fix_settlement_table.py

if [ $? -ne 0 ]; then
    echo "✗ Failed to drop table"
    exit 1
fi

echo ""
read -p "Press Enter to run migration..."
echo ""

# Step 3: Run migration with correct types
echo "Step 3: Running migration with correct column types..."
python3 migrate_settled_unsettled_wallet.py migrate

if [ $? -ne 0 ]; then
    echo "✗ Migration failed"
    exit 1
fi

echo ""
echo "Step 4: Verifying migration..."
python3 migrate_settled_unsettled_wallet.py status

echo ""
echo "=========================================="
echo "✅ MIGRATION FIX COMPLETED!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart backend"
echo "2. Test payin flow"
echo "3. Test settlement flow"
echo ""
