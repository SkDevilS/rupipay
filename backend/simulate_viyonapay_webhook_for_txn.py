#!/usr/bin/env python3
"""
Simulate ViyonaPay Webhook for Specific Transaction
Sends a test webhook to your callback endpoint for a real transaction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime
import time
from database import get_db_connection

def simulate_webhook_for_transaction(txn_id):
    """Simulate a ViyonaPay webhook for a specific transaction"""
    
    print("\n" + "="*80)
    print("  SIMULATE VIYONAPAY WEBHOOK FOR TRANSACTION")
    print("="*80)
    print(f"\nTransaction ID: {txn_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get transaction details from database
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT txn_id, order_id, merchant_id, amount, status, 
                       payee_name, payee_email, payee_mobile, created_at
                FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found: {txn_id}")
                return False
            
            print("✓ Transaction found in database:")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Current Status: {txn['status']}")
            print(f"  Customer: {txn['payee_name']}")
            print()
            
            # Prepare webhook payload matching ViyonaPay format
            webhook_payload = {
                "paymentStatus": "SUCCESS",  # Simulating successful payment
                "transactionId": f"VIYONA_TEST_{int(time.time())}",  # Simulated ViyonaPay transaction ID
                "paymentMode": "UPI",
                "cardType": "",
                "cardMasked": "",
                "orderId": txn['order_id'],
                "customerName": txn['payee_name'] or "Test Customer",
                "customerEmail": txn['payee_email'] or "test@example.com",
                "customerPhoneNumber": txn['payee_mobile'] or "9999999999",
                "amount": str(txn['amount']),
                "bankRefId": f"TEST_UTR_{int(time.time())}"  # Simulated bank reference
            }
            
            print("="*80)
            print("  WEBHOOK PAYLOAD")
            print("="*80)
            print(json.dumps(webhook_payload, indent=2))
            print()
            
            # Send webhook to callback endpoint
            callback_url = "https://api.moneyone.co.in/api/callback/viyonapay/payin"
            
            print("="*80)
            print("  SENDING WEBHOOK")
            print("="*80)
            print(f"URL: {callback_url}")
            print()
            
            try:
                response = requests.post(
                    callback_url,
                    json=webhook_payload,
                    headers={
                        'Content-Type': 'application/json',
                        'X-TIMESTAMP': str(int(time.time())),
                        'X-Request-Id': f"TEST_REQ_{int(time.time())}",
                        'User-Agent': 'ViyonaPay-Webhook-Simulator/1.0'
                    },
                    timeout=10
                )
                
                print(f"Response Status: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print()
                print("Response Body:")
                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2))
                except:
                    print(response.text[:500])
                
                print()
                
                if response.status_code == 200:
                    print("✅ Webhook sent successfully!")
                    print()
                    print("Now check:")
                    print("1. Transaction status in database:")
                    print(f"   SELECT * FROM payin_transactions WHERE txn_id = '{txn_id}';")
                    print()
                    print("2. Callback logs:")
                    print(f"   SELECT * FROM callback_logs WHERE txn_id = '{txn_id}' ORDER BY created_at DESC LIMIT 1;")
                    print()
                    print("3. Merchant wallet:")
                    print(f"   SELECT * FROM merchant_wallet_transactions WHERE reference_id = '{txn_id}';")
                    
                    # Check updated transaction status
                    print()
                    print("="*80)
                    print("  VERIFYING TRANSACTION UPDATE")
                    print("="*80)
                    
                    time.sleep(1)  # Give it a moment to process
                    
                    cursor.execute("""
                        SELECT txn_id, status, pg_txn_id, bank_ref_no, updated_at
                        FROM payin_transactions
                        WHERE txn_id = %s
                    """, (txn_id,))
                    
                    updated_txn = cursor.fetchone()
                    if updated_txn:
                        print(f"\nTransaction Status: {updated_txn['status']}")
                        print(f"PG Transaction ID: {updated_txn['pg_txn_id']}")
                        print(f"Bank Ref No: {updated_txn['bank_ref_no']}")
                        print(f"Updated At: {updated_txn['updated_at']}")
                        
                        if updated_txn['status'] == 'SUCCESS':
                            print("\n🎉 SUCCESS! Transaction updated to SUCCESS status!")
                            print("Your callback handler is working correctly!")
                        elif updated_txn['status'] == txn['status']:
                            print(f"\n⚠️  Transaction status unchanged: {updated_txn['status']}")
                            print("Check callback_logs table for details")
                    
                    return True
                else:
                    print(f"❌ Webhook failed with status {response.status_code}")
                    return False
                    
            except requests.exceptions.ConnectionError as e:
                print(f"❌ Connection Error: Cannot connect to {callback_url}")
                print(f"Error: {e}")
                return False
                
            except Exception as e:
                print(f"❌ Error sending webhook: {e}")
                import traceback
                traceback.print_exc()
                return False
                
    finally:
        conn.close()

if __name__ == "__main__":
    # Transaction ID from user
    txn_id = "VIYONAPAY_7679022140_ORD98787676565625992_20260323004738"
    
    print("\n" + "🧪"*40)
    print("  VIYONAPAY WEBHOOK SIMULATOR")
    print("🧪"*40)
    print("\nThis script will simulate a ViyonaPay SUCCESS webhook")
    print("for your test transaction to verify your callback handler.")
    print()
    
    success = simulate_webhook_for_transaction(txn_id)
    
    print("\n" + "="*80)
    if success:
        print("  TEST COMPLETED SUCCESSFULLY")
    else:
        print("  TEST FAILED")
    print("="*80 + "\n")
    
    sys.exit(0 if success else 1)
