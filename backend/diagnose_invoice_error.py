#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime
from database import get_db_connection

def diagnose_invoice_creation(txn_id):
    """
    Diagnose invoice creation issue by checking transaction data and API response
    """
    conn = None
    cursor = None
    
    try:
        print("=" * 80)
        print(f"🔍 DIAGNOSING INVOICE CREATION FOR TXN: {txn_id}")
        print("=" * 80)
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        cursor = conn.cursor()
        
        # Fetch transaction details
        print("📋 Fetching transaction details...")
        cursor.execute("""
            SELECT 
                txn_id,
                order_id,
                amount,
                payee_name,
                payee_email,
                payee_mobile,
                bank_ref_no,
                pg_txn_id,
                status,
                completed_at,
                created_at
            FROM payin_transactions
            WHERE txn_id = %s
        """, (txn_id,))
        
        txn = cursor.fetchone()
        
        if not txn:
            print(f"❌ Transaction {txn_id} not found")
            return
        
        print("✅ Transaction found:")
        print(f"   TXN ID: {txn['txn_id']}")
        print(f"   Order ID: {txn['order_id']}")
        print(f"   Amount: {txn['amount']}")
        print(f"   Status: {txn['status']}")
        print(f"   Customer: {txn['payee_name']}")
        print(f"   Email: {txn['payee_email']}")
        print(f"   Mobile: {txn['payee_mobile']}")
        print(f"   Bank Ref: {txn['bank_ref_no']}")
        print(f"   PG TXN ID: {txn['pg_txn_id']}")
        
        # Check if transaction is successful
        if txn['status'] != 'SUCCESS':
            print(f"❌ Transaction status is {txn['status']}, not SUCCESS")
            print("   Invoice can only be created for successful transactions")
            return
        
        print("\n📝 Preparing invoice data...")
        
        # Format timestamp
        timestamp = txn['completed_at'] or txn['created_at']
        if timestamp:
            formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            formatted_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract last 14 digits from order_id
        order_id_str = str(txn['order_id'])
        last_14_digits = order_id_str[-14:] if len(order_id_str) >= 14 else order_id_str
        
        # Get last 5 digits of order_id for making email/mobile unique
        last_5_digits = order_id_str[-5:] if len(order_id_str) >= 5 else order_id_str
        
        # Make email unique by adding last 5 digits before @
        original_email = txn['payee_email']
        if '@' in original_email:
            email_parts = original_email.split('@')
            unique_email = f"{email_parts[0]}{last_5_digits}@{email_parts[1]}"
        else:
            unique_email = f"{original_email}{last_5_digits}"
        
        # Make mobile unique by appending last 5 digits
        original_mobile = str(txn['payee_mobile'])
        unique_mobile = f"{original_mobile}{last_5_digits}"
        
        # Prepare invoice data
        invoice_data = {
            'amount': float(txn['amount']),
            'orderid': last_14_digits,
            'payee_name': txn['payee_name'],
            'payee_email': unique_email,
            'payee_mobile': unique_mobile,
            'UTR': txn['bank_ref_no'] or txn['pg_txn_id'] or 'N/A',
            'Refno': txn['pg_txn_id'] or txn['bank_ref_no'] or txn['txn_id'],
            'TimeStamp': formatted_timestamp
        }
        
        print("✅ Invoice data prepared:")
        print(json.dumps(invoice_data, indent=2))
        
        print("\n🌐 Sending request to invoice API...")
        print("URL: https://api.truaxisventures.in/api/auto-order/create")
        
        # Send to external invoice API
        try:
            response = requests.post(
                'https://api.truaxisventures.in/api/auto-order/create',
                json=invoice_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"📊 Response Data:")
                print(json.dumps(response_data, indent=2))
            except:
                print(f"📊 Response Text: {response.text}")
            
            if response.status_code == 201:
                print("✅ Invoice created successfully!")
            else:
                print(f"❌ Invoice creation failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python diagnose_invoice_error.py <txn_id>")
        print("Example: python diagnose_invoice_error.py VY_BAR_9000000001_TRD8CA0272674")
        sys.exit(1)
    
    txn_id = sys.argv[1]
    diagnose_invoice_creation(txn_id)