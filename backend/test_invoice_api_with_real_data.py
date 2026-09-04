#!/usr/bin/env python3
"""
Test the invoice API with real transaction data from database
This will help us understand what data to send
"""
import pymysql
import requests
import json
from datetime import datetime
from config import Config

def get_db_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def test_invoice_api():
    print("=" * 80)
    print("TESTING INVOICE API WITH REAL TRANSACTION DATA")
    print("=" * 80)
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get a random SUCCESS transaction
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
        WHERE status = 'SUCCESS'
        ORDER BY RAND()
        LIMIT 1
    """)
    
    txn = cursor.fetchone()
    
    if not txn:
        print("❌ No SUCCESS transactions found in database")
        cursor.close()
        conn.close()
        return
    
    print("\n📊 TRANSACTION DATA FROM DATABASE:")
    print("-" * 80)
    print(f"Transaction ID: {txn['txn_id']}")
    print(f"Order ID: {txn['order_id']}")
    print(f"Amount: {txn['amount']}")
    print(f"Customer Name: {txn['payee_name']}")
    print(f"Customer Email: {txn['payee_email']}")
    print(f"Customer Mobile: {txn['payee_mobile']}")
    print(f"Bank Ref: {txn['bank_ref_no']}")
    print(f"PG Txn ID: {txn['pg_txn_id']}")
    print(f"Status: {txn['status']}")
    print(f"Completed At: {txn['completed_at']}")
    print("-" * 80)
    
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
    
    # Prepare invoice data with unique email and mobile
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
    
    print("\n📤 DATA BEING SENT TO INVOICE API:")
    print("-" * 80)
    print(json.dumps(invoice_data, indent=2))
    print("-" * 80)
    
    # Send to invoice API
    print("\n🚀 SENDING REQUEST TO INVOICE API...")
    print(f"URL: https://api.truaxisventures.in/api/auto-order/create")
    
    try:
        response = requests.post(
            'https://api.truaxisventures.in/api/auto-order/create',
            json=invoice_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\n📥 RESPONSE STATUS: {response.status_code}")
        print("-" * 80)
        
        try:
            response_data = response.json()
            print("RESPONSE DATA:")
            print(json.dumps(response_data, indent=2))
        except:
            print("RESPONSE TEXT:")
            print(response.text)
        
        print("-" * 80)
        
        if response.status_code == 201 or (response.status_code == 200 and response_data.get('success')):
            print("\n✅ SUCCESS! Invoice created successfully")
            
            if response_data.get('order'):
                order = response_data['order']
                print(f"\n📋 ORDER DETAILS:")
                print(f"  Receipt Number: {order.get('receipt_number')}")
                print(f"  Order Number: {order.get('order_number')}")
                print(f"  Total Amount: {order.get('total_amount')}")
                
                if order.get('customer'):
                    customer = order['customer']
                    print(f"\n👤 CUSTOMER CREATED:")
                    print(f"  ID: {customer.get('id')}")
                    print(f"  Name: {customer.get('name')}")
                    print(f"  Email: {customer.get('email')}")
                    print(f"  Phone: {customer.get('phone')}")
        else:
            print(f"\n❌ FAILED! Status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST ERROR: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_invoice_api()
