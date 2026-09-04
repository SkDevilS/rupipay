"""
Diagnose Sabpaisa Grosmart Payment Creation Error
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
import requests
import hashlib
import hmac
import time

def check_credentials():
    """Check if all required credentials are configured"""
    print("=" * 60)
    print("CHECKING SABPAISA GROSMART CREDENTIALS")
    print("=" * 60)
    
    required_vars = [
        'SABPAISA_GROSMART_CLIENT_CODE',
        'SABPAISA_GROSMART_API_KEY',
        'SABPAISA_GROSMART_SECRET_KEY',
        'SABPAISA_GROSMART_BASE_URL'
    ]
    
    missing = []
    for var in required_vars:
        value = getattr(Config, var, None)
        if value:
            if 'KEY' in var or 'SECRET' in var:
                print(f"✓ {var}: {'*' * 20} (configured)")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT CONFIGURED")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing credentials: {', '.join(missing)}")
        return False
    else:
        print("\n✅ All credentials configured")
        return True

def test_api_connection():
    """Test basic API connectivity"""
    print("\n" + "=" * 60)
    print("TESTING API CONNECTION")
    print("=" * 60)
    
    base_url = Config.SABPAISA_GROSMART_BASE_URL
    print(f"Base URL: {base_url}")
    
    try:
        # Try to reach the base URL
        response = requests.get(base_url, timeout=10)
        print(f"✓ API is reachable (Status: {response.status_code})")
        return True
    except requests.exceptions.Timeout:
        print("✗ API request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_checksum_generation():
    """Test checksum generation"""
    print("\n" + "=" * 60)
    print("TESTING CHECKSUM GENERATION")
    print("=" * 60)
    
    # Test data
    merchant_id = Config.SABPAISA_GROSMART_CLIENT_CODE
    merchant_txn_id = "TEST_TXN_123"
    amount = "100.00"
    currency = "INR"
    timestamp = str(int(time.time()))
    
    print(f"Merchant ID: {merchant_id}")
    print(f"Transaction ID: {merchant_txn_id}")
    print(f"Amount: {amount}")
    print(f"Currency: {currency}")
    print(f"Timestamp: {timestamp}")
    
    # Generate checksum
    checksum_string = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
    print(f"\nChecksum String: {checksum_string}")
    
    secret_key = Config.SABPAISA_GROSMART_SECRET_KEY
    checksum = hmac.new(
        secret_key.encode('utf-8'),
        checksum_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Generated Checksum: {checksum}")
    print("✓ Checksum generation successful")
    return True

def test_payment_creation():
    """Test actual payment creation with Sabpaisa API"""
    print("\n" + "=" * 60)
    print("TESTING PAYMENT CREATION API")
    print("=" * 60)
    
    # Prepare test payment data
    merchant_id = Config.SABPAISA_GROSMART_CLIENT_CODE
    merchant_txn_id = f"TEST_{int(time.time())}"
    amount = "10.00"  # Small test amount
    currency = "INR"
    timestamp = str(int(time.time()))
    
    # Generate checksum
    checksum_string = f"{merchant_id}|{merchant_txn_id}|{amount}|{currency}|{timestamp}"
    checksum = hmac.new(
        Config.SABPAISA_GROSMART_SECRET_KEY.encode('utf-8'),
        checksum_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Prepare request (correct endpoint as per documentation)
    url = f"{Config.SABPAISA_GROSMART_BASE_URL}/api/v1/payments/s2s"
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': Config.SABPAISA_GROSMART_API_KEY
    }
    
    payload = {
        'merchantId': merchant_id,
        'merchantTxnId': merchant_txn_id,
        'amount': amount,
        'currency': currency,
        'timestamp': timestamp,
        'checksum': checksum,
        'customerName': 'Test Customer',
        'customerEmail': 'test@example.com',
        'customerMobile': '9999999999',
        'paymentMode': 'UPI',
        'returnUrl': 'https://example.com/return'
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Payment creation API call successful")
            return True
        else:
            print(f"\n✗ Payment creation failed with status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n✗ API request timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ Connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("SABPAISA GROSMART DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Step 1: Check credentials
    if not check_credentials():
        print("\n❌ DIAGNOSIS FAILED: Missing credentials")
        print("\nPlease configure the following in your .env file:")
        print("- SABPAISA_GROSMART_CLIENT_CODE")
        print("- SABPAISA_GROSMART_API_KEY")
        print("- SABPAISA_GROSMART_SECRET_KEY")
        print("- SABPAISA_GROSMART_BASE_URL")
        return
    
    # Step 2: Test API connection
    if not test_api_connection():
        print("\n⚠️ WARNING: Cannot reach API endpoint")
        print("This might be a network issue or incorrect base URL")
    
    # Step 3: Test checksum generation
    test_checksum_generation()
    
    # Step 4: Test actual payment creation
    test_payment_creation()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
