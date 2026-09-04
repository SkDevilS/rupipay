#!/usr/bin/env python3
"""
Verify Rang callback endpoint accessibility and configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime

def test_callback_endpoint_accessibility():
    """Test if callback endpoints are accessible"""
    print("=" * 80)
    print("RANG CALLBACK ENDPOINT ACCESSIBILITY TEST")
    print("=" * 80)
    
    endpoints = [
        {
            'name': 'Production Callback',
            'url': 'https://api.moneyone.co.in/rang-payin-callback',
            'description': 'Main callback endpoint for Rang'
        },
        {
            'name': 'Test Callback',
            'url': 'https://api.moneyone.co.in/test-rang-callback',
            'description': 'Test endpoint for connectivity verification'
        }
    ]
    
    test_data = {
        'status_id': '1',
        'amount': '100.00',
        'utr': 'TEST_UTR_CONNECTIVITY',
        'client_id': 'TEST_CONNECTIVITY_123',
        'message': 'Connectivity test'
    }
    
    for endpoint in endpoints:
        print(f"\n🧪 Testing: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print(f"Description: {endpoint['description']}")
        print("-" * 60)
        
        try:
            # Test JSON format
            print("📤 Testing JSON format...")
            response = requests.post(
                endpoint['url'],
                json=test_data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Endpoint is accessible and responding")
                try:
                    response_json = response.json()
                    print(f"Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"Response Text: {response.text[:200]}")
            elif response.status_code == 404:
                print("❌ Endpoint not found (404)")
            elif response.status_code == 500:
                print("❌ Server error (500)")
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")
            
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed - endpoint not accessible")
        except requests.exceptions.Timeout:
            print("❌ Request timeout - endpoint may be slow")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print()

def check_callback_url_in_database():
    """Check callback URLs stored in database"""
    print("=" * 80)
    print("DATABASE CALLBACK URL CONFIGURATION")
    print("=" * 80)
    
    try:
        from database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check recent Rang transactions and their callback URLs
        cursor.execute("""
            SELECT txn_id, order_id, callback_url, created_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            print("📊 CALLBACK URLs IN RECENT TRANSACTIONS:")
            print("-" * 80)
            
            for txn in transactions:
                print(f"TXN ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Callback URL: {txn['callback_url'] or 'NOT SET'}")
                print(f"Created: {txn['created_at']}")
                print("-" * 40)
            
            # Check if callback URLs are properly set
            callback_urls = [txn['callback_url'] for txn in transactions if txn['callback_url']]
            unique_urls = set(callback_urls)
            
            print(f"\n📋 CALLBACK URL ANALYSIS:")
            print(f"Transactions with callback URL: {len(callback_urls)}/{len(transactions)}")
            print(f"Unique callback URLs: {len(unique_urls)}")
            
            if unique_urls:
                print("\nConfigured URLs:")
                for url in unique_urls:
                    print(f"  • {url}")
            
        else:
            print("❌ No Rang transactions found for today")
        
        # Check merchant callback configuration
        cursor.execute("""
            SELECT merchant_id, payin_callback_url
            FROM merchant_callbacks
            WHERE payin_callback_url IS NOT NULL
        """)
        
        merchant_callbacks = cursor.fetchall()
        
        if merchant_callbacks:
            print(f"\n📋 MERCHANT CALLBACK CONFIGURATION:")
            print("-" * 50)
            for cb in merchant_callbacks:
                print(f"Merchant {cb['merchant_id']}: {cb['payin_callback_url']}")
        else:
            print("\n⚠️ No merchant callback URLs configured")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def generate_callback_configuration_guide():
    """Generate configuration guide for Rang team"""
    print("\n" + "=" * 80)
    print("RANG TEAM CONFIGURATION GUIDE")
    print("=" * 80)
    
    config_info = {
        "Callback URL": "https://api.moneyone.co.in/rang-payin-callback",
        "Method": "POST",
        "Content-Type": "application/json (preferred) or application/x-www-form-urlencoded",
        "Expected Parameters": {
            "status_id": "1 (Success), 2 (Pending), 3 (Failed)",
            "amount": "Transaction amount as string",
            "utr": "Bank reference number (UTR) - required for success",
            "client_id": "RefID sent during order creation (our txn_id)",
            "message": "Payment status message"
        },
        "Response Format": {
            "success": "boolean - true if processed successfully",
            "message": "string - processing result message",
            "txn_id": "string - our internal transaction ID",
            "status": "string - updated transaction status"
        }
    }
    
    print("📋 CONFIGURATION DETAILS TO SHARE WITH RANG:")
    print("-" * 60)
    
    for key, value in config_info.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")
        print()
    
    print("📝 SAMPLE CALLBACK REQUEST:")
    print("-" * 40)
    sample_request = {
        "status_id": "1",
        "amount": "500.00",
        "utr": "60xxx763",
        "client_id": "20260316151651329232",
        "message": "Payment successful"
    }
    print(json.dumps(sample_request, indent=2))
    
    print("\n📝 EXPECTED RESPONSE:")
    print("-" * 40)
    sample_response = {
        "success": True,
        "message": "Callback processed successfully",
        "txn_id": "20260316151651329232",
        "status": "SUCCESS"
    }
    print(json.dumps(sample_response, indent=2))
    
    print("\n⚠️ IMPORTANT NOTES:")
    print("-" * 40)
    print("• client_id must match the RefID sent during order creation")
    print("• UTR is required for successful transactions")
    print("• Callbacks should be sent for all status changes")
    print("• Duplicate callbacks are handled automatically")
    print("• Endpoint supports both JSON and form-encoded data")

def test_callback_with_curl_commands():
    """Generate curl commands for testing"""
    print("\n" + "=" * 80)
    print("CURL COMMANDS FOR TESTING")
    print("=" * 80)
    
    base_url = "https://api.moneyone.co.in"
    
    curl_commands = [
        {
            "name": "Test JSON Callback (Success)",
            "command": f"""curl -X POST {base_url}/test-rang-callback \\
  -H "Content-Type: application/json" \\
  -d '{{"status_id":"1","amount":"100.00","utr":"TEST123","client_id":"TEST001","message":"Success"}}'"""
        },
        {
            "name": "Test Form Callback (Success)",
            "command": f"""curl -X POST {base_url}/test-rang-callback \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "status_id=1&amount=100.00&utr=TEST123&client_id=TEST001&message=Success" """
        },
        {
            "name": "Production Callback Test (Use with caution)",
            "command": f"""curl -X POST {base_url}/rang-payin-callback \\
  -H "Content-Type: application/json" \\
  -d '{{"status_id":"1","amount":"100.00","utr":"TEST123","client_id":"REAL_TXN_ID","message":"Success"}}'"""
        }
    ]
    
    for cmd in curl_commands:
        print(f"📝 {cmd['name']}:")
        print("-" * 50)
        print(cmd['command'])
        print()

def main():
    """Main execution function"""
    print("🔍 RANG CALLBACK ENDPOINT VERIFICATION")
    print("=" * 80)
    print(f"Verification Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Test endpoint accessibility
    test_callback_endpoint_accessibility()
    
    # Step 2: Check database configuration
    check_callback_url_in_database()
    
    # Step 3: Generate configuration guide
    generate_callback_configuration_guide()
    
    # Step 4: Provide curl commands
    test_callback_with_curl_commands()
    
    print("=" * 80)
    print("✅ VERIFICATION COMPLETED")
    print("=" * 80)
    print()
    print("📋 ACTION ITEMS:")
    print("1. Verify endpoints are accessible from external networks")
    print("2. Share configuration details with Rang team")
    print("3. Test callback processing with real transaction IDs")
    print("4. Monitor callback logs after configuration")

if __name__ == "__main__":
    main()