"""
Diagnose Airpay Token Generation Issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
import requests
import json

def check_config():
    """Check if all required config values are present"""
    print("="*60)
    print("STEP 1: Checking Configuration")
    print("="*60)
    
    required_configs = {
        'AIRPAY_BASE_URL': Config.AIRPAY_BASE_URL,
        'AIRPAY_CLIENT_ID': Config.AIRPAY_CLIENT_ID,
        'AIRPAY_CLIENT_SECRET': Config.AIRPAY_CLIENT_SECRET,
        'AIRPAY_MERCHANT_ID': Config.AIRPAY_MERCHANT_ID,
        'AIRPAY_USERNAME': Config.AIRPAY_USERNAME,
        'AIRPAY_PASSWORD': Config.AIRPAY_PASSWORD,
        'AIRPAY_ENCRYPTION_KEY': Config.AIRPAY_ENCRYPTION_KEY
    }
    
    all_present = True
    for key, value in required_configs.items():
        if not value or value == '':
            print(f"❌ {key}: NOT SET")
            all_present = False
        else:
            # Show first few characters only
            display_value = str(value)[:10] + "..." if len(str(value)) > 10 else str(value)
            print(f"✓ {key}: {display_value}")
    
    print()
    return all_present

def test_token_generation():
    """Test token generation with detailed error info"""
    print("="*60)
    print("STEP 2: Testing Token Generation")
    print("="*60)
    
    url = f"{Config.AIRPAY_BASE_URL}/airpay/pay/v4/api/oauth2"
    
    payload = {
        'client_id': Config.AIRPAY_CLIENT_ID,
        'client_secret': Config.AIRPAY_CLIENT_SECRET,
        'merchant_id': int(Config.AIRPAY_MERCHANT_ID) if Config.AIRPAY_MERCHANT_ID else 0,
        'grant_type': 'client_credentials'
    }
    
    print(f"URL: {url}")
    print(f"Payload:")
    print(f"  client_id: {payload['client_id']}")
    print(f"  client_secret: {payload['client_secret'][:10]}..." if payload['client_secret'] else "  client_secret: NOT SET")
    print(f"  merchant_id: {payload['merchant_id']}")
    print(f"  grant_type: {payload['grant_type']}")
    print()
    
    try:
        print("Sending request...")
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body:")
        print(response.text)
        print()
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("Parsed JSON:")
                print(json.dumps(result, indent=2))
                
                if result.get('status_code') == '200' and result.get('status') == 'success':
                    print("\n✅ Token generation SUCCESSFUL!")
                    return True
                else:
                    print(f"\n❌ Token generation FAILED: {result.get('message')}")
                    return False
            except Exception as e:
                print(f"❌ Failed to parse JSON: {e}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("AIRPAY TOKEN GENERATION DIAGNOSTIC")
    print("="*60 + "\n")
    
    # Step 1: Check config
    config_ok = check_config()
    
    if not config_ok:
        print("\n❌ Configuration is incomplete!")
        print("Please add all required Airpay credentials to backend/.env")
        return
    
    # Step 2: Test token generation
    token_ok = test_token_generation()
    
    # Summary
    print("="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Configuration: {'✅ OK' if config_ok else '❌ FAILED'}")
    print(f"Token Generation: {'✅ OK' if token_ok else '❌ FAILED'}")
    print()
    
    if not token_ok:
        print("TROUBLESHOOTING STEPS:")
        print("1. Verify credentials with Airpay support")
        print("2. Check if BASE_URL is correct (should be https://kraken.airpay.co.in)")
        print("3. Ensure MERCHANT_ID is a number")
        print("4. Check if your IP is whitelisted with Airpay")
        print("5. Contact Airpay support: support@airpay.co.in")

if __name__ == '__main__':
    main()
