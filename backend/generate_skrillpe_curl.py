#!/usr/bin/env python3
"""
Generate curl commands for SkrillPe API testing with merchant ID 7679022140 and amount 300+
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import time
import base64
from config import Config

def generate_curl_commands():
    """Generate curl commands for testing SkrillPe API"""
    print("🔍 SkrillPe Curl Command Generator")
    print("=" * 60)
    
    # Configuration
    base_url = Config.SKRILLPE_BASE_URL
    auth_api_key = Config.SKRILLPE_AUTH_API_KEY
    auth_api_password = Config.SKRILLPE_AUTH_API_PASSWORD
    bearer_token = Config.SKRILLPE_BEARER_TOKEN
    company_alias = Config.SKRILLPE_COMPANY_ALIAS
    
    # Test payload with merchant ID 7679022140 and amount above 300
    payload = {
        'transactionId': f'CURL_7679022140_{int(time.time())}',
        'amount': '350.00',  # Above 300 as requested
        'customerNumber': '9876543210',
        'CompanyAlise': company_alias
    }
    
    payload_json = json.dumps(payload)
    url = f"{base_url}/api/skrill/upi/qr/send/intent/WL"
    
    print(f"API Endpoint: {url}")
    print(f"Merchant ID: 7679022140")
    print(f"Amount: ₹350.00 (above 300)")
    print(f"Payload: {payload_json}")
    print()
    
    # Generate Basic Auth token
    auth_string = f"{auth_api_key}:{auth_api_password}"
    basic_auth_token = base64.b64encode(auth_string.encode()).decode()
    
    # Curl command 1: Bearer Token + AUTH headers
    print("🧪 Curl Command 1: Bearer Token + AUTH Headers")
    print("-" * 50)
    curl_bearer = f"""curl -X POST '{url}' \\
  --header 'Content-Type: application/json' \\
  --header 'Authorization: Bearer {bearer_token}' \\
  --header 'AUTH-API_KEY: {auth_api_key}' \\
  --header 'AUTH-API_PASSWORD: {auth_api_password}' \\
  --data '{payload_json}'"""
    
    print(curl_bearer)
    print()
    
    # Curl command 2: Basic Auth + AUTH headers (Your suggestion)
    print("🧪 Curl Command 2: Basic Auth + AUTH Headers (RECOMMENDED)")
    print("-" * 50)
    curl_basic = f"""curl -X POST '{url}' \\
  --header 'Content-Type: application/json' \\
  --header 'AUTH-API_KEY: {auth_api_key}' \\
  --header 'AUTH-API_PASSWORD: {auth_api_password}' \\
  --header 'Authorization: Basic {basic_auth_token}' \\
  --data '{payload_json}'"""
    
    print(curl_basic)
    print()
    
    # Curl command 3: Only AUTH headers
    print("🧪 Curl Command 3: Only AUTH Headers")
    print("-" * 50)
    curl_auth_only = f"""curl -X POST '{url}' \\
  --header 'Content-Type: application/json' \\
  --header 'AUTH-API_KEY: {auth_api_key}' \\
  --header 'AUTH-API_PASSWORD: {auth_api_password}' \\
  --data '{payload_json}'"""
    
    print(curl_auth_only)
    print()
    
    # Curl command 4: Only Bearer Token
    print("🧪 Curl Command 4: Only Bearer Token")
    print("-" * 50)
    curl_bearer_only = f"""curl -X POST '{url}' \\
  --header 'Content-Type: application/json' \\
  --header 'Authorization: Bearer {bearer_token}' \\
  --data '{payload_json}'"""
    
    print(curl_bearer_only)
    print()
    
    # Save to file for easy copy-paste
    with open('skrillpe_curl_commands.txt', 'w') as f:
        f.write("SkrillPe API Test Curl Commands\n")
        f.write("Merchant ID: 7679022140, Amount: ₹350.00\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("1. Bearer Token + AUTH Headers:\n")
        f.write(curl_bearer + "\n\n")
        
        f.write("2. Basic Auth + AUTH Headers (RECOMMENDED):\n")
        f.write(curl_basic + "\n\n")
        
        f.write("3. Only AUTH Headers:\n")
        f.write(curl_auth_only + "\n\n")
        
        f.write("4. Only Bearer Token:\n")
        f.write(curl_bearer_only + "\n\n")
        
        f.write("Expected Response:\n")
        f.write('{\n')
        f.write('  "code": "0",\n')
        f.write('  "reason": "Successful Intent Url Created.",\n')
        f.write('  "intentUrl": "upi://pay?pa=...",\n')
        f.write('  "tinyUrl": "https://short.skrillpe.com/..."\n')
        f.write('}\n\n')
        
        f.write("If intentUrl and tinyUrl are empty, it's the SkrillPe issue we need to report.\n")
    
    print("📁 Curl commands saved to: skrillpe_curl_commands.txt")
    print()
    
    print("📋 Instructions:")
    print("1. Copy and run each curl command in your terminal")
    print("2. Check which one returns HTTP 200 with success message")
    print("3. Look for 'intentUrl' and 'tinyUrl' in the response")
    print("4. If response shows success but empty URLs, it's SkrillPe's issue")
    print("5. Report the working header format to SkrillPe team")

if __name__ == "__main__":
    generate_curl_commands()