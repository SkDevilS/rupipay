"""
SkrillPe Complete API Test Script
Tests the exact authentication flow as per SkrillPe documentation
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

class SkrillPeAPITester:
    def __init__(self):
        """Initialize with credentials from environment"""
        self.base_url = os.getenv('SKRILLPE_BASE_URL', 'https://clientapisrv.skrillpe.com/poutsaps')
        self.mid = os.getenv('SKRILLPE_MID', '28619924')
        self.mobile_number = os.getenv('SKRILLPE_MOBILE_NUMBER', '7376582857')
        self.company_alias = os.getenv('SKRILLPE_COMPANY_ALIAS', 'Moneyone')
        self.auth_api_key = os.getenv('SKRILLPE_AUTH_API_KEY', '')
        self.auth_api_password = os.getenv('SKRILLPE_AUTH_API_PASSWORD', '')
        
    def generate_bearer_token(self):
        """
        Generate Bearer Authentication token as per SkrillPE specification
        
        Steps:
        1. Hash mobile number with SHA1
        2. Base64 encode the hash
        3. Combine MID:hashed_password
        4. Base64 encode the combination with ISO-8859-1 encoding
        5. Return as "Bearer <token>"
        """
        try:
            print("\n" + "="*60)
            print("STEP 1: Generate SHA1 Hash of Mobile Number")
            print("="*60)
            print(f"Mobile Number: {self.mobile_number}")
            
            # Step 1: SHA1 hash of mobile number
            sha1_hash = hashlib.sha1(self.mobile_number.encode('utf-8')).digest()
            print(f"SHA1 Hash (bytes): {sha1_hash.hex()}")
            
            # Step 2: Base64 encode the hash
            password = base64.b64encode(sha1_hash).decode('utf-8')
            print(f"Base64 Encoded Password: {password}")
            
            print("\n" + "="*60)
            print("STEP 2: Create MID:Password Combination")
            print("="*60)
            # Step 3: Combine MID:password
            credentials = f"{self.mid}:{password}"
            print(f"Credentials String: {credentials}")
            
            print("\n" + "="*60)
            print("STEP 3: Base64 Encode with ISO-8859-1")
            print("="*60)
            # Step 4: Base64 encode with ISO-8859-1
            bearer_token = base64.b64encode(credentials.encode('iso-8859-1')).decode('utf-8')
            print(f"Bearer Token: {bearer_token}")
            
            # Step 5: Return with "Bearer" prefix
            final_token = f"Bearer {bearer_token}"
            print(f"Final Authorization Header: {final_token}")
            
            return final_token
            
        except Exception as e:
            print(f"❌ Error generating Bearer token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_headers(self):
        """Get complete request headers for SkrillPe API"""
        auth_token = self.generate_bearer_token()
        
        if not auth_token:
            return None
        
        headers = {
            'Authorization': auth_token,
            'AUTH-API_KEY': self.auth_api_key,
            'AUTH-API_PASSWORD': self.auth_api_password,
            'Content-Type': 'application/json'
        }
        
        return headers
    
    def test_api_call(self):
        """Test the actual API call to SkrillPe"""
        print("\n" + "="*60)
        print("CONFIGURATION CHECK")
        print("="*60)
        print(f"Base URL: {self.base_url}")
        print(f"MID: {self.mid}")
        print(f"Mobile: {self.mobile_number}")
        print(f"Company Alias: {self.company_alias}")
        print(f"Auth API Key: {self.auth_api_key[:20]}..." if self.auth_api_key else "Auth API Key: NOT SET")
        print(f"Auth API Password: {self.auth_api_password[:20]}..." if self.auth_api_password else "Auth API Password: NOT SET")
        
        # Get headers
        headers = self.get_headers()
        
        if not headers:
            print("\n❌ Failed to generate headers")
            return
        
        print("\n" + "="*60)
        print("STEP 4: Prepare API Request")
        print("="*60)
        
        # Prepare endpoint
        endpoint = "/api/skrill/upi/qr/send/intent/WL"
        url = f"{self.base_url}{endpoint}"
        print(f"Endpoint: {endpoint}")
        print(f"Full URL: {url}")
        
        # Prepare payload
        payload = {
            "transactionId": "TEST_TXN_" + str(int(os.times().elapsed * 1000)),
            "amount": "100",
            "customerNumber": "9999999999",
            "CompanyAlise": self.company_alias
        }
        
        print(f"\nPayload:")
        print(json.dumps(payload, indent=2))
        
        print(f"\nHeaders:")
        # Mask sensitive data in display
        display_headers = headers.copy()
        if 'Authorization' in display_headers:
            display_headers['Authorization'] = display_headers['Authorization'][:20] + "..."
        if 'AUTH-API_KEY' in display_headers:
            display_headers['AUTH-API_KEY'] = display_headers['AUTH-API_KEY'][:20] + "..."
        if 'AUTH-API_PASSWORD' in display_headers:
            display_headers['AUTH-API_PASSWORD'] = display_headers['AUTH-API_PASSWORD'][:20] + "..."
        print(json.dumps(display_headers, indent=2))
        
        print("\n" + "="*60)
        print("STEP 5: Make API Call")
        print("="*60)
        print("Making API call...")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print("\n" + "="*60)
            print("STEP 6: API Response")
            print("="*60)
            print(f"Status Code: {response.status_code}")
            print(f"\nResponse Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print(f"\nResponse Body:")
            if response.text:
                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2))
                except:
                    print(response.text)
            else:
                print("(Empty response)")
            
            print("\n" + "="*60)
            print("ANALYSIS")
            print("="*60)
            
            if response.status_code == 200:
                print("✅ API call successful (Status 200)")
                try:
                    data = response.json()
                    if 'intentUrl' in data or 'tinyUrl' in data:
                        print("✅ Response contains payment URLs")
                    if 'code' in data:
                        print(f"   Response Code: {data.get('code')}")
                    if 'reason' in data:
                        print(f"   Response Reason: {data.get('reason')}")
                except:
                    pass
            elif response.status_code == 401:
                print("❌ Authentication Failed (Status 401)")
                print("   Possible issues:")
                print("   - Incorrect MID or Mobile Number")
                print("   - Incorrect AUTH-API_KEY")
                print("   - Incorrect AUTH-API_PASSWORD")
                print("   - Token generation logic error")
            elif response.status_code == 403:
                print("❌ Forbidden (Status 403)")
                print("   Possible issues:")
                print("   - IP not whitelisted")
                print("   - Account not activated")
            elif response.status_code == 404:
                print("❌ Not Found (Status 404)")
                print("   Possible issues:")
                print("   - Incorrect endpoint URL")
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
            
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - check network/URL")
        except Exception as e:
            print(f"❌ Error making API call: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_curl_command(self):
        """Generate a curl command for manual testing"""
        print("\n" + "="*60)
        print("CURL COMMAND FOR MANUAL TESTING")
        print("="*60)
        
        headers = self.get_headers()
        if not headers:
            print("❌ Failed to generate headers")
            return
        
        endpoint = "/api/skrill/upi/qr/send/intent/WL"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "transactionId": "TEST_TXN_MANUAL",
            "amount": "100",
            "customerNumber": "9999999999",
            "CompanyAlise": self.company_alias
        }
        
        curl_cmd = f"curl -X POST '{url}' \\\n"
        for key, value in headers.items():
            curl_cmd += f"  -H '{key}: {value}' \\\n"
        curl_cmd += f"  -d '{json.dumps(payload)}'"
        
        print(curl_cmd)
        print("\n" + "="*60)

def main():
    print("="*60)
    print("SkrillPe API Complete Test")
    print("="*60)
    
    tester = SkrillPeAPITester()
    
    # Run the test
    tester.test_api_call()
    
    # Generate curl command
    tester.generate_curl_command()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)

if __name__ == "__main__":
    main()
