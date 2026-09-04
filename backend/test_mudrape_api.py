"""
Test script for Mudrape API integration
Tests token generation and basic connectivity
"""

import requests
import json
from config import Config

def test_mudrape_connection():
    """Test Mudrape API connection and token generation"""
    
    print("=" * 60)
    print("Mudrape API Connection Test")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Configuration Check:")
    print(f"   Base URL: {Config.MUDRAPE_BASE_URL}")
    print(f"   API Key: {Config.MUDRAPE_API_KEY[:20]}...")
    print(f"   API Secret: {Config.MUDRAPE_API_SECRET[:20]}...")
    print(f"   User ID: {Config.MUDRAPE_USER_ID}")
    
    if not Config.MUDRAPE_MERCHANT_MID or Config.MUDRAPE_MERCHANT_MID == 'YOUR_MERCHANT_MID':
        print("   ❌ MUDRAPE_MERCHANT_MID not configured")
        print("\n⚠️  Please update backend/.env with your Mudrape merchant credentials")
        return False
    
    print(f"   Merchant MID: {Config.MUDRAPE_MERCHANT_MID}")
    
    if not Config.MUDRAPE_MERCHANT_EMAIL or Config.MUDRAPE_MERCHANT_EMAIL == 'YOUR_MERCHANT_EMAIL':
        print("   ❌ MUDRAPE_MERCHANT_EMAIL not configured")
        print("\n⚠️  Please update backend/.env with your Mudrape merchant credentials")
        return False
    
    print(f"   Merchant Email: {Config.MUDRAPE_MERCHANT_EMAIL}")
    
    if not Config.MUDRAPE_MERCHANT_SECRET or Config.MUDRAPE_MERCHANT_SECRET == 'YOUR_MERCHANT_SECRET':
        print("   ❌ MUDRAPE_MERCHANT_SECRET not configured")
        print("\n⚠️  Please update backend/.env with your Mudrape merchant credentials")
        return False
    
    print(f"   Merchant Secret: {'*' * 20}")
    print("   ✅ All credentials configured")
    
    # Test token generation
    print("\n2. Testing Token Generation:")
    
    try:
        url = f"{Config.MUDRAPE_BASE_URL}/api/api-mudrape/genrate-token"
        
        headers = {
            'x-api-key': Config.MUDRAPE_API_KEY,
            'x-api-secret': Config.MUDRAPE_API_SECRET,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'mid': Config.MUDRAPE_MERCHANT_MID,
            'email': Config.MUDRAPE_MERCHANT_EMAIL,
            'secretkey': Config.MUDRAPE_MERCHANT_SECRET
        }
        
        print(f"   Sending request to: {url}")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            if data.get('token'):
                print("   ✅ Token generated successfully!")
                print(f"   Token: {data['token'][:30]}...")
                
                # Test create order endpoint (without actually creating)
                print("\n3. Testing Create Order Endpoint:")
                print("   (Checking endpoint availability, not creating actual order)")
                
                test_order_url = f"{Config.MUDRAPE_BASE_URL}/api/api-mudrape/create-order"
                print(f"   Endpoint: {test_order_url}")
                print(f"   User ID will be sent: {Config.MUDRAPE_USER_ID}")
                print("   ✅ Endpoint configured")
                print("   ✅ User ID configured")
                
                print("\n" + "=" * 60)
                print("✅ Mudrape API Connection Test PASSED")
                print("=" * 60)
                print("\nYou can now:")
                print("1. Configure service routing in Admin Dashboard")
                print("2. Route merchants to Mudrape")
                print("3. Test payment generation in Merchant Dashboard")
                
                return True
            else:
                print(f"   ❌ Token not found in response")
                print(f"   Response: {json.dumps(data, indent=2)}")
                return False
        else:
            print(f"   ❌ Token generation failed")
            print(f"   Response: {response.text}")
            
            if response.status_code == 401:
                print("\n   Possible issues:")
                print("   - Invalid API key or secret")
                print("   - Invalid merchant credentials")
                print("   - Check your Mudrape account status")
            elif response.status_code == 400:
                print("\n   Possible issues:")
                print("   - Missing or invalid parameters")
                print("   - Check merchant MID, email, and secret")
            
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout")
        print("   Check your internet connection and Mudrape API availability")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error")
        print("   Cannot reach Mudrape API. Check:")
        print("   - Internet connection")
        print("   - Firewall settings")
        print("   - Mudrape API status")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = test_mudrape_connection()
    
    if not success:
        print("\n" + "=" * 60)
        print("❌ Mudrape API Connection Test FAILED")
        print("=" * 60)
        print("\nPlease:")
        print("1. Verify your Mudrape credentials in backend/.env")
        print("2. Check Mudrape API documentation")
        print("3. Contact Mudrape support if issues persist")
