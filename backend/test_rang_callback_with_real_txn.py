#!/usr/bin/env python3
"""
Test Rang callback with real transaction ID from database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import requests
from datetime import datetime

def get_latest_rang_transaction():
    """Get the latest Rang transaction for testing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, merchant_id, order_id, amount, status
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return txn
        
    except Exception as e:
        print(f"Error getting transaction: {e}")
        return None

def test_callback_with_real_txn():
    """Test callback with real transaction"""
    
    # Get latest Rang transaction
    txn = get_latest_rang_transaction()
    
    if not txn:
        print("❌ No Rang transactions found in database")
        print("   Create a Rang transaction first using the API")
        return
    
    print("=" * 80)
    print("TESTING RANG CALLBACK WITH REAL TRANSACTION")
    print("=" * 80)
    print(f"Found transaction:")
    print(f"  TXN ID: {txn['txn_id']}")
    print(f"  Order ID: {txn['order_id']}")
    print(f"  Merchant: {txn['merchant_id']}")
    print(f"  Amount: ₹{txn['amount']}")
    print(f"  Current Status: {txn['status']}")
    print()
    
    # Use the order_id as client_id (this is what Rang will send back)
    client_id = txn['order_id']  # This is the RefID we sent to Rang
    
    # Test callback URL
    callback_url = "http://localhost:5000/rang-payin-callback"
    
    # Simulate SUCCESS callback
    callback_data = {
        'status_id': '1',  # 1 = Success
        'amount': str(txn['amount']),
        'utr': 'TEST123456789',  # Test UTR
        'report_id': '12345',
        'client_id': client_id,  # Our RefID (order_id)
        'message': 'Payment success'
    }
    
    print(f"Sending callback to: {callback_url}")
    print(f"Callback data: {callback_data}")
    print()
    
    try:
        response = requests.post(
            callback_url,
            data=callback_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Callback processed successfully!")
            print("   Check the database to verify:")
            print("   - Transaction status updated to SUCCESS")
            print("   - UTR field populated")
            print("   - Merchant wallet credited")
            print("   - Admin wallet credited with charges")
        else:
            print(f"\n❌ Callback failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure Flask server is running")
        print("   Start server with: python3 app.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_callback_with_real_txn()