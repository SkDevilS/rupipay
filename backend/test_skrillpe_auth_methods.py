"""
SkrillPe Authentication Methods Test
Tests different authentication combinations to find the correct one
"""

import os
import sys
import hashlib
import base64
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SkrillPeAuthTester:
    def __init__(self):
        self.base_url = os.getenv('SKRILLPE_BASE_URL', 'https://clientapisrv.skrillpe.com/poutsaps')
        self.mid = os.getenv('SKRILLPE_MID', '28619924')
        self.mobile_number = os.getenv('SKRILLPE_MOBILE_NUMBER', '7376582857')
        self.company_alias = os.getenv('SKRILLPE_COMPANY_ALIAS', 'Moneyone')
        self.auth_api_key = os.getenv('SKRILLPE_AUTH_API_KEY', '')
        self.auth_api_password = os.getenv('SKRILLPE_AUTH_API_PASSWORD', '')
        self.endpoint = "/api/skrill/upi/qr/send/intent/WL"
        self.url = f"{self.base_url}{self.endpoint}"
        
    def generate_basic_token(self):
        """Generate Basic auth token"""
        sha1_hash = hashlib.sha1(self.mobile_number.encode('utf-8')).digest()
        password = base64.b64encode(sha1_hash).decode('utf-8')
        credentials = f"{self.mid}:{password}"
        token = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
        return f"Basic {token}"
    
    def generate_bearer_token(self):
        """Generate Bearer auth token"""
        sha1_hash = hashlib.sha1(self.mobile_number.encode('utf-8')).digest()
        password = base64.b64encode(sha1_hash).decode('utf-8')
        credentials = f"{self.mid}:{password}"
        token = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
        return f"Bearer {token}"
    
    def get_payload(self):
        """Get test payload"""
        return {
            "transactionId": "TEST_AUTH_" + str(int(os.times().elapsed * 1000)),
            "amount": "300",
            "customerNumber": "9999999999",
            "CompanyAlise": self.company_alias
        }
    
    def test_method(self, method_name, headers):
        """Test a specific authentication method"""
        print(f"\n{'='*60}")
        print(f"Testing: {method_name}")
        print(f"{'='*60}")
        
        # Display headers (masked)
        display_headers = {}
        for key, value in headers.items():
            if len(value) > 30:
                display_headers[key] = value[:30] + "..."
            else:
                display_headers[key] = value
        print(f"Headers: {json.dumps(display_headers, indent=2)}")
        
        try:
            response = requests.post(
                self.url,
                headers=headers,
                json=self.get_payload(),
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.text:
                try:
                    print(f"Response: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Response: {response.text}")
            else:
                print("Response: (Empty)")
            
            if response.status_code == 200:
                print(f"✅ SUCCESS! This method works!")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
            
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def run_all_tests(self):
        """Test all authentication methods"""
        print("="*60)
        print("SkrillPe Authentication Methods Test")
        print("="*60)
        print(f"Base URL: {self.base_url}")
        print(f"Endpoint: {self.endpoint}")
        print(f"MID: {self.mid}")
        print(f"Mobile: {self.mobile_number}")
        
        methods = []
        
        # Method 1: Only AUTH-API headers (no Authorization)
        methods.append({
            'name': 'Method 1: Only AUTH-API headers',
            'headers': {
                'AUTH-API_KEY': self.auth_api_key,
                'AUTH-API_PASSWORD': self.auth_api_password,
                'Content-Type': 'application/json'
            }
        })
        
        # Method 2: Basic + AUTH-API headers
        methods.append({
            'name': 'Method 2: Basic + AUTH-API headers',
            'headers': {
                'Authorization': self.generate_basic_token(),
                'AUTH-API_KEY': self.auth_api_key,
                'AUTH-API_PASSWORD': self.auth_api_password,
                'Content-Type': 'application/json'
            }
        })
        
        # Method 3: Bearer + AUTH-API headers
        methods.append({
            'name': 'Method 3: Bearer + AUTH-API headers',
            'headers': {
                'Authorization': self.generate_bearer_token(),
                'AUTH-API_KEY': self.auth_api_key,
                'AUTH-API_PASSWORD': self.auth_api_password,
                'Content-Type': 'application/json'
            }
        })
        
        # Method 4: Only Basic Authorization
        methods.append({
            'name': 'Method 4: Only Basic Authorization',
            'headers': {
                'Authorization': self.generate_basic_token(),
                'Content-Type': 'application/json'
            }
        })
        
        # Method 5: Only Bearer Authorization
        methods.append({
            'name': 'Method 5: Only Bearer Authorization',
            'headers': {
                'Authorization': self.generate_bearer_token(),
                'Content-Type': 'application/json'
            }
        })
        
        # Method 6: Basic + AUTH-API_KEY only
        methods.append({
            'name': 'Method 6: Basic + AUTH-API_KEY only',
            'headers': {
                'Authorization': self.generate_basic_token(),
                'AUTH-API_KEY': self.auth_api_key,
                'Content-Type': 'application/json'
            }
        })
        
        # Method 7: Bearer + AUTH-API_KEY only
        methods.append({
            'name': 'Method 7: Bearer + AUTH-API_KEY only',
            'headers': {
                'Authorization': self.generate_bearer_token(),
                'AUTH-API_KEY': self.auth_api_key,
                'Content-Type': 'application/json'
            }
        })
        
        # Method 8: Basic + AUTH-API_PASSWORD only
        methods.append({
            'name': 'Method 8: Basic + AUTH-API_PASSWORD only',
            'headers': {
                'Authorization': self.generate_basic_token(),
                'AUTH-API_PASSWORD': self.auth_api_password,
                'Content-Type': 'application/json'
            }
        })
        
        # Run all tests
        successful_methods = []
        for method in methods:
            if self.test_method(method['name'], method['headers']):
                successful_methods.append(method['name'])
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        if successful_methods:
            print(f"✅ Successful methods:")
            for method in successful_methods:
                print(f"   - {method}")
        else:
            print("❌ No authentication method worked")
            print("\nPossible issues:")
            print("1. Incorrect credentials (MID, Mobile, API Key, API Password)")
            print("2. IP address not whitelisted")
            print("3. Account not activated")
            print("4. Different authentication mechanism required")
            print("\nRecommendation: Contact SkrillPe support to verify:")
            print("- Correct authentication method")
            print("- Correct credentials")
            print("- Account activation status")
            print("- IP whitelist status")

def main():
    tester = SkrillPeAuthTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
