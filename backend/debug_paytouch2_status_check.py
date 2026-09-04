#!/usr/bin/env python3
"""
Debug PayTouch2 Status Check Issue
Investigate why status check API is returning FAILED for successful transactions
"""

from database import get_db_connection
from paytouch2_service import paytouch2_service
import json

def debug_paytouch2_status_check():
    """Debug PayTouch2 status check issue"""
    
    print("🔍 Debugging PayTouch2 Status Check Issue")
    print("=" * 60)
    
    # Test with the transaction from your screenshot
    txn_id = "TXN849864DD0FB5"
    pg_txn_id = "DP20260317153909D985D8"
    reference_id = "DP20260317153909D985D8"
    
    print(f"Testing transaction: {txn_id}")
    print(f"PG TXN ID: {pg_txn_id}")
    print(f"Reference ID: {reference_id}")
    print("-" * 60)
    
    # Get current transaction status from database
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT txn_id, reference_id, status, pg_txn_id, utr, 
                       created_at, completed_at, error_message
                FROM payout_transactions
                WHERE txn_id = %s OR reference_id = %s
            """, (txn_id, reference_id))
            
            txn = cursor.fetchone()
            
            if txn:
                print("📊 Current Database Status:")
                print(f"  TXN ID: {txn['txn_id']}")
                print(f"  Reference ID: {txn['reference_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  PG TXN ID: {txn['pg_txn_id']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Completed: {txn['completed_at']}")
                print(f"  Error: {txn['error_message']}")
            else:
                print("❌ Transaction not found in database")
                return
        
        print("\n" + "=" * 60)
        print("🔍 Testing PayTouch2 Status Check API")
        print("=" * 60)
        
        # Test 1: Check with transaction_id
        print("\n1️⃣ Testing with transaction_id:")
        result1 = paytouch2_service.check_payout_status(
            transaction_id=txn['pg_txn_id'],
            external_ref=None
        )
        print(f"Result: {json.dumps(result1, indent=2)}")
        
        # Test 2: Check with external_ref
        print("\n2️⃣ Testing with external_ref:")
        result2 = paytouch2_service.check_payout_status(
            transaction_id=None,
            external_ref=txn['reference_id']
        )
        print(f"Result: {json.dumps(result2, indent=2)}")
        
        # Test 3: Check with both
        print("\n3️⃣ Testing with both transaction_id and external_ref:")
        result3 = paytouch2_service.check_payout_status(
            transaction_id=txn['pg_txn_id'],
            external_ref=txn['reference_id']
        )
        print(f"Result: {json.dumps(result3, indent=2)}")
        
        print("\n" + "=" * 60)
        print("🔍 Analysis")
        print("=" * 60)
        
        # Analyze results
        results = [result1, result2, result3]
        test_names = ["transaction_id only", "external_ref only", "both parameters"]
        
        for i, result in enumerate(results):
            print(f"\n{test_names[i]}:")
            if result.get('success'):
                api_status = result.get('status', 'UNKNOWN')
                api_utr = result.get('utr')
                print(f"  ✅ API Success: Status={api_status}, UTR={api_utr}")
                
                # Check status mapping
                status_map = {
                    'SUCCESS': 'SUCCESS',
                    'PENDING': 'QUEUED',
                    'FAILED': 'FAILED',
                    'PROCESSING': 'INPROCESS'
                }
                mapped_status = status_map.get(api_status.upper(), 'QUEUED')
                print(f"  📊 Mapped Status: {api_status} → {mapped_status}")
                
                if mapped_status != txn['status']:
                    print(f"  ⚠️  STATUS MISMATCH: DB={txn['status']}, API={mapped_status}")
                else:
                    print(f"  ✅ Status matches database")
            else:
                print(f"  ❌ API Error: {result.get('message')}")
        
        print("\n" + "=" * 60)
        print("🔧 Recommendations")
        print("=" * 60)
        
        # Check if any result shows SUCCESS
        success_results = [r for r in results if r.get('success') and r.get('status') == 'SUCCESS']
        failed_results = [r for r in results if r.get('success') and r.get('status') == 'FAILED']
        
        if success_results and failed_results:
            print("⚠️  INCONSISTENT API RESPONSES:")
            print("   Some API calls return SUCCESS, others return FAILED")
            print("   This suggests PayTouch2 API has inconsistent behavior")
            print("   Recommendation: Use the parameter combination that returns SUCCESS")
        
        elif failed_results and not success_results:
            print("❌ ALL API CALLS RETURN FAILED:")
            print("   This suggests either:")
            print("   1. The transaction actually failed at PayTouch2")
            print("   2. PayTouch2 API endpoint or parameters are incorrect")
            print("   3. PayTouch2 API has a bug")
        
        elif success_results and not failed_results:
            print("✅ ALL API CALLS RETURN SUCCESS:")
            print("   The transaction is successful at PayTouch2")
            print("   The issue might be in the status check endpoint logic")
        
        else:
            print("❌ NO SUCCESSFUL API CALLS:")
            print("   PayTouch2 API is not responding correctly")
            print("   Check API credentials and endpoint URL")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def test_paytouch2_api_endpoints():
    """Test different PayTouch2 API endpoints"""
    
    print("\n" + "=" * 60)
    print("🔍 Testing PayTouch2 API Endpoints")
    print("=" * 60)
    
    from config import Config
    import requests
    
    base_url = Config.PAYTOUCH2_BASE_URL
    token = Config.PAYTOUCH2_TOKEN
    
    print(f"Base URL: {base_url}")
    print(f"Token: {token[:10]}..." if token else "Token: NOT SET")
    
    # Test different endpoint variations
    endpoints = [
        "/api/payout/v2/get-report-status",
        "/api/payout/v2/get_report_status", 
        "/api/payout/v2/status",
        "/api/payout/v2/check-status",
        "/api/payout/v2/report-status"
    ]
    
    test_payload = {
        'token': token,
        'transaction_id': 'DP20260317153909D985D8',
        'external_ref': 'DP20260317153909D985D8'
    }
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        try:
            url = f"{base_url}{endpoint}"
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=test_payload,
                timeout=10
            )
            
            print(f"  Status Code: {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get('status', 'UNKNOWN')
                    print(f"  ✅ SUCCESS: Status = {status}")
                except:
                    print(f"  ⚠️  Response not JSON")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == '__main__':
    debug_paytouch2_status_check()
    test_paytouch2_api_endpoints()