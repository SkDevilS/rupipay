"""
Test Paytouchpayin Integration via Merchant Payin API
This script tests the complete flow through the merchant API endpoint
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"  # Change to your backend URL
MERCHANT_ID = "9000000001"  # Change to your test merchant ID
MERCHANT_PASSWORD = "Test@123"  # Change to your merchant password

def get_merchant_token():
    """Login and get JWT token"""
    print("=" * 80)
    print("STEP 1: Merchant Login")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/merchant/login"
    payload = {
        "merchantId": MERCHANT_ID,
        "password": MERCHANT_PASSWORD
    }
    
    print(f"📤 POST {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            print(f"✅ Login successful!")
            print(f"🔑 Token: {token[:50]}...")
            return token
        else:
            print(f"❌ Login failed!")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_paytouchpayin_order(token):
    """Test creating Paytouchpayin order via merchant API"""
    print("\n" + "=" * 80)
    print("STEP 2: Create Paytouchpayin Order via Merchant API")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/payin/create-order"
    
    # Generate unique order ID
    order_id = f"TEST{int(time.time())}"
    
    payload = {
        "amount": 10,
        "order_id": order_id,
        "customer_name": "Test Customer",
        "customer_mobile": "9876543210",
        "customer_email": "test@example.com"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"📤 POST {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"🔑 Authorization: Bearer {token[:30]}...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"\n📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Order created successfully!")
            print(f"\n📋 Order Details:")
            print(json.dumps(data, indent=2))
            
            # Check for payment_link
            if data.get('payment_link'):
                print(f"\n🔗 Payment Link: {data['payment_link']}")
            elif data.get('redirect_url'):
                print(f"\n🔗 Redirect URL: {data['redirect_url']}")
            
            return data
        else:
            print(f"\n❌ Order creation failed!")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error', 'Unknown error')}")
            except:
                pass
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def check_merchant_routing(token):
    """Check merchant's payin routing configuration"""
    print("\n" + "=" * 80)
    print("STEP 0: Check Merchant Routing Configuration")
    print("=" * 80)
    
    url = f"{BASE_URL}/api/merchant/profile"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"📤 GET {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"📥 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            merchant = data.get('merchant', {})
            
            print(f"\n✅ Merchant Profile:")
            print(f"  Merchant ID: {merchant.get('merchant_id')}")
            print(f"  Name: {merchant.get('name')}")
            print(f"  Status: {merchant.get('status')}")
            
            # Check routing
            print(f"\n📋 Service Routing:")
            print(f"  Payin Partner: {merchant.get('payin_partner', 'NOT SET')}")
            print(f"  Payout Partner: {merchant.get('payout_partner', 'NOT SET')}")
            
            payin_partner = merchant.get('payin_partner', '').upper()
            
            if payin_partner == 'PAYTOUCHPAYIN':
                print(f"\n✅ Merchant is routed to PAYTOUCHPAYIN")
                return True
            else:
                print(f"\n⚠️  Merchant is NOT routed to PAYTOUCHPAYIN")
                print(f"   Current routing: {payin_partner}")
                print(f"\n💡 To route merchant to Paytouchpayin:")
                print(f"   Run: python3 backend/setup_paytouchpayin_routing.py")
                return False
        else:
            print(f"❌ Failed to get merchant profile")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main test flow"""
    print("\n" + "=" * 80)
    print("PAYTOUCHPAYIN MERCHANT API TEST")
    print("Testing complete flow through merchant payin API")
    print("=" * 80)
    
    # Step 1: Login
    token = get_merchant_token()
    if not token:
        print("\n❌ Cannot proceed without token")
        return
    
    # Step 0: Check routing
    is_routed = check_merchant_routing(token)
    if not is_routed:
        print("\n⚠️  Merchant not routed to Paytouchpayin, but continuing test...")
    
    # Step 2: Create order
    order_data = test_paytouchpayin_order(token)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if order_data:
        print("✅ Test PASSED - Order created successfully")
        print(f"\n📋 Key Information:")
        print(f"  Transaction ID: {order_data.get('txn_id')}")
        print(f"  Order ID: {order_data.get('order_id')}")
        print(f"  Amount: ₹{order_data.get('amount')}")
        print(f"  Charge: ₹{order_data.get('charge')}")
        print(f"  Final Amount: ₹{order_data.get('final_amount')}")
        print(f"  Payment Link: {order_data.get('payment_link', 'N/A')}")
    else:
        print("❌ Test FAILED - Could not create order")
        print("\n🔍 Troubleshooting:")
        print("  1. Check if backend service is running")
        print("  2. Restart backend: sudo systemctl restart moneyone-backend")
        print("  3. Check logs: sudo journalctl -u moneyone-backend -f")
        print("  4. Verify merchant credentials")
        print("  5. Ensure merchant is routed to Paytouchpayin")


if __name__ == "__main__":
    main()
