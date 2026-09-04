#!/usr/bin/env python3
"""
Manually process the Viyonapay callback for order ORD98787865452612432
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from database import get_db_connection

# The callback data from Viyonapay
callback_data = {
    "response_status": 1,
    "encrypted_data": "Afp2eED73mw5VSM0Esa5e7CXzniYU62OKDjf5G5+3//G6xsxCboPHnC2D3XEiQ5lPp6PMVh7dCsrt8lvsNgbqB/Ar2ypfhMYibsKfu1DcM5+d1UNVpHgZxV4s2a9CYVMdsuxzeYWwi7c826G0cbMVlwNlEt9i88HhLb8BPEQKqEfRdIx+pPQncat6pd69hLureA7sfkG2XdthEfL94OcDi1Gb31IePg3OgstY8aGqk027JrxPU6yApZkyu8h0oz861e17f7AUIR6+21rslmRV10VoAvHIH4zZtUXzPU8FVa/PGumbk1LlM4Zfn4omzFClOGDv1zjccLIuH2bfH861+Cunmmq6DP4qU7xUgRDzi7aa5rZse/gPdzhsXeu+zMAaVjx7+P/l/kd5C11ApfABoKdBiyZWl4XbaZBmZajjQJ/YGE4KvHKbTRVfawsLx87pQO13sXIm3fPg5rTG4aEecmiE+1KtwT+JsAgzYIV5Rg7CsEL/HkBbwcthP+m3Lr8KBH10NtJQgFR06FmcqqCpO1q61aoJWh8fjT61TSs5tGfhpsj8V8="
}

headers = {
    "X-SIGNATURE": "YrAE9oqPFp/qUGkdt7Z61aZcldGwPbwon6uGVPSrqHL0LdvHCOYyGXJ3vNkbWgt1Dg9LtFzzTmpAOUPtjIh5Zw7omb/AOJ608qgbMmjjv64iiIrZ+8j3rrv+kqBSS6MzLvSmjI4go0nmSwCFYKPkX09bVpKm0OI8XjEg+7d9m5trDj+w0KJ5/JhP8S7OIvSZjYbIZ26grcx/9NdZgG6MNN0wSU86XQrIDl9mOHPVslSw8o/ekrYNi8Ec7iZFElxEYMWfqFP1gxdtImlafQf0pP9hd91HC+8P151Fgmp3osBXWYXVOpMUJ4zlh+M9DaeQXjlfbneBFsxVT4usr1iHiA==",
    "X-TIMESTAMP": "1774204672",
    "X-Request-Id": "5cfe4bd1-35c6-43b2-bdb8-aedd9d77a982",
    "X-API-KEY": "295415975dc48c94e6b41c39a558f2716491765cf650a742a190a1b462000c9f"
}

def load_client_secret_key():
    """Load the webhook secret key"""
    try:
        # Try environment variable first
        secret_key_b64 = os.getenv('VIYONAPAY_WEBHOOK_SECRET_KEY')
        if secret_key_b64:
            return base64.b64decode(secret_key_b64)
        
        # Try file
        key_path = os.path.join(os.path.dirname(__file__), 'viyonapay_webhook_secret.key')
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        
        print("❌ Webhook secret key not found")
        return None
    except Exception as e:
        print(f"❌ Error loading secret key: {e}")
        return None

def decrypt_webhook_response(encrypted_b64, secret_key, aad_dict):
    """Decrypt webhook response"""
    try:
        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_b64)
        
        # Extract nonce (first 12 bytes) and ciphertext
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        
        # Prepare AAD
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Decrypt
        aesgcm = AESGCM(secret_key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        
        # Parse JSON
        decrypted_json = json.loads(decrypted_bytes.decode('utf-8'))
        return decrypted_json
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        return None

def main():
    print(f"\n{'='*60}")
    print(f"🔓 Processing Viyonapay Callback Manually")
    print(f"{'='*60}\n")
    
    # Load secret key
    print("📋 Loading webhook secret key...")
    secret_key = load_client_secret_key()
    if not secret_key:
        print("❌ Cannot proceed without secret key")
        return
    
    print(f"✅ Secret key loaded ({len(secret_key)} bytes)\n")
    
    # Prepare AAD
    aad = {
        'timestamp': int(headers['X-TIMESTAMP']),
        'request_id': headers['X-Request-Id']
    }
    
    print(f"📋 AAD Data:")
    print(json.dumps(aad, indent=2))
    print()
    
    # Decrypt
    print("🔓 Decrypting callback data...")
    decrypted_data = decrypt_webhook_response(
        callback_data['encrypted_data'],
        secret_key,
        aad
    )
    
    if not decrypted_data:
        print("❌ Decryption failed")
        return
    
    print("✅ Decryption successful!\n")
    print(f"📦 Decrypted Data:")
    print(json.dumps(decrypted_data, indent=2))
    print()
    
    # Extract responseBody
    response_body = decrypted_data.get('responseBody', {})
    if not response_body:
        print("❌ No responseBody in decrypted data")
        return
    
    print(f"📦 Response Body:")
    print(json.dumps(response_body, indent=2))
    print()
    
    # Extract order_id
    order_id = response_body.get('orderId')
    if not order_id:
        print("❌ No orderId in response body")
        return
    
    print(f"🔍 Looking up order: {order_id}\n")
    
    # Check database
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    pg_partner,
                    status,
                    amount,
                    net_amount,
                    charge_amount,
                    pg_txn_id,
                    created_at
                FROM payin_transactions
                WHERE order_id = %s AND pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 1
            """, (order_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found for order_id: {order_id}")
                print("\n🔍 Checking if order exists with different pg_partner...")
                
                cursor.execute("""
                    SELECT txn_id, order_id, pg_partner, status, created_at
                    FROM payin_transactions
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (order_id,))
                
                all_txns = cursor.fetchall()
                if all_txns:
                    print(f"Found {len(all_txns)} transaction(s) with this order_id:")
                    for t in all_txns:
                        print(f"  - Txn: {t['txn_id']}, PG: {t['pg_partner']}, Status: {t['status']}")
                else:
                    print("No transactions found with this order_id")
                return
            
            print(f"✅ Transaction found!")
            print(f"\n📋 Transaction Details:")
            print(f"  Txn ID: {txn['txn_id']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  PG Partner: {txn['pg_partner']}")
            print(f"  Current Status: {txn['status']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Net Amount: ₹{txn['net_amount']}")
            print(f"  Charge: ₹{txn['charge_amount']}")
            print(f"  PG Txn ID: {txn['pg_txn_id']}")
            print(f"  Created: {txn['created_at']}")
            
            # Extract payment details from callback
            payment_status = response_body.get('paymentStatus')
            transaction_id = response_body.get('transactionId')
            bank_ref_id = response_body.get('bankRefId', '')
            
            print(f"\n📋 Callback Payment Details:")
            print(f"  Payment Status: {payment_status}")
            print(f"  Transaction ID: {transaction_id}")
            print(f"  Bank Ref ID: {bank_ref_id}")
            
            # Map status
            if payment_status == 'SUCCESS':
                new_status = 'SUCCESS'
            elif payment_status == 'FAILED':
                new_status = 'FAILED'
            elif payment_status == 'PENDING':
                new_status = 'PENDING'
            else:
                new_status = 'INITIATED'
            
            print(f"\n📋 Status Mapping:")
            print(f"  Viyonapay Status: {payment_status}")
            print(f"  Our Status: {new_status}")
            
            if txn['status'] == new_status:
                print(f"\n⚠️  Status is already {new_status}, no update needed")
            else:
                print(f"\n✅ Status should be updated from {txn['status']} to {new_status}")
    
    finally:
        conn.close()

if __name__ == '__main__':
    main()
