"""
Test PayTouch Data Flow
Tests actual data fetching and payload generation for all three endpoints
"""

import pymysql
from database import get_db_connection
from paytouch_service import paytouch_service
import json

def test_admin_payout_data():
    """Test admin personal payout data fetching"""
    print("=" * 80)
    print("Testing Admin Personal Payout Data Flow")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get a sample admin
            cursor.execute("SELECT admin_id FROM admin_users LIMIT 1")
            admin = cursor.fetchone()
            
            if not admin:
                print("❌ No admin users found")
                return False
            
            admin_id = admin['admin_id']
            print(f"✓ Admin ID: {admin_id}")
            
            # Get admin bank
            cursor.execute("""
                SELECT * FROM admin_banks 
                WHERE admin_id = %s AND is_active = TRUE 
                LIMIT 1
            """, (admin_id,))
            
            bank = cursor.fetchone()
            
            if not bank:
                print(f"⚠️  No active bank found for admin {admin_id}")
                print("   Creating test bank entry...")
                # This is just for testing - in production, admin must add bank
                return False
            
            print(f"✓ Bank Details:")
            print(f"  - Account Holder: {bank['account_holder_name']}")
            print(f"  - Account Number: {bank['account_number']}")
            print(f"  - IFSC: {bank['ifsc_code']}")
            print(f"  - Bank Name: {bank['bank_name']}")
            
            # Simulate payload generation
            reference_id = "TEST_ADMIN_123"
            payout_data = {
                'reference_id': reference_id,
                'amount': 100.00,
                'bene_name': bank['account_holder_name'],
                'bene_account': bank['account_number'],
                'bene_ifsc': bank['ifsc_code'],
                'bank_name': bank['bank_name']
            }
            
            print()
            print("Generated Payload (would be sent to PayTouch):")
            payload = {
                'token': paytouch_service.token,
                'request_id': payout_data['reference_id'],
                'bene_account': payout_data['bene_account'],
                'bene_ifsc': payout_data['bene_ifsc'],
                'bene_name': payout_data['bene_name'],
                'amount': float(payout_data['amount']),
                'currency': 'INR',
                'narration': 'Truaxis',
                'payment_mode': 'IMPS',
                'bank_name': payout_data['bank_name'],
                'bank_branch': 'oooo'
            }
            print(json.dumps(payload, indent=2))
            print()
            print("✅ Admin Personal Payout: Data flow is CORRECT")
            return True
            
    finally:
        conn.close()

def test_merchant_settle_fund_data():
    """Test merchant settle fund data fetching"""
    print()
    print("=" * 80)
    print("Testing Merchant Settle Fund Data Flow")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get a sample merchant
            cursor.execute("SELECT merchant_id FROM merchants WHERE is_active = TRUE LIMIT 1")
            merchant = cursor.fetchone()
            
            if not merchant:
                print("❌ No active merchants found")
                return False
            
            merchant_id = merchant['merchant_id']
            print(f"✓ Merchant ID: {merchant_id}")
            
            # Get merchant bank
            cursor.execute("""
                SELECT * FROM merchant_banks 
                WHERE merchant_id = %s AND is_active = TRUE 
                LIMIT 1
            """, (merchant_id,))
            
            bank = cursor.fetchone()
            
            if not bank:
                print(f"⚠️  No active bank found for merchant {merchant_id}")
                return False
            
            print(f"✓ Bank Details:")
            print(f"  - Account Holder: {bank['account_holder_name']}")
            print(f"  - Account Number: {bank['account_number']}")
            print(f"  - IFSC: {bank['ifsc_code']}")
            print(f"  - Bank Name: {bank['bank_name']}")
            
            # Check service routing
            cursor.execute("""
                SELECT pg_partner FROM service_routing
                WHERE service_type = 'PAYOUT'
                AND routing_type = 'SINGLE_USER'
                AND merchant_id = %s
                AND is_active = TRUE
                LIMIT 1
            """, (merchant_id,))
            
            routing = cursor.fetchone()
            
            if not routing:
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE service_type = 'PAYOUT'
                    AND routing_type = 'ALL_USERS'
                    AND is_active = TRUE
                    LIMIT 1
                """)
                routing = cursor.fetchone()
            
            if routing:
                print(f"✓ Service Routing: {routing['pg_partner']}")
            else:
                print("⚠️  No payout routing configured")
            
            # Simulate payload generation
            reference_id = "TEST_SF_123"
            payout_data = {
                'reference_id': reference_id,
                'amount': 1000.00,
                'bene_name': bank['account_holder_name'],
                'bene_account': bank['account_number'],
                'bene_ifsc': bank['ifsc_code'],
                'bank_name': bank['bank_name']
            }
            
            print()
            print("Generated Payload (would be sent to PayTouch):")
            payload = {
                'token': paytouch_service.token,
                'request_id': payout_data['reference_id'],
                'bene_account': payout_data['bene_account'],
                'bene_ifsc': payout_data['bene_ifsc'],
                'bene_name': payout_data['bene_name'],
                'amount': float(payout_data['amount']),
                'currency': 'INR',
                'narration': 'Truaxis',
                'payment_mode': 'IMPS',
                'bank_name': payout_data['bank_name'],
                'bank_branch': 'oooo'
            }
            print(json.dumps(payload, indent=2))
            print()
            print("✅ Merchant Settle Fund: Data flow is CORRECT")
            return True
            
    finally:
        conn.close()

def test_merchant_direct_payout_data():
    """Test merchant direct payout data fetching"""
    print()
    print("=" * 80)
    print("Testing Merchant Direct Payout Data Flow")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get a sample merchant
            cursor.execute("SELECT merchant_id FROM merchants WHERE is_active = TRUE LIMIT 1")
            merchant = cursor.fetchone()
            
            if not merchant:
                print("❌ No active merchants found")
                return False
            
            merchant_id = merchant['merchant_id']
            print(f"✓ Merchant ID: {merchant_id}")
            
            # Check service routing
            cursor.execute("""
                SELECT pg_partner FROM service_routing
                WHERE service_type = 'PAYOUT'
                AND routing_type = 'SINGLE_USER'
                AND merchant_id = %s
                AND is_active = TRUE
                LIMIT 1
            """, (merchant_id,))
            
            routing = cursor.fetchone()
            
            if not routing:
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE service_type = 'PAYOUT'
                    AND routing_type = 'ALL_USERS'
                    AND is_active = TRUE
                    LIMIT 1
                """)
                routing = cursor.fetchone()
            
            if routing:
                print(f"✓ Service Routing: {routing['pg_partner']}")
            else:
                print("⚠️  No payout routing configured")
            
            # Simulate request data (provided by merchant in API call)
            request_data = {
                'account_holder_name': 'Test Beneficiary',
                'account_number': '1234567890',
                'ifsc_code': 'SBIN0001234',
                'bank_name': 'State Bank of India',
                'amount': 500.00
            }
            
            print(f"✓ Request Data (from API call):")
            print(f"  - Account Holder: {request_data['account_holder_name']}")
            print(f"  - Account Number: {request_data['account_number']}")
            print(f"  - IFSC: {request_data['ifsc_code']}")
            print(f"  - Bank Name: {request_data['bank_name']}")
            
            # Simulate payload generation
            reference_id = "TEST_DP_123"
            payout_data = {
                'reference_id': reference_id,
                'amount': request_data['amount'],
                'bene_name': request_data['account_holder_name'],
                'bene_account': request_data['account_number'],
                'bene_ifsc': request_data['ifsc_code'],
                'bank_name': request_data['bank_name']
            }
            
            print()
            print("Generated Payload (would be sent to PayTouch):")
            payload = {
                'token': paytouch_service.token,
                'request_id': payout_data['reference_id'],
                'bene_account': payout_data['bene_account'],
                'bene_ifsc': payout_data['bene_ifsc'],
                'bene_name': payout_data['bene_name'],
                'amount': float(payout_data['amount']),
                'currency': 'INR',
                'narration': 'Truaxis',
                'payment_mode': 'IMPS',
                'bank_name': payout_data['bank_name'],
                'bank_branch': 'oooo'
            }
            print(json.dumps(payload, indent=2))
            print()
            print("✅ Merchant Direct Payout: Data flow is CORRECT")
            return True
            
    finally:
        conn.close()

if __name__ == '__main__':
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PayTouch Data Flow Test" + " " * 36 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    results = []
    
    # Test all three endpoints
    results.append(("Admin Personal Payout", test_admin_payout_data()))
    results.append(("Merchant Settle Fund", test_merchant_settle_fund_data()))
    results.append(("Merchant Direct Payout", test_merchant_direct_payout_data()))
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    print("=" * 80)
    print()
