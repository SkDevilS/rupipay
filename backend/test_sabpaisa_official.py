"""
Sabpaisa Grosmart API Test - Official Documentation Compliant
Tests the API exactly as per official Sabpaisa documentation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
import requests
import hashlib
import hmac
import time
import json
from datetime import datetime

def print_header(text):
    print(f"\n{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}\n")

def print_section(text):
    print(f"\n{text}")
    print(f"{'-' * len(text)}")

def generate_checksum(merchant_id, merchant_txn_id, amount, currency, timestamp, secret_key):
    """
    Generate HMAC-SHA256 checksum as per official documentation
    
    Base string format: merchantId|merchantTxnId|amount|currency|timestamp
    Output: 64-character lowercase hex string
    """
    base_string = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
    
    checksum = hmac.new(
        secret_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().lower()
    
    return base_string, checksum

def test_sabpaisa_official():
    """Test Sabpaisa API with official documentation format"""
    
    print_header("SABPAISA GROSMART API TEST - OFFICIAL DOCUMENTATION")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version.split()[0]}")
    
    # Configuration
    base_url = Config.SABPAISA_GROSMART_BASE_URL
    merchant_id = Config.SABPAISA_GROSMART_CLIENT_CODE
    api_key = Config.SABPAISA_GROSMART_API_KEY
    secret_key = Config.SABPAISA_GROSMART_SECRET_KEY
    
    print_section("📋 Configuration")
    print(f"  Base URL: {base_url}")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"  Secret Key: {secret_key[:20]}...{secret_key[-10:]}")
    
    # Validate configuration
    if not merchant_id or merchant_id == "YOUR_CLIENT_CODE":
        print(f"\n❌ ERROR: Merchant ID not configured")
        print(f"   Please set SABPAISA_GROSMART_CLIENT_CODE in .env file")
        return False
    
    if not api_key or api_key == "YOUR_API_KEY":
        print(f"\n❌ ERROR: API Key not configured")
        print(f"   Please set SABPAISA_GROSMART_API_KEY in .env file")
        return False
    
    if not secret_key or secret_key == "YOUR_SECRET_KEY":
        print(f"\n❌ ERROR: Secret Key not configured")
        print(f"   Please set SABPAISA_GROSMART_SECRET_KEY in .env file")
        return False
    
    # Test data (as per official documentation)
    timestamp = int(time.time())
    merchant_txn_id = f"ORDER_{datetime.now().strftime('%Y%m%d')}_{timestamp}"
    amount = 50000  # ₹500 in paise (as per documentation example)
    currency = "INR"
    
    print_section("📦 Transaction Details")
    print(f"  Merchant Txn ID: {merchant_txn_id}")
    print(f"  Amount: {amount} paise (₹{amount/100})")
    print(f"  Currency: {currency}")
    print(f"  Timestamp: {timestamp} ({datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"  Payment Mode: UPI_INTENT")
    
    # Generate checksum
    base_string, checksum = generate_checksum(
        merchant_id, merchant_txn_id, amount, currency, timestamp, secret_key
    )
    
    print_section("🔐 Checksum Generation")
    print(f"  Base String: {base_string}")
    print(f"  Checksum: {checksum}")
    print(f"  Length: {len(checksum)} characters")
    
    # Validate checksum
    if len(checksum) != 64:
        print(f"\n❌ ERROR: Checksum length is {len(checksum)}, expected 64")
        return False
    
    if not checksum.islower():
        print(f"\n⚠️  WARNING: Checksum contains uppercase characters")
    
    # Prepare request payload (exactly as per official documentation)
    payload = {
        "merchantId": merchant_id,
        "merchantTxnId": merchant_txn_id,
        "amount": amount,  # INTEGER in paise
        "currency": currency,
        "customerName": "Test Customer",
        "customerEmail": "test@example.com",
        "customerPhone": "9876543210",
        "paymentMode": "UPI_INTENT",  # As per documentation
        "timestamp": timestamp,  # INTEGER Unix seconds
        "checksum": checksum,
        "description": "Test Payment - Official API",
        "upiExpiryMinutes": 5
    }
    
    # Prepare headers (exactly as per official documentation)
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Merchant-Id": merchant_id
    }
    
    # Endpoint (as per official documentation)
    url = f"{base_url}/api/v1/payments/s2s"
    
    print_section("📤 API Request")
    print(f"  URL: {url}")
    print(f"  Method: POST")
    print(f"\n  Headers:")
    for key, value in headers.items():
        if 'Key' in key:
            print(f"    {key}: {value[:20]}...")
        else:
            print(f"    {key}: {value}")
    
    print(f"\n  Payload:")
    print(json.dumps(payload, indent=4))
    
    # Send request
    print_section("🚀 Sending Request")
    print(f"  Waiting for response...")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        elapsed_time = time.time() - start_time
        
        print_section("📥 Response")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Time: {elapsed_time:.2f} seconds")
        
        # Parse response
        try:
            response_json = response.json()
            print(f"\n  Body:")
            print(json.dumps(response_json, indent=4))
        except:
            print(f"\n  Body (Raw):")
            print(response.text)
            response_json = {}
        
        # Analyze response
        print_section("📊 Analysis")
        
        if response.status_code == 201:
            print(f"  ✅ HTTP 201 Created - Payment initiated successfully")
            if response_json.get('success'):
                print(f"  ✅ API returned success=true")
                print(f"\n  Payment Details:")
                print(f"    Payment ID: {response_json.get('paymentId')}")
                print(f"    Txn ID: {response_json.get('txnId')}")
                print(f"    Status: {response_json.get('status')}")
                print(f"    Intent URL: {response_json.get('intentUrl', 'N/A')}")
                print(f"    Message: {response_json.get('message')}")
                print(f"    Trace ID: {response_json.get('traceId')}")
                
                print(f"\n  ✅ SUCCESS - Integration is working!")
                return True
            else:
                print(f"  ⚠️  API returned success=false")
                print(f"  Message: {response_json.get('message')}")
                return False
                
        elif response.status_code == 200:
            print(f"  ✅ HTTP 200 OK - Payment created")
            return True
            
        elif response.status_code == 400:
            error_code = response_json.get('errorCode')
            error_message = response_json.get('errorMessage')
            trace_id = response_json.get('traceId')
            
            print(f"  ❌ HTTP 400 Bad Request")
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            if trace_id:
                print(f"  Trace ID: {trace_id}")
            
            # Provide specific guidance based on error code
            if error_code == "INVALID_TIMESTAMP":
                print(f"\n  💡 Fix: Ensure your server clock is synced (NTP)")
            elif error_code == "REQUEST_EXPIRED":
                print(f"\n  💡 Fix: Generate a fresh timestamp for each request")
            elif error_code == "INVALID_SIGNATURE":
                print(f"\n  💡 Fix: Verify base string format and secret key")
            elif error_code == "INVALID_PAYMENT_MODE":
                print(f"\n  💡 Fix: Use UPI_QR or UPI_INTENT")
            elif error_code == "VALIDATION_ERROR":
                print(f"\n  💡 Fix: Check field constraints in documentation")
            elif error_code == "DUPLICATE_TRANSACTION":
                print(f"\n  💡 Fix: Use a unique merchantTxnId for each payment")
            elif error_code == "PAYMENT_FAILED":
                print(f"\n  💡 Fix: Retry the payment or contact support")
            elif error_code == "SERVICE_UNAVAILABLE":
                print(f"\n  💡 Fix: Retry after a few seconds")
            
            return False
            
        elif response.status_code == 401:
            print(f"  ❌ HTTP 401 Unauthorized - Invalid credentials")
            error_code = response_json.get('errorCode')
            error_message = response_json.get('errorMessage')
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            print(f"\n  💡 Fix: Check API key and merchant ID in .env file")
            return False
            
        elif response.status_code == 403:
            print(f"  ❌ HTTP 403 Forbidden - S2S not enabled")
            error_code = response_json.get('errorCode')
            error_message = response_json.get('errorMessage')
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            
            if error_code == "S2S_NOT_ENABLED":
                print(f"\n  💡 Fix: Contact SabPaisa support to enable S2S payments")
                print(f"         for merchant account: {merchant_id}")
            
            return False
            
        elif response.status_code == 500:
            print(f"  ❌ HTTP 500 Internal Server Error - Sabpaisa server error")
            error_code = response_json.get('error', {}).get('code')
            error_message = response_json.get('error', {}).get('message')
            trace_id = response_json.get('traceId')
            
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            if trace_id:
                print(f"  Trace ID: {trace_id} (Save this for support)")
            
            print(f"\n  💡 This is a server-side issue on Sabpaisa's end")
            print(f"     Action: Contact Sabpaisa support with trace ID")
            return False
            
        else:
            print(f"  ❌ HTTP {response.status_code} - Unexpected status code")
            return False
        
    except requests.exceptions.Timeout:
        print_section("❌ Request Timeout")
        print(f"  The API server did not respond within 30 seconds")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print_section("❌ Connection Error")
        print(f"  Could not connect to {base_url}")
        print(f"  Error: {str(e)}")
        return False
        
    except Exception as e:
        print_section("❌ Unexpected Error")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    try:
        success = test_sabpaisa_official()
        
        print_header("TEST COMPLETE")
        
        if success:
            print(f"✅ All checks passed - Integration is working!")
            print(f"\nNext Steps:")
            print(f"  1. Get webhook secret from Sabpaisa team")
            print(f"  2. Add webhook secret to .env file")
            print(f"  3. Test with real merchant account")
            sys.exit(0)
        else:
            print(f"❌ Test failed - Review the errors above")
            print(f"\nTroubleshooting:")
            print(f"  1. Check your .env file configuration")
            print(f"  2. Verify credentials with Sabpaisa team")
            print(f"  3. Ensure S2S is enabled for your account")
            print(f"  4. Contact Sabpaisa support if needed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Test interrupted by user\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
