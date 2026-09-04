"""
Test Mudrape Payin API
"""
import requests
import json
from config import Config

def test_mudrape_payin():
    """Test Mudrape payin order creation"""
    
    print("=" * 60)
    print("Testing Mudrape Payin API")
    print("=" * 60)
    
    # Configuration
    base_url = Config.MUDRAPE_BASE_URL
    api_key = Config.MUDRAPE_API_KEY
    api_secret = Config.MUDRAPE_API_SECRET
    user_id = Config.MUDRAPE_USER_ID
    merchant_mid = Config.MUDRAPE_MERCHANT_MID
    merchant_email = Config.MUDRAPE_MERCHANT_EMAIL
    merchant_secret = Config.MUDRAPE_MERCHANT_SECRET
    
    print(f"\nBase URL: {base_url}")
    print(f"API Key: {api_key[:20]}...")
    print(f"User ID: {user_id}")
    
    # Step 1: Generate Token
    print("\n" + "=" * 60)
    print("Step 1: Generating Token")
    print("=" * 60)
    
    token_url = f"{base_url}/api/api-mudrape/genrate-token"
    
    token_headers = {
        'x-api-key': api_key,
        'x-api-secret': api_secret,
        'Content-Type': 'application/json'
    }
    
    token_payload = {
        'mid': merchant_mid,
        'email': merchant_email,
        'secretkey': merchant_secret
    }
    
    print(f"Token URL: {token_url}")
    print(f"Token Payload: {json.dumps(token_payload, indent=2)}")
    
    try:
        token_response = requests.post(
            token_url,
            headers=token_headers,
            json=token_payload,
            timeout=30
        )
        
        print(f"\nToken Response Status: {token_response.status_code}")
        print(f"Token Response: {token_response.text}")
        
        if token_response.status_code not in [200, 201]:
            print("\n✗ Token generation failed!")
            return
        
        token_data = token_response.json()
        if not token_data.get('success'):
            print("\n✗ Token generation failed!")
            print(f"Error: {token_data.get('message')}")
            return
        
        token = token_data.get('token')
        print(f"\n✓ Token generated successfully!")
        print(f"Token: {token[:50]}...")
        
    except Exception as e:
        print(f"\n✗ Token generation exception: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Create Order
    print("\n" + "=" * 60)
    print("Step 2: Creating Payin Order")
    print("=" * 60)
    
    order_url = f"{base_url}/api/api-mudrape/create-order"
    
    # Generate 20-digit RefID
    import time
    from datetime import datetime
    import random
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')  # 14 digits
    random_part = str(random.randint(100000, 999999))  # 6 digits
    ref_id = f"{timestamp}{random_part}"  # 20 digits
    
    order_headers = {
        'x-api-key': api_key,
        'x-api-secret': api_secret,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    order_payload = {
        'refId': ref_id,
        'amount': 100,  # Test with ₹100
        'name': 'Test Customer',
        'mobile': '9876543210',
        'email': 'test@example.com',
        'userId': user_id
    }
    
    print(f"Order URL: {order_url}")
    print(f"Order Payload: {json.dumps(order_payload, indent=2)}")
    print(f"RefID Length: {len(ref_id)} digits")
    
    try:
        order_response = requests.post(
            order_url,
            headers=order_headers,
            json=order_payload,
            timeout=30
        )
        
        print(f"\nOrder Response Status: {order_response.status_code}")
        print(f"Order Response: {order_response.text}")
        
        if order_response.status_code in [200, 201]:
            order_data = order_response.json()
            if order_data.get('success'):
                print("\n✓ Order created successfully!")
                response_data = order_data.get('data', {})
                print(f"Transaction ID: {response_data.get('txnId')}")
                print(f"QR String: {response_data.get('qrString', 'N/A')[:50]}...")
                print(f"UPI Link: {response_data.get('upiLink', 'N/A')}")
            else:
                print("\n✗ Order creation failed!")
                print(f"Error: {order_data.get('message')}")
        else:
            print("\n✗ Order creation failed!")
            print(f"Error: {order_response.text}")
            
    except Exception as e:
        print(f"\n✗ Order creation exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_mudrape_payin()
