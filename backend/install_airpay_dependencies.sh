#!/bin/bash

# Install Airpay V4 Integration Dependencies
# This script installs the required Python packages for Airpay integration

echo "Installing Airpay V4 dependencies..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Install pycryptodome for AES encryption/decryption
pip3 install pycryptodome

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "Test the installation:"
echo "  python3 test_airpay_oauth2_complete.py"
