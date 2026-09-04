#!/usr/bin/env python3
"""
Test Rang callback system with correct transaction lookup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime
from database import get_db_connection

def get_recent_rang_transactions():
    """Get recent Rang transactions to test with"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, order_id, merchant_id, amount, status
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return transactions
        
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

def test_callback_with_real_transaction():
    """Test callback with real transaction data"""
    print("=" * 80)
    print("TESTING RANG CALLBACK WITH REAL TRANSACTIONS")
    print("=" * 80)
    
    transactions = get_recent_rang_transactions()
    
    if not transactions:
        print("❌ No Rang transactions found for today")
        return
    
    print(f"📊 Found {len(transactions)} Rang transaction(s) to test with")
    print()
    
    for i, txn in enumerate(transactions, 1):
        print(f"🧪 TEST {i}: Transaction {txn['txn_id']}")
        print("-" * 60)
        print(f"TXN ID: {txn['txn_id']}")
        print(f"Order ID: {txn['order_id']}")
        print(f"Current Status: {txn['status']}")
        print(f"Amount: ₹{txn['amount']}")
        
        # Test SUCCESS callback
        test_callback_data = {
            'status_id': '1',  # SUCCESS
            'amount': str(txn['amount']),
            'utr': f'TEST_UTR_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'client_id': txn['txn_id'],  # This is the RefID we sent to Rang
            'message': 'Payment successful - TEST'
        }
        
        print(f"\n📤 Sending test callback:")
        print(f"Callback Data: {json.dumps(test_callback_data, indent=2)}")
        
        try:
            # Test with JSON format (as Rang is now sending JSON)
            url = "http://localhost:5000/rang-payin-callback"
            
            response = requests.post(
                url,
                json=test_callback_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"\n📥 Response:")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('success'):
                    print(f"✅ Callback processed successfully!")
                    print(f"Status updated to: {response_json.get('status')}")
                else:
                    print(f"❌ Callback processing failed: {response_json.get('message')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
        
        print("\n" + "=" * 60)
        print()

def test_callback_formats():
    """Test both JSON and form-encoded formats"""
    print("=" * 80)
    print("TESTING CALLBACK FORMAT COMPATIBILITY")
    print("=" * 80)
    
    # Use a test transaction ID
    test_data = {
        'status_id': '1',
        'amount': '100.00',
        'utr': 'TEST_UTR_FORMAT_123',
        'client_id': 'TEST_TXN_ID_123',
        'message': 'Payment successful'
    }
    
    formats = [
        {
            'name': 'JSON Format (Current Rang)',
            'headers': {'Content-Type': 'application/json'},
            'method': 'json'
        },
        {
            'name': 'Form-encoded Format (Legacy)',
            'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
            'method': 'data'
        }
    ]
    
    for fmt in formats:
        print(f"\n🧪 Testing: {fmt['name']}")
        print("-" * 50)
        
        try:
            url = "http://localhost:5000/test-rang-callback"
            
            if fmt['method'] == 'json':
                response = requests.post(url, json=test_data, headers=fmt['headers'], timeout=10)
            else:
                response = requests.post(url, data=test_data, headers=fmt['headers'], timeout=10)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ {fmt['name']} works correctly!")
            else:
                print(f"❌ {fmt['name']} failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def verify_callback_url_configuration():
    """Verify callback URL configuration"""
    print("\n" + "=" * 80)
    print("CALLBACK URL CONFIGURATION VERIFICATION")
    print("=" * 80)
    
    print("📋 CALLBACK URL DETAILS:")
    print("-" * 50)
    print("Production URL: https://api.moneyone.co.in/rang-payin-callback")
    print("Test URL: https://api.moneyone.co.in/test-rang-callback")
    print("Local Test URL: http://localhost:5000/rang-payin-callback")
    print()
    
    print("📝 EXPECTED CALLBACK FORMAT:")
    print("-" * 50)
    expected_format = {
        "status_id": "1 (Success), 2 (Pending), 3 (Failed)",
        "amount": "Transaction amount",
        "utr": "Bank reference number (UTR)",
        "client_id": "RefID sent to Rang (our txn_id)",
        "message": "Payment message"
    }
    
    for key, desc in expected_format.items():
        print(f"  {key}: {desc}")
    
    print("\n⚠️ IMPORTANT NOTES:")
    print("-" * 50)
    print("• client_id should match our txn_id (RefID sent to Rang)")
    print("• Rang is now sending JSON format callbacks")
    print("• Both JSON and form-encoded formats are supported")
    print("• Callback URL must be whitelisted with Rang team")

def check_transaction_id_mapping():
    """Check how transaction IDs are mapped"""
    print("\n" + "=" * 80)
    print("TRANSACTION ID MAPPING VERIFICATION")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, order_id, pg_txn_id, created_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            print("📊 RECENT RANG TRANSACTIONS:")
            print("-" * 70)
            print(f"{'TXN ID (RefID)':<25} {'Order ID':<20} {'PG TXN ID':<15} {'Created'}")
            print("-" * 70)
            
            for txn in transactions:
                print(f"{txn['txn_id']:<25} {txn['order_id']:<20} {txn['pg_txn_id'] or 'None':<15} {txn['created_at']}")
            
            print("\n📝 MAPPING EXPLANATION:")
            print("-" * 50)
            print("• TXN ID (RefID): Sent to Rang as RefID, returned as client_id in callback")
            print("• Order ID: Merchant's order identifier")
            print("• PG TXN ID: Rang's internal transaction ID (if provided)")
            print("\n✅ Callback should use client_id to lookup txn_id in database")
        else:
            print("❌ No Rang transactions found for today")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking transaction mapping: {e}")

def main():
    """Main execution function"""
    print("🔧 RANG CALLBACK SYSTEM FIX VERIFICATION")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Verify transaction ID mapping
    check_transaction_id_mapping()
    
    # Step 2: Test callback formats
    test_callback_formats()
    
    # Step 3: Test with real transactions
    test_callback_with_real_transaction()
    
    # Step 4: Verify configuration
    verify_callback_url_configuration()
    
    print("\n" + "=" * 80)
    print("✅ CALLBACK SYSTEM FIX VERIFICATION COMPLETED")
    print("=" * 80)
    print()
    print("📋 NEXT STEPS:")
    print("1. Deploy the callback fix to production")
    print("2. Contact Rang team to verify callback URL configuration")
    print("3. Test with a real payment to confirm callbacks are received")
    print("4. Monitor callback logs for successful processing")

if __name__ == "__main__":
    main()