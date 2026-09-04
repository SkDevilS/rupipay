#!/usr/bin/env python3
"""
Extract last 200 ViyonaPay payin API requests with complete payload, request ID, and timestamp
"""

import sys
import os
import json
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def extract_viyonapay_requests():
    """Extract last 200 ViyonaPay payin requests from database"""
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # First check which columns exist
            cursor.execute("DESCRIBE payin_transactions")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]
            
            # Build query with only existing columns
            base_columns = [
                'txn_id', 'merchant_id', 'order_id', 'amount', 'charge_amount',
                'net_amount', 'charge_type', 'status', 'pg_partner', 'pg_txn_id',
                'payee_name', 'payee_email', 'payee_mobile', 'product_info',
                'payment_url', 'callback_url', 'created_at', 'updated_at'
            ]
            
            # Add optional columns if they exist
            optional_columns = ['bank_ref_no', 'payment_mode', 'error_message', 'remarks', 'completed_at']
            
            select_columns = []
            for col in base_columns:
                if col in column_names:
                    select_columns.append(col)
            
            for col in optional_columns:
                if col in column_names:
                    select_columns.append(col)
            
            # Get last 200 ViyonaPay payin transactions with all details
            query = f"""
                SELECT {', '.join(select_columns)}
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 200
            """
            
            cursor.execute(query)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No ViyonaPay transactions found")
                return
            
            print(f"\n{'='*100}")
            print(f"VIYONAPAY PAYIN API REQUESTS - LAST 200 CALLS")
            print(f"{'='*100}\n")
            print(f"Total Records Found: {len(transactions)}\n")
            
            # Prepare detailed output
            results = []
            
            for idx, txn in enumerate(transactions, 1):
                # Reconstruct the API request payload
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
                
                # Create detailed record
                record = {
                    "sequence": idx,
                    "request_id": txn['txn_id'],
                    "timestamp": txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                    "merchant_id": txn['merchant_id'],
                    "order_id": txn['order_id'],
                    "pg_transaction_id": txn['pg_txn_id'],
                    "status": txn['status'],
                    "amount": float(txn['amount']),
                    "charge_amount": float(txn['charge_amount']) if txn.get('charge_amount') else 0,
                    "net_amount": float(txn['net_amount']) if txn.get('net_amount') else 0,
                    "charge_type": txn.get('charge_type'),
                    "bank_ref_no": txn.get('bank_ref_no'),
                    "payment_mode": txn.get('payment_mode'),
                    "error_message": txn.get('error_message'),
                    "payment_url": txn.get('payment_url'),
                    "callback_url": txn['callback_url'],
                    "request_payload": request_payload,
                    "updated_at": txn['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['updated_at'] else None
                }
                
                results.append(record)
                
                # Print formatted output
                print(f"{'─'*100}")
                print(f"[{idx}] REQUEST ID: {txn['txn_id']}")
                print(f"{'─'*100}")
                print(f"Timestamp:        {record['timestamp']}")
                print(f"Merchant ID:      {txn['merchant_id']}")
                print(f"Order ID:         {txn['order_id']}")
                print(f"PG Txn ID:        {txn['pg_txn_id']}")
                print(f"Status:           {txn['status']}")
                print(f"Amount:           ₹{txn['amount']}")
                print(f"Charge:           ₹{txn.get('charge_amount', 0)} ({txn.get('charge_type', 'N/A')})")
                print(f"Net Amount:       ₹{txn.get('net_amount', 0)}")
                print(f"Bank Ref No:      {txn.get('bank_ref_no') or 'N/A'}")
                print(f"Payment Mode:     {txn.get('payment_mode') or 'N/A'}")
                print(f"Updated At:       {record['updated_at']}")
                print(f"Completed At:     {txn.get('completed_at') or 'N/A'}")
                print(f"\nREQUEST PAYLOAD:")
                print(json.dumps(request_payload, indent=2))
                print(f"\nCustomer Details:")
                print(f"  Name:           {txn['payee_name']}")
                print(f"  Email:          {txn['payee_email']}")
                print(f"  Mobile:         {txn['payee_mobile']}")
                print(f"\nPayment URL:      {txn.get('payment_url') or 'N/A'}")
                print(f"Callback URL:     {txn.get('callback_url') or 'N/A'}")
                
                if txn.get('error_message'):
                    print(f"\n⚠️  Error Message:  {txn['error_message']}")
                
                if txn.get('remarks'):
                    print(f"📝 Remarks:        {txn['remarks']}")
                
                print()
            
            # Save to JSON file
            output_file = f"viyonapay_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n{'='*100}")
            print(f"✅ Data exported to: {output_file}")
            print(f"{'='*100}\n")
            
            # Summary statistics
            print(f"SUMMARY STATISTICS:")
            print(f"{'─'*100}")
            
            status_counts = {}
            total_amount = 0
            total_charges = 0
            
            for txn in transactions:
                status = txn['status']
                status_counts[status] = status_counts.get(status, 0) + 1
                total_amount += float(txn['amount'])
                if txn.get('charge_amount'):
                    total_charges += float(txn['charge_amount'])
            
            print(f"Total Transactions:   {len(transactions)}")
            print(f"Total Amount:         ₹{total_amount:,.2f}")
            print(f"Total Charges:        ₹{total_charges:,.2f}")
            print(f"\nStatus Breakdown:")
            for status, count in sorted(status_counts.items()):
                print(f"  {status:20s}: {count}")
            
            print(f"\n{'='*100}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    extract_viyonapay_requests()
