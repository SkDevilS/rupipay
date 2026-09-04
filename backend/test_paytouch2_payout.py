#!/usr/bin/env python3
"""
Test PayTouch2 Payout Integration
Tests the complete PayTouch2 payout flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paytouch2_service import paytouch2_service
from database import get_db_connection
import json
from datetime import datetime

def test_paytouch2_connection():
    """Test basic PayTouch2 API connectivity"""
    print("🔧 Testing PayTouch2 API Connection")
    print("=" * 50)
    
    # Test with a dummy status check
    result = paytouch2_service.check_payout_status(
        transaction_id="TEST_TXN_123",
        external_ref="TEST_REF_123"
    )
    
    print(f"Connection Test Result: {json.dumps(result, indent=2)}")
    
    if result.get('success') or 'Status check failed' in result.get('message', ''):
        print("✅ PayTouch2 API is reachable")
        return True
    else:
        print("❌ PayTouch2 API connection failed")
        return False

def test_paytouch2_admin_payout():
    """Test admin personal payout via PayTouch2"""
    print("\n🔧 Testing PayTouch2 Admin Personal Payout")
    print("=" * 50)
    
    # Test payout data
    payout_data = {
        'reference_id': f"TEST_ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'amount': 100.00,
        'bene_name': 'Test Admin User',
        'bene_account': '1234567890',
        'bene_ifsc': 'SBIN0001234',
        'bank_name': 'State Bank of India',
        'bank_branch': 'Test Branch',
        'narration': 'Test admin payout',
        'bene_mobile': '9876543210',
        'bene_email': 'admin@test.com'
    }
    
    print(f"Test Payout Data: {json.dumps(payout_data, indent=2)}")
    
    result = paytouch2_service.initiate_payout(
        merchant_id=None,
        payout_data=payout_data,
        admin_id='ADMIN_TEST'
    )
    
    print(f"Admin Payout Result: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ Admin payout initiated successfully")
        return result
    else:
        print("❌ Admin payout failed")
        return None

def test_paytouch2_merchant_payout():
    """Test merchant payout via PayTouch2"""
    print("\n🔧 Testing PayTouch2 Merchant Payout")
    print("=" * 50)
    
    # First check if test merchant exists
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return None
    
    try:
        with conn.cursor() as cursor:
            # Check for a test merchant
            cursor.execute("""
                SELECT merchant_id, full_name, scheme_id
                FROM merchants
                WHERE is_active = TRUE
                LIMIT 1
            """)
            merchant = cursor.fetchone()
            
            if not merchant:
                print("❌ No active merchant found for testing")
                return None
            
            print(f"Using test merchant: {merchant['merchant_id']} - {merchant['full_name']}")
            
            # Test payout data
            payout_data = {
                'reference_id': f"TEST_MERCHANT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'amount': 50.00,
                'bene_name': 'Test Merchant Beneficiary',
                'bene_account': '9876543210',
                'bene_ifsc': 'HDFC0001234',
                'bank_name': 'HDFC Bank',
                'bank_branch': 'Test Branch',
                'narration': 'Test merchant payout',
                'bene_mobile': '9876543210',
                'bene_email': 'merchant@test.com'
            }
            
            print(f"Test Payout Data: {json.dumps(payout_data, indent=2)}")
            
            result = paytouch2_service.initiate_payout(
                merchant_id=merchant['merchant_id'],
                payout_data=payout_data,
                admin_id=None
            )
            
            print(f"Merchant Payout Result: {json.dumps(result, indent=2)}")
            
            if result.get('success'):
                print("✅ Merchant payout initiated successfully")
                return result
            else:
                print("❌ Merchant payout failed")
                return None
                
    finally:
        conn.close()

def test_paytouch2_status_check():
    """Test PayTouch2 status check API"""
    print("\n🔧 Testing PayTouch2 Status Check")
    print("=" * 50)
    
    # Test with dummy transaction ID
    result = paytouch2_service.check_payout_status(
        transaction_id="DUMMY_TXN_123",
        external_ref="DUMMY_REF_123"
    )
    
    print(f"Status Check Result: {json.dumps(result, indent=2)}")
    
    if result.get('success') or 'not found' in result.get('message', '').lower():
        print("✅ Status check API is working")
        return True
    else:
        print("❌ Status check API failed")
        return False

def check_paytouch2_configuration():
    """Check PayTouch2 configuration"""
    print("\n🔧 Checking PayTouch2 Configuration")
    print("=" * 50)
    
    from config import Config
    
    print(f"PayTouch2 Base URL: {Config.PAYTOUCH2_BASE_URL}")
    print(f"PayTouch2 Token: {Config.PAYTOUCH2_TOKEN[:10]}...")
    
    if not Config.PAYTOUCH2_BASE_URL or not Config.PAYTOUCH2_TOKEN:
        print("❌ PayTouch2 configuration is incomplete")
        return False
    
    print("✅ PayTouch2 configuration looks good")
    return True

def check_database_setup():
    """Check if database is ready for PayTouch2"""
    print("\n🔧 Checking Database Setup")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if service_routing table exists and has PayTouch2 entries
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM service_routing
                WHERE pg_partner = 'Paytouch2'
            """)
            result = cursor.fetchone()
            
            print(f"PayTouch2 service routing entries: {result['count']}")
            
            # Check payout_transactions table structure
            cursor.execute("DESCRIBE payout_transactions")
            columns = [row['Field'] for row in cursor.fetchall()]
            
            required_columns = ['pg_partner', 'pg_txn_id', 'status', 'utr']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ Missing columns in payout_transactions: {missing_columns}")
                return False
            
            print("✅ Database structure is ready for PayTouch2")
            return True
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run all PayTouch2 tests"""
    print("🚀 PayTouch2 Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration Check", check_paytouch2_configuration),
        ("Database Setup Check", check_database_setup),
        ("API Connection Test", test_paytouch2_connection),
        ("Status Check Test", test_paytouch2_status_check),
        ("Admin Payout Test", test_paytouch2_admin_payout),
        ("Merchant Payout Test", test_paytouch2_merchant_payout),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PayTouch2 integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")
    
    print("\n📝 Next Steps:")
    print("1. Configure PayTouch2 callback URL in dashboard:")
    print("   https://api.moneyone.co.in/api/callback/paytouch2/payout")
    print("2. Add PayTouch2 to service routing for merchants")
    print("3. Test with real transactions")

if __name__ == '__main__':
    main()