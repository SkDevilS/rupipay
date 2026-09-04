"""
Test Oxymoney Barringer Integration - Complete Flow
Tests token generation, payin creation, and status check
"""

import os
import sys
import requests
import json
from datetime import datetime
from config import Config

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

class OxymoneyBarringerTester:
    def __init__(self):
        self.base_url = "https://api.transxt.in"
        self.secret_key = Config.OXY_BAR_SECRET_KEY
        self.initial_token = Config.OXY_BAR_INITIAL_AUTH_TOKEN
        self.mid = Config.OXY_BAR_MID
        self.bpm_identifier = Config.OXY_BAR_BPM_IDENTIFIER
        
        # Add username and password for API 1.0 auth
        self.username = Config.OXY_BAR_USERNAME
        self.password = Config.OXY_BAR_PASSWORD
        
        # VPAs
        self.vpas = [
            Config.OXY_BAR_VPA1,
            Config.OXY_BAR_VPA2,
            Config.OXY_BAR_VPA3,
            Config.OXY_BAR_VPA4,
            Config.OXY_BAR_VPA5,
        ]
        
        self.access_token = None
        self.test_txn_id = None
        
    def print_config(self):
        """Print configuration (masked)"""
        print_section("Configuration Check")
        print(f"Base URL: {self.base_url}")
        print(f"Username: {self.username}")
        print(f"Password: {self.password[:10]}...{self.password[-10:] if len(self.password) > 20 else ''}")
        print(f"MID: {self.mid}")
        print(f"BPM Identifier: {self.bpm_identifier}")
        print(f"Secret Key: {self.secret_key[:10]}...{self.secret_key[-10:] if len(self.secret_key) > 20 else ''}")
        print(f"Initial Token: {self.initial_token[:20]}...{self.initial_token[-20:] if len(self.initial_token) > 40 else ''}")
        print(f"\nVPAs:")
        for i, vpa in enumerate(self.vpas, 1):
            print(f"  VPA{i}: {vpa}")
        print()
        
    def test_1_generate_token(self):
        """Test 1: Generate Access Token"""
        print_section("Test 1: Generate Access Token")
        
        try:
            # Use API 1.0 (same as Truaxis/Grosmart pattern)
            url = f"{self.base_url}/api/1.0/auth"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.initial_token}'
            }
            
            # Payload structure: payload + checksum wrapper
            payload = {
                "payload": {
                    "userName": Config.OXY_BAR_USERNAME,
                    "password": Config.OXY_BAR_PASSWORD
                },
                "checksum": "92992"  # Hardcoded as per TransXT documentation
            }
            
            print_info(f"POST {url}")
            print_info(f"Username: {Config.OXY_BAR_USERNAME}")
            print_info(f"Password: {Config.OXY_BAR_PASSWORD[:10]}..." if len(Config.OXY_BAR_PASSWORD) > 10 else Config.OXY_BAR_PASSWORD)
            print_info(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
            print_info(f"Payload structure: payload + checksum wrapper")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            print(f"\nStatus Code: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)}")
            except:
                print(f"Response (raw): {response.text}")
                response_json = {}
            
            if response.status_code == 200:
                # Check for success in TransXT format
                if response_json.get('errorCode') in ['0', '00', '000'] and response_json.get('errorMsg') == 'SUCCESS':
                    self.access_token = response_json.get('token')
                    if self.access_token:
                        print_success(f"Access token generated successfully")
                        print_info(f"Token: {self.access_token[:30]}...{self.access_token[-30:] if len(self.access_token) > 60 else ''}")
                        return True
                    else:
                        print_error("No access token in response")
                        print_error(f"Full response: {response_json}")
                        return False
                else:
                    print_error(f"Token generation failed: {response_json.get('errorMsg', 'Unknown error')}")
                    print_error(f"Error code: {response_json.get('errorCode')}")
                    return False
            else:
                print_error(f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_checksum(self, payload_dict):
        """Generate checksum using API 1.0"""
        try:
            if not self.access_token:
                print_error("No access token available for checksum generation")
                return None
            
            url = f"{self.base_url}/api/1.0/checksum"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            # Prepare request with payload + checksum wrapper
            request_body = {
                "payload": payload_dict,
                "checksum": "92992"  # Hardcoded as per documentation
            }
            
            print_info(f"Generating checksum for payload: {json.dumps(payload_dict, indent=2)}")
            
            response = requests.post(url, json=request_body, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print_error(f"Checksum generation failed: {response.text}")
                return None
            
            result = response.json()
            
            if result.get('errorCode') in ['0', '00', '000'] and result.get('errorMsg') == 'SUCCESS':
                checksum = result.get('response', {}).get('checksum')
                print_success(f"Checksum generated: {checksum[:20]}...")
                return checksum
            else:
                print_error(f"Checksum error: {result.get('errorMsg', 'Unknown error')}")
                return None
                
        except Exception as e:
            print_error(f"Checksum generation exception: {str(e)}")
            return None
    
    def test_2_create_payin(self):
        """Test 2: Create Payin Order"""
        print_section("Test 2: Create Payin Order")
        
        if not self.access_token:
            print_error("No access token available. Run test_1_generate_token first.")
            return False
        
        try:
            # Generate test transaction ID
            self.test_txn_id = f"OXY_BAR_TEST_{int(datetime.now().timestamp())}"
            
            # Generate unique client ref ID
            client_ref_id = f"OXBAR_TEST_{int(datetime.now().timestamp())}"
            
            # Select first VPA for testing
            selected_vpa = self.vpas[0]
            
            # Prepare intent payload
            intent_payload = {
                "merchantVpa": selected_vpa,
                "mid": self.mid,
                "amount": "100.00",  # Test with ₹100
                "note": "Test payment for Barringer integration",
                "clientRefId": client_ref_id,
                "expiryValue": "1"  # 1 minute expiry
            }
            
            # Generate checksum
            print_info("Generating checksum...")
            checksum = self.generate_checksum(intent_payload)
            if not checksum:
                print_error("Failed to generate checksum")
                return False
            
            # Prepare request body with payload + checksum wrapper
            request_body = {
                "payload": intent_payload,
                "checksum": checksum
            }
            
            url = f"{self.base_url}/api/1.2/upi/intent/{self.bpm_identifier}/{client_ref_id}"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            print_info(f"POST {url}")
            print_info(f"Client Ref ID: {client_ref_id}")
            print_info(f"VPA: {selected_vpa}")
            print_info(f"Amount: ₹100.00")
            print_info(f"Request body structure: payload + checksum wrapper")
            
            response = requests.post(url, headers=headers, json=request_body, timeout=30)
            
            print(f"\nStatus Code: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)}")
            except:
                print(f"Response (raw): {response.text}")
                response_json = {}
            
            if response.status_code == 200:
                # Check for success in TransXT format
                if response_json.get('errorCode') in ['0', '00', '000'] and response_json.get('errorMsg') == 'SUCCESS':
                    print_success("Payin order created successfully")
                    
                    # Extract payment details
                    response_data = response_json.get('response', {})
                    intent_url = response_data.get('intentUrl')
                    qr_string = response_data.get('qrString')
                    txn_id = response_data.get('txnId')
                    
                    if intent_url:
                        print_success(f"Intent URL: {intent_url}")
                    if qr_string:
                        print_success(f"QR String: {qr_string[:50]}...")
                    if txn_id:
                        print_success(f"TransXT Txn ID: {txn_id}")
                    
                    return True
                else:
                    print_error(f"Payin creation failed: {response_json.get('errorMsg', 'Unknown error')}")
                    print_error(f"Error code: {response_json.get('errorCode')}")
                    return False
            else:
                print_error(f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_3_check_status(self):
        """Test 3: Check Transaction Status"""
        print_section("Test 3: Check Transaction Status")
        
        if not self.access_token:
            print_error("No access token available. Run test_1_generate_token first.")
            return False
        
        if not self.test_txn_id:
            print_error("No transaction ID available. Run test_2_create_payin first.")
            return False
        
        try:
            # Prepare status payload
            status_payload = {
                "clientrefid": self.test_txn_id
            }
            
            # Generate checksum
            print_info("Generating checksum for status check...")
            checksum = self.generate_checksum(status_payload)
            if not checksum:
                print_error("Failed to generate checksum")
                return False
            
            # Prepare request body with payload + checksum wrapper
            request_body = {
                "payload": status_payload,
                "checksum": checksum
            }
            
            url = f"{self.base_url}/api/1.0/checktxndetails"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            print_info(f"POST {url}")
            print_info(f"Client Ref ID: {self.test_txn_id}")
            print_info(f"Request body structure: payload + checksum wrapper")
            
            response = requests.post(url, headers=headers, json=request_body, timeout=30)
            
            print(f"\nStatus Code: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)}")
            except:
                print(f"Response (raw): {response.text}")
                response_json = {}
            
            if response.status_code == 200:
                # Check for success in TransXT format
                if response_json.get('errorCode') in ['0', '00', '000'] and response_json.get('errorMsg') == 'SUCCESS':
                    print_success("Status check successful")
                    
                    # Extract status details
                    response_data = response_json.get('response', {})
                    status = response_data.get('status')
                    rrn = response_data.get('rrn')
                    amount = response_data.get('amount')
                    
                    print_info(f"Status: {status}")
                    if rrn:
                        print_info(f"RRN: {rrn}")
                    if amount:
                        print_info(f"Amount: ₹{amount}")
                    
                    return True
                else:
                    print_error(f"Status check failed: {response_json.get('errorMsg', 'Unknown error')}")
                    print_error(f"Error code: {response_json.get('errorCode')}")
                    return False
            else:
                print_error(f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_4_token_refresh(self):
        """Test 4: Token Refresh (Optional)"""
        print_section("Test 4: Token Refresh")
        
        print_warning("Note: TransXT API 1.0 doesn't have a separate token refresh endpoint.")
        print_warning("Tokens expire after 15 minutes. Generate a new token when needed.")
        print_info("Skipping this test as it's not applicable to API 1.0")
        
        return True  # Mark as passed since it's not applicable
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print_section("Oxymoney Barringer Integration Test Suite")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Print configuration
        self.print_config()
        
        # Run tests
        results = {}
        
        # Test 1: Generate Token
        results['token_generation'] = self.test_1_generate_token()
        
        if results['token_generation']:
            # Test 2: Create Payin
            results['payin_creation'] = self.test_2_create_payin()
            
            # Test 3: Check Status
            results['status_check'] = self.test_3_check_status()
            
            # Test 4: Token Refresh (optional)
            results['token_refresh'] = self.test_4_token_refresh()
        else:
            print_warning("\nSkipping remaining tests due to token generation failure")
            results['payin_creation'] = False
            results['status_check'] = False
            results['token_refresh'] = False
        
        # Print summary
        print_section("Test Summary")
        print(f"{'Test':<30} {'Result':<10}")
        print("-" * 40)
        for test_name, result in results.items():
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r)
        
        print(f"\n{passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print_success("\n🎉 All tests passed!")
        elif passed_tests > 0:
            print_warning(f"\n⚠ {total_tests - passed_tests} test(s) failed")
        else:
            print_error("\n✗ All tests failed")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return results

def main():
    """Main function"""
    print(f"\n{BLUE}╔══════════════════════════════════════════════════════════╗")
    print(f"║  Oxymoney Barringer Integration Test                    ║")
    print(f"║  TransXT API Testing Suite                              ║")
    print(f"╚══════════════════════════════════════════════════════════╝{RESET}\n")
    
    # Check if credentials are set
    if not Config.OXY_BAR_USERNAME or not Config.OXY_BAR_PASSWORD:
        print_error("OXY_BAR_USERNAME or OXY_BAR_PASSWORD not set in environment variables!")
        print_info("Please set the following environment variables:")
        print("  - OXY_BAR_USERNAME")
        print("  - OXY_BAR_PASSWORD")
        print("  - OXY_BAR_SECRET_KEY")
        print("  - OXY_BAR_INITIAL_AUTH_TOKEN")
        print("  - OXY_BAR_MID")
        print("  - OXY_BAR_BPM_IDENTIFIER")
        print("  - OXY_BAR_VPA1 through OXY_BAR_VPA5")
        sys.exit(1)
    
    # Create tester instance
    tester = OxymoneyBarringerTester()
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
