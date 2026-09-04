#!/usr/bin/env python3
"""
Test Airpay Token Generation with Decryption
"""

import requests
import os
from config import Config
from airpay_service import AirpayService

def test_airpay_token_with_decryption():
    """Test Airpay OAuth2 token generation with decryption"""
    
    print("🧪 Testing Airpay Token Generation with Decryption")
    print("=" * 60)
    
    # Initialize Airpay service
    airpay = AirpayService()
    
    print(f"Base URL: {airpay.base_url}")
    print(f"Client ID: {airpay.client_id}")
    print(f"Client Secret: {airpay.client_secret[:10]}...")
    print(f"Merchant ID: {airpay.merchant_id}")
    print(f"Encryption Key: {airpay.encryption_key[:10]}...")
    print()
    
    # Test token generation
    print("📤 Testing token generation...")
    result = airpay.generate_access_token()
    
    print(f"Result: {result}")
    
    if result['success']:
        print("✅ Token generation successful!")
        print(f"Access Token: {result['token'][:30]}..." if result.get('token') else "No token returned")
    else:
        print("❌ Token generation failed")
        print(f"Error: {result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    test_airpay_token_with_decryption()