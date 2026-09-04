#!/usr/bin/env python3
"""
Manually sync Rang transaction status and trigger callback processing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from rang_service import RangService
from datetime import datetime
import json
import requests

def get_rang_transaction_by_order_id(order_id):
    """Get Rang transaction by order ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, status, 
                bank_ref_no, pg_txn_id, callback_url,
                created_at, completed_at
            FROM payin_transactions 
            WHERE order_id = %s AND pg_partner = 'Rang'
        """, (order_id,))
        
        transaction = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return transaction
        
    except Exception as e:
        print(f"❌ Error getting transaction: {e}")
        return None

def trigger_manual_callback(transaction, rang_status, rang_utr, rang_message):
    """Manually trigger callback processing"""
    try:
        print(f"\n🔄 TRIGGERING MANUAL CALLBACK...")
        
        # Map Rang status to callback format
        if str(rang_status).upper() in ['SUCCESS', 'COMPLETED', 'PAID']:
            status_id = '1'  # Success
        elif str(rang_status).upper() in ['FAILED', 'CANCELLED']:
            status_id = '3'  # Failed
        else:
            status_id = '2'  # Pending/Initiated
        
        # Prepare callback data
        callback_data = {
            'status_id': status_id,
            'amount': str(transaction['amount']),
            'utr': rang_utr or 'MANUAL_SYNC',
            'report_id': '12345',  # Dummy report ID
            'client_id': transaction['order_id'],  # Our RefID
            'message': rang_message or f'Manual sync - {rang_status}'
        }
        
        print(f"Callback data: {callback_data}")
        
        # Send to our callback endpoint
        callback_url = "https://api.moneyone.co.in/rang-payin-callback"
        
        response = requests.post(
            callback_url,
            data=callback_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        print(f"Callback response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print(f"✅ Manual callback processed successfully!")
            return True
        else:
            print(f"❌ Manual callback failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering manual callback: {e}")
        return False

def verify_transaction_update(order_id):
    """Verify that transaction was updated after callback"""
    try:
        print(f"\n🔍 VERIFYING TRANSACTION UPDATE...")
        
        transaction = get_rang_transaction_by_order_id(order_id)
        
        if transaction:
            print(f"Updated transaction status:")
            print(f"  TXN ID: {transaction['txn_id']}")
            print(f"  Status: {transaction['status']}")
            print(f"  UTR: {transaction['bank_ref_no'] or 'None'}")
            print(f"  PG TXN ID: {transaction['pg_txn_id'] or 'None'}")
            print(f"  Completed At: {transaction['completed_at'] or 'None'}")
            return transaction
        else:
            print(f"❌ Could not retrieve updated transaction")
            return None
            
    except Exception as e:
        print(f"❌ Error verifying update: {e}")
        return None

def main():
    print("RANG MANUAL STATUS SYNC")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get order ID from user
    order_id = input("Enter Rang Order ID (RefID) to sync: ").strip()
    
    if not order_id:
        print("❌ No Order ID provided")
        return
    
    # Get transaction from database
    print(f"\n📋 Getting transaction for Order ID: {order_id}")
    transaction = get_rang_transaction_by_order_id(order_id)
    
    if not transaction:
        print(f"❌ No Rang transaction found with Order ID: {order_id}")
        return
    
    print(f"✅ Found transaction:")
    print(f"  TXN ID: {transaction['txn_id']}")
    print(f"  Merchant: {transaction['merchant_id']}")
    print(f"  Amount: ₹{transaction['amount']}")
    print(f"  Current Status: {transaction['status']}")
    print(f"  Created: {transaction['created_at']}")
    
    # Check with Rang API
    print(f"\n🔍 Checking with Rang API...")
    
    try:
        rang_service = RangService()
        result = rang_service.check_payment_status(order_id)
        
        if not result['success']:
            print(f"❌ Rang API Error: {result.get('message', 'Unknown error')}")
            return
        
        rang_data = result['data']
        print(f"✅ Rang API Response:")
        print(f"{json.dumps(rang_data, indent=2)}")
        
        # Extract status information
        rang_status = rang_data.get('status', 'Unknown')
        rang_message = rang_data.get('message', '')
        rang_utr = rang_data.get('utr', rang_data.get('UTR', ''))
        
        print(f"\n📊 Status Comparison:")
        print(f"  Database: {transaction['status']}")
        print(f"  Rang: {rang_status}")
        
        if str(transaction['status']).upper() == str(rang_status).upper():
            print(f"✅ Status already matches - no sync needed")
            return
        
        print(f"⚠️ Status mismatch detected!")
        
        # Ask user if they want to sync
        sync_confirm = input(f"\nDo you want to sync status from Rang? (y/N): ").strip().lower()
        
        if sync_confirm != 'y':
            print("❌ Sync cancelled by user")
            return
        
        # Trigger manual callback
        success = trigger_manual_callback(transaction, rang_status, rang_utr, rang_message)
        
        if success:
            # Verify the update
            verify_transaction_update(order_id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 50)

if __name__ == "__main__":
    main()