import os
import requests
import json
from dotenv import load_dotenv

def test_rmshamster_api():
    # Load environment variables
    load_dotenv()
    
    base_url = os.getenv('RMSHAMSTER_BASE_URL', 'https://rmstrade.online')
    api_token = os.getenv('RMSHAMSTER_API_TOKEN', '')
    
    print("="*50)
    print("Testing RMS_HAMSTER API")
    print("="*50)
    print(f"Base URL: {base_url}")
    print(f"Token Length: {len(api_token)} characters")
    
    if not api_token:
        print("❌ Error: RMSHAMSTER_API_TOKEN is empty in your .env file!")
        return
        
    url = f"{base_url}/api/add-money/v3/createOrder"
    
    # Generate a random test order ID
    import time
    client_id = f"TEST_HAMSTER_{int(time.time())}"
    
    payload = {
        'api_token': api_token,
        'amount': 100,  # 100 INR
        'redirect_url': 'https://google.com',
        'callback_url': 'https://google.com',
        'client_id': client_id,
        'customer_name': 'Test User',
        'customer_mobile': '9999999999',
        'customer_email': 'test@test.com'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("\nSending Request...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps({**payload, 'api_token': '***' + api_token[-4:] if len(api_token) > 4 else '***'}, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print("\n" + "="*50)
        print(f"Response Status: {response.status_code}")
        print("="*50)
        
        try:
            resp_json = response.json()
            print(json.dumps(resp_json, indent=2))
            
            if response.status_code in [200, 201] and resp_json.get('status') == 'success':
                print("\n✅ SUCCESS: API Token is valid and working!")
                print(f"Created Test Order ID: {client_id}")
            else:
                print("\n❌ FAILED: The request was not successful.")
                
        except json.JSONDecodeError:
            print(f"Raw text response:\n{response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")

if __name__ == '__main__':
    test_rmshamster_api()
