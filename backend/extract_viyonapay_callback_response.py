#!/usr/bin/env python3
"""
Extract and display ViyonaPay callback response data for mapping
This script retrieves the most recent ViyonaPay callback and displays all fields
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime

def extract_viyonapay_callback():
    """Extract the most recent ViyonaPay callback response"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("  CHECKING PAYIN_TRANSACTIONS TABLE")
            print("="*80)
            
            # First check payin_transactions for ViyonaPay
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    pg_partner,
                    pg_txn_id,
                    bank_ref_no,
                    utr,
                    payment_mode,
                    created_at,
                    updated_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            transaction = cursor.fetchone()
            
            if transaction:
                print(f"\n✅ Found ViyonaPay Transaction:\n")
                print(f"Transaction ID: {transaction['txn_id']}")
                print(f"Order ID: {transaction['order_id']}")
                print(f"Merchant ID: {transaction['merchant_id']}")
                print(f"Amount: ₹{transaction['amount']}")
                print(f"Status: {transaction['status']}")
                print(f"PG TXN ID: {transaction['pg_txn_id']}")
                print(f"Bank Ref No: {transaction['bank_ref_no']}")
                print(f"UTR: {transaction['utr']}")
                print(f"Payment Mode: {transaction['payment_mode']}")
                print(f"Created: {transaction['created_at']}")
                print(f"Updated: {transaction['updated_at']}")
                
                txn_id = transaction['txn_id']
            else:
                print("\n❌ No ViyonaPay transactions found")
                txn_id = None
            
            print("\n" + "="*80)
            print("  CHECKING CALLBACK_LOGS TABLE")
            print("="*80)
            
            # Check callback_logs for raw callback data
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE request_data LIKE '%VIYONAPAY%'
                   OR request_data LIKE '%viyonapay%'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            callback = cursor.fetchone()
            
            if callback:
                print(f"\n✅ Found ViyonaPay Callback:\n")
                print(f"Callback ID: {callback['id']}")
                print(f"Merchant ID: {callback['merchant_id']}")
                print(f"Callback URL: {callback['callback_url']}")
                print(f"Response Code: {callback['response_code']}")
                print(f"Created: {callback['created_at']}")
                
                print("\n" + "="*80)
                print("  RAW REQUEST DATA (What ViyonaPay sent)")
                print("="*80)
                
                try:
                    request_data = json.loads(callback['request_data']) if callback['request_data'] else {}
                    print(json.dumps(request_data, indent=2))
                except:
                    print(callback['request_data'])
                
                if callback['response_data']:
                    print("\n" + "="*80)
                    print("  RESPONSE DATA (What we sent back)")
                    print("="*80)
                    print(callback['response_data'])
            else:
                print("\n❌ No ViyonaPay callbacks found in callback_logs")
            
            # Check for encrypted webhook data
            print("\n" + "="*80)
            print("  CHECKING FOR ENCRYPTED WEBHOOK DATA")
            print("="*80)
            
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    request_data,
                    created_at
                FROM callback_logs
                WHERE (request_data LIKE '%encryptedData%' 
                   OR request_data LIKE '%signature%'
                   OR request_data LIKE '%aad%')
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            encrypted_callback = cursor.fetchone()
            
            if encrypted_callback:
                print(f"\n✅ Found Encrypted Webhook Data:\n")
                print(f"Callback ID: {encrypted_callback['id']}")
                print(f"Merchant ID: {encrypted_callback['merchant_id']}")
                print(f"Created: {encrypted_callback['created_at']}")
                
                print("\n" + "="*80)
                print("  ENCRYPTED WEBHOOK STRUCTURE")
                print("="*80)
                
                try:
                    webhook_data = json.loads(encrypted_callback['request_data'])
                    print(json.dumps(webhook_data, indent=2))
                    
                    # Show structure
                    print("\n" + "="*80)
                    print("  WEBHOOK FIELDS PRESENT")
                    print("="*80)
                    for key in webhook_data.keys():
                        print(f"  ✓ {key}")
                except:
                    print(encrypted_callback['request_data'])
            
            # Generate mapping template
            print("\n" + "="*80)
            print("  FIELD MAPPING TEMPLATE")
            print("="*80)
            print("""
# ViyonaPay Callback Response Mapping

Based on the callback data above, map the following fields:

## Transaction Status Mapping
- SUCCESS → 'SUCCESS'
- FAILED → 'FAILED'
- PENDING → 'PENDING'

## Field Mapping
{
    "txn_id": "our_transaction_id",
    "order_id": "viyonapay_order_id or merchantOrderId",
    "pg_txn_id": "viyonapay_transaction_id or paymentId",
    "bank_ref_no": "viyonapay_bank_reference or rrn",
    "utr": "viyonapay_utr or referenceNumber",
    "status": "viyonapay_status",
    "amount": "viyonapay_amount",
    "payment_mode": "viyonapay_payment_method"
}

## Decrypted Response Structure (if encrypted)
After decryption, the response should contain:
- Transaction/Payment ID
- Order ID
- Status
- Amount
- UTR/Reference Number
- Payment Method
- Timestamp
            """)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ViyonaPay Callback Response Extractor")
    print("  Extract callback data for field mapping")
    print("="*80)
    extract_viyonapay_callback()
    print("\n" + "="*80)
