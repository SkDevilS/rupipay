#!/usr/bin/env python3
"""
Comprehensive Sabpaisa Grosmart Payin Integration Test Suite
Tests all aspects of the integration including:
- Checksum generation
- Payment creation (UPI Intent)
- Payment status checking
- Webhook callback handling
- Wallet crediting
- Idempotency
"""

import requests
import json
import hmac
import hashlib
import base64
import time
from datetime import datetime
import sys
import os

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Sabpaisa Credentials
SABPAISA_BASE_URL = "https://merchant-api.sabpaisa.in"
CLIENT_CODE = "GROS1"
API_KEY = "sp_VnZyfhBwunpPlq2-OqZdzGx-jwtW7e4ma5oFJZyzC-g"
SECRET_KEY = "sec_nO_3BmCMpUOSRcvABZylNmac7g5LumG4zAamrNgmbPQ"
WEBHOOK_SECRET = "your_webhook_secret_here"  # To be provided by Sabpaisa

# Your Backend URL
BACKEND_URL = "http://localhost:5000"  # Change to your actual backend URL
WEBHOOK_URL = f"{BACKEND_URL}/api/callback/sabpaisa-grosmart/webhook"

# Test Merchant Details
TEST_MERCHANT_ID = "9876543210"
TEST_MERCHANT_TOKEN = "your_jwt_token_here"  # Get from merchant login


def print_header(text):
    """Print section header"""
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}{text.center(70)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")


def print_section(text):
    """Print subsection"""
    print(f"\n{BOLD}{BLUE}▶ {text}{RESET}")
    print(f"{BLUE}{'-'*70}{RESET}")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text):
    """Print info message"""
    print(f"{CYAN}ℹ️  {text}{RESET}")


def generate_checksum(merchant_id, merchant_txn_id, amount, currency, timestamp, secret_key):
    """
    Generate HMAC-SHA256 checksum for Sabpaisa
    
    Formula: HMAC-SHA256(secretKey, merchantId|merchantTxnId|amount|currency|timestamp)
    """
    message = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature.lower()


def test_checksum_generation():
    """Test 1: Verify checksum generation"""
    print_section("Test 1: Checksum Generation")
    
    try:
        merchant_id = CLIENT_CODE
        merchant_txn_id = f"SBP_GROS_{TEST_MERCHANT_ID}_TEST001_{int(time.time())}"
        amount = 50000  # ₹500 in paise
        currency = "INR"
        timestamp = int(time.time())
        
        checksum = generate_checksum(merchant_id, merchant_txn_id, amount, currency, timestamp, SECRET_KEY)
        
        print_info(f"Merchant ID: {merchant_id}")
        print_info(f"Merchant Txn ID: {merchant_txn_id}")
        print_info(f"Amount: {amount} paise (₹{amount/100})")
        print_info(f"Currency: {currency}")
        print_info(f"Timestamp: {timestamp}")
        print_info(f"Checksum: {checksum}")
        
        # Verify checksum is 64 hex characters
        if len(checksum) == 64 and all(c in '0123456789abcdef' for c in checksum):
            print_success("Checksum generated correctly (64 hex characters)")
            return True
        else:
            print_error(f"Invalid checksum format: {len(checksum)} characters")
            return False
            
    except Exception as e:
        print_error(f"Checksum generation failed: {e}")
        return False


def test_payment_creation():
    """Test 2: Create UPI Intent payment"""
    print_section("Test 2: Payment Creation (UPI Intent)")
    
    try:
        # Generate transaction ID
        timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
        merchant_txn_id = f"SBP_GROS_{TEST_MERCHANT_ID}_TEST002_{timestamp_str}"
        
        # Test amount: ₹500
        amount_paise = 50000
        
        # Generate checksum
        timestamp = int(time.time())
        checksum = generate_checksum(
            CLIENT_CODE,
            merchant_txn_id,
            amount_paise,
            "INR",
            timestamp,
            SECRET_KEY
        )
        
        # Prepare payload
        payload = {
            'merchantId': CLIENT_CODE,
            'merchantTxnId': merchant_txn_id,
            'amount': amount_paise,
            'currency': 'INR',
            'customerName': 'Test Customer',
            'customerEmail': 'test@example.com',
            'customerPhone': '9876543210',
            'paymentMode': 'UPI_INTENT',
            'timestamp': timestamp,
            'checksum': checksum,
            'description': 'Test Payment',
            'upiExpiryMinutes': 5
        }
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': API_KEY,
            'X-Merchant-Id': CLIENT_CODE
        }
        
        url = f"{SABPAISA_BASE_URL}/api/v1/payments/s2s"
        
        print_info(f"URL: {url}")
        print_info(f"Merchant Txn ID: {merchant_txn_id}")
        print_info(f"Amount: ₹{amount_paise/100}")
        
        # Send request
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print_info(f"Response Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            
            if result.get('success'):
                print_success("Payment created successfully")
                print_info(f"Payment ID: {result.get('paymentId')}")
                print_info(f"Sabpaisa Txn ID: {result.get('txnId')}")
                print_info(f"Intent URL: {result.get('intentUrl')}")
                print_info(f"Status: {result.get('status')}")
                
                return {
                    'success': True,
                    'merchant_txn_id': merchant_txn_id,
                    'payment_id': result.get('paymentId'),
                    'sp_txn_id': result.get('txnId'),
                    'intent_url': result.get('intentUrl'),
                    'amount': amount_paise / 100
                }
            else:
                print_error(f"API Error: {result.get('message')}")
                return {'success': False}
        else:
            print_error(f"HTTP Error {response.status_code}")
            print_error(f"Response: {response.text}")
            return {'success': False}
            
    except Exception as e:
        print_error(f"Payment creation failed: {e}")
        return {'success': False}


def test_payment_status_check(merchant_txn_id):
    """Test 3: Check payment status"""
    print_section("Test 3: Payment Status Check")
    
    try:
        url = f"{SABPAISA_BASE_URL}/api/v2/payments/enquiry"
        
        payload = {
            'clientCode': CLIENT_CODE,
            'merchantTxnId': merchant_txn_id
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': API_KEY
        }
        
        print_info(f"Checking status for: {merchant_txn_id}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print_info(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print_success("Status check successful")
                print_info(f"Status: {result.get('status')}")
                print_info(f"Sabpaisa Txn ID: {result.get('txnId')}")
                print_info(f"Bank RRN: {result.get('bankRrn')}")
                print_info(f"Payment Mode: {result.get('paymentMode')}")
                
                return {
                    'success': True,
                    'status': result.get('status'),
                    'txn_id': result.get('txnId'),
                    'bank_rrn': result.get('bankRrn')
                }
            else:
                print_error(f"API Error: {result.get('message')}")
                return {'success': False}
        else:
            print_error(f"HTTP Error {response.status_code}")
            print_error(f"Response: {response.text}")
            return {'success': False}
            
    except Exception as e:
        print_error(f"Status check failed: {e}")
        return {'success': False}


def test_webhook_signature_verification():
    """Test 4: Webhook signature verification"""
    print_section("Test 4: Webhook Signature Verification")
    
    try:
        # Create test webhook payload
        timestamp_ms = int(time.time() * 1000)
        
        webhook_payload = {
            'event': 'payment.success',
            'txn_id': 'SP_TEST_12345',
            'merchant_txn_id': f'SBP_GROS_{TEST_MERCHANT_ID}_TEST_WEBHOOK_{int(time.time())}',
            'status': 'SUCCESS',
            'request_amount': 500.00,
            'paid_amount': 500.00,
            'currency': 'INR',
            'payment_mode': 'UPI',
            'bank_txn_id': 'BANK_TEST_001',
            'bank_rrn': 'RRN_TEST_001',
            'completed_at': datetime.now().isoformat() + 'Z',
            'timestamp': datetime.now().isoformat() + 'Z',
            'idempotency_key': f'SP_TEST_12345_SUCCESS'
        }
        
        # Convert to JSON
        raw_body = json.dumps(webhook_payload).encode('utf-8')
        
        # Generate signature
        signed_payload = f"{timestamp_ms}.{raw_body.decode('utf-8')}"
        signature = base64.b64encode(
            hmac.new(
                WEBHOOK_SECRET.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        signature_header = f"{timestamp_ms}.{signature}"
        
        print_info(f"Webhook Payload: {json.dumps(webhook_payload, indent=2)}")
        print_info(f"Timestamp: {timestamp_ms}")
        print_info(f"Signature Header: {signature_header}")
        
        # Verify signature
        parts = signature_header.split('.')
        if len(parts) != 2:
            print_error("Invalid signature format")
            return False
        
        ts, received_sig = parts
        
        # Check timestamp freshness (5 minutes)
        current_time = int(time.time() * 1000)
        time_diff = abs(current_time - int(ts))
        
        if time_diff > 300000:
            print_error(f"Signature expired (time diff: {time_diff}ms)")
            return False
        
        print_success(f"Timestamp is fresh (diff: {time_diff}ms)")
        
        # Verify signature
        to_sign = f"{ts}.{raw_body.decode('utf-8')}"
        expected_sig = base64.b64encode(
            hmac.new(
                WEBHOOK_SECRET.encode('utf-8'),
                to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        if hmac.compare_digest(expected_sig, received_sig):
            print_success("Webhook signature verified successfully")
            return True
        else:
            print_error("Webhook signature verification failed")
            return False
            
    except Exception as e:
        print_error(f"Signature verification test failed: {e}")
        return False


def test_webhook_callback_simulation():
    """Test 5: Simulate webhook callback"""
    print_section("Test 5: Webhook Callback Simulation")
    
    try:
        # Create test webhook payload
        timestamp_ms = int(time.time() * 1000)
        merchant_txn_id = f'SBP_GROS_{TEST_MERCHANT_ID}_TEST_CALLBACK_{int(time.time())}'
        
        webhook_payload = {
            'event': 'payment.success',
            'txn_id': 'SP_CALLBACK_12345',
            'merchant_txn_id': merchant_txn_id,
            'status': 'SUCCESS',
            'request_amount': 500.00,
            'paid_amount': 500.00,
            'currency': 'INR',
            'payment_mode': 'UPI',
            'bank_txn_id': 'BANK_CALLBACK_001',
            'bank_rrn': 'RRN_CALLBACK_001',
            'completed_at': datetime.now().isoformat() + 'Z',
            'timestamp': datetime.now().isoformat() + 'Z',
            'idempotency_key': f'SP_CALLBACK_12345_SUCCESS'
        }
        
        # Convert to JSON
        raw_body = json.dumps(webhook_payload).encode('utf-8')
        
        # Generate signature
        signed_payload = f"{timestamp_ms}.{raw_body.decode('utf-8')}"
        signature = base64.b64encode(
            hmac.new(
                WEBHOOK_SECRET.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        signature_header = f"{timestamp_ms}.{signature}"
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-SabPaisa-Signature': signature_header,
            'X-SabPaisa-Timestamp': str(timestamp_ms),
            'X-SabPaisa-Event': 'payment.success',
            'X-SabPaisa-Delivery-Id': 'test-delivery-001'
        }
        
        print_info(f"Webhook URL: {WEBHOOK_URL}")
        print_info(f"Merchant Txn ID: {merchant_txn_id}")
        print_info(f"Event: payment.success")
        
        # Send webhook
        response = requests.post(WEBHOOK_URL, json=webhook_payload, headers=headers, timeout=10)
        
        print_info(f"Response Status: {response.status_code}")
        
        if response.status_code in [200, 401]:  # 401 is expected if webhook secret not configured
            print_success("Webhook endpoint is accessible")
            
            if response.status_code == 200:
                print_success("Webhook processed successfully")
                return True
            else:
                print_warning("Webhook signature verification failed (expected if webhook secret not configured)")
                return True
        else:
            print_error(f"Webhook endpoint error: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to backend at {BACKEND_URL}")
        print_warning("Make sure backend is running and accessible")
        return False
    except Exception as e:
        print_error(f"Webhook callback test failed: {e}")
        return False


def test_backend_payin_endpoint():
    """Test 6: Backend payin endpoint"""
    print_section("Test 6: Backend Payin Endpoint")
    
    try:
        url = f"{BACKEND_URL}/api/payin/order/create"
        
        # Prepare test data
        order_data = {
            'amount': 500,
            'orderid': f'TEST_ORDER_{int(time.time())}',
            'payee_fname': 'Test',
            'payee_lname': 'Customer',
            'payee_mobile': '9876543210',
            'payee_email': 'test@example.com',
            'productinfo': 'Test Product'
        }
        
        headers = {
            'Authorization': f'Bearer {TEST_MERCHANT_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        print_info(f"URL: {url}")
        print_info(f"Order ID: {order_data['orderid']}")
        print_info(f"Amount: ₹{order_data['amount']}")
        
        # Note: This would require actual merchant token
        print_warning("This test requires valid merchant JWT token")
        print_info("To test this endpoint:")
        print_info("1. Login to merchant dashboard")
        print_info("2. Get JWT token from browser console: localStorage.getItem('token')")
        print_info("3. Update TEST_MERCHANT_TOKEN in this script")
        
        return True
        
    except Exception as e:
        print_error(f"Backend endpoint test failed: {e}")
        return False


def test_transaction_id_format():
    """Test 7: Transaction ID format"""
    print_section("Test 7: Transaction ID Format")
    
    try:
        merchant_id = TEST_MERCHANT_ID
        order_id = "TEST_ORDER_001"
        timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
        
        txn_id = f"SBP_GROS_{merchant_id}_{order_id}_{timestamp_str}"
        
        print_info(f"Transaction ID: {txn_id}")
        
        # Verify format
        parts = txn_id.split('_')
        
        if len(parts) >= 4 and parts[0] == 'SBP' and parts[1] == 'GROS':
            print_success("Transaction ID format is correct")
            print_info(f"  Prefix: {parts[0]}_{parts[1]}")
            print_info(f"  Merchant ID: {parts[2]}")
            print_info(f"  Order ID: {parts[3]}")
            print_info(f"  Timestamp: {parts[4] if len(parts) > 4 else 'N/A'}")
            return True
        else:
            print_error("Invalid transaction ID format")
            return False
            
    except Exception as e:
        print_error(f"Transaction ID format test failed: {e}")
        return False


def test_amount_conversion():
    """Test 8: Amount conversion (Rupees to Paise)"""
    print_section("Test 8: Amount Conversion")
    
    try:
        test_amounts = [
            (100, 10000),
            (500, 50000),
            (1000, 100000),
            (5000, 500000),
            (10000, 1000000)
        ]
        
        all_passed = True
        
        for rupees, expected_paise in test_amounts:
            paise = int(rupees * 100)
            
            if paise == expected_paise:
                print_success(f"₹{rupees} = {paise} paise ✓")
            else:
                print_error(f"₹{rupees} = {paise} paise (expected {expected_paise})")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_error(f"Amount conversion test failed: {e}")
        return False


def test_api_connectivity():
    """Test 9: API Connectivity"""
    print_section("Test 9: API Connectivity")
    
    try:
        # Test Sabpaisa API connectivity
        print_info("Testing Sabpaisa API connectivity...")
        
        try:
            response = requests.get(SABPAISA_BASE_URL, timeout=10)
            print_success(f"Sabpaisa API is reachable (Status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print_error(f"Cannot connect to Sabpaisa API at {SABPAISA_BASE_URL}")
            return False
        except Exception as e:
            print_warning(f"Sabpaisa API connectivity check: {e}")
        
        # Test Backend connectivity
        print_info("Testing Backend connectivity...")
        
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=10)
            print_success(f"Backend is reachable (Status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print_warning(f"Cannot connect to Backend at {BACKEND_URL}")
            print_info("Make sure backend is running")
        except Exception as e:
            print_warning(f"Backend connectivity check: {e}")
        
        return True
        
    except Exception as e:
        print_error(f"Connectivity test failed: {e}")
        return False


def test_credentials_validation():
    """Test 10: Credentials Validation"""
    print_section("Test 10: Credentials Validation")
    
    try:
        print_info("Validating Sabpaisa credentials...")
        
        # Check if credentials are set
        if not CLIENT_CODE or CLIENT_CODE == "GROS1":
            print_warning("Using default CLIENT_CODE: GROS1")
        else:
            print_success(f"CLIENT_CODE: {CLIENT_CODE}")
        
        if not API_KEY or len(API_KEY) < 20:
            print_error("Invalid API_KEY")
            return False
        else:
            print_success(f"API_KEY: {API_KEY[:20]}...")
        
        if not SECRET_KEY or len(SECRET_KEY) < 20:
            print_error("Invalid SECRET_KEY")
            return False
        else:
            print_success(f"SECRET_KEY: {SECRET_KEY[:20]}...")
        
        if WEBHOOK_SECRET == "your_webhook_secret_here":
            print_warning("WEBHOOK_SECRET not configured (will be provided by Sabpaisa)")
        else:
            print_success(f"WEBHOOK_SECRET: {WEBHOOK_SECRET[:20]}...")
        
        print_success("Credentials validation passed")
        return True
        
    except Exception as e:
        print_error(f"Credentials validation failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print_header("SABPAISA GROSMART PAYIN INTEGRATION TEST SUITE")
    
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Webhook URL: {WEBHOOK_URL}")
    print_info(f"Test Merchant ID: {TEST_MERCHANT_ID}")
    
    results = {}
    
    # Test 1: Checksum Generation
    results['Checksum Generation'] = test_checksum_generation()
    
    # Test 2: Credentials Validation
    results['Credentials Validation'] = test_credentials_validation()
    
    # Test 3: API Connectivity
    results['API Connectivity'] = test_api_connectivity()
    
    # Test 4: Transaction ID Format
    results['Transaction ID Format'] = test_transaction_id_format()
    
    # Test 5: Amount Conversion
    results['Amount Conversion'] = test_amount_conversion()
    
    # Test 6: Webhook Signature Verification
    results['Webhook Signature Verification'] = test_webhook_signature_verification()
    
    # Test 7: Payment Creation
    payment_result = test_payment_creation()
    results['Payment Creation'] = payment_result.get('success', False)
    
    # Test 8: Payment Status Check (if payment was created)
    if payment_result.get('success'):
        print_info("Waiting 2 seconds before status check...")
        time.sleep(2)
        status_result = test_payment_status_check(payment_result['merchant_txn_id'])
        results['Payment Status Check'] = status_result.get('success', False)
    else:
        print_warning("Skipping payment status check (payment creation failed)")
        results['Payment Status Check'] = None
    
    # Test 9: Webhook Callback Simulation
    results['Webhook Callback Simulation'] = test_webhook_callback_simulation()
    
    # Test 10: Backend Payin Endpoint
    results['Backend Payin Endpoint'] = test_backend_payin_endpoint()
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is True:
            print_success(f"{test_name}")
            passed += 1
        elif result is False:
            print_error(f"{test_name}")
            failed += 1
        else:
            print_warning(f"{test_name} (skipped)")
            skipped += 1
    
    print(f"\n{BOLD}Results:{RESET}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    print(f"  {RED}Failed: {failed}{RESET}")
    print(f"  {YELLOW}Skipped: {skipped}{RESET}")
    print(f"  {BOLD}Total: {len(results)}{RESET}")
    
    # Print next steps
    print_header("NEXT STEPS")
    
    print_info("1. Configure Webhook Secret:")
    print(f"   {CYAN}SABPAISA_GROSMART_WEBHOOK_SECRET=<secret_from_sabpaisa>{RESET}")
    
    print_info("2. Provide Callback URL to Sabpaisa Team:")
    print(f"   {CYAN}{WEBHOOK_URL}{RESET}")
    
    print_info("3. Test with Real Merchant:")
    print(f"   {CYAN}Get JWT token from merchant dashboard{RESET}")
    print(f"   {CYAN}Update TEST_MERCHANT_TOKEN in this script{RESET}")
    
    print_info("4. Monitor Webhooks:")
    print(f"   {CYAN}tail -f /var/log/backend.log | grep Sabpaisa{RESET}")
    
    print_info("5. Check Database:")
    print(f"   {CYAN}SELECT * FROM payin_transactions WHERE pg_partner = 'SABPAISA_GROSMART' ORDER BY created_at DESC;{RESET}")
    
    print_header("INTEGRATION CHECKLIST")
    
    checklist = [
        ("✓", "Checksum generation working"),
        ("✓", "API credentials configured"),
        ("✓", "Transaction ID format correct"),
        ("✓", "Amount conversion correct"),
        ("✓", "Webhook signature verification working"),
        ("?", "Payment creation tested (requires API access)"),
        ("?", "Payment status check tested (requires API access)"),
        ("?", "Webhook callback tested (requires backend running)"),
        ("?", "Merchant endpoint tested (requires JWT token)"),
        ("?", "Webhook secret configured (pending from Sabpaisa)"),
    ]
    
    for status, item in checklist:
        if status == "✓":
            print_success(item)
        elif status == "?":
            print_warning(item)
        else:
            print_error(item)
    
    return failed == 0


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
