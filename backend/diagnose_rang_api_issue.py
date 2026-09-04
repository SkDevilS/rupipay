#!/usr/bin/env python3
"""
Diagnose Rang API connectivity and configuration issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
from config import Config
import requests
import json
from datetime import datetime

def test_rang_api_connectivity():
    """Test basic connectivity to Rang API"""
    print("RANG API CONNECTIVITY TEST")
    print("=" * 50)
    
    try:
        rang_service = RangService()
        
        print(f"Base URL: {rang_service.base_url}")
        print(f"MID: {rang_service.mid}")
        print(f"Email: {rang_service.email}")
        print(f"Secret Key: {rang_service.secret_key[:10]}...")
        
        # Test basic connectivity
        test_url = f"{rang_service.base_url}/api/payin/v1/status-check"
        print(f"\nTesting URL: {test_url}")
        
        # Test with a dummy payload to see response format
        test_payload = {
            "RefId": "TEST123456789",
            "Service_Id": "1"
        }
        
        headers = rang_service.get_headers()
        print(f"Headers: {headers}")
        
        response = requests.post(test_url, json=test_payload, headers=headers, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 404:
            print("\n⚠️ 404 Error - Possible issues:")
            print("1. API endpoint URL is incorrect")
            print("2. API version is wrong")
            print("3. Service is not available")
        elif response.status_code == 401:
            print("\n⚠️ 401 Error - Authentication issue:")
            print("1. Check MID, Email, Secret Key")
            print("2. Verify credentials with Rang team")
        elif response.status_code == 400:
            print("\n⚠️ 400 Error - Bad Request:")
            print("1. Payload format might be incorrect")
            print("2. Required fields missing")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing connectivity: {e}")
        return False

def check_rang_credentials():
    """Check if Rang credentials are properly configured"""
    print("\nRANG CREDENTIALS CHECK")
    print("=" * 50)
    
    print(f"RANG_BASE_URL: {Config.RANG_BASE_URL}")
    print(f"RANG_MID: {Config.RANG_MID}")
    print(f"RANG_EMAIL: {Config.RANG_EMAIL}")
    print(f"RANG_SECRET_KEY: {'*' * len(Config.RANG_SECRET_KEY) if Config.RANG_SECRET_KEY else 'NOT SET'}")
    
    missing_configs = []
    if not Config.RANG_BASE_URL:
        missing_configs.append("RANG_BASE_URL")
    if not Config.RANG_MID:
        missing_configs.append("RANG_MID")
    if not Config.RANG_EMAIL:
        missing_configs.append("RANG_EMAIL")
    if not Config.RANG_SECRET_KEY:
        missing_configs.append("RANG_SECRET_KEY")
    
    if missing_configs:
        print(f"\n❌ Missing configurations: {', '.join(missing_configs)}")
        return False
    else:
        print(f"\n✅ All credentials are configured")
        return True

def test_different_api_endpoints():
    """Test different possible API endpoints"""
    print("\nTESTING DIFFERENT API ENDPOINTS")
    print("=" * 50)
    
    base_url = Config.RANG_BASE_URL
    endpoints_to_test = [
        "/api/payin/v1/status-check",
        "/api/v1/payin/status-check", 
        "/api/payin/status-check",
        "/payin/v1/status-check",
        "/status-check",
        "/api/v1/status-check"
    ]
    
    test_payload = {
        "RefId": "TEST123456789",
        "Service_Id": "1"
    }
    
    rang_service = RangService()
    headers = rang_service.get_headers()
    
    for endpoint in endpoints_to_test:
        test_url = f"{base_url}{endpoint}"
        print(f"\nTesting: {test_url}")
        
        try:
            response = requests.post(test_url, json=test_payload, headers=headers, timeout=5)
            print(f"  Status: {response.status_code}")
            if response.status_code != 404:
                print(f"  Response: {response.text[:100]}...")
                if response.status_code == 200:
                    print(f"  ✅ This endpoint works!")
                    return test_url
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def check_recent_transaction_creation():
    """Check if recent transactions were actually created on Rang side"""
    print("\nCHECKING RECENT TRANSACTION CREATION")
    print("=" * 50)
    
    from database import get_db_connection
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get most recent transaction
        cursor.execute("""
            SELECT txn_id, order_id, amount, status, pg_txn_id, created_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not txn:
            print("❌ No Rang transactions found")
            return
        
        print(f"Most recent transaction:")
        print(f"  TXN ID: {txn['txn_id']}")
        print(f"  Order ID: {txn['order_id']}")
        print(f"  Amount: ₹{txn['amount']}")
        print(f"  Status: {txn['status']}")
        print(f"  PG TXN ID: {txn['pg_txn_id']}")
        print(f"  Created: {txn['created_at']}")
        
        # Check if PG TXN ID exists (indicates successful creation on Rang side)
        if txn['pg_txn_id']:
            print(f"\n✅ Transaction has PG TXN ID - likely created on Rang side")
            print(f"   Try using PG TXN ID for status check: {txn['pg_txn_id']}")
        else:
            print(f"\n⚠️ No PG TXN ID - transaction may not have been created on Rang side")
            print(f"   This could explain the 404 errors")
        
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")

def main():
    print("RANG API DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check credentials
    creds_ok = check_rang_credentials()
    
    if not creds_ok:
        print("\n❌ Cannot proceed without proper credentials")
        return
    
    # Step 2: Test connectivity
    connectivity_ok = test_rang_api_connectivity()
    
    # Step 3: Test different endpoints if main one fails
    if not connectivity_ok:
        print("\nTrying alternative endpoints...")
        working_endpoint = test_different_api_endpoints()
        
        if working_endpoint:
            print(f"\n✅ Found working endpoint: {working_endpoint}")
        else:
            print(f"\n❌ No working endpoints found")
    
    # Step 4: Check transaction creation
    check_recent_transaction_creation()
    
    print(f"\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    print("1. Contact Rang team to verify:")
    print("   - Correct API endpoint URL")
    print("   - API credentials (MID, Email, Secret Key)")
    print("   - API documentation for status check")
    print("2. Check if transactions are being created successfully")
    print("3. Verify RefID format expected by Rang")
    print("4. Test with Rang's provided sample data")

if __name__ == "__main__":
    main()