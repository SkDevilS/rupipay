"""
Test Advanced Search API Endpoint
This script tests the Flask API endpoint directly to diagnose the 500 error
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from getpass import getpass

# Configuration
BASE_URL = "http://localhost:5000"

def login(admin_id, password):
    """Login and get JWT token"""
    print("=" * 60)
    print("Step 1: Login to get admin token")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/admin/login"
    payload = {
        "adminId": admin_id,
        "password": password
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            token = data.get('token')
            print(f"\n✅ Login successful!")
            print(f"Token: {token[:50]}...")
            return token
        else:
            print(f"\n❌ Login failed: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"\n❌ Login error: {str(e)}")
        return None

def test_payin_advanced_search(token, merchant_id, mode, date=None, from_date=None, to_date=None):
    """Test payin advanced search endpoint"""
    print("\n" + "=" * 60)
    print("Step 2: Testing Payin Advanced Search")
    print("=" * 60)
    
    url = f"{BASE_URL}/payin/admin/advanced-search"
    
    # Build payload
    payload = {
        "merchant_id": merchant_id,
        "mode": mode
    }
    
    if mode == "single":
        payload["date"] = date
    else:
        payload["from_date"] = from_date
        payload["to_date"] = to_date
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    print(f"\nURL: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"\nSending request...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"\nResponse Body:")
            print(json.dumps(data, indent=2))
            
            if response.status_code == 200 and data.get('success'):
                print("\n✅ Payin advanced search successful!")
                
                # Display results
                result_data = data.get('data', {})
                print(f"\n📊 Results:")
                print(f"  Merchant: {result_data.get('merchant_name')} ({result_data.get('merchant_id')})")
                
                if mode == "single":
                    print(f"  Date: {result_data.get('date')}")
                    print(f"  Total Transactions: {result_data.get('total_transactions')}")
                    print(f"  Total Amount: ₹{result_data.get('total_amount'):,.2f}")
                    print(f"  Total Charges: ₹{result_data.get('total_charges'):,.2f}")
                    print(f"  Net Amount: ₹{result_data.get('net_amount'):,.2f}")
                else:
                    summary = result_data.get('summary', {})
                    print(f"  Date Range: {result_data.get('from_date')} to {result_data.get('to_date')}")
                    print(f"  Total Transactions: {summary.get('total_transactions')}")
                    print(f"  Total Amount: ₹{summary.get('total_amount'):,.2f}")
                    print(f"  Total Charges: ₹{summary.get('total_charges'):,.2f}")
                    print(f"  Net Amount: ₹{summary.get('net_amount'):,.2f}")
                    print(f"  Days: {len(result_data.get('daily_data', []))}")
                
                return True
            else:
                print(f"\n❌ Payin advanced search failed: {data.get('message')}")
                return False
                
        except json.JSONDecodeError:
            print(f"\n❌ Failed to parse JSON response")
            print(f"Raw response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n❌ Request error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_payout_advanced_search(token, merchant_id, mode, date=None, from_date=None, to_date=None):
    """Test payout advanced search endpoint"""
    print("\n" + "=" * 60)
    print("Step 3: Testing Payout Advanced Search")
    print("=" * 60)
    
    url = f"{BASE_URL}/payout/admin/advanced-search"
    
    # Build payload
    payload = {
        "merchant_id": merchant_id,
        "mode": mode
    }
    
    if mode == "single":
        payload["date"] = date
    else:
        payload["from_date"] = from_date
        payload["to_date"] = to_date
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    print(f"\nURL: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"\nSending request...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"\nResponse Body:")
            print(json.dumps(data, indent=2))
            
            if response.status_code == 200 and data.get('success'):
                print("\n✅ Payout advanced search successful!")
                
                # Display results
                result_data = data.get('data', {})
                print(f"\n📊 Results:")
                print(f"  Merchant: {result_data.get('merchant_name')} ({result_data.get('merchant_id')})")
                
                if mode == "single":
                    print(f"  Date: {result_data.get('date')}")
                    print(f"  Total Transactions: {result_data.get('total_transactions')}")
                    print(f"  Total Amount: ₹{result_data.get('total_amount'):,.2f}")
                    print(f"  Total Charges: ₹{result_data.get('total_charges'):,.2f}")
                    print(f"  Net Amount: ₹{result_data.get('net_amount'):,.2f}")
                else:
                    summary = result_data.get('summary', {})
                    print(f"  Date Range: {result_data.get('from_date')} to {result_data.get('to_date')}")
                    print(f"  Total Transactions: {summary.get('total_transactions')}")
                    print(f"  Total Amount: ₹{summary.get('total_amount'):,.2f}")
                    print(f"  Total Charges: ₹{summary.get('total_charges'):,.2f}")
                    print(f"  Net Amount: ₹{summary.get('net_amount'):,.2f}")
                    print(f"  Days: {len(result_data.get('daily_data', []))}")
                
                return True
            else:
                print(f"\n❌ Payout advanced search failed: {data.get('message')}")
                return False
                
        except json.JSONDecodeError:
            print(f"\n❌ Failed to parse JSON response")
            print(f"Raw response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n❌ Request error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🔍 Advanced Search API Test Tool\n")
    
    # Get credentials
    admin_id = input("Enter admin ID (phone/username): ").strip()
    password = getpass("Enter admin password: ")
    
    # Login
    token = login(admin_id, password)
    
    if not token:
        print("\n❌ Cannot proceed without valid token")
        sys.exit(1)
    
    # Get search parameters
    print("\n" + "=" * 60)
    print("Search Parameters")
    print("=" * 60)
    
    merchant_id = input("\nEnter merchant ID (default: 9000000001): ").strip() or "9000000001"
    
    mode = input("Enter mode (single/range, default: single): ").strip() or "single"
    
    if mode == "single":
        date = input("Enter date (YYYY-MM-DD, default: 2026-04-10): ").strip() or "2026-04-10"
        from_date = None
        to_date = None
    else:
        from_date = input("Enter from date (YYYY-MM-DD, default: 2026-04-01): ").strip() or "2026-04-01"
        to_date = input("Enter to date (YYYY-MM-DD, default: 2026-04-10): ").strip() or "2026-04-10"
        date = None
    
    # Test payin
    payin_success = test_payin_advanced_search(
        token, merchant_id, mode, date, from_date, to_date
    )
    
    # Test payout
    payout_success = test_payout_advanced_search(
        token, merchant_id, mode, date, from_date, to_date
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Payin Advanced Search: {'✅ PASSED' if payin_success else '❌ FAILED'}")
    print(f"Payout Advanced Search: {'✅ PASSED' if payout_success else '❌ FAILED'}")
    print("=" * 60)
    
    if payin_success and payout_success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)
