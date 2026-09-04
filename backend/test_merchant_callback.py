"""
Quick test script to verify merchant callback URL is working
Tests: https://hab.pay777.co.uk/call-mone
"""

import requests
import json
from datetime import datetime

def test_callback_url():
    """Test the merchant's callback URL with sample data"""
    
    callback_url = "https://hab.pay777.co.uk/call-mone"
    
    # Sample callback payload
    test_payload = {
        'txn_id': 'TEST_TXN_' + datetime.now().strftime('%Y%m%d%H%M%S'),
        'order_id': 'TEST_ORDER_123',
        'status': 'SUCCESS',
        'amount': 100.00,
        'utr': 'TEST_UTR_123456',
        'pg_txn_id': 'TEST_PG_TXN_789',
        'pg_partner': 'Mudrape',
        'payment_mode': 'UPI',
        'timestamp': datetime.now().isoformat()
    }
    
    print("=" * 80)
    print("Testing Merchant Callback URL")
    print("=" * 80)
    print(f"URL: {callback_url}")
    print(f"\nPayload:")
    print(json.dumps(test_payload, indent=2))
    print("\n" + "=" * 80)
    print("Sending request...")
    print("=" * 80)
    
    try:
        response = requests.post(
            callback_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\n✓ Request sent successfully!")
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        print(response.text[:500])
        
        if 200 <= response.status_code < 300:
            print("\n✓ SUCCESS: Callback URL is working!")
            return True
        else:
            print(f"\n⚠ WARNING: Received HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n✗ ERROR: Request timed out (10 seconds)")
        print("  - The server might be slow or unresponsive")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ ERROR: Connection failed")
        print(f"  - {str(e)}")
        print("\nPossible causes:")
        print("  - URL is incorrect")
        print("  - Server is down")
        print("  - DNS resolution failed")
        print("  - Firewall blocking the connection")
        return False
        
    except requests.exceptions.SSLError as e:
        print(f"\n✗ ERROR: SSL/TLS error")
        print(f"  - {str(e)}")
        print("\nPossible causes:")
        print("  - Invalid SSL certificate")
        print("  - Certificate expired")
        print("  - Certificate mismatch")
        return False
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
        return False

if __name__ == '__main__':
    print("\nMerchant Callback URL Test")
    print("This will send a TEST payload to: https://hab.pay777.co.uk/call-mone")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    test_callback_url()
