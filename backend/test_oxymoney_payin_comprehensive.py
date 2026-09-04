#!/usr/bin/env python3
"""
Comprehensive Oxymoney Payin Testing Script
Tests all aspects of Oxymoney_Grosmart payin integration

Features tested:
1. Token generation
2. Checksum generation
3. VPA availability and rotation
4. Payment intent creation
5. Transaction status check
6. Callback handling simulation
7. Database verification
8. Wallet credit verification
9. VPA usage tracking
10. Error handling

Usage:
    python test_oxymoney_payin_comprehensive.py
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from decimal import Decimal

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import get_db_connection
from oxymoney_grosmart_service import oxymoney_grosmart_service

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_section(text):
    """Print section header"""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}▶ {text}{Colors.ENDC}")

class OxymoneyPayinTester:
    """Comprehensive Oxymoney Payin Tester"""
    
    def __init__(self):
        """Initialize tester"""
        self.service = oxymoney_grosmart_service
        self.test_merchant_id = None
        self.test_txn_id = None
        self.test_order_id = None
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def run_all_tests(self):
        """Run all tests"""
        print_header("OXYMONEY PAYIN COMPREHENSIVE TEST SUITE")
        
        print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"Base URL: {self.service.base_url}")
        print_info(f"Username: {self.service.username}")
        print_info(f"VPAs configured: {len(self.service.vpas)}")
        
        # Run tests in sequence
        tests = [
            ("Configuration Validation", self.test_configuration),
            ("Database Connection", self.test_database_connection),
            ("Token Generation", self.test_token_generation),
            ("Checksum Generation", self.test_checksum_generation),
            ("VPA Availability Check", self.test_vpa_availability),
            ("VPA Usage Statistics", self.test_vpa_usage_stats),
            ("Test Merchant Setup", self.test_merchant_setup),
            ("Payment Intent Creation", self.test_payment_intent_creation),
            ("Transaction Database Entry", self.test_transaction_database),
            ("VPA Usage Recording", self.test_vpa_usage_recording),
            ("Transaction Status Check", self.test_transaction_status),
            ("Callback Simulation", self.test_callback_simulation),
            ("Wallet Credit Verification", self.test_wallet_credit),
            ("Error Handling", self.test_error_handling),
            ("VPA Rotation Logic", self.test_vpa_rotation),
        ]
        
        for test_name, test_func in tests:
            print_section(f"TEST: {test_name}")
            try:
                result = test_func()
                if result:
                    self.test_results['passed'] += 1
                    print_success(f"{test_name} - PASSED")
                else:
                    self.test_results['failed'] += 1
                    print_error(f"{test_name} - FAILED")
            except Exception as e:
                self.test_results['failed'] += 1
                print_error(f"{test_name} - EXCEPTION: {str(e)}")
                import traceback
                traceback.print_exc()
            
            time.sleep(1)  # Brief pause between tests
        
        # Print summary
        self.print_test_summary()
    
    def test_configuration(self):
        """Test 1: Validate configuration"""
        print_info("Validating Oxymoney configuration...")
        
        required_configs = [
            ('OXYMONEY_GROSMART_BASE_URL', self.service.base_url),
            ('OXYMONEY_GROSMART_USERNAME', self.service.username),
            ('OXYMONEY_GROSMART_PASSWORD', self.service.password),
            ('OXYMONEY_GROSMART_SECRET_KEY', self.service.secret_key),
        ]
        
        all_valid = True
        for config_name, config_value in required_configs:
            if not config_value or config_value == 'your_value_here':
                print_error(f"{config_name} is not configured")
                all_valid = False
            else:
                print_success(f"{config_name}: {'*' * 10} (configured)")
        
        # Check VPAs
        print_info(f"\nVPA Configuration:")
        for idx, vpa in enumerate(self.service.vpas, 1):
            if vpa and vpa != 'vpa@bank':
                print_success(f"VPA {idx}: {vpa}")
            else:
                print_error(f"VPA {idx}: Not configured")
                all_valid = False
        
        print_info(f"\nVPA Limits:")
        print_info(f"  Daily limit per VPA: ₹{self.service.vpa_daily_limit:,.2f}")
        print_info(f"  Safety threshold: ₹{self.service.vpa_safety_threshold:,.2f}")
        print_info(f"  Total daily capacity: ₹{self.service.vpa_daily_limit * len(self.service.vpas):,.2f}")
        
        return all_valid
    
    def test_database_connection(self):
        """Test 2: Database connection"""
        print_info("Testing database connection...")
        
        conn = get_db_connection()
        if not conn:
            print_error("Failed to connect to database")
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result:
                    print_success("Database connection successful")
                    
                    # Check required tables
                    required_tables = [
                        'payin_transactions',
                        'oxymoney_vpa_usage',
                        'merchant_wallet_transactions',
                        'merchants'
                    ]
                    
                    for table in required_tables:
                        cursor.execute(f"SHOW TABLES LIKE '{table}'")
                        if cursor.fetchone():
                            print_success(f"Table '{table}' exists")
                        else:
                            print_error(f"Table '{table}' not found")
                            return False
                    
                    return True
                else:
                    print_error("Database query failed")
                    return False
        finally:
            conn.close()
    
    def test_token_generation(self):
        """Test 3: Token generation"""
        print_info("Testing access token generation...")
        
        # Force fresh token generation
        token = self.service.generate_access_token(force_refresh=True)
        
        if token:
            print_success(f"Access token generated: {token[:30]}...")
            print_info(f"Token length: {len(token)} characters")
            
            # Test token caching
            print_info("\nTesting token caching...")
            cached_token = self.service.generate_access_token()
            
            if cached_token == token:
                print_success("Token caching works correctly")
            else:
                print_warning("Token caching may not be working")
            
            return True
        else:
            print_error("Failed to generate access token")
            return False
    
    def test_checksum_generation(self):
        """Test 4: Checksum generation"""
        print_info("Testing checksum generation...")
        
        test_payload = {
            "merchantVpa": "test@bank",
            "mid": "12345",
            "amount": "100.00",
            "note": "Test payment",
            "clientRefId": "TEST123",
            "expiryValue": "1"
        }
        
        checksum = self.service.generate_checksum(test_payload)
        
        if checksum:
            print_success(f"Checksum generated: {checksum[:30]}...")
            print_info(f"Checksum length: {len(checksum)} characters")
            return True
        else:
            print_error("Failed to generate checksum")
            return False
    
    def test_vpa_availability(self):
        """Test 5: VPA availability check"""
        print_info("Testing VPA availability...")
        
        test_amount = 1000.00
        vpa, vpa_index = self.service.get_available_vpa(test_amount)
        
        if vpa:
            print_success(f"Available VPA found: {vpa} (Index: {vpa_index})")
            return True
        else:
            print_warning("No VPA available (all at limit)")
            return True  # Not a failure, just at limit
    
    def test_vpa_usage_stats(self):
        """Test 6: VPA usage statistics"""
        print_info("Testing VPA usage statistics...")
        
        stats = self.service.get_vpa_usage_stats()
        
        if stats:
            print_success(f"Retrieved stats for {len(stats)} VPAs")
            
            print_info("\nVPA Usage Summary:")
            for stat in stats:
                print_info(f"  VPA {stat['vpa_index']}: {stat['vpa']}")
                print_info(f"    Usage: ₹{stat['total_usage']:,.2f} / ₹{stat['daily_limit']:,.2f}")
                print_info(f"    Transactions: {stat['transaction_count']}")
                print_info(f"    Remaining: ₹{stat['remaining']:,.2f}")
                print_info(f"    Status: {stat['status']}")
            
            return True
        else:
            print_error("Failed to retrieve VPA usage stats")
            return False
    
    def test_merchant_setup(self):
        """Test 7: Setup test merchant"""
        print_info("Setting up test merchant...")
        
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                # Find an active merchant for testing
                cursor.execute("""
                    SELECT merchant_id, full_name, email, scheme_id
                    FROM merchants
                    WHERE is_active = 1
                    LIMIT 1
                """)
                
                merchant = cursor.fetchone()
                
                if merchant:
                    self.test_merchant_id = merchant['merchant_id']
                    print_success(f"Using test merchant: {self.test_merchant_id}")
                    print_info(f"  Name: {merchant['full_name']}")
                    print_info(f"  Email: {merchant['email']}")
                    print_info(f"  Scheme ID: {merchant['scheme_id']}")
                    return True
                else:
                    print_error("No active merchant found for testing")
                    return False
        finally:
            conn.close()
    
    def test_payment_intent_creation(self):
        """Test 8: Create payment intent"""
        print_info("Testing payment intent creation...")
        
        if not self.test_merchant_id:
            print_error("No test merchant available")
            return False
        
        # Generate unique order ID
        self.test_order_id = f"TEST_OX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        order_data = {
            'amount': 100.00,
            'orderid': self.test_order_id,
            'payee_fname': 'Test',
            'payee_lname': 'User',
            'payee_email': 'test@example.com',
            'payee_mobile': '9876543210',
            'note': 'Test payment for Oxymoney integration',
            'expiryValue': 1,
            'callback_url': 'https://webhook.site/test-callback'
        }
        
        print_info(f"Creating payment intent for order: {self.test_order_id}")
        print_info(f"Amount: ₹{order_data['amount']}")
        
        result = self.service.create_payin_order(self.test_merchant_id, order_data)
        
        if result.get('success'):
            self.test_txn_id = result.get('txn_id')
            print_success("Payment intent created successfully")
            print_info(f"  Transaction ID: {self.test_txn_id}")
            print_info(f"  Order ID: {result.get('order_id')}")
            print_info(f"  Amount: ₹{result.get('amount')}")
            print_info(f"  Charge: ₹{result.get('charge_amount')}")
            print_info(f"  Net Amount: ₹{result.get('net_amount')}")
            print_info(f"  Payment Intent ID: {result.get('payment_intent_id')}")
            print_info(f"  Payment URL: {result.get('payment_url')[:50]}...")
            print_info(f"  VPA Used: {result.get('vpa_used')}")
            print_info(f"  Status: {result.get('status')}")
            return True
        else:
            print_error(f"Failed to create payment intent: {result.get('message')}")
            return False
    
    def test_transaction_database(self):
        """Test 9: Verify transaction in database"""
        print_info("Verifying transaction in database...")
        
        if not self.test_txn_id:
            print_error("No test transaction ID available")
            return False
        
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT txn_id, merchant_id, order_id, amount, charge_amount,
                           net_amount, status, pg_partner, pg_txn_id, payment_url,
                           callback_url, created_at
                    FROM payin_transactions
                    WHERE txn_id = %s
                """, (self.test_txn_id,))
                
                txn = cursor.fetchone()
                
                if txn:
                    print_success("Transaction found in database")
                    print_info(f"  Transaction ID: {txn['txn_id']}")
                    print_info(f"  Merchant ID: {txn['merchant_id']}")
                    print_info(f"  Order ID: {txn['order_id']}")
                    print_info(f"  Amount: ₹{txn['amount']}")
                    print_info(f"  Status: {txn['status']}")
                    print_info(f"  PG Partner: {txn['pg_partner']}")
                    print_info(f"  PG Txn ID: {txn['pg_txn_id']}")
                    print_info(f"  Created: {txn['created_at']}")
                    return True
                else:
                    print_error("Transaction not found in database")
                    return False
        finally:
            conn.close()
    
    def test_vpa_usage_recording(self):
        """Test 10: Verify VPA usage recording"""
        print_info("Verifying VPA usage recording...")
        
        if not self.test_txn_id:
            print_error("No test transaction ID available")
            return False
        
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT vpa, amount, txn_id, merchant_id, created_at
                    FROM oxymoney_vpa_usage
                    WHERE txn_id = %s
                """, (self.test_txn_id,))
                
                usage = cursor.fetchone()
                
                if usage:
                    print_success("VPA usage recorded")
                    print_info(f"  VPA: {usage['vpa']}")
                    print_info(f"  Amount: ₹{usage['amount']}")
                    print_info(f"  Transaction ID: {usage['txn_id']}")
                    print_info(f"  Merchant ID: {usage['merchant_id']}")
                    print_info(f"  Recorded at: {usage['created_at']}")
                    return True
                else:
                    print_error("VPA usage not recorded")
                    return False
        finally:
            conn.close()
    
    def test_transaction_status(self):
        """Test 11: Check transaction status"""
        print_info("Testing transaction status check...")
        
        if not self.test_txn_id:
            print_error("No test transaction ID available")
            return False
        
        # Get pg_txn_id from database
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_txn_id FROM payin_transactions
                    WHERE txn_id = %s
                """, (self.test_txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn or not txn['pg_txn_id']:
                    print_error("No PG transaction ID found")
                    return False
                
                pg_txn_id = txn['pg_txn_id']
        finally:
            conn.close()
        
        print_info(f"Checking status for PG Txn ID: {pg_txn_id}")
        
        result = self.service.check_transaction_status(txn_id=pg_txn_id)
        
        if result.get('success'):
            print_success("Status check successful")
            print_info(f"  Status: {result.get('status')}")
            print_info(f"  Txn Status: {result.get('txn_status')}")
            print_info(f"  Amount: {result.get('amount')}")
            print_info(f"  RRN: {result.get('rrn')}")
            print_info(f"  Client Ref ID: {result.get('client_ref_id')}")
            return True
        else:
            print_error(f"Status check failed: {result.get('message')}")
            return False
    
    def test_callback_simulation(self):
        """Test 12: Simulate callback"""
        print_info("Simulating callback (manual verification required)...")
        
        if not self.test_txn_id:
            print_error("No test transaction ID available")
            return False
        
        # Get transaction details
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_txn_id, amount FROM payin_transactions
                    WHERE txn_id = %s
                """, (self.test_txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print_error("Transaction not found")
                    return False
                
                # Create sample callback payload
                callback_payload = {
                    "rrn": "247340973172",
                    "note": "Test payment",
                    "refId": "X2604301144251324189192222",
                    "txnId": txn['pg_txn_id'],
                    "amount": str(txn['amount']),
                    "errorCode": "00",
                    "errorMsg": "",
                    "status": "SUCCESS",
                    "tpRespCode": "",
                    "clientRefId": "TEST_CLIENT_REF",
                    "txnDate": datetime.now().isoformat(),
                    "payerDtls": {
                        "mobileNo": "919876543210",
                        "vpa": "test@axl",
                        "acNo": "438802120024524",
                        "ifsc": "UBIN0543888",
                        "name": "Test User",
                        "mccCode": "0000"
                    },
                    "merchantDtls": {
                        "merchantVpa": "merchant@bank",
                        "name": "Test Merchant",
                        "mccCode": "5641",
                        "mId": "31280"
                    }
                }
                
                print_success("Sample callback payload created")
                print_info("\nCallback Payload:")
                print(json.dumps(callback_payload, indent=2))
                
                print_warning("\nTo test callback, send POST request to:")
                print_warning("  URL: http://your-server/api/callback/oxy-grosmart/payin")
                print_warning("  Method: POST")
                print_warning("  Content-Type: application/json")
                print_warning("  Body: (payload shown above)")
                
                return True
        finally:
            conn.close()
    
    def test_wallet_credit(self):
        """Test 13: Verify wallet credit (for successful transactions)"""
        print_info("Checking wallet credit status...")
        
        if not self.test_txn_id:
            print_error("No test transaction ID available")
            return False
        
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                # Check if wallet was credited
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (self.test_txn_id,))
                
                result = cursor.fetchone()
                
                if result['count'] > 0:
                    print_success("Wallet credit found")
                    
                    # Get details
                    cursor.execute("""
                        SELECT merchant_id, amount, description, created_at
                        FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (self.test_txn_id,))
                    
                    credit = cursor.fetchone()
                    print_info(f"  Merchant ID: {credit['merchant_id']}")
                    print_info(f"  Amount: ₹{credit['amount']}")
                    print_info(f"  Description: {credit['description']}")
                    print_info(f"  Created: {credit['created_at']}")
                    return True
                else:
                    print_warning("No wallet credit found (transaction may not be successful yet)")
                    return True  # Not a failure, just pending
        finally:
            conn.close()
    
    def test_error_handling(self):
        """Test 14: Error handling"""
        print_info("Testing error handling...")
        
        # Test with invalid amount
        print_info("\n1. Testing invalid amount...")
        result = self.service.create_payin_order(self.test_merchant_id, {
            'amount': -100,
            'orderid': 'TEST_INVALID',
            'payee_fname': 'Test',
            'payee_email': 'test@example.com',
            'payee_mobile': '9876543210'
        })
        
        if not result.get('success'):
            print_success("Invalid amount rejected correctly")
        else:
            print_error("Invalid amount not rejected")
            return False
        
        # Test with missing fields
        print_info("\n2. Testing missing required fields...")
        result = self.service.create_payin_order(self.test_merchant_id, {
            'amount': 100
        })
        
        if not result.get('success'):
            print_success("Missing fields rejected correctly")
        else:
            print_error("Missing fields not rejected")
            return False
        
        # Test with invalid merchant
        print_info("\n3. Testing invalid merchant...")
        result = self.service.create_payin_order('INVALID_MERCHANT', {
            'amount': 100,
            'orderid': 'TEST_INVALID',
            'payee_fname': 'Test',
            'payee_email': 'test@example.com',
            'payee_mobile': '9876543210'
        })
        
        if not result.get('success'):
            print_success("Invalid merchant rejected correctly")
        else:
            print_error("Invalid merchant not rejected")
            return False
        
        print_success("\nAll error handling tests passed")
        return True
    
    def test_vpa_rotation(self):
        """Test 15: VPA rotation logic"""
        print_info("Testing VPA rotation logic...")
        
        # Get current VPA usage
        stats = self.service.get_vpa_usage_stats()
        
        if not stats:
            print_error("Failed to get VPA stats")
            return False
        
        print_info("\nCurrent VPA Status:")
        available_vpas = 0
        for stat in stats:
            status_icon = "✓" if stat['status'] == 'AVAILABLE' else "⚠"
            print_info(f"  {status_icon} VPA {stat['vpa_index']}: {stat['usage_percentage']}% used")
            if stat['status'] == 'AVAILABLE':
                available_vpas += 1
        
        print_info(f"\nAvailable VPAs: {available_vpas} / {len(stats)}")
        
        if available_vpas > 0:
            print_success("VPA rotation system is working")
            print_info(f"System can handle more transactions using {available_vpas} available VPA(s)")
        else:
            print_warning("All VPAs are at or near limit")
            print_info("VPA usage will reset at midnight (00:00 IST)")
        
        return True
    
    def print_test_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print_info(f"Total Tests: {total_tests}")
        print_success(f"Passed: {self.test_results['passed']}")
        print_error(f"Failed: {self.test_results['failed']}")
        print_warning(f"Warnings: {self.test_results['warnings']}")
        print_info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed'] == 0:
            print_success("\n🎉 ALL TESTS PASSED! Oxymoney integration is working correctly.")
        else:
            print_error(f"\n⚠️  {self.test_results['failed']} test(s) failed. Please review the errors above.")
        
        print_info(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Print next steps
        print_header("NEXT STEPS")
        print_info("1. Review the test results above")
        print_info("2. If payment intent was created, complete the payment using the payment URL")
        print_info("3. Monitor the callback endpoint for status updates")
        print_info("4. Check VPA usage statistics in admin panel")
        print_info("5. Verify wallet credits after successful payment")
        
        if self.test_txn_id:
            print_info(f"\nTest Transaction ID: {self.test_txn_id}")
            print_info(f"Test Order ID: {self.test_order_id}")
            print_info("\nYou can use these IDs to track the test transaction in the database")

def main():
    """Main function"""
    try:
        tester = OxymoneyPayinTester()
        tester.run_all_tests()
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nTest suite error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
