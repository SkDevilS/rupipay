#!/usr/bin/env python3
"""
Extract ViyonaPay failed requests (401 errors and intent creation failures)
Shows the exact payload that was sent to ViyonaPay API
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def extract_failed_requests():
    """Extract failed ViyonaPay requests with exact payloads"""
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Check which columns exist
            cursor.execute("DESCRIBE payin_transactions")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]
            
            # Build query with existing columns
            base_columns = [
                'txn_id', 'merchant_id', 'order_id', 'amount', 'charge_amount',
                'net_amount', 'charge_type', 'status', 'pg_partner', 'pg_txn_id',
                'payee_name', 'payee_email', 'payee_mobile', 'product_info',
                'payment_url', 'callback_url', 'created_at', 'updated_at'
            ]
            
            optional_columns = ['bank_ref_no', 'payment_mode', 'error_message', 'remarks', 'completed_at']
            
            select_columns = []
            for col in base_columns:
                if col in column_names:
                    select_columns.append(col)
            
            for col in optional_columns:
                if col in column_names:
                    select_columns.append(col)
            
            # Get failed ViyonaPay transactions
            query = f"""
                SELECT {', '.join(select_columns)}
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                AND status = 'FAILED'
                ORDER BY created_at DESC
                LIMIT 200
            """
            
            cursor.execute(query)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\n❌ No failed ViyonaPay transactions found")
                return
            
            print("\n" + "="*100)
            print("VIYONAPAY FAILED REQUESTS - 401 ERRORS & INTENT CREATION FAILURES")
            print("="*100 + "\n")
            print(f"Total Failed Requests Found: {len(transactions)}\n")
            
            # Filter for 401 and intent creation errors
            error_401_count = 0
            intent_failed_count = 0
            other_errors = 0
            
            results = []
            
            for idx, txn in enumerate(transactions, 1):
                error_msg = txn.get('error_message', '')
                remarks = txn.get('remarks', '')
                
                # Check if it's a 401 or intent creation error
                is_401_error = '401' in str(error_msg) or '401' in str(remarks)
                is_intent_error = 'intent' in str(error_msg).lower() or 'intent' in str(remarks).lower()
                
                if is_401_error:
                    error_401_count += 1
                    error_type = "401 UNAUTHORIZED"
                elif is_intent_error:
                    intent_failed_count += 1
                    error_type = "INTENT CREATION FAILED"
                else:
                    other_errors += 1
                    error_type = "OTHER ERROR"
                
                # Reconstruct the exact API request payload that was sent
                request_payload = {
                    "orderId": txn['order_id'],
                    "amount": str(txn['amount']),
                    "currency": "INR",
                    "name": txn['payee_name'],
                    "email": txn['payee_email'],
                    "phone": txn['payee_mobile'],
                    "payinType": "upiMasterMerchant",
                    "note": txn['product_info'] or "Payment"
                }
                
                record = {
                    "sequence": idx,
                    "error_type": error_type,
                    "request_id": txn['txn_id'],
                    "timestamp": txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                    "merchant_id": txn['merchant_id'],
                    "order_id": txn['order_id'],
                    "pg_transaction_id": txn.get('pg_txn_id'),
                    "status": txn['status'],
                    "amount": float(txn['amount']),
                    "error_message": error_msg,
                    "remarks": remarks,
                    "request_payload": request_payload,
                    "updated_at": txn['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['updated_at'] else None
                }
                
                results.append(record)
                
                # Print detailed output for 401 and intent errors
                if is_401_error or is_intent_error:
                    print(f"{'─'*100}")
                    print(f"[{idx}] ❌ {error_type}")
                    print(f"{'─'*100}")
                    print(f"Request ID:       {txn['txn_id']}")
                    print(f"Timestamp:        {record['timestamp']}")
                    print(f"Merchant ID:      {txn['merchant_id']}")
                    print(f"Order ID:         {txn['order_id']}")
                    print(f"Amount:           ₹{txn['amount']}")
                    
                    print(f"\n📤 EXACT PAYLOAD SENT TO VIYONAPAY:")
                    print(json.dumps(request_payload, indent=2))
                    
                    print(f"\n👤 CUSTOMER DETAILS:")
                    print(f"  Name:           {txn['payee_name']}")
                    print(f"  Email:          {txn['payee_email']}")
                    print(f"  Mobile:         {txn['payee_mobile']}")
                    
                    if error_msg:
                        print(f"\n❌ ERROR MESSAGE:")
                        print(f"  {error_msg}")
                    
                    if remarks:
                        print(f"\n📝 REMARKS:")
                        print(f"  {remarks}")
                    
                    print(f"\n⏱️  Created:        {record['timestamp']}")
                    print(f"⏱️  Updated:        {record['updated_at']}")
                    print()
            
            # Save to JSON
            output_file = f"viyonapay_failed_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n{'='*100}")
            print(f"✅ Data exported to: {output_file}")
            print(f"{'='*100}\n")
            
            # Summary
            print(f"📊 SUMMARY:")
            print(f"{'─'*100}")
            print(f"Total Failed Requests:    {len(transactions)}")
            print(f"401 Unauthorized Errors:  {error_401_count}")
            print(f"Intent Creation Failures: {intent_failed_count}")
            print(f"Other Errors:             {other_errors}")
            
            # Show common error patterns
            error_patterns = {}
            for txn in transactions:
                error_msg = txn.get('error_message', 'No error message')
                if error_msg:
                    # Truncate long messages
                    short_msg = error_msg[:100] if len(error_msg) > 100 else error_msg
                    error_patterns[short_msg] = error_patterns.get(short_msg, 0) + 1
            
            if error_patterns:
                print(f"\n📋 COMMON ERROR PATTERNS:")
                for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  [{count:3d}x] {error}")
            
            print(f"\n{'='*100}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    extract_failed_requests()
